"""
Form-filling agent based on LangGraph for automatically populating web forms.
This module defines the core agent logic and workflow for auto-filling forms
based on user input and interactive form field completion.
"""
import os
from typing import Dict, List, Any, Optional, TypedDict, Literal,Union
from uuid import uuid4
from dotenv import load_dotenv
from .llm_client import llm as model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
import traceback
import asyncio
from backend.formfiller.agents import analyze_form_executor, process_field_executor
import json
import re
import ast

from .tools.ai_search_tool import ai_search_tool

# simple search function (you could plug in SerpAPI, Tavily, Bing, etc.)
def search_tool(query: str) -> str:
        return ai_search_tool(query)
# Load environment variables
load_dotenv()

# Initialize the model
model = AzureChatOpenAI(
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
    openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)


# Create a checkpointer for persistence
checkpointer = MemorySaver()

# Define form field structure
class FormField(TypedDict):
    """Structure for individual form fields"""
    field_id: str  # Corresponds to data_id in the API model
    fieldLabel: str  # Corresponds to fieldLabel in the API model
    fieldType: str  # input, select, radio, checkbox, textarea, etc. - Corresponds to fieldType
    fieldValue: Optional[Union[str, List[str]]]  # Corresponds to fieldValue in the API model
    required: bool  # Corresponds to is_required in the API model
    options: Optional[List[Dict[str, str]]]  # For dropdown, radio, etc. - Objects with key/value pairs
    description: Optional[str]  # Help text - Not in API model but preserved
    validation: Optional[str]  # Validation rules - Not in API model but preserved

# Define the state structure for our graph
class FormFillerState(TypedDict, total=False):
    """State for the form-filling workflow"""
    user_message: str  # required
    form_fields: list  # optional
    filled_fields: list[dict[str, Any]]  # optional
    missing_fields: list[str]  # optional
    current_field: Optional[List[dict]]  # optional
    #next_field: Optional[List[dict]]  # optional
    conversation_history: List[Dict[str, Any]]  # optional
    status: Literal["in_progress", "awaiting_info", "completed"]  # optional
    response_message: str  # optional
    thread_id: str  # optional

def extract_json_from_output(output: str):
    # Clean up formatting
    output = output.strip().strip("`").strip()

    # Remove "Final Answer:" prefix if present
    if output.startswith("Final Answer:"):
        output = output.replace("Final Answer:", "", 1).strip()

    # Try to extract the JSON block using regex
    match = re.search(r"({.*})", output, re.DOTALL)
    if not match:
        return {
            "error": "Agent failed to complete analysis. No valid JSON found.",
            "raw_output": output
        }

    json_str = match.group(1).strip()

    # Try parsing as real JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass  # Try next method

    # Try parsing as Python dict (e.g., single quotes)
    try:
        return ast.literal_eval(json_str)
    except Exception as e:
        return {
            "error": "Failed to parse output as JSON or Python dict.",
            "exception": str(e),
            "raw_output": json_str
        }

def is_field_filled(field_value) -> bool:
    """
    Check if a field value is properly filled.
    Returns False for None, empty string, empty list, or empty dict.
    """
    if field_value is None:
        return False
    if field_value == "":
        return False
    if isinstance(field_value, list) and len(field_value) == 0:
        return False
    if isinstance(field_value, dict) and len(field_value) == 0:
        return False
    return True

