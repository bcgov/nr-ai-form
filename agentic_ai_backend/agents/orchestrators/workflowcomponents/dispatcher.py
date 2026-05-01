import os
import re
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from agent_framework.openai import OpenAIChatCompletionClient

from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.skillsregistry import (
    CONVERSATION_AGENT_ID,
    DISPATCHER_INTENT_SKILL,
    FORM_SUPPORT_AGENT_ID,
    skills_provider,
)


class AzureGatewayChatCompletionClient(OpenAIChatCompletionClient):
    """Compatibility wrapper for Azure gateways that reject empty assistant content with tool_calls."""

    def _prepare_message_for_openai(self, message):
        prepared_messages = super()._prepare_message_for_openai(message)
        for prepared_message in prepared_messages:
            if prepared_message.get("role") == "assistant" and "tool_calls" in prepared_message:
                prepared_message.setdefault("content", " ")
        return prepared_messages


_DISPATCHER_AGENT_INSTRUCTIONS = (
    "You are the BC water permit orchestrator's intent classifier. "
    f"Always begin by calling the `load_skill` tool with skill_name='{DISPATCHER_INTENT_SKILL.name}' "
    "to retrieve the full classification rules, then return a structured response matching IntentListModel "
    "with one IntentModel per target agent."
)

_dispatcher_agent: Any = None


def _get_dispatcher_agent():
    """Build the intent-classifier agent on demand. Returns ``None`` when Azure creds are missing."""
    global _dispatcher_agent
    if _dispatcher_agent is not None:
        return _dispatcher_agent

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not (api_key and endpoint and deployment and api_version):
        return None

    client = AzureGatewayChatCompletionClient(
        model=deployment,
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )
    _dispatcher_agent = client.as_agent(
        name="DispatcherIntentAgent",
        instructions=_DISPATCHER_AGENT_INSTRUCTIONS,
        context_providers=[skills_provider],
        default_options={
            "temperature": 0.1,
            "response_format": IntentListModel,
        },
    )
    return _dispatcher_agent


class Dispatcher(Executor):
    """
    The sole purpose of this executor is to dispatch the input of the workflow to
    other executors.
    """

    @handler
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[IntentListModel]):
        #TODOL:ABIN, need to sanitize the PII from the user query
        if not conversation:
            raise RuntimeError("Input conversation must not be empty.")

        last_message = conversation[-1]

        userquery = ""
        if hasattr(last_message, 'text'):
            userquery = last_message.text
        elif isinstance(last_message, dict) and 'text' in last_message:
            userquery = last_message['text']
        else:
            userquery = str(last_message)

        if not userquery:
            raise RuntimeError("Input must not be empty.")

        _, normalized_query = self._extract_step_context(userquery)

        intent = await self._classify(normalized_query)
        await ctx.send_message(intent)

    def _extract_step_context(self, userquery: str) -> tuple[str | None, str]:
        match = re.match(r"^(step\d+(?:-[^:]+)?):(.*)$", userquery, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None, userquery.strip()

        step_identifier = match.group(1).strip()
        normalized_query = match.group(2).strip()
        return step_identifier, normalized_query or userquery.strip()

    async def _classify(self, query: str) -> IntentListModel:
        agent = _get_dispatcher_agent()
        if agent is None:
            return self._fallback_classification(query)

        try:
            response = await agent.run(query)
            parsed = response.value
            if parsed is None or not parsed.intents:
                return self._fallback_classification(query)

            for intent in parsed.intents:
                intent.query = query
                intent.confidence = max(0.0, min(10.0, intent.confidence))
                print(f"Intent: {intent.confidence}, Agent: {intent.targetagent}, Query: {intent.query}")

            return parsed
        except Exception as exc:
            print(f"Dispatcher agent classification failed: {exc}")
            return self._fallback_classification(query)

    def _fallback_classification(self, query: str) -> IntentListModel:
        lowered_query = query.lower()

        strong_form_terms = (
            "bceid",
            "eligible",
            "eligibility",
            "apply without",
            "step",
            "field",
            "upload",
            "document",
            "co-applicant",
            "coapplicant",
            "declaration",
            "privacy confirmation",
            "frontcounter",
            "payment method",
            "farm owner",
        )

        if any(term in lowered_query for term in strong_form_terms):
            return IntentListModel(
                intents=[
                    IntentModel(
                        confidence=6.5,
                        targetagent=FORM_SUPPORT_AGENT_ID,
                        query=query,
                    )
                ]
            )

        return IntentListModel(
            intents=[
                IntentModel(
                    confidence=4.0,
                    targetagent=CONVERSATION_AGENT_ID,
                    query=query,
                )
            ]
        )
