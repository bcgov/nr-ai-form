"""
Orchestrator Agent using A2A protocol
This version uses A2A to communicate with remote agents instead of direct imports.
"""
import os
import sys
import asyncio
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, handler
from typing_extensions import Never
from typing import Any, Union, Optional
from dotenv import load_dotenv
import uuid

# Import CosmosDBService
from utils.cosmosdbservice import CosmosDBService

# Import A2A executors
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.aggregator import Aggregator

load_dotenv()



async def orchestrate_a2a(query: str, 
                          conversation_agent_url: str = "http://localhost:8000",
                          form_support_agent_url: str = "http://localhost:8001",
                          step_number: Union[int, str] = "step2-Eligibility",
                          session_id: Optional[str] = None):
    """
    Orchestrate using A2A protocol to communicate with remote agents.
    
    Args:
        query: User query to process
        conversation_agent_url: Base URL of the Conversation Agent A2A server
        form_support_agent_url: Base URL of the Form Support Agent A2A server
        step_number: Form step number for the Form Support Agent (default: 2)
        session_id: Optional session ID for thread persistence
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

    agent = workflow.as_agent(
        "Orchestrator Agent"
    )

    # Initialize Thread
    thread = None
    cosmos_service = None
    thread_id = session_id or str(uuid.uuid4())

    try:
        # Initialize Cosmos DB Service
        connection_string = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
        container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
        cosmos_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
        cosmos_api_key = os.getenv("AZURE_COSMOS_DB_KEY")
        environment = os.getenv("CSSAI_EXECUTION_ENV","localhost")
        
        if connection_string:
            cosmos_service = CosmosDBService(connection_string=None, endpoint=cosmos_endpoint, cosmosapi_key=cosmos_api_key, database_name=database_name, environment=environment)
            
            # Try to load existing thread
            if session_id:
                print(f"Loading thread {session_id} from Cosmos DB...")
                thread_state = await cosmos_service.load_item(container_name, session_id, session_id)
                if thread_state:
                    print("Thread state found. Resuming conversation.")
                    thread = await agent.deserialize_thread(thread_state)
                else:
                    print("Thread state not found. Creating new thread.")
        else:
            print("Warning: AZURE_COSMOS_CONNECTION_STRING not set. Thread persistence disabled.")

    except Exception as e:
        print(f"Error initializing Cosmos DB or loading thread: {e}")

    # Create new thread if not loaded
    if thread is None:
        print("Creating new thread.")
        thread = agent.get_new_thread()

    # Run the workflow
    accumulated_text = ""
    async for event in agent.run_stream(query, thread=thread):
        if hasattr(event, "text"):
            accumulated_text += event.text

    # Parse results
    final_data = None
    if accumulated_text:
        try:
            import ast
            final_data = ast.literal_eval(accumulated_text)
        except Exception as e:
            print(f"Could not parse accumulated text as data: {e}")
            final_data = None

    # Save Thread State
    if cosmos_service and thread:
        try:
            print(f"Saving thread {thread_id} to Cosmos DB...")
            state = await thread.serialize()
            item = {
                "id": thread_id,
                "thread_state": state
            }
            await cosmos_service.save_item(container_name, item)
            print("Thread state saved.")
        except Exception as e:
            print(f"Error saving thread state: {e}")

    # Process and display results
    if final_data and isinstance(final_data, list):
        print("===== Final Aggregated Conversation (A2A) from Orchestrator Agent=====")
        messages: list[Any] = final_data
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
    elif accumulated_text:
        print("===== Final Response (Text only) =====")
        print(accumulated_text)
    
    return final_data


if __name__ == "__main__":
    # Get query from command line or use default
    query = sys.argv[-1] if len(sys.argv) > 1 else "What is the BC government permit application process for Water License Application?"
    
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
