import sys
import os
import asyncio
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalSemanticIntent,
)
from agent_framework.openai import OpenAIChatCompletionClient

# Add parent directory to path to allow importing 'tools' (llm mode only).
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.azure_ai_search import azure_ai_search


load_dotenv()

DEFAULT_KB_API_VERSION = "2025-11-01-preview"
DEFAULT_KB_MAX_OUTPUT_SIZE = 5001
MIN_KB_MAX_OUTPUT_SIZE = 500
DEFAULT_KB_MAX_RUNTIME_SECONDS = 30
DEFAULT_KB_MAX_HISTORY_MESSAGES = 10
DEFAULT_KB_REQUEST_MODE = "messages"
DEFAULT_KB_OUTPUT_MODE = "answerSynthesis"
DEFAULT_KB_REASONING_EFFORT = "low"
SUPPORTED_KB_REQUEST_MODES = {"messages", "intents"}
SUPPORTED_KB_OUTPUT_MODES = {"answerSynthesis", "extractiveData"}
SUPPORTED_KB_REASONING_EFFORTS = {"minimal", "low", "medium"}

CONVERSATION_AGENT_MODE_KNOWLEDGEBASE = "knowledgebase"
CONVERSATION_AGENT_MODE_LLM = "llm"
SUPPORTED_CONVERSATION_AGENT_MODES = {
    CONVERSATION_AGENT_MODE_KNOWLEDGEBASE,
    CONVERSATION_AGENT_MODE_LLM,
}
DEFAULT_CONVERSATION_AGENT_MODE = CONVERSATION_AGENT_MODE_KNOWLEDGEBASE


def _get_choice_env(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {allowed_values}.")
    return value


def _get_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc

    if parsed_value < 1:
        raise ValueError(f"{name} must be greater than 0.")

    return parsed_value


def _get_kb_max_output_size() -> int:
    raw_value = os.getenv(
        "AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE",
        str(DEFAULT_KB_MAX_OUTPUT_SIZE),
    )
    try:
        max_output_size = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE must be an integer."
        ) from exc

    if max_output_size < MIN_KB_MAX_OUTPUT_SIZE:
        raise ValueError(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE must be greater than 5000 "
            f"(got {max_output_size})."
        )

    return max_output_size


class AzureGatewayChatCompletionClient(OpenAIChatCompletionClient):
    """Compatibility wrapper for gateways that reject null assistant tool-call content."""

    def _prepare_message_for_openai(self, message):
        prepared_messages = super()._prepare_message_for_openai(message)
        for prepared_message in prepared_messages:
            if prepared_message.get("role") == "assistant" and "tool_calls" in prepared_message:
                # Some OpenAI-compatible gateways reject null/empty assistant content when tool_calls are present.
                prepared_message.setdefault("content", " ")
        return prepared_messages


# Backward-compatible alias for older patches/tests that referenced the beta client name.
AzureOpenAIChatClient = AzureGatewayChatCompletionClient


