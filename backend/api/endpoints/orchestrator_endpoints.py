from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from langgraph.graph import END, StateGraph, START
from pydantic import BaseModel
from backend.core.logging import get_logger
import json

# Imports for agent invoke functions (assuming module names; adjust based on actual file structure)
from backend.api.agents.source_agent import invoke_source_agent
from backend.api.agents.permissions_agent import invoke_permissions_agent
from backend.api.agents.usage_agent import invoke_usage_agent
from backend.api.agents.orchestrator_agent import orchestrator_executor

logger = get_logger(__name__)
load_dotenv()


# Form field model for the JSON array
class FormField(BaseModel):
    """Model for individual form fields"""

    data_id: str = None
    fieldLabel: str = None
    fieldType: str = None
    fieldValue: str = None


# Base request model for POST endpoint
class RequestModel(BaseModel):
    """Base request model for the POST endpoint"""

    message: str
    formFields: Optional[List[FormField]] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# Base response model
class ResponseModel(BaseModel):
    """Base response model for the POST endpoint"""

    status: str
    message: str
    data: Any = None
    timestamp: str


# Define workflow state
class WorkflowState(TypedDict):
    """State structure for the LangGraph workflow."""

    input: str
    form_fields: Optional[List[FormField]]
    orchestrator_output: str
    source_output: Dict[str, Any]  # Changed to Dict since this returns a dictionary
    permissions_output: str
    usage_output: str


# Define workflow nodes (async for compatibility)
async def orchestrator_node(state: WorkflowState) -> WorkflowState:
    """Orchestrator node that decides delegation"""
    try:
        result = await orchestrator_executor.ainvoke({"input": state["input"]})
        return {"orchestrator_output": result["output"]}
    except Exception as e:
        logger.error(f"Error in orchestrator node: {str(e)}")
        return {"orchestrator_output": f"Error: {str(e)}"}


async def source_node(state: WorkflowState) -> WorkflowState:
    """Source node that processes the request"""
    try:
        result = await invoke_source_agent(state["input"], state["form_fields"])
        return {"source_output": result}
    except Exception as e:
        logger.error(f"Error in source node: {str(e)}")
        # Return an error as a dictionary to maintain consistent typing
        return {"source_output": {
            "agent": "SourceAgent", 
            "query": state.get("input", ""),
            "documents": [],
            "message": f"Error: {str(e)}"
        }}


async def permissions_node(state: WorkflowState) -> WorkflowState:
    """Permissions node that processes the request"""
    try:
        result = await invoke_permissions_agent(state["input"], state["form_fields"])
        return {"permissions_output": result}
    except Exception as e:
        logger.error(f"Error in permissions node: {str(e)}")
        return {"permissions_output": f"Error: {str(e)}"}


async def usage_node(state: WorkflowState) -> WorkflowState:
    """Usage node that processes the request"""
    try:
        result = await invoke_usage_agent(state["input"], state["form_fields"])
        return {"usage_output": result}
    except Exception as e:
        logger.error(f"Error in usage node: {str(e)}")
        return {"usage_output": f"Error: {str(e)}"}


# Routing function for conditional delegation
def route_after_orchestrator(state: WorkflowState) -> str:
    """
    Determine which agent to route to based on orchestrator output.
    Returns a single key that matches one of the keys in edge_map.
    """
    output = state.get("orchestrator_output", "").lower()
    
    # Check for different agents in output
    # Priority order: source, usage, permissions (if uncommented)
    if "source" in output:
        return "source"
    if "permissions" in output:
        return "permissions"
    if "usage" in output:
        return "usage"
    
    # Default case if no matches
    return END


# Create the workflow
workflow = StateGraph(WorkflowState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("source", source_node)
workflow.add_node("permissions", permissions_node)
workflow.add_node("usage", usage_node)
workflow.set_entry_point("orchestrator")
# Define routing map based on possible return values from route_after_orchestrator
edge_map = {
    "source": "source",             # If only source is returned
    "usage": "usage",               # If only usage is returned
    "permissions": "permissions",  # If only permissions is returned
    END: END                        # If empty list is returned
}

# Add conditional edge from orchestrator to other nodes
workflow.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    edge_map
)
workflow.add_edge(START, "orchestrator")
workflow.add_edge("source", END)
workflow.add_edge("permissions", END)
workflow.add_edge("usage", END)
# Compile the workflow
app_workflow = workflow.compile()
print(app_workflow.get_graph().draw_ascii())
router = APIRouter()


@router.post("/process", response_model=ResponseModel)
async def process_request(request: RequestModel):
    """
    Main POST endpoint to receive and process requests
    This endpoint uses the orchestrator agent to process incoming requests.
    """
    try:
        logger.info("Processing request", request=request)
        # Use the LangGraph workflow to process the request (async)
        workflow_result = await app_workflow.ainvoke(
            {"input": request.message, "form_fields": request.formFields}
        )
        logger.info("Workflow result", result=workflow_result)
        # Synthesize outputs (simple concatenation; improve with LLM if needed)
        outputs = []
        
        # Add orchestrator output if available
        orchestrator_output = workflow_result.get("orchestrator_output", "")
        if orchestrator_output:
            outputs.append(orchestrator_output)
        
        # Handle source_output which is now a dict
        source_output = workflow_result.get("source_output", {})
        if isinstance(source_output, dict):
            # Create a nicely formatted string representation of the source output
            source_message = source_output.get('message', '')
            documents = source_output.get('documents', [])
            
            source_output_parts = []
            if source_message:
                source_output_parts.append(f"Source Agent Message: {source_message}")
            
            if documents:
                source_output_parts.append("Relevant Documents:")
                for i, doc in enumerate(documents[:3], 1):  # Show only top 3 documents
                    snippet = doc.get('snippet', '')
                    if snippet:
                        source_output_parts.append(f"  {i}. {snippet[:200]}...")
            
            if source_output_parts:
                outputs.append("\n".join(source_output_parts))
            else:
                outputs.append("Source Agent: No relevant information found")
        elif source_output:
            # Fallback for any string outputs (shouldn't happen after our fixes)
            outputs.append(str(source_output))
            
        # Add usage output if available
        usage_output = workflow_result.get("usage_output", "")
        if usage_output:
            outputs.append(f"Usage Agent: {usage_output}")
        
        # Add permissions output when implemented
        permissions_output = workflow_result.get("permissions_output", "")
        if permissions_output:
            outputs.append(f"Permissions Agent: {permissions_output}")
        
        synthesized_output = "\n".join(outputs).strip()
        # Process the request with workflow results (handle missing outputs if not delegated)
        processed_data: Any = {
            # "received_message": request.message,
            "orchestrator_output": workflow_result.get("orchestrator_output"),
            "source_output": workflow_result.get("source_output"),  # Preserving original structure for API
            "permissions_output": workflow_result.get("permissions_output"),
            "usage_output": workflow_result.get("usage_output"),
            "synthesized_output": synthesized_output
            if synthesized_output
            else "No agent outputs generated.",
            "received_form_fields": request.formFields,
            "received_data": request.data,
            "received_metadata": request.metadata,
            "processed_at": datetime.now().isoformat(),
        }
        return ResponseModel(
            status="success",
            message="Request processed successfully by orchestrator agent",
            data=processed_data,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(
            "Error processing orchestrator request",
            error=str(e),
            error_type=type(e).__name__,
            request_message=request.message,
            form_fields_count=len(request.formFields) if request.formFields else 0,
            timestamp=datetime.now().isoformat(),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=(f"Error processing request: {str(e)}")
        )
