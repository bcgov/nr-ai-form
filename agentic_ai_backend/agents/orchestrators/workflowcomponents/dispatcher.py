import os
import re
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from openai import AsyncAzureOpenAI

from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.skillsregistry import (
    CONVERSATION_AGENT_ID,
    DISPATCHER_INTENT_SKILL,
    FORM_SUPPORT_AGENT_ID,
)

_dispatcher_client: AsyncAzureOpenAI | None = None
_dispatcher_deployment: str | None = None


def _get_dispatcher_client() -> tuple[AsyncAzureOpenAI, str] | tuple[None, None]:
    """Lazily build the Azure OpenAI client. Returns (None, None) when creds are missing."""
    global _dispatcher_client, _dispatcher_deployment
    if _dispatcher_client is not None and _dispatcher_deployment is not None:
        return _dispatcher_client, _dispatcher_deployment

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not (api_key and endpoint and deployment and api_version):
        return None, None

    _dispatcher_client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint,
        azure_deployment=deployment,
    )
    _dispatcher_deployment = deployment
    return _dispatcher_client, _dispatcher_deployment


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

        step, normalized_query = self._extract_step_context(userquery)

        intent = await self._classify(normalized_query, step)
        await ctx.send_message(intent)

    def _extract_step_context(self, userquery: str) -> tuple[str | None, str]:
        match = re.match(r"^(step\d+(?:-[^:]+)?):(.*)$", userquery, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None, userquery.strip()

        step_identifier = match.group(1).strip()
        normalized_query = match.group(2).strip()
        return step_identifier, normalized_query or userquery.strip()

    async def _classify(self, query: str, step: str | None) -> IntentListModel:
        client, deployment = _get_dispatcher_client()
        if client is None:
            return self._fallback_classification(query)

        try:
            print(f"Classifying query with dispatcher LLM: {query} for step: {step}")
            completion = await client.chat.completions.parse(
                model=deployment,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": DISPATCHER_INTENT_SKILL.content},
                    {"role": "user", "content": {"query": query, "step": step}},
                ],
                response_format=IntentListModel,
            )
            parsed = completion.choices[0].message.parsed

            if parsed is None or not parsed.intents:
                return self._fallback_classification(query)

            for intent in parsed.intents:
                intent.query = query
                intent.confidence = max(0.0, min(10.0, intent.confidence))
                print(f"Intent: {intent.confidence}, Agent: {intent.targetagent}, Query: {intent.query}")

            return parsed
        except Exception as exc:
            print(f"Dispatcher LLM classification failed: {exc}")
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
