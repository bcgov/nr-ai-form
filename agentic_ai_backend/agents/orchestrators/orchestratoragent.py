"""
Orchestrator Agent using A2A protocol
This version uses A2A to communicate with remote agents instead of direct imports.
"""
import os
import sys
import asyncio
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, handler
from typing_extensions import Never
from typing import Any, Union
from dotenv import load_dotenv

# Import A2A executors
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.aggregator import Aggregator

load_dotenv()


async def orchestrate_a2a(query: str, 
                          conversation_agent_url: str = "http://localhost:8000",
                          form_support_agent_url: str = "http://localhost:8001",
                          step_number: Union[int, str] = "step2-Eligibility"):
    """
    Orchestrate using A2A protocol to communicate with remote agents.
    
    Args:
        query: User query to process
        conversation_agent_url: Base URL of the Conversation Agent A2A server
        form_support_agent_url: Base URL of the Form Support Agent A2A server
        step_number: Form step number for the Form Support Agent (default: 2)
    """
    
    # Create A2A executors
    conversation_executor = ConversationAgentA2AExecutor(base_url=conversation_agent_url)
    form_support_executor = FormSupportAgentA2AExecutor(
        base_url=form_support_agent_url,
        step_number=step_number
    )
    
    executors = [conversation_executor, form_support_executor]

    # Create workflow components
    dispatcher = Dispatcher(
        id="Dispatcher", 
        name="Dispatcher", 
        instructions="You are a user query dispatcher that forwards the input to the appropriate executor(s). In this case the conversation agent and the form support agent."
    )
    
    aggregator = Aggregator(
        id="Aggregator", 
        name="Aggregator", 
        instructions="You are an aggregator that aggregates the results from the different executors. In this case the conversation agent and the form support agent."
    )

    # Build the workflow
    builder = WorkflowBuilder()
    builder.set_start_executor(dispatcher)
    builder.add_fan_out_edges(dispatcher, executors)   
    builder.add_fan_in_edges(executors, aggregator)
    workflow = builder.build()

    # Run the workflow
    output_evt: WorkflowOutputEvent | None = None
    async for event in workflow.run_stream(query):
        if isinstance(event, WorkflowOutputEvent):
            output_evt = event

    # Process and display results
    if output_evt:
        print("===== Final Aggregated Conversation (A2A) from Orchestrator Agent=====")
        messages: list[Any] = output_evt.data
        for i, item in enumerate(messages, start=1):
            source = "unknown"
            text = str(item)
            
            # Handle dict responses from A2A executors (most common case)
            if isinstance(item, dict):
                source = item.get('source', 'unknown')
                text = item.get('response', str(item))
            
            # Handle AgentExecutorResponse
            elif hasattr(item, 'executor_id'):
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
    
    return output_evt


if __name__ == "__main__":
    # Get query from command line or use default
    query = sys.argv[-1] if len(sys.argv) > 1 else "What is the water permit application process?"
    
    # Get A2A URLs from environment or use defaults
    conversation_url = os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000")
    form_support_url = os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001")
    
    # Get step number from environment or use default
    step_number = os.getenv("FORM_STEP_NUMBER", "step2-Eligibility")
    
    print(f"Starting Orchestrator with A2A communication")
    print(f"Conversation Agent: {conversation_url}")
    print(f"Form Support Agent: {form_support_url}")
    print(f"Form Step: {step_number}")
    print(f"Query: {query}\n")
    
    asyncio.run(orchestrate_a2a(query, conversation_url, form_support_url, step_number))
