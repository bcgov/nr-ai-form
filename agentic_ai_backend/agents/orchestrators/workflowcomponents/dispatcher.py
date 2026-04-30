import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from openai import AsyncAzureOpenAI

from models.intentmodel import IntentListModel, IntentModel

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
            "You are the Intent Classifier for a BC water permit application assistant.\n\n"
            "Select the most appropriate target agent(s) for the user's query based on the following criteria.\n"
            "Analyze the user's query, select target agents, and assign a confidence score from 0 to 10 based on the analysis, "
            f"and choose one or more target agents: `{FORM_SUPPORT_AGENT_ID}` and/or `{CONVERSATION_AGENT_ID}`.\n\n"
        
            f"Use `{CONVERSATION_AGENT_ID}` for informational or enquiry-style questions. "
            "This includes questions about legislation, permits, authorizations, BCEID login, eligibility, timelines, "
            "processes, policies, definitions, requirements, fees, statuses, or general BC water application subject matter.\n\n"

            "STRICT: If the query starts with or mainly asks using enquiry phrases such as "
            "'what is', 'what are', 'how', 'how to', 'why', 'explain', 'where', 'when', 'who can', "
            f"select `{CONVERSATION_AGENT_ID}` unless it clearly asks about a specific form field or form step.\n\n"

            f"Use `{FORM_SUPPORT_AGENT_ID}` only when the user is asking for help with the application form itself, "
            "including filling out a field, selecting an option, understanding a specific form step, fixing form-entry issues, "
            "or navigating a step in the application workflow.\n\n"

            f"Use the Form Agent Intent Mapper JSON to identify form-step or form-filling intents for `{FORM_SUPPORT_AGENT_ID}`.\n"
            f"Form Agent Intent Mapper JSON is like:\n"
            f"```json\n{mapper_json}\n```\n\n"

            f"If the user query does not clearly match the Form Agent Intent Mapper, prefer `{CONVERSATION_AGENT_ID}`.\n"
            "When both form guidance and general explanation are needed, return both agents.\n\n"

            f"if the user's query has a statement followed by a question then response should have both agents with confidence score of 7 or higher. For example, 'I am farm owner, Am I eligible?'. This should return both agents because it has a statement and then a question.\n\n"

            "Return structured output only. Do not include explanations outside the structured output. "
            "Return object or objects with an `intents` field that contains the routing decisions."
        )
        user_prompt = (        
            f"User query:\n{query}\n\n"
            "Detect the intent. Preserve the normalized query text in the `query` field."
        )

        try:
            completion = await client.chat.completions.parse(
                model=deployment,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
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

            return max(parsed.intents, key=lambda intent: intent.confidence)
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
