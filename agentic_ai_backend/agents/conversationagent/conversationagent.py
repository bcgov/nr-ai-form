import sys
import os
import asyncio
import logging
import time
from dataclasses import dataclass
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalSemanticIntent,
)
from agent_framework import tool
from agent_framework.openai import OpenAIChatCompletionClient

# Add parent directories to path to allow importing 'tools' and the shared 'utils'
# package (llm mode only). 'utils' lives at agentic_ai_backend/utils.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tools.azure_ai_search import azure_ai_search
from utils.blobservice import BlobService
from models.client_settings_type import ConversationAgentClientSettings
from conversationconstants import (
    CONVERSATION_AGENT_MODE_LLM,
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_TEMPERATURE,
    DEFAULT_CONVERSATION_AGENT_MODE,
    DEFAULT_KB_API_VERSION,
    DEFAULT_KB_MAX_HISTORY_MESSAGES,
    DEFAULT_KB_MAX_OUTPUT_SIZE,
    DEFAULT_KB_MAX_RUNTIME_SECONDS,
    DEFAULT_KB_OUTPUT_MODE,
    DEFAULT_KB_REASONING_EFFORT,
    DEFAULT_KB_REQUEST_MODE,
    SUPPORTED_CONVERSATION_AGENT_MODES,
)
from utils.tenantsettings import (
    AZURE_BLOB_CONNECTION_STRING_ENV,
    AZURE_BLOB_CONTAINER_ENV,
    AZURE_OPENAI_API_KEY_ENV,
    AZURE_OPENAI_ENDPOINT_ENV,
    AZURE_SEARCH_API_KEY_ENV,
    AZURE_SEARCH_ENDPOINT_ENV,
    environment_setting,
    setting_from_client_config,
    settings_cache_parts,
    top_level_setting_from_client,
)


@dataclass
class _CachedInstructions:
    text: str
    expires_at: float


_INSTRUCTIONS_CACHE: dict[tuple[str, str, str], _CachedInstructions] = {}
_INSTRUCTIONS_CACHE_TTL_SECONDS = float(os.getenv("CONVERSATION_PROMPT_CACHE_TTL_SECONDS", "300"))


def make_azure_ai_search_tool(client_settings: ConversationAgentClientSettings):
    """
    Factory function that creates an Azure AI Search tool for a specific client configuration.

    This function creates a closure that binds the client_settings to the azure_ai_search
    function, allowing it to be used as a tool by the agent framework with tenant-specific
    configuration (endpoint, API key, index name, etc.).

    Args:
        client_settings: Tenant-specific configuration containing Azure Search credentials
                        and settings (endpoint, API key, index name, etc.)

    Returns:
        A tool function that can be used by the agent framework to perform Azure AI Search
        queries. The returned function takes a query string and returns search results.
    """
    @tool(
        name="azure_ai_search",
        description="Retrieves information related with Permit Applications using Azure AI Search",
    )
    def azure_ai_search_for_client(query: str) -> str:
        return azure_ai_search(query, client_settings=client_settings)

    return azure_ai_search_for_client


load_dotenv()

logger = logging.getLogger(__name__)

class AzureGatewayChatCompletionClient(OpenAIChatCompletionClient):
    """Compatibility wrapper for gateways that reject null assistant tool-call content."""

    def _prepare_message_for_openai(self, message):
        prepared_messages = super()._prepare_message_for_openai(message)
        for prepared_message in prepared_messages:
            if prepared_message.get("role") == "assistant" and "tool_calls" in prepared_message:
                prepared_message.setdefault("content", " ")
        return prepared_messages


# Backward-compatible alias for older patches/tests that referenced the beta client name.
AzureOpenAIChatClient = AzureGatewayChatCompletionClient


