"""Resolve which fields of a step are actually on screen, and which are worth validating.

Hidden fields must never reach the model: an applicant cannot be asked about an answer the
form never showed them. Everything here is deliberately fail-open - when a condition cannot
be evaluated we treat the field as visible, because over-including a field costs a few prompt
tokens while under-including one silently drops a real answer.
"""

import logging
from typing import Any, Dict, Optional

from agents.formsupportagent.services.localformdefinitionservice import (
    NON_DATA_FIELD_TYPES,
    normalize_fields,
)

logger = logging.getLogger(__name__)

# Condition operators seen in the committed definitions. Anything else is unresolvable.
_SUPPORTED_OPERATORS = frozenset({"equals", "in"})

# Checkbox/boolean "off" markers. These are present values that carry nothing to assess.
_FALSEY_MARKERS = frozenset({"n", "false", "no", "off", "0", "unchecked"})


def _as_comparable(value: Any) -> str:
    return str(value).strip().casefold()


def field_value(field_key: str, field: Dict[str, Any], form_data: Dict[str, Any]) -> Any:
    """Look a field's answer up by dict key, falling back to the field's own id.

    A handful of definitions give a field a dict key and an ``id`` that differ (for example
    key ``TotalAnnualQuantity`` with ``"id": "Quantity"``). The frontend captures by the
    rendered element's data-id, so either spelling may turn up in form_data.
    """
    if field_key in form_data:
        return form_data[field_key]
    field_id = field.get("id")
    if field_id and field_id in form_data:
        return form_data[field_id]
    return None


def _condition_field_name(condition: Dict[str, Any]) -> Optional[str]:
    # Flat conditions spell it `formField`; `all`-wrapped ones spell it `field`. Both occur.
    name = condition.get("formField") or condition.get("field")
    return str(name) if name else None


def _evaluate_condition(condition: Dict[str, Any], form_data: Dict[str, Any]) -> Optional[bool]:
    """Evaluate one condition. Returns None when it cannot be resolved."""
    if not isinstance(condition, dict):
        return None

    # A condition naming another step is an inter-step dependency. A single-step payload has
    # no answers from that step, so this is unresolvable by construction.
    if condition.get("stepNumber"):
        return None

    name = _condition_field_name(condition)
    if not name or name not in form_data:
        return None

    operator = str(condition.get("operator") or "").strip().casefold()
    if operator not in _SUPPORTED_OPERATORS:
        return None

    actual = _as_comparable(form_data[name])
    expected = condition.get("value")

    if operator == "equals":
        return actual == _as_comparable(expected)

    # "in": the expected side is a list of acceptable values.
    if isinstance(expected, (list, tuple, set)):
        return actual in {_as_comparable(item) for item in expected}
    return actual == _as_comparable(expected)


def is_field_visible(field: Dict[str, Any], form_data: Dict[str, Any]) -> bool:
    """Evaluate a field's ``visibleIf``, defaulting to visible whenever it cannot be resolved."""
    rule = field.get("visibleIf")
    if not isinstance(rule, dict):
        return True

    conditions = rule.get("all")
    if isinstance(conditions, list):
        # `all` is an AND. An unresolvable member must not veto the others, but neither can it
        # confirm them, so we only hide when something resolves cleanly to False.
        for condition in conditions:
            if _evaluate_condition(condition, form_data) is False:
                return False
        return True

    return _evaluate_condition(rule, form_data) is not False


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def _is_unchecked(field: Dict[str, Any], value: Any) -> bool:
    """True for a checkbox/boolean sitting in its 'off' state.

    These are present values with nothing to assess, and they would otherwise swamp a step
    like step3-Technical-Information-Works, which is almost entirely checkboxes.
    """
    if str(field.get("type") or "").casefold() not in ("checkbox", "boolean"):
        return False
    if value is False:
        return True

    comparable = _as_comparable(value)
    false_value = field.get("falseValue")
    if false_value is not None and comparable == _as_comparable(false_value):
        return True
    value_map = field.get("valueMap")
    if isinstance(value_map, dict) and "false" in value_map:
        if comparable == _as_comparable(value_map["false"]):
            return True
    return comparable in _FALSEY_MARKERS


def resolve_validatable_fields(
    form_definition: Optional[Dict[str, Any]],
    form_data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Return the fields that should be sent to the model, keyed by their identifier.

    Drops, in order: fields hidden by ``visibleIf``; field types that hold no answer;
    read-only fields; blank answers (missingness is the form engine's job, and neither
    plausibility nor completeness is defined for an empty value); and unchecked checkboxes.
    """
    fields = normalize_fields(form_definition)
    if not fields:
        return {}

    validatable: Dict[str, Dict[str, Any]] = {}
    for key, field in fields.items():
        if str(field.get("type") or "").casefold() in NON_DATA_FIELD_TYPES:
            continue
        if field.get("readOnly"):
            continue
        if not is_field_visible(field, form_data):
            continue

        value = field_value(key, field, form_data)
        if _is_blank(value) or _is_unchecked(field, value):
            continue

        validatable[key] = field

    return validatable


def build_field_payload(
    fields: Dict[str, Dict[str, Any]],
    form_data: Dict[str, Any],
) -> list[Dict[str, Any]]:
    """Shape the surviving fields into the compact list handed to the model.

    ``units``/``min``/``max`` are carried through deliberately - they are what makes a
    plausibility judgement possible on a quantity field.
    """
    payload = []
    for key, field in fields.items():
        entry: Dict[str, Any] = {
            "id": key,
            "title": field.get("title"),
            "description": field.get("description"),
            "type": field.get("type"),
            "value": field_value(key, field, form_data),
        }
        for optional_key in ("enum", "maxLength", "units", "min", "max"):
            if field.get(optional_key) is not None:
                entry[optional_key] = field[optional_key]
        payload.append({k: v for k, v in entry.items() if v is not None})
    return payload
