"""
Orchestrator Agent using A2A protocol
This version uses A2A to communicate with remote agents instead of direct imports.
"""
import os
import sys
import asyncio
from agent_framework import Executor, WorkflowBuilder, handler
from agent_framework import ChatMessage, Role
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
    conversation_executor = ConversationAgentA2AExecutor(base_url=conversation_agent_url)
    form_support_executor = FormSupportAgentA2AExecutor(
        base_url=form_support_agent_url,
        step_number=step_number
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

        workflow_result = await agent.workflow.run(input_messages)
        outputs = workflow_result.get_outputs()
        if outputs:
            # The Aggregator calls ctx.yield_output([aggregated_result])
            # so outputs[0] is the list directly; unwrap if needed.
            first_output = outputs[0]
            if isinstance(first_output, list):
                final_data = first_output
            else:
                final_data = outputs

        if thread and final_data:
            from agent_framework import ChatMessage, Role
            # Build a response ChatMessage from the aggregated result text
            aggregated_text = ""
            if isinstance(final_data, list) and final_data:
                agg = final_data[0]
                if isinstance(agg, dict):
                    aggregated_text = agg.get("response", str(agg))
                else:
                    aggregated_text = str(agg)
            response_messages = [ChatMessage(role=Role.ASSISTANT, text=aggregated_text)] if aggregated_text else []
            await agent._notify_thread_of_new_messages(thread, input_messages, response_messages)

        # Save Thread State
        if thread:
            try:
                print(f"Saving thread {thread_id} to Redis...")          
                await db_utils.save_thread_state(thread_id, thread)
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
