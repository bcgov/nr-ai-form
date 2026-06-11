"""Skill registry backed by Microsoft Agent Framework's SkillsProvider.

The dispatcher prompt lives as `skills/dispatcher/system.md` and is fetched from
Azure Blob Storage when configured (see `promptsource.load_prompt`), falling back
to that bundled local copy. Static substitutions (sub-agent IDs, the form-step
intent mapper) are baked into the skill body. The resulting `Skill` is registered
on a `SkillsProvider` that the dispatcher attaches to its agent so the LLM
discovers and loads it via the framework's `load_skill` tool at runtime.

The skill is built lazily (`get_dispatcher_skill`) rather than at import time:
this module is imported before `load_dotenv()` runs in the entry points, so the
blob credentials are only reliably present once a prompt is first requested.
"""

import json
from functools import lru_cache
from pathlib import Path
from string import Template

from agent_framework import Skill, SkillsProvider

from workflowcomponents.promptsource import load_prompt

FORM_SUPPORT_AGENT_ID = "FormSupportAgentA2A"
CONVERSATION_AGENT_ID = "ConversationAgentA2A"

_FORM_MAPPER_PATH = Path(__file__).with_name("formstepsintendmapper.json")


@lru_cache(maxsize=1)
def _form_step_intent_mapper_json() -> str:
    with _FORM_MAPPER_PATH.open("r", encoding="utf-8") as mapper_file:
        return json.dumps(json.load(mapper_file), indent=2)


@lru_cache(maxsize=1)
def _dispatcher_content() -> str:
    raw = load_prompt(
        blob_path_env="AGENT_DISPATCHER_PROMPTS_PATH",
        blob_filename="system.md",
        local_rel_path="dispatcher/system.md",
    )
    return Template(raw).safe_substitute(
        form_support_agent_id=FORM_SUPPORT_AGENT_ID,
        conversation_agent_id=CONVERSATION_AGENT_ID,
        mapper_json=_form_step_intent_mapper_json(),
    )


@lru_cache(maxsize=1)
def get_dispatcher_skill() -> Skill:
    return Skill(
        name="dispatcher-intent",
        description=(
            "Intent classifier for the BC water permit orchestrator. Decides whether to "
            "route the user query to FormSupportAgentA2A, ConversationAgentA2A, or both, "
            "with a 0-10 confidence score per agent."
        ),
        content=_dispatcher_content(),
    )


@lru_cache(maxsize=1)
def get_skills_provider() -> SkillsProvider:
    return SkillsProvider(skills=[get_dispatcher_skill()])
