from agent_framework import Executor, WorkflowContext, handler
import logging
from typing import Any
from typing_extensions import Never
import json
from string import Template

from openai import AsyncAzureOpenAI

from clientprofiles import OrchestratorRuntimeSettings
from models.intentmodel import IntentListModel
from workflowcomponents.orchestratorsettings import openai_common_settings, runtime_int_value, runtime_value
from workflowcomponents.promptsource import DEFAULT_PROMPT_SOURCE, PromptSource
from workflowcomponents.routing import get_primary_intent, select_subagents

logger = logging.getLogger(__name__)



class Aggregator(Executor):
    """Collect sub-agent results and curate a single user-facing response.

    Two inbound message types:
      * `IntentListModel` from the dispatcher - resets state and tells the
        aggregator how many executor results to expect on this turn.
      * `dict` from each selected sub-agent executor - buffered until the
        expected count is reached, then merged via the LLM.

    Also supports a legacy `list[Any]` path (fan-in) for tests / older callers.
    """

    # Last-resort decline text. Hardcoded on purpose, for two reasons:
    #
    # 1. It runs when everything else has already failed - the LLM calls,
    #    the sub-agent calls, and the tenant's own message fetch. So it must
    #    not itself depend on config, network, or blob storage; those are
    #    exactly what failed to get us here.
    # 2. It is the default for every tenant, so the wording stays generic.
    #    Program-specific text (contact numbers, office names, branding)
    #    belongs in that tenant's gracefulDecline blob - put it here and
    #    every other tenant inherits it.
    FIRST_ATTEMPT_FALLBACK = (
        "I'm not finding a clear answer for that yet. Try rephrasing your "
        "question."
    )
    SECOND_ATTEMPT_FALLBACK = (
        "I'm still not finding a clear answer.\n\n"
        "You can try rephrasing your question, or contact your program's support team if you need further help."
    )

    def __init__(
        self,
        *args: Any,
        prompt_source: PromptSource | None = None,
        runtime_settings: OrchestratorRuntimeSettings | None = None,
        active_executor_ids: list[str] | None = None,
        session_id: str | None = None,
        thread_manager: Any | None = None,
        edge_case_templates: dict[str, str] | None = None,
        first_attempt_fallback: str | None = None,
        second_attempt_fallback: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # PromptSource and OpenAI settings are request-scoped for tenant isolation.
        self._prompt_source = prompt_source or DEFAULT_PROMPT_SOURCE
        self._runtime_settings = runtime_settings
        self._expected_count: int = 0
        self._buffered: list[Any] = []
        self._client: AsyncAzureOpenAI | None = None
        self._client_signature: tuple | None = None
        # Enabled executor ids for this tenant; used to reject dispatcher choices
        # that point to agents disabled in the tenant profile.
        self._active_executor_ids = active_executor_ids or []
        # Optional: drives the "first response / second attempt" escalation
        # tiering. Both are None for legacy/test construction, in which case
        # every graceful-decline turn just gets the first-attempt message.
        self._session_id = session_id
        self._thread_manager = thread_manager
        # Tenant-specific category templates, resolved from Azure Blob Storage
        # per "custom"-policy tenant (see edgecaseservice.py). No tenant
        # content lives in code: when a tenant has no override configured, or
        # its category isn't in the tenant's own templates.json, this stays
        # empty and handle_intent falls back to the plain first_attempt_fallback
        # text below - never a per-category message.
        self._edge_case_templates = edge_case_templates or {}
        self._first_attempt_fallback = first_attempt_fallback or self.FIRST_ATTEMPT_FALLBACK
        self._second_attempt_fallback = second_attempt_fallback or self.SECOND_ATTEMPT_FALLBACK


    def _aggregator_user_prompt_template(self) -> Template:
        raw = self._prompt_source.load_prompt(
            blob_path_env="AGENT_AGGREGATOR_PROMPTS_PATH",
            blob_filename="user.md",
            local_rel_path="aggregator/user.md",
        )
        return Template(raw)

    def _aggregator_system_prompt(self) -> str:
        return self._prompt_source.load_prompt(
            blob_path_env="AGENT_AGGREGATOR_PROMPTS_PATH",
            blob_filename="system.md",
            local_rel_path="aggregator/system.md",
        )

    def _get_or_create_client(
        self, api_key: str, endpoint: str, api_version: str, deployment: str
    ) -> AsyncAzureOpenAI:
        signature = (api_key, endpoint, api_version, deployment)
        if self._client is None or self._client_signature != signature:
            self._client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_deployment=deployment,
            )
            self._client_signature = signature
        return self._client

    @staticmethod
    def _has_conversation_text(text: str) -> bool:
        if not text:
            return False
        stripped = text.strip()
        return bool(stripped) and stripped.lower() != "not found"

    @staticmethod
    def _has_form_text(text: str) -> bool:
        if not text:
            return False
        # Strip surrounding JSON-style quotes so a JSON-stringified literal like
        # '"No Match"' is treated the same as the bare token "No Match".
        unquoted = text.strip().strip('"\'').strip().lower()
        return unquoted not in ("", "no match", "{}", "[]", "null")

    async def _next_no_answer_message(self) -> str:
        """Advance the per-session consecutive-failure counter and pick the tier."""
        if not self._session_id or not self._thread_manager:
            return self._first_attempt_fallback
        try:
            count = await self._thread_manager.increment_no_answer_count(self._session_id)
        except Exception as e:
            logger.warning("Failed to update no-answer counter: %s", e)
            return self._first_attempt_fallback
        return self._first_attempt_fallback if count <= 1 else self._second_attempt_fallback

    async def _reset_no_answer_count(self) -> None:
        """Clear the consecutive-failure counter once a real answer is produced."""
        if not self._session_id or not self._thread_manager:
            return
        try:
            await self._thread_manager.reset_no_answer_count(self._session_id)
        except Exception as e:
            logger.warning("Failed to reset no-answer counter: %s", e)

    async def _yield_graceful_decline(
        self, ctx: WorkflowContext[Never, list[Any]], active_results: list[Any]
    ) -> None:
        """Yield the tiered fallback message instead of raw/empty/error content."""
        message = await self._next_no_answer_message()
        print("Aggregator: unable to answer confidently, returning graceful fallback.")
        await ctx.yield_output(
            [
                {
                    "source": "Aggregator",
                    "response": message,
                    "original_results": active_results,
                }
            ]
        )

    @handler
    async def handle_intent(self, task: IntentListModel, ctx: WorkflowContext[Never, list[Any]]) -> None:
        """Reset state for a new turn and learn how many executor results to wait for."""
        if task.category is not None:
            # Fixed out-of-scope/edge-case bucket (see EdgeCaseCategory): no
            # sub-agent is invoked for this turn (orchestratoragent.py skips
            # them at the edge level), so respond directly instead of waiting
            # for executor results that will never arrive.
            self._expected_count = 0
            self._buffered = []
            await self._reset_no_answer_count()
            template = self._edge_case_templates.get(task.category, self._first_attempt_fallback)
            print(f"Aggregator: edge-case category '{task.category.value}' detected, returning fixed template.")
            await ctx.yield_output(
                [
                    {
                        "source": "Aggregator",
                        "response": template,
                        "category": task.category.value,
                    }
                ]
            )
            return

        high_conf = select_subagents(task)
        if high_conf:
            wanted = {intent.targetagent for intent in high_conf}
        else:
            wanted = {get_primary_intent(task).targetagent}

        if self._active_executor_ids:
            available = set(self._active_executor_ids)
            selected = wanted & available
            if not selected:
                raise RuntimeError(
                    f"Invalid routing state: selected agent(s) are not enabled for this tenant. "
                    f"Selected agent(s): {sorted(wanted)}. Enabled agent(s): {self._active_executor_ids}."
                )
        else:
            selected = wanted

        self._expected_count = len(selected)
        self._buffered = []

    @handler
    async def handle_result(self, result: dict[str, Any], ctx: WorkflowContext[Never, list[Any]]) -> None:
        """Buffer a single executor result; aggregate once the expected count is reached."""
        self._buffered.append(result)
        if self._expected_count and len(self._buffered) >= self._expected_count:
            buffered = self._buffered
            self._buffered = []
            self._expected_count = 0
            await self._aggregate(buffered, ctx)

    @handler
    async def handle_fan_in(self, results: list[Any], ctx: WorkflowContext[Never, list[Any]]) -> None:
        """Legacy fan-in entry point (used by older tests)."""
        await self._aggregate(results, ctx)

    async def _aggregate(self, results: list[Any], ctx: WorkflowContext[Never, list[Any]]) -> None:
        normalized_results = self._normalize_results(results)
        print("Aggregator received results: ", normalized_results)

        filtered_results = [
            result
            for result in normalized_results
            if not (isinstance(result, dict) and result.get("skipped") is True)
        ]
        if not filtered_results:
            # Every executor skipped (e.g. neither agent was confident enough to
            # take this turn). Nothing to merge - this is a "can't answer" turn.
            await self._yield_graceful_decline(ctx, normalized_results)
            return

        active_results = filtered_results

        conversation_text = ""
        form_text = ""
        form_step = ""

        for res in active_results:
            if isinstance(res, dict):
                if res.get("error") is True:
                    # Executor-side failure (A2A/HTTP/timeout). Never treat the
                    # exception text as usable agent content.
                    continue
                source = res.get("source", "")
                if "Conversation" in source:
                    conversation_text = res.get("response", "") or ""
                    print("Conversation Text: ", conversation_text)
                elif "FormSupport" in source:
                    raw_form = res.get("response", "")
                    form_text = (
                        json.dumps(raw_form)
                        if isinstance(raw_form, (dict, list))
                        else (raw_form or "")
                    )
                    print("Form Text: ", form_text)
                    form_step = res.get("step_number", "")

        has_conversation = self._has_conversation_text(conversation_text)
        has_form = self._has_form_text(form_text)

        if not has_conversation and not has_form:
            # Both agents errored, were empty, or returned "not found"/"no
            # match" - there is nothing valid to merge or return.
            await self._yield_graceful_decline(ctx, active_results)
            return

        # Short-circuit: only Conversation Agent returned usable content.
        # Conversation Agent already produces natural language, so there's
        # nothing for the aggregator LLM to merge - return it directly.
        if has_conversation and not has_form:
            aggregated_result = {
                "source": "Aggregator",
                "response": conversation_text,
                "original_results": active_results,
            }
            print("Aggregator: short-circuit (conversation-only). No LLM call.")
            await self._reset_no_answer_count()
            await ctx.yield_output([aggregated_result])
            return

        api_key, endpoint, deployment, api_version = openai_common_settings(self._runtime_settings)
        aggregator_deployment = runtime_value(
            self._runtime_settings,
            "azureOpenAIAggregatorChatDeploymentName",
            default=deployment,
        )
        if api_key and endpoint and aggregator_deployment and api_version:
            try:
                client = self._get_or_create_client(
                    api_key, endpoint, api_version, aggregator_deployment
                )

                system_prompt = self._aggregator_system_prompt()

                user_prompt = self._aggregator_user_prompt_template().safe_substitute(
                    conversation_text=conversation_text,
                    form_text=form_text,
                    form_step=form_step,
                )

                max_completion_tokens = runtime_int_value(
                    self._runtime_settings,
                    "azureOpenAIAggregatorMaxCompletionTokens",
                    default=600,
                )
                request_kwargs: dict[str, Any] = {
                    "model": aggregator_deployment,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_completion_tokens": max_completion_tokens,
                }
                # if "gpt-5" in aggregator_deployment.lower():
                #     request_kwargs["reasoning_effort"] = "minimal"

                completion = await client.chat.completions.create(**request_kwargs)

                final_text = completion.choices[0].message.content

                aggregated_result = {
                    "source": "Aggregator",
                    "response": final_text,
                    "original_results": active_results
                }

                print("Aggregated Result: ", aggregated_result)

                await self._reset_no_answer_count()
                await ctx.yield_output([aggregated_result])
                return

            except Exception as e:
                print(f"Error in Aggregator LLM call: {e}")
                logger.warning("Aggregator LLM call failed: %s", e)
        else:
            print("Aggregator: Missing Azure OpenAI credentials (API_KEY, ENDPOINT, DEPLOYMENT, or API_VERSION).")
            logger.warning("Aggregator Azure OpenAI settings are incomplete.")

        # The merge LLM is unavailable or failed, but at least one side has
        # genuinely usable content - salvage that instead of leaking the raw,
        # unmerged executor dicts (which may include partially-error content).
        salvage_text = conversation_text if has_conversation else form_text
        print("Aggregator: LLM merge unavailable, salvaging single-source content.")
        await self._reset_no_answer_count()
        await ctx.yield_output(
            [
                {
                    "source": "Aggregator",
                    "response": salvage_text,
                    "original_results": active_results,
                }
            ]
        )

    def _normalize_results(self, results: Any) -> list[Any]:
        """Normalize single-message and multi-message inputs to a list."""
        if isinstance(results, list):
            return results
        if isinstance(results, tuple):
            return list(results)
        return [results]
