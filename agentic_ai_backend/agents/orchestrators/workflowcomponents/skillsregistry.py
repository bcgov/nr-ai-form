"""Dispatcher prompt registry for tenant-aware orchestrator routing.

The dispatcher prompt and the form step intent mapper JSON are loaded from
tenant-specific Azure Blob Storage through request-scoped PromptSource. There is
no local-file fallback in production; the legacy local_rel_path argument is
ignored by PromptSource and kept only for API compatibility with older call sites.

The mapper (tenantResources.prompts.formMapper -> <dir>/stepmapper.json) is only
loaded when the tenant's dispatcher prompt references $mapper_json.

PromptSource caches orchestrator prompt blobs in memory using the tenant config
fingerprint, container, prompt path, and filename as the cache key. The cache TTL
is controlled by ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS, defaults to 300 seconds,
and can be set to 0 to disable prompt caching during active prompt development.
Static substitutions are still applied in one place before dispatcher LLM calls.
"""

import json
from dataclasses import dataclass
from string import Template

from workflowcomponents.promptsource import DEFAULT_PROMPT_SOURCE, PromptSource

FORM_SUPPORT_AGENT_ID = "FormSupportAgentA2A"
CONVERSATION_AGENT_ID = "ConversationAgentA2A"

FORM_MAPPER_PATH_KEY = "AGENT_FORM_MAPPER_PATH"
FORM_MAPPER_FILENAME = "stepmapper.json"


@dataclass(frozen=True)
class DispatcherSkill:
    """Prompt metadata used by the dispatcher.

    The Microsoft Agent Framework `Skill` type is abstract in newer versions.
    The dispatcher only needs prompt text for the chat-completions system
    message, so this local value object avoids binding routing to framework
    internals that are not used by the workflow.
    """

    name: str
    description: str
    content: str


def _form_step_intent_mapper_json(source: PromptSource) -> str:
    raw = source.load_prompt(
        blob_path_env=FORM_MAPPER_PATH_KEY,
        blob_filename=FORM_MAPPER_FILENAME,
        local_rel_path=f"stepmapper/{FORM_MAPPER_FILENAME}",
    )
    try:
        return json.dumps(json.loads(raw), indent=2)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Form step intent mapper {FORM_MAPPER_FILENAME} is not valid JSON: {exc}") from exc


def _dispatcher_content(prompt_source: PromptSource | None = None) -> str:
    source = prompt_source or DEFAULT_PROMPT_SOURCE
    raw = source.load_prompt(
        blob_path_env="AGENT_DISPATCHER_PROMPTS_PATH",
        blob_filename="system.md",
        local_rel_path="dispatcher/system.md",
    )
    substitutions = {
        "form_support_agent_id": FORM_SUPPORT_AGENT_ID,
        "conversation_agent_id": CONVERSATION_AGENT_ID,
    }
    # Only tenants whose dispatcher prompt embeds the mapper need it configured.
    if "mapper_json" in raw:
        substitutions["mapper_json"] = _form_step_intent_mapper_json(source)
    return Template(raw).safe_substitute(**substitutions)


def get_dispatcher_skill(prompt_source: PromptSource | None = None) -> DispatcherSkill:
    return DispatcherSkill(
        name="dispatcher-intent",
        description=(
            "Intent classifier for the BC water permit orchestrator. Decides whether to "
            "route the user query to FormSupportAgentA2A, ConversationAgentA2A, or both, "
            "with a 0-10 confidence score per agent. Also flags fixed out-of-scope/edge-case "
            "categories (see EdgeCaseCategory) that bypass sub-agent routing entirely."
        ),
        content=_dispatcher_content(prompt_source),
    )
