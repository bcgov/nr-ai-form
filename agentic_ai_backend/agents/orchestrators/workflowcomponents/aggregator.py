from agent_framework import Executor, WorkflowContext, handler
from typing import Any
import os
from openai import AsyncAzureOpenAI

class Aggregator(Executor):
    """Aggregate the results from the different tasks and yield the final output."""

    @handler
    async def handle(self, results: list[Any], ctx: WorkflowContext):
        """Receive the results from the source executors.

        The framework will automatically collect messages from the source executors
        and deliver them as a list.

        Args:
            results (list[Any]): execution results from upstream executors.
                The type annotation must be a list of union types that the upstream
                executors will produce.
            ctx (WorkflowContext[Never, list[Any]]): A workflow context that can yield the final output.
        """
        
        # Check if we have OpenAI config
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

        if api_key and endpoint and deployment:
            try:
                client = AsyncAzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=endpoint
                )
                
                # Extract information from results
                conversation_text = ""
                form_text = ""
                form_step = ""
                
                for res in results:
                    if isinstance(res, dict):
                        source = res.get("source", "")
                        if "Conversation" in source:
                            conversation_text = res.get("response", "")
                            print("Conversation Text: ", conversation_text)
                        elif "FormSupport" in source:
                            form_text = res.get("response", "")
                            print("Form Text: ", form_text)
                            form_step = res.get("step_number", "")
                
               
                system_prompt = (
                    "You are a helpful assistant for the applicants of BC Permit Application. "
                    "Your goal is to curate the responses from Form Support Agent and Conversation Agent and provide a single response to the user."
                )
                
                #TODO: ABIN, need to pull from Blob Store for more flexible prompts??? 
                user_prompt = f"""
                You have received information from two sub agents:
                
                1. Conversation Agent (General Info comes from Azure AI Search): 
                {conversation_text}
                
                2. Form Support Agent (Form Specific Info for step '{form_step}'): 
                {form_text}
                
                Your task:
                - Synthesize a single, natural, and helpful response for the user.
                - Synthesized response content of Conversation Agent will come first, then the response content of Form Support Agent.
                - On Step 2 - Eligibility, if the user query is related to 'North Coast Transmission line' or 'BC Hydro Sustainability Project' or 'clean energy project that received a new Energy Purchase Agreement from BC Hydro'or 'increasing the supply of housing units' then discard the responses from Form Support Agent and Conversation Agent, and indicate those queries are not supported for PILOT release.
                - If the conversation agent has "Not found" in response, then you must rely on the Form Support Agent's response.
                - If the Form Support Agent suggests a specific action, YOU MUST PRIORITIZE this action in your response. Guide the user to take that action.
                - For e.g. if the `type` is "button" and `title` is "Apply without BCeID", then you must guide the user "If you'd like to proceed without a BCeID, please click the "Apply without BCeID" button on the form to start your application".
                - *Strict*: if the suggestion from Form Support Agent has `type` is "radio" and then response should indicate like "AI Assistant has selected the option for you."                
                - If the Form Support Agent says "no match" or implies no specific form action is needed right now, rely primarily on the Conversation Agent's information if there are any response from Conversation Agent.
                - Do not mention "Conversation Agent" or "Form Support Agent" by name. Speak as a single entity ("I" or "we").
                - *Strict*: if the conversation agent's response is NOT FOUND, and there is valid 'suggestedvalue' in JSON response from Form Support agent, then response should indicate the action taken by AI Bot's suggestion, rather than directing the user to take action.
                """
                
                completion = await client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],                   
                )
                
                final_text = completion.choices[0].message.content
                
                
                aggregated_result = {
                    "source": "Aggregator",
                    "response": final_text,
                    "original_results": results 
                }

                print("Aggregated Result: ", aggregated_result)
                
                
                await ctx.yield_output([aggregated_result])
                return

            except Exception as e:
                print(f"Error in Aggregator LLM call: {e}")
                # Fallback to returning original results if LLM fails/errors
        else:
            print("Aggregator: Missing Azure OpenAI credentials (API_KEY, ENDPOINT, or DEPLOYMENT). Returning raw results.")
        
        print("Aggregator: Yielding raw results.")
        await ctx.yield_output(results)