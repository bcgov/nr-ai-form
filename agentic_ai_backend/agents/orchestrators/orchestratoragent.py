"""
Orchestrator Agent using A2A protocol
This version uses A2A to communicate with remote agents instead of direct imports.
"""
import os
import sys
import asyncio
import ast
from agent_framework import Executor, WorkflowBuilder, handler
from agent_framework._workflows._message_utils import normalize_messages_input
from typing_extensions import Never
from typing import Any, Union, Optional
from dotenv import load_dotenv
import uuid


from threadmanagement.redisdbutils import redisdbutils

# Import A2A executors
from workflowcomponents.conversationagentexecutor import ConversationAgentA2AExecutor
from workflowcomponents.formsupportagentexecutor import FormSupportAgentA2AExecutor
from workflowcomponents.dispatcher import Dispatcher
from workflowcomponents.aggregator import Aggregator

load_dotenv()

# Global Redis Utils instance
_redis_utils_instance = None

def get_redis_utils():
    global _redis_utils_instance
    if _redis_utils_instance is None:
        _redis_utils_instance = redisdbutils()
    return _redis_utils_instance


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
    conversation_executor = ConversationAgentA2AExecutor(base_url=conversation_agent_url, session_id=session_id)
    form_support_executor = FormSupportAgentA2AExecutor(
        base_url=form_support_agent_url,
        step_number=step_number,
        session_id=session_id
    )
    
    executors = [conversation_executor, form_support_executor]

    #Dispatcher is NOT attached with an LLM will append memory and PII detection in futre  . 
    dispatcher = Dispatcher(
        id="Dispatcher", 
        name="Dispatcher", 
        instructions="You are a user query dispatcher that forwards the input to the appropriate executor(s). In this case the conversation agent and the form support agent."
    )
    
    #Aggregator is attached with an LLM at the moment, for message curation, and upadte for Multi-turn conversatin . 
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

    #ABIN : as part of SHOWCASE-4181 workflow is transformed as an agent to accomodate multi-turn conversation
    agent = workflow.as_agent(
        "Orchestrator Agent"
    )

    
    thread_id = session_id or str(uuid.uuid4()) #TODO: This UUID is generated for with GUID temp, once we crack the logic from FE, ths will have mapper.
    

    final_data = None
    
    # Get singleton Redis Utils
    db_utils = get_redis_utils()

    try:
        # Load thread state
        thread = await db_utils.get_thread_state(thread_id, agent)
       
        input_messages = normalize_messages_input(query)

        # Pass thread to agent.run() so WorkflowAgent maintains conversation history (b251216+)
        result = await agent.run(input_messages, thread=thread)
        final_data = ast.literal_eval(result.text) if result.text else None

        # Save updated thread state to Redis
        if thread:
            try:
                print(f"Saving thread {thread_id} to Redis...")          
                await db_utils.save_thread_state(thread_id, thread)
                print("Thread state saved.")
            except Exception as e:
                print(f"Error saving thread state: {e}")
        # Add thread_id to response
        if final_data and isinstance(final_data, list):
            final_data.append({"thread_id": thread_id})

    except Exception as e:
        print(f"Error in orchestrate_a2a: {e}")
        # Consider handling appropriately

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
    
    #try:
    asyncio.run(orchestrate_a2a(query, conversation_url, form_support_url, step_number))
    #finally:
        # Cleanup singleton on exit (only for script run)
        #_utils = get_redis_utils()
        #if _utils:
            #asyncio.run(_utils.close())
