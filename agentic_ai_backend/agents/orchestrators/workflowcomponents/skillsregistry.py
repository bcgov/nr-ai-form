"""Skill registry backed by Microsoft Agent Framework's SkillsProvider.

The dispatcher prompt lives as `skills/dispatcher/system.md`. Static
substitutions (sub-agent IDs, the form-step intent mapper) are baked into the
skill body at module load. The resulting `Skill` is registered on a
`SkillsProvider` that the dispatcher attaches to its agent so the LLM
discovers and loads it via the framework's `load_skill` tool at runtime.
"""

import json
from functools import lru_cache
from pathlib import Path
from string import Template

from agent_framework import Skill, SkillsProvider

FORM_SUPPORT_AGENT_ID = "FormSupportAgentA2A"
CONVERSATION_AGENT_ID = "ConversationAgentA2A"

_SKILLS_DIR = Path(__file__).parent / "skills"
_FORM_MAPPER_PATH = Path(__file__).with_name("formstepsintendmapper.json")


def _load_md(rel_path: str) -> str:
    return (_SKILLS_DIR / rel_path).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _form_step_intent_mapper_json() -> str:
    with _FORM_MAPPER_PATH.open("r", encoding="utf-8") as mapper_file:
        return json.dumps(json.load(mapper_file), indent=2)


_dispatcher_content = Template(_load_md("dispatcher/system.md")).safe_substitute(
    form_support_agent_id=FORM_SUPPORT_AGENT_ID,
    conversation_agent_id=CONVERSATION_AGENT_ID,
    mapper_json=_form_step_intent_mapper_json(),
)


DISPATCHER_INTENT_SKILL = Skill(
    name="dispatcher-intent",
    description=(
        "Intent classifier for the BC water permit orchestrator. Decides whether to "
        "route the user query to FormSupportAgentA2A, ConversationAgentA2A, or both, "
        "with a 0-10 confidence score per agent."
    ),
    content=_dispatcher_content,
)

skills_provider = SkillsProvider(skills=[DISPATCHER_INTENT_SKILL])
