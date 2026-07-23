"""
Orchestrator Agent using A2A protocol
This version uses A2A to communicate with remote agents instead of direct imports.
"""
import ast
import logging
import os
from agent_framework import WorkflowBuilder
from agent_framework._workflows._message_utils import normalize_messages_input
from typing import Any, Union, Optional
from dotenv import load_dotenv
import uuid


from threadmanagement.redisdbutils import redisdbutils

# Import A2A executors
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.aggregator import Aggregator
from workflowcomponents.promptsource import PromptSource
from workflowcomponents.routing import get_primary_intent, select_subagents
from clientprofiles import TenantAgentSettings
from models.intentmodel import IntentListModel

CONVERSATION_AGENT_COSMOS_NAME = "conversationAgent"
FORM_SUPPORT_AGENT_COSMOS_NAME = "formSupportAgent"

logger = logging.getLogger(__name__)

def _select_target_executors(intent_list: Any, target_ids: list[str]) -> list[str]:
    """Pick which sub-agent executors should run for a given dispatcher classification.

    - If any intent is at or above the high-confidence threshold, route only to those
      agents (one or both, depending on the IntentListModel).
    - If nothing crosses the threshold, route to the highest-confidence agent, but
      only if that agent is enabled for this tenant.
    """
    if not isinstance(intent_list, IntentListModel):
        return list(target_ids)

    high_conf = select_subagents(intent_list)
    if high_conf:
        wanted = {intent.targetagent for intent in high_conf}
    else:
        wanted = {get_primary_intent(intent_list).targetagent}

    selected = [tid for tid in target_ids if tid in wanted]
    # Defense-in-depth: Dispatcher is tenant-aware, but this workflow edge group
    # is the final boundary before executor fan-out. Keep this guard so a bad
    # LLM classification, legacy dispatcher construction, or future routing bug
    # cannot execute an agent disabled for the tenant.
    if not selected:
        raise RuntimeError(
            f"Invalid routing state: selected agent(s) are not enabled for this tenant. "
            f"Selected agent(s): {sorted(wanted)}. Enabled agent(s): {target_ids}."
        )
    return selected

load_dotenv()

# Global Redis Utils instance
_redis_utils_instance = None

def get_redis_utils():
    global _redis_utils_instance
    if _redis_utils_instance is None:
        _redis_utils_instance = redisdbutils()
    return _redis_utils_instance


