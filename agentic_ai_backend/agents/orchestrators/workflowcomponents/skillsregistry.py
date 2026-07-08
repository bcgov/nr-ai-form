"""Skill registry backed by Microsoft Agent Framework's SkillsProvider.

The dispatcher prompt is loaded from tenant-specific Azure Blob Storage through
request-scoped PromptSource. There is no local-file fallback in production; the
legacy local_rel_path argument is ignored by PromptSource and kept only for API
compatibility with older call sites.

PromptSource caches orchestrator prompt blobs in memory using the tenant config
fingerprint, container, prompt path, and filename as the cache key. The cache TTL
is controlled by ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS, defaults to 300 seconds,
and can be set to 0 to disable prompt caching during active prompt development.
Static substitutions are still applied in one place before creating the Skill.
"""

import json
from functools import lru_cache
from pathlib import Path
from string import Template

from agent_framework import Skill, SkillsProvider

from workflowcomponents.promptsource import DEFAULT_PROMPT_SOURCE, PromptSource

FORM_SUPPORT_AGENT_ID = "FormSupportAgentA2A"
CONVERSATION_AGENT_ID = "ConversationAgentA2A"

_FORM_MAPPER_PATH = Path(__file__).with_name("formstepsintendmapper.json")


@lru_cache(maxsize=1)
def _form_step_intent_mapper_json() -> str:
    with _FORM_MAPPER_PATH.open("r", encoding="utf-8") as mapper_file:
        return json.dumps(json.load(mapper_file), indent=2)


def _dispatcher_content(prompt_source: PromptSource | None = None) -> str:
    source = prompt_source or DEFAULT_PROMPT_SOURCE
    raw = source.load_prompt(
        blob_path_env="AGENT_DISPATCHER_PROMPTS_PATH",
        blob_filename="system.md",
        local_rel_path="dispatcher/system.md",
    )
    return Template(raw).safe_substitute(
        form_support_agent_id=FORM_SUPPORT_AGENT_ID,
        conversation_agent_id=CONVERSATION_AGENT_ID,
        mapper_json=_form_step_intent_mapper_json(),
    )


def get_dispatcher_skill(prompt_source: PromptSource | None = None) -> Skill:
    return Skill(
        name="dispatcher-intent",
        description=(
            "Intent classifier for the BC water permit orchestrator. Decides whether to "
            "route the user query to FormSupportAgentA2A, ConversationAgentA2A, or both, "
            "with a 0-10 confidence score per agent."
        ),
        content=_dispatcher_content(prompt_source),
    )


def get_skills_provider(prompt_source: PromptSource | None = None) -> SkillsProvider:
    return SkillsProvider(skills=[get_dispatcher_skill(prompt_source)])
