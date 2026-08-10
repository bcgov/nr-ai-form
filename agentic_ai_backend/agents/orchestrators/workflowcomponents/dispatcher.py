import json
import logging
import re
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from openai import AsyncAzureOpenAI

from clientprofiles import OrchestratorRuntimeSettings
from models.intentmodel import IntentListModel, IntentModel
from workflowcomponents.promptsource import PromptSource
from workflowcomponents.orchestratorsettings import openai_common_settings
from workflowcomponents.skillsregistry import (
    CONVERSATION_AGENT_ID,
    FORM_SUPPORT_AGENT_ID,
    get_dispatcher_skill,
)

logger = logging.getLogger(__name__)

class Dispatcher(Executor):
    """Route each user turn to the tenant-appropriate sub-agent executor(s)."""

    def __init__(
        self,
        *args: Any,
        prompt_source: PromptSource | None = None,
        runtime_settings: OrchestratorRuntimeSettings | None = None,
        active_executor_ids: list[str] | None = None,
        edge_case_policy: str = "default",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # PromptSource and OpenAI settings are request-scoped for tenant isolation.
        self._prompt_source = prompt_source
        self._runtime_settings = runtime_settings
        # Only these executor ids are enabled for the current tenant. The dispatcher
        # prompt is guided by this list and the parsed result is validated below.
        self._active_executor_ids = active_executor_ids or []
        # Tenants that haven't opted into custom edge-case categories ("default")
        # must never trigger edge-case behavior downstream, even if their own
        # dispatcher prompt or a stray LLM classification sets `category` - this
        # is enforced below regardless of prompt content.
        self._edge_case_policy = edge_case_policy
        self._client: AsyncAzureOpenAI | None = None
        self._client_signature: tuple[str, str, str, str] | None = None

    def _get_or_create_client(self) -> tuple[AsyncAzureOpenAI, str] | tuple[None, None]:
        """Build an Azure OpenAI client from tenant runtime settings."""
        api_key, endpoint, deployment, api_version = openai_common_settings(self._runtime_settings)
        if not (api_key and endpoint and deployment and api_version):
            return None, None

        signature = (api_key, endpoint, deployment, api_version)
        if self._client is None or self._client_signature != signature:
            self._client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_deployment=deployment,
            )
            self._client_signature = signature

        return self._client, deployment
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
        client, deployment = self._get_or_create_client()
        if client is None:
            return self._fallback_classification(query)

        # TODO: Remove the fallback list once every Dispatcher caller passes
        # tenant-derived active_executor_ids. It only preserves legacy/unit-test
        # construction where Dispatcher is created outside the orchestrator flow.
        enabled_agents = self._active_executor_ids or [CONVERSATION_AGENT_ID, FORM_SUPPORT_AGENT_ID]

        try:
            print(f"Classifying query with dispatcher LLM: {query} for step: {step}")
            completion = await client.chat.completions.parse(
                model=deployment,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": get_dispatcher_skill(self._prompt_source).content},
                    {
                        "role": "system",
                        "content": (
                            "Enabled agents for this tenant: "
                            f"{', '.join(enabled_agents)}. Select only from this list."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"query": query, "step": step, "enabled_agents": enabled_agents}
                        ),
                    },
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

        except Exception as exc:
            print(f"Dispatcher LLM classification failed: {exc}")
            logger.warning("Dispatcher LLM classification failed: %s", exc)
            return self._fallback_classification(query)

        return self._apply_edge_case_policy(self._validate_enabled_agents(parsed))

    def _apply_edge_case_policy(self, intents: IntentListModel) -> IntentListModel:
        """Clear `category` for tenants that haven't opted into custom edge cases.

        Defense-in-depth: a tenant's own dispatcher prompt already controls
        whether the LLM is even told about edge-case categories, but this
        guard means a "default"-policy tenant can never trigger edge-case
        behavior even from a misconfigured prompt or a stray classification.
        """
        if self._edge_case_policy == "custom" or intents.category is None:
            return intents
        return intents.model_copy(update={"category": None})

    def _validate_enabled_agents(self, intents: IntentListModel) -> IntentListModel:
        if not self._active_executor_ids:
            return intents

        enabled = set(self._active_executor_ids)
        selected_disabled = sorted(
            {intent.targetagent for intent in intents.intents if intent.targetagent not in enabled}
        )
        if selected_disabled:
            raise RuntimeError(
                f"Invalid routing state: selected agent(s) are not enabled for this tenant. "
                f"Selected agent(s): {selected_disabled}. Enabled agent(s): {self._active_executor_ids}."
            )
        return intents

    def _enabled_intent(self, targetagent: str, query: str, confidence: float) -> IntentListModel:
        if self._active_executor_ids and targetagent not in self._active_executor_ids:
            raise RuntimeError(
                f"Invalid routing state: selected agent(s) are not enabled for this tenant. "
                f"Selected agent(s): {[targetagent]}. Enabled agent(s): {self._active_executor_ids}."
            )
        return IntentListModel(
            intents=[
                IntentModel(
                    confidence=confidence,
                    targetagent=targetagent,
                    query=query,
                )
            ]
        )

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
            return self._enabled_intent(FORM_SUPPORT_AGENT_ID, query, 6.5)

        return self._enabled_intent(CONVERSATION_AGENT_ID, query, 4.0)