class ConversationAgent:
    """Answers user queries against Azure AI Search.

    Two modes selected by ``CONVERSATION_AGENT_MODE``:

    - ``knowledgebase`` (default): direct Azure AI Search Knowledge Base
      retrieval (agentic), no LLM in this service.
    - ``llm``: Azure OpenAI chat completion driving the ``azure_ai_search``
      tool — the older flow preserved here for fallback.
    """

    class _SessionShim:
        # KB retrieval is stateless per call; the A2A server still calls
        # ``agent.agent.create_session(session_id=...)``, so we hand back a
        # lightweight state object that round-trips through the server cache.
        def create_session(self, session_id=None):
            return {"session_id": session_id, "messages": []}

    def __init__(self, endpoint=None, api_key=None, deployment_name=None,
                 api_version=None, max_tokens=None, temperature=None):
        self._mode = _get_choice_env(
            "CONVERSATION_AGENT_MODE",
            DEFAULT_CONVERSATION_AGENT_MODE,
            SUPPORTED_CONVERSATION_AGENT_MODES,
        )
        if self._mode == CONVERSATION_AGENT_MODE_LLM:
            self._init_llmlogic(
                endpoint, api_key, deployment_name, api_version,
                max_tokens, temperature,
            )
        else:
            self._init_knowledgebase()

    def _init_knowledgebase(self):
        search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        search_api_key = os.environ["AZURE_SEARCH_API_KEY"]
        knowledge_base_name = os.environ["AZURE_SEARCH_KNOWLEDGE_AGENT_NAME"]
        kb_api_version = os.getenv(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_API_VERSION",
            DEFAULT_KB_API_VERSION,
        )

        client_kwargs = {}
        if kb_api_version:
            client_kwargs["api_version"] = kb_api_version

        self._search_endpoint = search_endpoint
        self._kb_api_version = kb_api_version
        self._max_output_size = _get_kb_max_output_size()
        self._max_runtime_seconds = _get_positive_int_env(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_RUNTIME_SECONDS",
            DEFAULT_KB_MAX_RUNTIME_SECONDS,
        )
        self._max_history_messages = _get_positive_int_env(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_HISTORY_MESSAGES",
            DEFAULT_KB_MAX_HISTORY_MESSAGES,
        )
        self._request_mode = _get_choice_env(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE",
            DEFAULT_KB_REQUEST_MODE,
            SUPPORTED_KB_REQUEST_MODES,
        )
        self._output_mode = _get_choice_env(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_OUTPUT_MODE",
            DEFAULT_KB_OUTPUT_MODE,
            SUPPORTED_KB_OUTPUT_MODES,
        )
        self._reasoning_effort = _get_choice_env(
            "AZURE_SEARCH_KNOWLEDGE_AGENT_REASONING_EFFORT",
            DEFAULT_KB_REASONING_EFFORT,
            SUPPORTED_KB_REASONING_EFFORTS,
        )
        self._client = KnowledgeBaseRetrievalClient(
            endpoint=search_endpoint,
            credential=AzureKeyCredential(search_api_key),
            knowledge_base_name=knowledge_base_name,
            **client_kwargs,
        )
        self.agent = self._SessionShim()

    def _init_llmlogic(self, endpoint, api_key, deployment_name, api_version,
                     max_tokens, temperature):
        endpoint = endpoint or os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = api_key or os.environ["AZURE_OPENAI_API_KEY"]
        deployment_name = deployment_name or os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        api_version = api_version or os.environ["AZURE_OPENAI_API_VERSION"]
        if max_tokens is None:
            max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "800"))
        if temperature is None:
            temperature = float(os.getenv("AGENT_TEMPERATURE", "0.1"))

        client = AzureOpenAIChatClient(
            model=deployment_name,
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        agent_kwargs = {
            "instructions": """
                You are an assistant for BC Government's Permit Application. Use the azure_ai_search tool to answer user queries.

                STRICT RULES:
                1. You must ONLY use the information provided by the azure_ai_search tool.
                2. If the azure_ai_search tool returns "No results found" or an empty result, return "Not found" immediately.
                3. Always include the metadata (Source and Processed with) from the azure_ai_search and all the azure_ai_search for the information you provide in your response.
                4. Format your response clearly, citing the source and processed with and all the azure_ai_search results at the end.
            """,
            "tools": [azure_ai_search],
            "name": "ConversationAgent",
        }
        self.agent = client.as_agent(
            **agent_kwargs,
            default_options={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tool_choice": "required",
            },
        )

    async def run(self, userquery, session=None, thread=None):
        if self._mode == CONVERSATION_AGENT_MODE_LLM:
            return await self._run_llmlogic(userquery)
        return await self._run_knowledgebase(userquery, session, thread)

    async def _run_llmlogic(self, userquery):
        # Mirrors prior behavior: session/thread is intentionally not threaded
        # into the underlying agent call.
        result = await self.agent.run(userquery)
        return result.text

    async def _run_knowledgebase(self, userquery, session=None, thread=None):
        session_state = self._get_session_state(session, thread)
        request, user_message = self._build_request(userquery, session_state)
        try:
            result = await asyncio.to_thread(
                self._client.retrieve, retrieval_request=request
            )
        except Exception as e:
            error_message = self._format_retrieval_error(str(e))
            print(f"Error calling Azure AI Search Knowledge Base: {error_message}")
            return f"Error retrieving from Knowledge Base: {error_message}"

        answer = self._extract_answer(result)
        if session_state is not None and user_message is not None:
            self._append_message(session_state, user_message)
            self._append_message(
                session_state,
                self._create_text_message("assistant", answer),
            )

        return answer

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

    def _build_request(self, userquery, session_state):
        if self._request_mode == "messages":
            user_message = self._create_text_message("user", userquery)
            request_messages = []
            if session_state is not None:
                request_messages.extend(session_state["messages"])
            request_messages.append(user_message)
            # The installed SDK can still serialize preview-only fields even
            # though its typed constructor has not caught up yet.
            request = KnowledgeBaseRetrievalRequest(
                {
                    "messages": request_messages,
                    "outputMode": self._output_mode,
                    "maxOutputSize": self._max_output_size,
                    "maxRuntimeInSeconds": self._max_runtime_seconds,
                    "retrievalReasoningEffort": {"kind": self._reasoning_effort},
                }
            )
            return request, user_message

        request = KnowledgeBaseRetrievalRequest(
            intents=[KnowledgeRetrievalSemanticIntent(search=userquery)],
            max_output_size_in_tokens=self._max_output_size,
            max_runtime_in_seconds=self._max_runtime_seconds,
        )
        return request, None

    def _append_message(self, session_state, message: KnowledgeBaseMessage) -> None:
        session_state["messages"].append(message)
        if len(session_state["messages"]) > self._max_history_messages:
            session_state["messages"] = session_state["messages"][
                -self._max_history_messages:
            ]

    def _format_retrieval_error(self, error_message: str) -> str:
        if self._request_mode == "messages" and (
            "parameter 'messages'" in error_message
            or "parameter 'outputMode'" in error_message
        ):
            return (
                f"{error_message} This endpoint or API version does not support "
                "message-based agentic retrieval. Use "
                f"AZURE_SEARCH_KNOWLEDGE_AGENT_API_VERSION={DEFAULT_KB_API_VERSION} "
                "with an Azure AI Search knowledge base endpoint, or set "
                "AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE=intents for llm "
                f"compatibility. Current endpoint: {self._search_endpoint}; current "
                f"api version: {self._kb_api_version}."
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
    agent = ConversationAgent()
    print("User Query is {0}".format(query))
    result = await agent.run(query)
    print(result)


if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(dryrun(query))
