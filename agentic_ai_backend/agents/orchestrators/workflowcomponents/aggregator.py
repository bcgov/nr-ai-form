from agent_framework import Executor, WorkflowContext, handler
from typing import Any
from typing_extensions import Never
import json
import os
from openai import AsyncAzureOpenAI

from models.intentmodel import IntentListModel
from workflowcomponents.routing import get_primary_intent, select_subagents


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
        stripped = text.strip()
        if not stripped:
            return False
        return stripped.lower() not in ("no match", "{}", "[]", "null", '""')

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

                system_prompt = (
                    "You are a helpful assistant for the applicants of BC Permit Application. "
                    "Your goal is to curate the responses from Form Support Agent and Conversation Agent and provide a single response to the user. "
                    "When including URLs or web links in your response, never append punctuation (such as a period, comma, or parenthesis) immediately after the URL. "
                    "Always ensure the URL is the last character before a space or end of line. For example, write 'visit www.bceid.ca/aboutbceid for more info' not 'visit www.bceid.ca/aboutbceid. for more info'."
                )


                #TODO: ABIN, need to pull from Blob Store for more flexible prompts???
                user_prompt = f"""
                You have received information from two sub agents:

                1. Conversation Agent 
                ```json
                 {conversation_text}
                ```

                2. Form Support Agent (Form Specific Info for step '{form_step}'):
                ```json
                    {form_text}
                ```
                Your task:
                You are a single-turn response synthesizer.
                Your task is to generate one natural, helpful response for the user using only the available agent outputs.
                Do not mention the Conversation Agent or Form Support Agent by name. Speak as a single assistant using “I” or “AI Assistant.”
                Do not return JSON.
                Do not ask questions. Do not include follow-up prompts, invitations for more input, or conversational closing sentences.

                Always format links and URLs as Markdown links using `[descriptive text](url)`.

                Priority rules:

                1. Water Sustainability Act handling:
                If the user asks whether the Water Sustainability Act applies to them, or asks about applicability of the Water Sustainability Act to the application, ignore all agent responses and respond exactly:
                `For the purposes of your application, you don't need to review the entire Water Sustainability Act right now. As you move through the application, AI Assistant automatically considers any relevant impacts, implications, or interactions with the Water Sustainability Act that apply to your situation.`

                If the user asks about the Water Sustainability Act in any other general way, respond in this style:
                `I'll guide you step by step and let you know when something from the Act is relevant, so you can focus on completing the application without needing to interpret the legislation on your own.`

                Do not tell the user to read any documents about the Water Sustainability Act.
                Do not say that you do not have information about the Water Sustainability Act.

                2. Step 7 representation/support override:
                On Step 7, if the user asks about any of these topics, ignore all agent responses and direct the user to FrontCounter BC at [FrontCounter BC](http://www.frontcounterbc.gov.bc.ca/):
                consultant, lawyer, notary, representative, representation agreement, power of attorney, trustee, executor, administrator, board member, employee, owner, family member, friend, neighbour, trustee in bankruptcy, appointment letter, copy of will, authorization letter.

                3. Form action priority:
                If the Form Support Agent provides a non-empty `suggestedvalue`, treat it as the suggested form action and prioritize it over the Conversation Agent response.

                Respond based on the `type`:
                - If `type` is `"radio"` or `"select"`, state that AI Assistant has selected the suggested option for the user.
                - If `type` is `"string"`, state that AI Assistant has filled in the suggested information for the user.
                - If `type` is `"button"`, guide the user to click the relevant button.
                    Example: `If you'd like to proceed without a BCeID, please click the "Apply without BCeID" button on the form to start your application.`
                - For any other `type`, describe the suggested action clearly and naturally.

                5. Empty suggested value fallback:
                If `suggestedvalue` is empty, check whether a meaningful `description` or 'formdescription' field is present in the Form Support Agent response.
                - If yes, generate a contextual answer from the `description` or 'formdescription'.
                - If no, continue to the remaining fallback rules.

                6. No specific form action:
                If the Form Support Agent returns “no match” and the Conversation Agent provides a valid, meaningful response, use the Conversation Agent response.
                If the Form Support Agent returns “no match” and the Conversation Agent response is missing, empty, invalid, or unavailable, treat this as no useful response.

                7. Conversation Agent not found:
                If the Conversation Agent returns “Not found” and the Form Support Agent provides a valid, meaningful response, use the Form Support Agent response.
                If the Conversation Agent returns “Not found” and the Form Support Agent response is missing, empty, invalid, or unavailable, treat this as no useful response.

                8. No useful response:
                If neither agent responds, neither agent provides a valid, meaningful response, the only available response is “Not found,” the only available response is “no match,” both agents return “no match,” or any available agent response is an error message, direct the user to contact [FrontCounter BC](http://www.frontcounterbc.gov.bc.ca/).

                9. No unsupported content:
                Do not make up, infer, or add information that is not supported by the agent responses.
                The final response must rely only on valid, meaningful content from the provided agent responses.
                Error messages, failed tool calls, HTTP errors, timeout messages, internal server errors, empty responses, “Not found,” and “no match” are not valid content.
                If there is no valid agent response to rely on, direct the user to contact [FrontCounter BC](http://www.frontcounterbc.gov.bc.ca/).

                Formatting and content rules:
                10. On Step 3, Technical Information, if calculations are involved, do not use LaTeX. Write calculations as plain text.
                11. Generate only the final user-facing response. Do not explain which rule was applied.
                """

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
                if "gpt-5" in aggregator_deployment.lower():
                    request_kwargs["reasoning_effort"] = "minimal"

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
