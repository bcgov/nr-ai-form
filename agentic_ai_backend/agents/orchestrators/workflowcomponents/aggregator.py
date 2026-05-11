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

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if api_key and endpoint and deployment and api_version:
            try:
                client = AsyncAzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=endpoint,
                    azure_deployment=deployment,
                )

                conversation_text = ""
                form_text = ""
                form_step = ""

                for res in active_results:
                    if isinstance(res, dict):
                        source = res.get("source", "")
                        if "Conversation" in source:
                            conversation_text = res.get("response", "")
                            print("Conversation Text: ", conversation_text)
                        elif "FormSupport" in source:
                            raw_form = res.get("response", "")
                            form_text = (
                                json.dumps(raw_form)
                                if isinstance(raw_form, (dict, list))
                                else raw_form
                            )
                            print("Form Text: ", form_text)
                            form_step = res.get("step_number", "")

                system_prompt = (
                    "You are a helpful assistant for the applicants of BC Permit Application. "
                    "Your goal is to curate the responses from Form Support Agent and Conversation Agent and provide a single response to the user. "
                    "When including URLs or web links in your response, never append punctuation (such as a period, comma, or parenthesis) immediately after the URL. "
                    "Always ensure the URL is the last character before a space or end of line. For example, write 'visit www.bceid.ca/aboutbceid for more info' not 'visit www.bceid.ca/aboutbceid. for more info'."
                )

                #TODO: ABIN, need to pull from Blob Store for more flexible prompts???
                user_prompt = f"""
                You have received information from two sub agents:

                1. Conversation Agent (General Info comes from Azure AI Search):
                {conversation_text}

                2. Form Support Agent (Form Specific Info for step '{form_step}'):
                {form_text}

                Your task:
                - Synthesize a single, natural, and helpful response for the user only from subagent's response.
                - If the conversation agent has "Not found" in response, then you must rely on the Form Support Agent's response.
                - if user ask about the Water Sustainability Act, then response something like, I'll guide you step by step and let you know when something from the Act is relevant, so you can focus on completing the application without needing to interpret the legislation on your own" **. Do NOT tell the user to read any documents, and do NOT mention you do not have any information.
                - If the Form Support Agent suggests a specific action, YOU MUST PRIORITIZE this action in your response. Guide the user to take that action.
                - You are a single-turn document generator. Do not ask questions and do not include any follow-up or conversational sentences. Do not append advice, recommendations, or invitations for further input.
                - For e.g. if the `type` is "button" and `title` is "Apply without BCeID", then you must guide the user "If you'd like to proceed without a BCeID, please click the "Apply without BCeID" button on the form to start your application".
                - On step 3 - Technical Information, If there are any calculations involved, DO NOT use LATEX to display those calculations. Just write it out as a simple text.
                - *Strict*: if the suggestion from Form Support Agent has `type` is "radio" or `type` is "select" then the response should indicate like "AI Assistant has selected the option for you."
                - *Strict*: if the suggestion from Form Support Agent has `type` is "string" then the response should acknowledge that the information has been filled in for the user (e.g., "AI Assistant has filled in your supporting information details for you.")
                - If the Form Support Agent says "no match" or implies no specific form action is needed right now, rely primarily on the Conversation Agent's information if there are any response from Conversation Agent.
                - Do not mention "Conversation Agent" or "Form Support Agent" by name. Speak as a single entity ("I" or "we").
                - Do not send a JSON in the aggregated response; Only the original results can contain the respective responses from Conversation Agent and Form Support Agent.
                - *Strict*: if the conversation agent's response is NOT FOUND, and there is valid 'suggestedvalue' in JSON response from Form Support agent, then response should indicate the action taken by AI Bot's suggestion, rather than directing the user to take action.
                - *Strict*: Preserve all Markdown links exactly as they appear in the sub-agent responses. If a sub-agent provides a link in the format [text](url), you MUST keep it in that exact format in your response. Never convert a Markdown link into a bare URL. If you introduce any new URLs yourself, also format them as Markdown links using [descriptive text](url).
                - **Strict*: If the user queries like "Does the water sustainability act apply to me ?" or "applicability of water sustainability act with the application", IGNORE responses from Conversation Agent(ConversationAgentA2A)  and Form Support Agent(FormSupportAgentA2A) , ** AI Assistant SHOULD ALWAYS answer like "For the purposes of your application, you don't need to review the entire Water Sustainability Act right now. As you move through the application, AI Assistant automatically consider any relevant impacts, implications, or interactions with the water sustainility act that apply to your situation.
                - If none of the agent is not able to provide any response, then redirect the user to contact FrontCounter BC for support at [FrontCounter BC](http://www.frontcounterbc.gov.bc.ca/).
                - **Strict*: In step 7 if user ask any about these keywords "consultant", "lawyer","notary","representative","representation agreement","power of attorney", "trustee","executor","administrator","board member","employee","owner","family member","friend","neighbour","trustee in bankruptcy","appointment letter","copy of will","authorization letter", ignore the conversation agent and form agent reponse and always like reponse like for more info contact frontcounterbc at [FrontCounter BC](http://www.frontcounterbc.gov.bc.ca/).
                """
                completion = await client.chat.completions.create(
                    model=deployment,
                    temperature=0.1,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                )

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
