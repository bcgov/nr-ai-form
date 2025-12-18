import os
import sys

# TODO ABIN: STARTS HERE - Below code is temporary to allow importing sibling packages, Soon A2A integration will eliminate this hardbinding.
current_dir = os.path.dirname(os.path.abspath(__file__))
agents_dir = os.path.dirname(current_dir)
backend_dir = os.path.dirname(agents_dir)
sys.path.append(agents_dir)  # For importing formsupportagent, conversationagent
sys.path.append(backend_dir)  # For importing utils
# TODO ABIN: END HERE - Below code is temporary to allow importing sibling packages, Soon A2A integration will eliminate this hardbinding.

import asyncio
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, handler
from typing_extensions import Never
from typing import Any
from dotenv import load_dotenv

# Import sibling agent packages
from formsupportagent.formsupportagent import FormSupportAgent
from conversationagent.conversationagent import ConversationAgent
from utils.formutils import get_form_context

load_dotenv()

class Dispatcher(Executor):
    """
    The sole purpose of this executor is to dispatch the input of the workflow to
    other executors.
    """

    @handler    
    async def handle(self, userquery:str, ctx: WorkflowContext[str]):
        if not userquery:
            raise RuntimeError("Input must not be empty.")

        await ctx.send_message(userquery)


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
        await ctx.yield_output(results)


async def orchestrate(query):

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    model =  os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]


    json_path = os.path.join("..","formsupportagent","formdefinitions", "step2.json") #TODO ABIN: Temp code This shoud come form a form or blob store

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
                
    form_context_str = get_form_context(json_path)  

    formsupportagent = FormSupportAgent(endpoint,api_key,deployment_name,form_context_str)
    conversationagent = ConversationAgent(endpoint,api_key)
    executors = [conversationagent.agent, formsupportagent.agent]


    dispatcher = Dispatcher(id="Dispatcher"  , name="Dispatcher" , instructions="You are a dispatcher that forwards the input to the appropriate executor")
    
    aggregator = Aggregator(id="Aggregator"  , name="Aggregator" , instructions="You are an aggregator that aggregates the results from the different executors")


    builder = WorkflowBuilder()

    builder.set_start_executor(dispatcher)
    builder.add_fan_out_edges(dispatcher, executors)   
    builder.add_fan_in_edges(executors, aggregator)
    workflow = builder.build()

    output_evt: WorkflowOutputEvent  | None = None
    async for event in workflow.run_stream(query):
        if isinstance(event, WorkflowOutputEvent):
            output_evt = event

    if output_evt:
        print("===== Final Aggregated Conversation (messages) =====")
        messages: list[Any] = output_evt.data
        for i, item in enumerate(messages, start=1):
            source = "unknown"
            text = str(item)
            
            # Handle AgentExecutorResponse
            if hasattr(item, 'executor_id'):
                source = item.executor_id
                
                # Try to get text from agent_run_response
                if hasattr(item, 'agent_run_response') and hasattr(item.agent_run_response, 'text'):
                    text = item.agent_run_response.text
                elif hasattr(item, 'full_conversation') and item.full_conversation:
                    last_msg = item.full_conversation[-1]
                    if hasattr(last_msg, 'text'):
                        text = last_msg.text
            
            # Handle ChatMessage directly (fallback)
            elif hasattr(item, 'author_name'):
                source = item.author_name if item.author_name else "user"
                text = item.text

            print(f"{'-' * 60}\n\n{i:02d} [{source}]:\n{text}")


   


if __name__ == "__main__":
    query = sys.argv[-1]
    asyncio.run(orchestrate(query))