# Node 1: Initial form analysis: orchestrator node
async def analyze_form(state: FormFillerState) -> FormFillerState:
    """
    Orchestrator agent: analyzes user input and form fields, identifies missing fields, and routes to process_field_input if needed.
    """
    # Initialize optional fields if not present
    user_message = state["user_message"]
    form_fields = state.get("form_fields", [])
    filled_fields = state.get("filled_fields", [])
    missing_fields = state.get("missing_fields", [])
    current_field = state.get("current_field")
    conversation_history = state.get("conversation_history", [])
    status = state.get("status", "in_progress")
    response_message = state.get("response_message", "")
    thread_id = state.get("thread_id", str(uuid4()))
    #import pdb; pdb.set_trace()
    # Add conversation history summary for context if available, but avoid duplicate 'content' keys
    if conversation_history:
        history_context = "Previous conversation:\n"
        for entry in conversation_history:
            role_val = entry.get("role")
            content_val = entry.get("content", "")
            if role_val == "user":
                role = "User"
            elif role_val == "assistant":
                role = "Assistant"
            else:
                role = str(role_val) if role_val else "Unknown"
            history_context += f"{role}: {content_val}\n"
        # Only add the summary if it is not already present as a 'content' value
        if not any(entry.get("content", None) == history_context for entry in conversation_history if isinstance(entry, dict)):
            conversation_history.append({"role": "system", "content": history_context})

    # get labels for all the fields
    search_results = search_tool(json.dumps({"message": user_message, "formFields": form_fields}))
    # Get response from the LLM
    response = await analyze_form_executor.ainvoke({"message": user_message, "formFields": form_fields, "search_results": search_results})

    cleaned_str = extract_json_from_output(response['text'])

    if isinstance(cleaned_str, str):
        return {
            **state,
            "filled_fields": [],
            "missing_fields": [],
            "current_field": None,
            "conversation_history": conversation_history,
            "status": "awaiting_info",
            "response_message": cleaned_str,
            "thread_id": thread_id,
        }

    # Update conversation history
    history = conversation_history.copy()
    history.append({"role": "user", "content": user_message})

    # Determine next steps based on missing fields
    new_filled_fields = cleaned_str.get("filled_fields", [])
    # Always append, never overwrite
    if filled_fields is None:
        filled_fields = []
    if new_filled_fields:
        # Only add new fields that are not already present (by data_id)
        existing_ids = {f.get('data_id') for f in filled_fields if isinstance(f, dict)}
        for f in new_filled_fields:
            if isinstance(f, dict) and f.get('data_id') not in existing_ids:
                filled_fields.append(f)

    # Filter missing_fields: remove any whose data_id exists in form_fields and fieldValue is not empty
    raw_missing_fields = cleaned_str.get("missing_fields", [])
    # Build a set of data_ids in form_fields with non-empty fieldValue
    filled_data_ids = set()
    for f in form_fields:
        if isinstance(f, dict) and f.get('data_id'):
            if is_field_filled(f.get('fieldValue')):
                filled_data_ids.add(f['data_id'])
    # Support both str and dict in missing_fields
    missing_fields = []
    for f in raw_missing_fields:
        if isinstance(f, dict):
            if f.get('data_id') not in filled_data_ids:
                missing_fields.append(f)
        else:
            if f not in filled_data_ids:
                missing_fields.append(f)

    status = "completed" if not missing_fields else "awaiting_info"
    current_field = missing_fields[0] if missing_fields else None

    # Generate response based on analysis
    if status == "completed" and filled_fields:
        response_message = "Great! I've filled out the entire form based on your information."
    else:
        response_message = cleaned_str.get("message", "")

    history.append({"role": "assistant", "content": response_message})

    # If there are missing fields, route to process_field_input
    if missing_fields:
        # Call process_field_input directly
        next_state = {
            **state,
            "filled_fields": filled_fields,
            "form_fields": form_fields,
            "missing_fields": missing_fields,
            "current_field": current_field,
            "conversation_history": history,
            "status": "awaiting_info",
            "response_message": response_message,
            "thread_id": thread_id,
        }
        return await process_field_input(next_state)

    return {
        **state,
        "filled_fields": filled_fields,
        "form_fields": form_fields,
        "missing_fields": missing_fields,
        "current_field": current_field,
        "conversation_history": history,
        "status": status,
        "response_message": response_message,
        "thread_id": thread_id,
    }