class ConversationAgent:
    """Answers user queries against Azure AI Search.

    Two modes selected by ``conversationAgentMode`` in client_settings config:

    - ``knowledgebase`` (default): direct Azure AI Search Knowledge Base
      retrieval (agentic), no LLM in this service.
    - ``llm``: Azure OpenAI chat completion driving the ``azure_ai_search``
      tool - the older flow preserved here for fallback.

    All configuration is driven by client_settings (per-tenant profile from
    Cosmos DB). No os.getenv() for tenant-specific settings.
    """

    class _SessionShim:
        def create_session(self, session_id=None):
            return {"session_id": session_id, "messages": []}

    def __init__(self):
        # Lightweight init - actual client setup happens per-request in run()
        # based on the tenant's client_settings.
        self.agent = self._SessionShim()

    async def run(self, userquery, session=None, thread=None, *, client_settings: ConversationAgentClientSettings):
        """Run the conversation agent with per-tenant config from client_settings."""
        cfg = client_settings.get("config") or {}
        mode = setting_from_client_config(
            client_settings,
            "conversationAgentMode",
            default=DEFAULT_CONVERSATION_AGENT_MODE,
        )

        if mode not in SUPPORTED_CONVERSATION_AGENT_MODES:
            raise ValueError(f"conversationAgentMode must be one of: {SUPPORTED_CONVERSATION_AGENT_MODES}")

        if mode == CONVERSATION_AGENT_MODE_LLM:
            llm_query = userquery.strip().replace(" ", " + ")
            return await self._run_llmlogic(llm_query, cfg, client_settings)
        return await self._run_knowledgebase(userquery, session, thread, cfg, client_settings)

    async def _run_llmlogic(self, userquery, cfg, client_settings: ConversationAgentClientSettings):
        endpoint = environment_setting(AZURE_OPENAI_ENDPOINT_ENV, required=True)
        api_key = environment_setting(AZURE_OPENAI_API_KEY_ENV, required=True)
        deployment_name = setting_from_client_config(client_settings, "azureOpenaiChatDeploymentName", required=True)
        api_version = setting_from_client_config(client_settings, "azureOpenaiApiVersion", required=True)
        max_tokens = cfg.get("agentMaxTokens", DEFAULT_AGENT_MAX_TOKENS)
        temperature = cfg.get("agentTemperature", DEFAULT_AGENT_TEMPERATURE)

        client = AzureOpenAIChatClient(
            model=deployment_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

        instructions = self._load_instructions(client_settings)
        agent = client.as_agent(
            instructions=instructions,
            tools=[make_azure_ai_search_tool(client_settings)],
            name="ConversationAgent",
            default_options={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tool_choice": "required",
            },
        )

        result = await agent.run(userquery)
        return result.text

    async def _run_knowledgebase(self, userquery, session, thread, cfg, client_settings: ConversationAgentClientSettings):
        search_endpoint = environment_setting(AZURE_SEARCH_ENDPOINT_ENV, required=True)
        search_api_key = environment_setting(AZURE_SEARCH_API_KEY_ENV, required=True)
        knowledge_base_name = setting_from_client_config(client_settings, "azureSearchKnowledgeAgentName", required=True)
        kb_api_version = setting_from_client_config(client_settings, "azureSearchKnowledgeAgentApiVersion", default=DEFAULT_KB_API_VERSION)
        max_output_size = int(setting_from_client_config(client_settings, "azureSearchKnowledgeAgentMaxOutputSize", default=DEFAULT_KB_MAX_OUTPUT_SIZE))
        max_runtime_seconds = int(setting_from_client_config(client_settings, "azureSearchKnowledgeAgentMaxRuntimeSeconds", default=DEFAULT_KB_MAX_RUNTIME_SECONDS))
        max_history_messages = int(setting_from_client_config(client_settings, "azureSearchKnowledgeAgentMaxHistoryMessages", default=DEFAULT_KB_MAX_HISTORY_MESSAGES))
        request_mode = setting_from_client_config(client_settings, "azureSearchKnowledgeAgentRequestMode", default=DEFAULT_KB_REQUEST_MODE)
        output_mode = setting_from_client_config(client_settings, "azureSearchKnowledgeAgentOutputMode", default=DEFAULT_KB_OUTPUT_MODE)
        reasoning_effort = setting_from_client_config(client_settings, "azureSearchKnowledgeAgentReasoningEffort", default=DEFAULT_KB_REASONING_EFFORT)

        client_kwargs = {}
        if kb_api_version:
            client_kwargs["api_version"] = kb_api_version

        kb_client = KnowledgeBaseRetrievalClient(
            endpoint=search_endpoint,
            credential=AzureKeyCredential(search_api_key),
            knowledge_base_name=knowledge_base_name,
            **client_kwargs,
        )

        session_state = self._get_session_state(session, thread)
        request, user_message = self._build_request(
            userquery, session_state, request_mode, output_mode,
            max_output_size, max_runtime_seconds, reasoning_effort,
        )

        try:
            result = await asyncio.to_thread(kb_client.retrieve, retrieval_request=request)
        except Exception as e:
            error_message = self._format_retrieval_error(
                str(e), request_mode, search_endpoint, kb_api_version,
            )
            logger.warning("Error calling Azure AI Search Knowledge Base: %s", error_message)
            return f"Error retrieving from Knowledge Base: {error_message}"

        answer = self._extract_answer(result)
        if session_state is not None and user_message is not None:
            self._append_message(session_state, user_message, max_history_messages)
            self._append_message(
                session_state,
                self._create_text_message("assistant", answer),
                max_history_messages,
            )

        return answer

    def _load_instructions(self, client_settings: ConversationAgentClientSettings) -> str:
        """Load agent instructions from Azure Blob Storage using tenant config."""
        blob_conn_str = environment_setting(AZURE_BLOB_CONNECTION_STRING_ENV, required=True)
        container_name = environment_setting(AZURE_BLOB_CONTAINER_ENV, required=True)
        prompt_path = top_level_setting_from_client(client_settings, "promptPath", required=True)
        if not blob_conn_str or not container_name or not prompt_path:
            raise RuntimeError("ConversationAgent instruction blob config is required.")

        client_id, fingerprint = settings_cache_parts(client_settings)
        cache_key = (client_id, fingerprint, prompt_path)
        now = time.monotonic()
        cached = _INSTRUCTIONS_CACHE.get(cache_key)
        if _INSTRUCTIONS_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
            return cached.text

        try:
            blob_service = BlobService(blob_conn_str)
            instructions = blob_service.read_blob_text(container_name, prompt_path)
            if instructions.strip():
                if _INSTRUCTIONS_CACHE_TTL_SECONDS > 0:
                    _INSTRUCTIONS_CACHE[cache_key] = _CachedInstructions(
                        text=instructions,
                        expires_at=now + _INSTRUCTIONS_CACHE_TTL_SECONDS,
                    )
                return instructions
            raise RuntimeError(f"ConversationAgent instructions blob {container_name}/{prompt_path} is empty.")
        except Exception as e:
            raise RuntimeError(f"Failed to load ConversationAgent instructions from blob {container_name}/{prompt_path}: {e}") from e

    @staticmethod
    def _get_session_state(session, thread):
        state = session or thread
        if isinstance(state, dict):
            state.setdefault("messages", [])
            return state
        return None

    @staticmethod
    def _create_text_message(role: str, text: str) -> KnowledgeBaseMessage:
        return KnowledgeBaseMessage(
            role=role,
            content=[KnowledgeBaseMessageTextContent(text=text)],
        )

    def _build_request(self, userquery, session_state, request_mode, output_mode,
                       max_output_size, max_runtime_seconds, reasoning_effort):
        if request_mode == "messages":
            user_message = self._create_text_message("user", userquery)
            request_messages = []
            if session_state is not None:
                request_messages.extend(session_state["messages"])
            request_messages.append(user_message)
            request = KnowledgeBaseRetrievalRequest(
                {
                    "messages": request_messages,
                    "outputMode": output_mode,
                    "maxOutputSize": max_output_size,
                    "maxRuntimeInSeconds": max_runtime_seconds,
                    "retrievalReasoningEffort": {"kind": reasoning_effort},
                }
            )
            return request, user_message

        request = KnowledgeBaseRetrievalRequest(
            intents=[KnowledgeRetrievalSemanticIntent(search=userquery)],
            max_output_size_in_tokens=max_output_size,
            max_runtime_in_seconds=max_runtime_seconds,
        )
        return request, None

    def _append_message(self, session_state, message: KnowledgeBaseMessage, max_history: int) -> None:
        session_state["messages"].append(message)
        if len(session_state["messages"]) > max_history:
            session_state["messages"] = session_state["messages"][-max_history:]

    @staticmethod
    def _format_retrieval_error(error_message: str, request_mode: str,
                                search_endpoint: str, kb_api_version: str) -> str:
        if request_mode == "messages" and (
            "parameter 'messages'" in error_message
            or "parameter 'outputMode'" in error_message
        ):
            return (
                f"{error_message} This endpoint or API version does not support "
                "message-based agentic retrieval. Set "
                "azureSearchKnowledgeAgentRequestMode=intents in client profile "
                f"for compatibility. Current endpoint: {search_endpoint}; current "
                f"api version: {kb_api_version}."
            )
        return error_message

    @staticmethod
    def _extract_answer(result) -> str:
        response = getattr(result, "response", None) or []
        for message in response:
            for content in getattr(message, "content", None) or []:
                text = getattr(content, "text", None)
                if text:
                    return text
        return "Not found"


async def dryrun(query):
    raise RuntimeError(
        "ConversationAgent dryrun no longer reads tenant settings from .env. "
        "Invoke through the orchestrator so client_settings are resolved from Cosmos."
    )

if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))
