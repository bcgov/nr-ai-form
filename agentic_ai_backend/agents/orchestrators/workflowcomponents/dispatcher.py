import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from openai import AsyncAzureOpenAI

from models.intentmodel import IntentModel

FORM_SUPPORT_AGENT_ID = "FormSupportAgentA2A"
CONVERSATION_AGENT_ID = "ConversationAgentA2A"



class Dispatcher(Executor):
    """
    The sole purpose of this executor is to dispatch the input of the workflow to
    other executors.
    """

    @handler
    async def handle(self, conversation: list[Any], ctx: WorkflowContext[IntentModel]):
        #TODOL:ABIN, need to sanitize the PII from the user query
        if not conversation:
            raise RuntimeError("Input conversation must not be empty.")

        last_message = conversation[-1]
        
        # Determine how to get text based on message type
        userquery = ""
        if hasattr(last_message, 'text'):
            userquery = last_message.text
        elif isinstance(last_message, dict) and 'text' in last_message:
            userquery = last_message['text']
        else:
            userquery = str(last_message)

        if not userquery:
            raise RuntimeError("Input must not be empty.")

        current_step, normalized_query = self._extract_step_context(userquery)
        mapper_json = json.dumps(load_form_step_intent_mapper(), indent=2)

        intent = await self._classify_with_llm(
            query=normalized_query,
            mapper_json=mapper_json,
            current_step=current_step,
        )

        await ctx.send_message(intent)

    def _extract_step_context(self, userquery: str) -> tuple[str | None, str]:
        match = re.match(r"^(step\d+(?:-[^:]+)?):(.*)$", userquery, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None, userquery.strip()

        step_identifier = match.group(1).strip()
        normalized_query = match.group(2).strip()
        return step_identifier, normalized_query or userquery.strip()

    async def _classify_with_llm(self, query: str, mapper_json: str, current_step: str | None) -> IntentModel:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if not (api_key and endpoint and deployment and api_version):
            return self._fallback_classification(query)

        client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            azure_deployment=deployment,
        )

        system_prompt = (
            "You are the dispatcher for a BC water permit application assistant. "
            "Your job is to choose exactly one target agent for the user's query. "
            f"Choose `{FORM_SUPPORT_AGENT_ID}` only when the query is about filling the application form, "
            "understanding a form step, eligibility in the application, BCeID/application entry, "
            "field meanings, uploads, declarations, or other form-step help described in the mapper. "
            f"Choose `{CONVERSATION_AGENT_ID}` for general informational questions about legislation, "
            "permits, authorizations, processes, timelines, policies, or other broad subject matter "
            "that is not specifically about completing the form. "
            f"If the query does not clearly match the form-step mapper, prefer `{CONVERSATION_AGENT_ID}`. "
            "Return structured output only. Set `confidence` on a 0 to 10 scale."
        )
        user_prompt = (
            f"Current application step context: {current_step or 'unknown'}\n\n"
            f"Form step intent mapper:\n{mapper_json}\n\n"
            f"User query:\n{query}\n\n"
            "Classify the route. Preserve the normalized query text in the `query` field."
        )

        try:
            completion = await client.beta.chat.completions.parse(
                model=deployment,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=IntentModel,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                return self._fallback_classification(query)

            parsed.query = query
            parsed.confidence = max(0.0, min(10.0, parsed.confidence))
            print(f"Dispatcher LLM classification: {parsed}")
            return parsed
        except Exception as exc:
            print(f"Dispatcher LLM classification failed: {exc}")
            return self._fallback_classification(query)

    def _fallback_classification(self, query: str) -> IntentModel:
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
            return IntentModel(
                confidence=6.5,
                targetagent=FORM_SUPPORT_AGENT_ID,
                query=query,
            )

        return IntentModel(
            confidence=4.0,
            targetagent=CONVERSATION_AGENT_ID,
            query=query,
        )


@lru_cache(maxsize=1)
def load_form_step_intent_mapper() -> list[dict[str, Any]]:
    mapper_path = Path(__file__).with_name("formstepsintendmapper.json")
    with mapper_path.open("r", encoding="utf-8") as mapper_file:
        return json.load(mapper_file)