# Node 2: Process user input for specific field
async def process_field_input(state: FormFillerState) -> FormFillerState:
    """
    Processes user input for a specific requested field. Loops until all fields are filled.
    """
    user_message = state["user_message"]
    filled_fields = state.get("filled_fields", [])
    form_fields = state.get("form_fields", [])
    missing_fields = state.get("missing_fields", [])
    conversation_history = state.get("conversation_history", [])
    current_field = state.get("current_field")
    thread_id = state.get("thread_id", str(uuid4()))
    response_message = state.get("response_message", "")

    # If no current_field or missing_fields, return state
    if not current_field or not missing_fields:
        user_message = state["user_message"]
        filled_fields = state.get("filled_fields", [])
        missing_fields = state.get("missing_fields", [])
        conversation_history = state.get("conversation_history", [])
        current_field = state.get("current_field")
        thread_id = state.get("thread_id", str(uuid4()))

        # If no current_field or missing_fields, return state
        if not current_field or not missing_fields:
            return {
                **state,
                "status": "completed" if not missing_fields else "awaiting_info",
                "thread_id": thread_id,
            }

        # Always work on the current_field (assume it's a dict or list of dicts)
        if isinstance(current_field, list):
            field = current_field[0]
        else:
            field = current_field

        response = await process_field_executor.ainvoke(
            {
                "current_field_details": field,
                "data_id": field.get("data_id"),
                "fieldLabel": field.get("fieldLabel"),
                "fieldType": field.get("fieldType"),
                "is_required": field.get("is_required"),
                "validation_message": field.get("validation_message", ""),
                "options": field.get("options", []),
                "user_message": user_message
            }
        )

        output_text = (response.get("output") if isinstance(response, dict) else None) or str(response)

        try:
            cleaned_str = ast.literal_eval(output_text)
            form_data = json.loads(cleaned_str['text'])
        except Exception:
            form_data = {"status": "failed", "message": "Invalid input format."}

        history = conversation_history.copy()
        history.append({"role": "user", "content": user_message})

        current_field_details_updated = form_data.get('current_field_details')
        success = form_data.get('success', False)
        if isinstance(current_field_details_updated, dict) and success:
            # Always append, never overwrite
            if filled_fields is None:
                filled_fields = []
            # Only add if not already present (by data_id)
            existing_ids = {f.get('data_id') for f in filled_fields if isinstance(f, dict)}
            if current_field_details_updated.get('data_id') not in existing_ids:
                filled_fields.append(current_field_details_updated)
            # Remove from missing_fields
            missing_fields = [f for f in missing_fields if (f.get('data_id') if isinstance(f, dict) else f) != current_field_details_updated['data_id']]

            # Filter missing_fields: remove any whose data_id exists in form_fields and fieldValue is not empty
            filled_data_ids = set()
            for ff in form_fields:
                if isinstance(ff, dict) and ff.get('data_id'):
                    if is_field_filled(ff.get('fieldValue')):
                        filled_data_ids.add(ff['data_id'])
            filtered_missing_fields = []
            for f in missing_fields:
                if isinstance(f, dict):
                    if f.get('data_id') not in filled_data_ids:
                        filtered_missing_fields.append(f)
                else:
                    if f not in filled_data_ids:
                        filtered_missing_fields.append(f)
            missing_fields = filtered_missing_fields

            current_field = missing_fields[0] if missing_fields else None
            status = "completed" if not missing_fields else "awaiting_info"
            response_text = form_data.get("message", "")

            # If more fields to fill, recursively call process_field_input
            if current_field:
                next_state = {
                    **state,
                    "filled_fields": filled_fields,
                    "missing_fields": missing_fields,
                    "current_field": current_field,
                    "conversation_history": history,
                    "status": status,
                    "response": response_text,
                    "thread_id": thread_id,
                }
                return await process_field_input(next_state)

            return {
                **state,
                "filled_fields": filled_fields,
                "form_fields": form_fields,
                "missing_fields": missing_fields,
                "current_field": current_field,
                "conversation_history": history,
                "status": status,
                "response": response_text,
                "thread_id": thread_id,
            }
        else:
            # Not success, keep asking for correct info
            response_text = form_data.get("message", "Please provide the correct information for the field.")
            status = "awaiting_info"
            history.append({"role": "assistant", "content": response_text})
            return {
                **state,
                "conversation_history": history,
                "status": status,
                "response": response_text,
                "thread_id": thread_id,
            }
    else:
        return {
            **state,
            "status": "completed" if not missing_fields else "awaiting_info",
            "thread_id": thread_id,
        }
# Conditional edge function
def route_next_step(state: FormFillerState) -> str:
    """
    Determines the next step in the workflow based on the current state.
    """
    if state["status"] == "completed":
        return END  # Changed from "end" to END constant
    elif state["status"] == "awaiting_info":
        return "human_input" 
    else:
        return "analyze_form"

# Human in the loop node (placeholder)
async def human_input(state: FormFillerState) -> FormFillerState:
    """
    Placeholder node for receiving human input. In a real system, this would be an interrupt
    point where the system waits for user input.
    """
    return state

# Create the graph
form_filler_graph = StateGraph(FormFillerState)

# Add nodes
form_filler_graph.add_node("analyze_form", analyze_form)
form_filler_graph.add_node("process_field_input", process_field_input)
#form_filler_graph.add_node("human_input", human_input)

# Add edges
form_filler_graph.add_edge(START, "analyze_form")
form_filler_graph.add_edge("analyze_form", "process_field_input")
#form_filler_graph.add_conditional_edges("analyze_form", route_next_step)
#form_filler_graph.add_edge("human_input", "process_field_input")
form_filler_graph.add_conditional_edges("process_field_input", route_next_step)
# Remove this line: form_filler_graph.add_edge("end", END)

# Compile the graph with checkpointing and human-in-the-loop support
compiled_graph = form_filler_graph.compile(
    checkpointer=checkpointer
)
print(compiled_graph.get_graph().draw_ascii())

async def chat_analyze_form(state: FormFillerState) -> Dict[str, Any]:
    """
    Analyzes the user message and form fields for the chat-based form-filling process.

    Args:
        user_message: The initial user message
        form_fields: List of form fields to fill
        
    Returns:
        Initial state and response information
    """
    thread_id = str(uuid4())
    
    # initial_state = {
    #     "user_message": state["user_message"],
    #     "form_fields": state["form_fields"],
    #     "filled_fields": [],
    #     "missing_fields": [],
    #     "current_field": None,
    #     #"next_field": None,
    #     "conversation_history": state["user_message"],
    #     "status": "in_progress",
    #     "response_message": "",
    #     "thread_id": thread_id
    # }
    
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await compiled_graph.ainvoke(state, config)
 
        return {
            "thread_id": thread_id,
            "response_message": result["response_message"],
            "status": result["status"],
            "filled_fields": result["filled_fields"],
            "form_fields": result["form_fields"],
            "missing_fields": result["missing_fields"],
            "current_field": result["current_field"],
            "conversation_history": result["conversation_history"]
        }
    except Exception as e:
            print("LangGraph Error:", e)
            traceback.print_exc()
            return {"error": str(e), "traceback": traceback.format_exc()}
