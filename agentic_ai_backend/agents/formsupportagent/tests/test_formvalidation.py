"""Tests for the LLM-backed form validation path.

The LLM client is stubbed rather than mocked at the HTTP layer, in the spirit of the
orchestrator's StubDispatcher/StubWorker tests: feed the structured-output model directly and
assert on what the server-side sanitizer does with it.
"""

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# The agent modules use absolute `agents.formsupportagent.*` imports, so the backend root has
# to be importable the same way the server bootstraps it.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from agents.formsupportagent.formvalidation import validator as validator_module
from agents.formsupportagent.formvalidation.fieldvisibility import (
    build_field_payload,
    is_field_visible,
    resolve_validatable_fields,
)
from agents.formsupportagent.formvalidation.validator import validate_step
from agents.formsupportagent.models.formvalidationmodel import LlmIssue, LlmIssueList
from agents.formsupportagent.services.localformdefinitionservice import (
    LocalFormDefinitionService,
    normalize_fields,
)

_DEFINITIONS = Path(__file__).resolve().parent.parent / "formdefinitions"


def _load(step: str) -> dict:
    with open(_DEFINITIONS / f"{step}.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


class NormalizeFieldsTests(unittest.TestCase):
    def test_formfields_key(self):
        fields = normalize_fields(_load("step2-Eligibility"))
        self.assertIn("AnswerOnJob_eligible", fields)
        self.assertEqual(fields["AnswerOnJob_eligible"]["type"], "radio")

    def test_legacy_properties_dict(self):
        fields = normalize_fields({"properties": {"A": {"type": "text", "id": "A"}}})
        self.assertEqual(list(fields), ["A"])

    def test_legacy_properties_list_uses_id(self):
        fields = normalize_fields({"properties": [{"id": "B", "type": "text"}]})
        self.assertEqual(list(fields), ["B"])

    def test_every_committed_definition_normalizes(self):
        # Guards against a new definition arriving in a shape we don't understand.
        for path in _DEFINITIONS.glob("*.json"):
            with self.subTest(definition=path.name):
                with open(path, "r", encoding="utf-8") as handle:
                    self.assertIsInstance(normalize_fields(json.load(handle)), dict)


class VisibilityTests(unittest.TestCase):
    def test_flat_equals_hides_field(self):
        fields = normalize_fields(_load("step4-Location-Land-Details"))
        pid = fields["ParcelIdentifierPID"]
        self.assertTrue(is_field_visible(pid, {"LandOwnershipCategory": "Private Land"}))
        self.assertFalse(is_field_visible(pid, {"LandOwnershipCategory": "Provincial Crown Land"}))

    def test_in_operator(self):
        fields = normalize_fields(_load("step4-Location-Land-Details"))
        metes = fields["MetesAndBounds"]
        self.assertTrue(is_field_visible(metes, {"LandOwnershipCategory": "Other"}))
        self.assertFalse(is_field_visible(metes, {"LandOwnershipCategory": "Private Land"}))

    def test_compound_all_uses_field_spelling(self):
        fields = normalize_fields(_load("step3-Technical-Information-Works"))
        status = fields["Status_Access Road"]
        self.assertTrue(is_field_visible(status, {"Selected_Access_Road": "Y"}))
        self.assertFalse(is_field_visible(status, {"Selected_Access_Road": "N"}))

    def test_unresolvable_conditions_fail_open(self):
        # Referenced field absent from form_data.
        absent = {"visibleIf": {"formField": "Missing", "operator": "equals", "value": "Y"}}
        self.assertTrue(is_field_visible(absent, {}))

        # Operator we don't implement.
        unknown_op = {"visibleIf": {"formField": "A", "operator": "matches", "value": "Y"}}
        self.assertTrue(is_field_visible(unknown_op, {"A": "Y"}))

        # Inter-step condition, unresolvable from a single-step payload.
        cross_step = {
            "visibleIf": {
                "all": [
                    {
                        "stepNumber": "step3-Technical-Information-Works",
                        "formField": "Selected_Dam",
                        "operator": "equals",
                        "value": "Y",
                    }
                ]
            }
        }
        self.assertTrue(is_field_visible(cross_step, {"Selected_Dam": "N"}))

    def test_case_and_whitespace_insensitive(self):
        field = {"visibleIf": {"formField": "A", "operator": "equals", "value": "Private Land"}}
        self.assertTrue(is_field_visible(field, {"A": "  private land "}))


class ValidatableFieldTests(unittest.TestCase):
    def test_blank_and_non_data_fields_excluded(self):
        definition = {
            "formfields": {
                "Answered": {"type": "text", "id": "Answered", "title": "t"},
                "Blank": {"type": "text", "id": "Blank", "title": "t"},
                "Whitespace": {"type": "text", "id": "Whitespace", "title": "t"},
                "Continue": {"type": "button", "id": "Continue", "title": "t"},
                "Locked": {"type": "text", "id": "Locked", "title": "t", "readOnly": True},
            }
        }
        data = {
            "Answered": "something",
            "Blank": "",
            "Whitespace": "   ",
            "Continue": "click",
            "Locked": "value",
        }
        self.assertEqual(list(resolve_validatable_fields(definition, data)), ["Answered"])

    def test_unchecked_checkboxes_excluded(self):
        definition = {
            "formfields": {
                "On": {"type": "checkbox", "id": "On", "title": "t"},
                "Off": {"type": "checkbox", "id": "Off", "title": "t"},
                "Mapped": {
                    "type": "boolean",
                    "id": "Mapped",
                    "title": "t",
                    "valueMap": {"true": "Y", "false": "N"},
                },
                "Explicit": {"type": "checkbox", "id": "Explicit", "title": "t", "falseValue": "0"},
            }
        }
        data = {"On": "Y", "Off": "N", "Mapped": "N", "Explicit": "0"}
        self.assertEqual(list(resolve_validatable_fields(definition, data)), ["On"])

    def test_value_resolves_by_key_or_id(self):
        # A few definitions give a field a dict key and an `id` that differ.
        definition = {
            "formfields": {"TotalAnnualQuantity": {"type": "number", "id": "Quantity", "title": "t"}}
        }
        by_id = resolve_validatable_fields(definition, {"Quantity": 42})
        self.assertEqual(list(by_id), ["TotalAnnualQuantity"])
        by_key = resolve_validatable_fields(definition, {"TotalAnnualQuantity": 42})
        self.assertEqual(list(by_key), ["TotalAnnualQuantity"])

    def test_payload_carries_units_and_bounds(self):
        definition = {
            "formfields": {
                "Q": {
                    "type": "number",
                    "id": "Q",
                    "title": "Quantity",
                    "units": "m3/day",
                    "min": 0,
                    "max": 100,
                }
            }
        }
        fields = resolve_validatable_fields(definition, {"Q": 5})
        entry = build_field_payload(fields, {"Q": 5})[0]
        self.assertEqual(entry["units"], "m3/day")
        self.assertEqual(entry["max"], 100)
        self.assertEqual(entry["id"], "Q")

    def test_hidden_fields_never_reach_the_payload(self):
        definition = _load("step4-Location-Land-Details")
        data = {"LandOwnershipCategory": "Provincial Crown Land", "ParcelIdentifierPID": "012345678"}
        self.assertNotIn("ParcelIdentifierPID", resolve_validatable_fields(definition, data))


class LocalFormDefinitionServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = LocalFormDefinitionService()

    def test_loads_committed_definition(self):
        self.assertIsNotNone(self.service.fetch_form_definition("step2-Eligibility.json"))
        self.assertIsNotNone(self.service.fetch_form_definition("step2-Eligibility"))

    def test_rejects_path_traversal(self):
        for unsafe in ("../../../etc/passwd", "step2/../../x", "..\\..\\secrets", "a/b", ""):
            with self.subTest(step=unsafe):
                self.assertIsNone(self.service.fetch_form_definition(unsafe))

    def test_missing_definition_returns_none(self):
        self.assertIsNone(self.service.fetch_form_definition("step999-Nope"))


class _StubCompletion:
    """Mimics the shape validate_step reads: completion.choices[0].message.parsed."""

    def __init__(self, parsed):
        message = type("Message", (), {"parsed": parsed})()
        choice = type("Choice", (), {"message": message})()
        self.choices = [choice]


def _stub_client(result=None, exc=None, delay=0.0):
    async def parse(**_kwargs):
        if delay:
            await asyncio.sleep(delay)
        if exc is not None:
            raise exc
        return _StubCompletion(result)

    completions = type("Completions", (), {"parse": staticmethod(parse)})()
    chat = type("Chat", (), {"completions": completions})()
    return type("Client", (), {"chat": chat})()


_DEFINITION = {
    "formName": "Test step",
    "formfields": {
        "Explanation": {"type": "textarea", "id": "Explanation", "title": "Explain"},
        "Category": {
            "type": "radio",
            "id": "Category",
            "title": "Category",
            "enum": ["Private Land", "Other"],
        },
    },
}
_DATA = {"Explanation": "n/a", "Category": "Private Land"}


class ValidateStepTests(unittest.TestCase):
    def _run(self, client, parsed_issues=None):
        with patch.object(
            validator_module, "_get_or_create_client", return_value=(client, "gpt-test")
        ):
            return asyncio.run(validate_step("step-test", _DEFINITION, _DATA))

    def test_happy_path(self):
        client = _stub_client(
            LlmIssueList(
                issues=[
                    LlmIssue(
                        fieldId="Explanation",
                        severity="warning",
                        message="This explanation is very brief.",
                    )
                ]
            )
        )
        issues, status = self._run(client)
        self.assertEqual(status, "ok")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].fieldId, "Explanation")
        self.assertEqual(issues[0].stepId, "step-test")

    def test_unknown_field_id_dropped(self):
        client = _stub_client(
            LlmIssueList(
                issues=[LlmIssue(fieldId="NotAField", severity="info", message="Hmm.")]
            )
        )
        issues, status = self._run(client)
        self.assertEqual(status, "ok")
        self.assertEqual(issues, [])

    def test_duplicate_field_deduped_and_cap_enforced(self):
        client = _stub_client(
            LlmIssueList(
                issues=[
                    LlmIssue(fieldId="Explanation", severity="info", message="One."),
                    LlmIssue(fieldId="Explanation", severity="info", message="Two."),
                    LlmIssue(fieldId="Category", severity="info", message="Three."),
                ]
            )
        )
        issues, _ = self._run(client)
        self.assertEqual([i.fieldId for i in issues], ["Explanation", "Category"])

    def test_long_message_truncated(self):
        client = _stub_client(
            LlmIssueList(
                issues=[LlmIssue(fieldId="Explanation", severity="info", message="x" * 500)]
            )
        )
        issues, _ = self._run(client)
        self.assertEqual(len(issues[0].message), 300)

    def test_suggested_value_outside_enum_stripped(self):
        client = _stub_client(
            LlmIssueList(
                issues=[
                    LlmIssue(
                        fieldId="Category",
                        severity="info",
                        message="Consider this.",
                        suggestedValue="Crown Land",
                    )
                ]
            )
        )
        issues, _ = self._run(client)
        self.assertIsNone(issues[0].suggestedValue)

    def test_suggested_value_inside_enum_kept(self):
        client = _stub_client(
            LlmIssueList(
                issues=[
                    LlmIssue(
                        fieldId="Category",
                        severity="info",
                        message="Consider this.",
                        suggestedValue="Other",
                    )
                ]
            )
        )
        issues, _ = self._run(client)
        self.assertEqual(issues[0].suggestedValue, "Other")

    def test_llm_exception_degrades_silently(self):
        issues, status = self._run(_stub_client(exc=RuntimeError("429 rate limited")))
        self.assertEqual((issues, status), ([], "unavailable"))

    def test_parsed_none_degrades_silently(self):
        issues, status = self._run(_stub_client(result=None))
        self.assertEqual((issues, status), ([], "unavailable"))

    def test_timeout_degrades_silently(self):
        client = _stub_client(LlmIssueList(issues=[]), delay=0.2)
        with patch.object(validator_module, "_VALIDATION_TIMEOUT_SECONDS", 0.01):
            issues, status = self._run(client)
        self.assertEqual((issues, status), ([], "unavailable"))

    def test_unconfigured_client_degrades_silently(self):
        with patch.object(validator_module, "_get_or_create_client", return_value=(None, None)):
            issues, status = asyncio.run(validate_step("step-test", _DEFINITION, _DATA))
        self.assertEqual((issues, status), ([], "unavailable"))

    def test_no_validatable_fields_skips_llm_and_reports_ok(self):
        def _explode(*_a, **_k):
            raise AssertionError("LLM must not be called when there is nothing to validate")

        with patch.object(validator_module, "_get_or_create_client", _explode):
            issues, status = asyncio.run(validate_step("step-test", _DEFINITION, {}))
        self.assertEqual((issues, status), ([], "ok"))


if __name__ == "__main__":
    unittest.main()
