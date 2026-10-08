import json
import unittest
from pathlib import Path

from clientprofiles import ClientProfile
from clientprofiles.settings import build_tenant_agent_settings
from workflowcomponents.promptsource import PromptSource
from workflowcomponents.skillsregistry import (
    FORM_MAPPER_FILENAME,
    FORM_MAPPER_PATH_KEY,
    get_dispatcher_skill,
)

SEED_FILE = Path(__file__).resolve().parents[3] / "clientprofiles" / "seed" / "client_profiles.json"
MAPPER = [{"stepIdentifier": "step2-Eligibility", "shortDescription": "Eligibility", "intentTags": ["eligible"]}]


class StubPromptSource(PromptSource):
    """PromptSource that serves blobs from a dict keyed by (path key, filename)."""

    def __init__(self, blobs: dict[tuple[str, str], str], prompt_directories: dict[str, str]):
        super().__init__(prompt_directories=prompt_directories)
        object.__setattr__(self, "blobs", blobs)
        object.__setattr__(self, "requested", [])

    def load_prompt(self, blob_path_env, blob_filename, local_rel_path):
        self.requested.append((blob_path_env, blob_filename))
        if blob_path_env not in self.prompt_directories:
            raise RuntimeError(f"Orchestrator prompt blob config is required for {blob_filename}.")
        return self.blobs[(blob_path_env, blob_filename)]


def _source(dispatcher_prompt: str, mapper: str | None = None) -> StubPromptSource:
    blobs = {("AGENT_DISPATCHER_PROMPTS_PATH", "system.md"): dispatcher_prompt}
    directories = {"AGENT_DISPATCHER_PROMPTS_PATH": "tenants/t/agentprompts/dispatcher"}
    if mapper is not None:
        blobs[(FORM_MAPPER_PATH_KEY, FORM_MAPPER_FILENAME)] = mapper
        directories[FORM_MAPPER_PATH_KEY] = "tenants/t/stepmapper"
    return StubPromptSource(blobs, directories)


class DispatcherMapperTests(unittest.TestCase):
    def test_mapper_is_loaded_from_blob_and_substituted(self):
        source = _source("Agents: $form_support_agent_id\n$mapper_json", json.dumps(MAPPER))

        content = get_dispatcher_skill(source).content

        self.assertIn("FormSupportAgentA2A", content)
        self.assertIn(json.dumps(MAPPER, indent=2), content)
        self.assertIn((FORM_MAPPER_PATH_KEY, FORM_MAPPER_FILENAME), source.requested)

    def test_mapper_not_loaded_when_prompt_does_not_reference_it(self):
        source = _source("Agents: $conversation_agent_id")

        content = get_dispatcher_skill(source).content

        self.assertEqual(content, "Agents: ConversationAgentA2A")
        self.assertNotIn((FORM_MAPPER_PATH_KEY, FORM_MAPPER_FILENAME), source.requested)

    def test_referenced_but_unconfigured_mapper_fails_fast(self):
        with self.assertRaisesRegex(RuntimeError, FORM_MAPPER_FILENAME):
            get_dispatcher_skill(_source("$mapper_json"))

    def test_invalid_mapper_json_fails_fast(self):
        with self.assertRaisesRegex(RuntimeError, "not valid JSON"):
            get_dispatcher_skill(_source("$mapper_json", "{not json"))


class FormMapperProfileTests(unittest.TestCase):
    def test_form_mapper_flows_from_profile_to_prompt_directories(self):
        with SEED_FILE.open(encoding="utf-8") as seed:
            profiles = {p["clientId"]: p for p in json.load(seed)}

        water = build_tenant_agent_settings(
            ClientProfile.model_validate(profiles["11111111-1111-4111-8111-111111111111"])
        )

        self.assertEqual(
            water.orchestrator_prompts.prompt_directories[FORM_MAPPER_PATH_KEY],
            "tenants/water/stepmapper",
        )


if __name__ == "__main__":
    unittest.main()
