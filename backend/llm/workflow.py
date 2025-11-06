"""
Workflow graph and node definitions for LLM agentic flow.
"""
from langgraph.graph import StateGraph, END, START
from typing import TypedDict
from .agents.land_agent import land_executor
from .agents.water_agent import water_executor

class WorkflowState(TypedDict):
    message: str
    formFields: list
    route: str
    response: dict  # response now includes both message and populated formFields

async def orchestrator_node(state: WorkflowState) -> WorkflowState:
    """Orchestrator node that routes to land or water agent."""
    # Dummy routing logic for now
    route = "land" if "land" in state["message"].lower() else "water"
    return {"route": route}

async def land_node(state: WorkflowState) -> WorkflowState:
    result = await land_executor.ainvoke({"message": state["message"]})
    output_text = (
        result.get("output") if isinstance(result, dict) else None
    ) or str(result)
    return {"response": {"message": output_text, "formFields": state["formFields"]}}

async def water_node(state: WorkflowState) -> WorkflowState:
    result = await water_executor.ainvoke({"message": state["message"], "formFields": state["formFields"] })
    output_text = (
        result.get("output") if isinstance(result, dict) else None
    ) or str(result)
    # Assume result may include updated formFields if agent fills them
    populated_fields = result.get("formFields", state["formFields"]) if isinstance(result, dict) else state["formFields"]
    return {"response": {"message": output_text, "formFields": populated_fields}}

workflow = StateGraph(WorkflowState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("land", land_node)
workflow.add_node("water", water_node)
workflow.add_edge(START, "orchestrator")
workflow.add_conditional_edges(
    "orchestrator",
    lambda s: s["route"],
    {
        "land": "land",
        "water": "water",
    },
)
workflow.add_edge("land", END)
workflow.add_edge("water", END)

app_workflow = workflow.compile()
#print(app_workflow.get_graph().draw_ascii())