from agent_framework import Executor, WorkflowContext, handler
from typing import Any
from typing_extensions import Never
import json
import os
from functools import lru_cache
from string import Template

from openai import AsyncAzureOpenAI

from models.intentmodel import IntentListModel
from workflowcomponents.promptsource import load_prompt
from workflowcomponents.routing import get_primary_intent, select_subagents


@lru_cache(maxsize=1)
def _aggregator_user_prompt_template() -> Template:
    raw = load_prompt(
        blob_path_env="AGENT_AGGREGATOR_PROMPTS_PATH",
        blob_filename="user.md",
        local_rel_path="aggregator/user.md",
    )
    return Template(raw)


@lru_cache(maxsize=1)
def _aggregator_system_prompt() -> str:
    return load_prompt(
        blob_path_env="AGENT_AGGREGATOR_PROMPTS_PATH",
        blob_filename="system.md",
        local_rel_path="aggregator/system.md",
    )


class Aggregator(Executor):
    """Collect sub-agent results and curate a single user-facing response.

    Two inbound message types:
      * `IntentListModel` from the dispatcher — resets state and tells the
        aggregator how many executor results to expect on this turn.
      * `dict` from each selected sub-agent executor — buffered until the
        expected count is reached, then merged via the LLM.

    Also supports a legacy `list[Any]` path (fan-in) for tests / older callers.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._expected_count: int = 0
        self._buffered: list[Any] = []
        self._client: AsyncAzureOpenAI | None = None
        self._client_signature: tuple | None = None

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

    @handler
    async def handle_intent(self, task: IntentListModel, ctx: WorkflowContext[Never, list[Any]]) -> None:
        """Reset state for a new turn and learn how many executor results to wait for."""
        high_conf = select_subagents(task)
        if high_conf:
            wanted = {intent.targetagent for intent in high_conf}
        else:
            wanted = {get_primary_intent(task).targetagent}

        self._expected_count = len(wanted)
        self._buffered = []
        print(f"Aggregator: expecting {self._expected_count} result(s) for agents {wanted}")

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
            print("Aggregator: Skipped-only result received. Nothing to aggregate.")
            return

        active_results = filtered_results

        conversation_text = ""
        form_text = ""
        form_step = ""

        for res in active_results:
            if isinstance(res, dict):
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

        # Short-circuit: only Conversation Agent returned usable content.
        # Conversation Agent already produces natural language, so there's
        # nothing for the aggregator LLM to merge — return it directly.
        if self._has_conversation_text(conversation_text) and not self._has_form_text(form_text):
            aggregated_result = {
                "source": "Aggregator",
                "response": conversation_text,
                "original_results": active_results,
            }
            print("Aggregator: short-circuit (conversation-only). No LLM call.")
            await ctx.yield_output([aggregated_result])
            return

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        aggregator_deployment = (
            os.getenv("AZURE_OPENAI_AGGREGATOR_CHAT_DEPLOYMENT_NAME") or deployment
        )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if api_key and endpoint and aggregator_deployment and api_version:
            try:
                client = self._get_or_create_client(
                    api_key, endpoint, api_version, aggregator_deployment
                )

                system_prompt = _aggregator_system_prompt()

                user_prompt = _aggregator_user_prompt_template().safe_substitute(
                    conversation_text=conversation_text,
                    form_text=form_text,
                    form_step=form_step,
                )

                try:
                    max_completion_tokens = int(
                        os.getenv("AZURE_OPENAI_AGGREGATOR_MAX_COMPLETION_TOKENS", "600")
                    )
                except ValueError:
                    max_completion_tokens = 600

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

                await ctx.yield_output([aggregated_result])
                return

            except Exception as e:
                print(f"Error in Aggregator LLM call: {e}")
        else:
            print("Aggregator: Missing Azure OpenAI credentials (API_KEY, ENDPOINT, DEPLOYMENT, or API_VERSION). Returning raw results.")

        print("Aggregator: Yielding raw results.")
        await ctx.yield_output(active_results)

    def _normalize_results(self, results: Any) -> list[Any]:
        """Normalize single-message and multi-message inputs to a list."""
        if isinstance(results, list):
            return results
        if isinstance(results, tuple):
            return list(results)
        return [results]