def _parse_workflow_result_text(result_text: str) -> list[dict]:
    """Normalize workflow text output into a list of payload dicts."""
    if not result_text:
        return []

    try:
        parsed = ast.literal_eval(result_text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return [parsed]
    except (SyntaxError, ValueError):
        parsed_items = [
            ast.literal_eval(literal_text)
            for literal_text in _split_top_level_literals(result_text)
        ]

        normalized_items: list[dict] = []
        for item in parsed_items:
            if isinstance(item, list):
                normalized_items.extend(item)
            else:
                normalized_items.append(item)

        return normalized_items


def _split_top_level_literals(result_text: str) -> list[str]:
    literals: list[str] = []
    start_index: int | None = None
    depth = 0
    in_string = False
    quote_char = ""
    escape_next = False

    for index, char in enumerate(result_text):
        if start_index is None:
            if char.isspace():
                continue
            start_index = index

        if in_string:
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == quote_char:
                in_string = False
            continue

        if char in {"'", '"'}:
            in_string = True
            quote_char = char
            continue

        if char in "{[(":
            depth += 1
            continue

        if char in "}])":
            depth -= 1
            if depth == 0 and start_index is not None:
                literals.append(result_text[start_index : index + 1].strip())
                start_index = None

    return literals

async def orchestrate_a2a(query: str,
                          conversation_agent_url: str = "http://localhost:8000",
                          form_support_agent_url: str = "http://localhost:8001",
                          step_number: Union[int, str, None] = None,
                          session_id: Optional[str] = None,
                          *,
                          tenant_settings: TenantAgentSettings):
    """
    Orchestrate using A2A protocol to communicate with remote agents.

    Args:
        query: User query to process
        conversation_agent_url: Base URL of the Conversation Agent A2A server
        form_support_agent_url: Base URL of the Form Support Agent A2A server
        step_number: Form step number for the Form Support Agent (default: 2)
        session_id: Optional session ID for thread persistence
        tenant_settings: Validated tenant settings resolved at the gateway boundary
    """

    effective_session_id = session_id or str(uuid.uuid4())


    runtime_settings = tenant_settings.orchestrator_runtime
    effective_step_number = step_number or runtime_settings.formStepNumber
    a2a_timeout_seconds = runtime_settings.a2aClientTimeoutSeconds

    orchestrator_prompts = tenant_settings.orchestrator_prompts
    prompt_source = PromptSource(
        connection_string=os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING"),
        container_name=os.getenv("AZURE_BLOBSTORAGE_CONTAINER"),
        prompt_directories=orchestrator_prompts.prompt_directories,
        cache_namespace=tenant_settings.config_fingerprint,
    )

    conversation_agent_enabled = tenant_settings.conversation.enabled if tenant_settings.conversation else None
    form_support_agent_enabled = tenant_settings.form_support.enabled if tenant_settings.form_support else None

    # Option 1: orchestrator owns durable session state in Redis and forwards a
    # curated slice of the conversation to the stateless sub-agents.
    db_utils = get_redis_utils()
    prior_history = await db_utils.get_history_turns(effective_session_id)

    executors = []
    if conversation_agent_enabled:
        conversation_settings = tenant_settings.conversation
        # Create A2A executors
        conversation_executor = ConversationAgentA2AExecutor(
            base_url=conversation_agent_url,
            session_id=effective_session_id,
            client_settings=conversation_settings,
            timeout=a2a_timeout_seconds
        )
        executors.append(conversation_executor)

    if form_support_agent_enabled:
        form_support_settings = tenant_settings.form_support
        # Create A2A executors
        form_support_executor = FormSupportAgentA2AExecutor(
            base_url=form_support_agent_url,
            step_number=effective_step_number,
            session_id=effective_session_id,
            history=prior_history,
            client_settings=form_support_settings,
            timeout=a2a_timeout_seconds
        )
        executors.append(form_support_executor)

    if not executors:
        raise RuntimeError("Tenant profile must enable at least one sub-agent.")

    active_executor_ids = [executor.id for executor in executors]

    #Dispatcher is NOT attached with an LLM will append memory and PII detection in futre  .
    dispatcher = Dispatcher(
        id="Dispatcher",
        name="Dispatcher",
        instructions="You are a user query dispatcher that forwards the input to the appropriate executor(s). In this case the conversation agent and the form support agent.",
        prompt_source=prompt_source,
        runtime_settings=runtime_settings,
        active_executor_ids=active_executor_ids,
    )

    #Aggregator is attached with an LLM at the moment, for message curation, and upadte for Multi-turn conversatin .
    aggregator = Aggregator(
        id="Aggregator",
        name="Aggregator",
        instructions="You are an aggregator that aggregates the results from the different executors. In this case the conversation agent and the form support agent.",
        prompt_source=prompt_source,
        runtime_settings=runtime_settings,
        active_executor_ids=active_executor_ids,
    )

    # Build workflow with dynamic sub-agent routing:
    # 1. Executors list is built based on tenant settings (which agents are enabled)
    # 2. Dispatcher classifies the user query using IntentListModel to decide which
    #    active executor(s) should handle it (one or both)
    # 3. Edges are conditionally added only for enabled executors
    # 4. Each executor's output flows directly to Aggregator (no fan-in barrier)
    # 5. Aggregator processes results and generates the final response
    workflow_builder = WorkflowBuilder(start_executor=dispatcher).add_edge(dispatcher, aggregator)
    if len(executors) == 1:
        workflow_builder.add_edge(dispatcher, executors[0])
    else:
        workflow_builder.add_multi_selection_edge_group(dispatcher, executors, _select_target_executors)

    for executor in executors:
        workflow_builder.add_edge(executor, aggregator)

    workflow = workflow_builder.build()
    #ABIN : as part of SHOWCASE-4181 workflow is transformed as an agent to accomodate multi-turn conversation
    agent = workflow.as_agent(
        "Orchestrator Agent"
    )


    thread_id = effective_session_id


    final_data = None

    try:
        # Load session state
        session = await db_utils.get_thread_state(thread_id, agent)

        step_appened_query= f"{effective_step_number}:{query}"  #TODO : This is a temp solution to pass the step number to Conversation, Once DISPATCHER Logic is implemented we will have a better solution later.
        input_messages = normalize_messages_input(step_appened_query)

        result = await agent.run(input_messages, session=session)
        print(f"Raw result from agent: {result}")
        final_data = _parse_workflow_result_text(result.text) if result.text else None

        # Save updated session state to Redis
        if session:
            try:
                print(f"Saving thread {thread_id} to Redis...")          
                await db_utils.save_thread_state(thread_id, session)
                print("Thread state saved.")
            except Exception as e:
                print(f"Error saving thread state: {e}")
                logger.warning("Error saving thread state: %s", e)
        # Add thread_id to response
        if final_data and isinstance(final_data, list):
            final_data.append({"thread_id": thread_id})
    except Exception as e:
        print(f"Error in orchestrate_a2a: {e}")
        logger.exception("Error in orchestrate_a2a")
        raise RuntimeError(f"Orchestration failed: {e}") from e

    return final_data


if __name__ == "__main__":
    raise RuntimeError(
        "Standalone orchestrator execution requires tenant settings from Cosmos. "
        "Use orchestrator_agent_server.py so the tenant profile is resolved before orchestration."
    )
