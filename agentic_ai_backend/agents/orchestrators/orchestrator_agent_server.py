
"""
FastAPI A2A Wrapper for Orchestrator Agent
"""
import os
import uvicorn
import json
from fastapi import WebSocket,FastAPI, HTTPException
from dotenv import load_dotenv
from typing import Any, List, Optional
from orchestratoragent import orchestrate_a2a

load_dotenv()

from models.orchestratormodel import InvokeRequest, InvokeResponse

#TODO ABIN: This is a temporary A2A enoiinbt for testing and invoke, later on we will use PUB-SUB mechanism from a Queue to use that.

app = FastAPI(
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Orchestrator Agent A2A API",
        "version": "1.0.0",
        "endpoints": {
            "manifest": "/.well-known/agent.json",
            "invoke": "/invoke",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/.well-known/agent.json")
async def agent_manifest():
 
    import json
    manifest = os.path.join(os.path.dirname(__file__), "agentmanifest", "manifest.json")
    if not os.path.exists(manifest):
         raise HTTPException(status_code=404, detail="Manifest not found")
    with open(manifest, "r") as f:
        return json.load(f)

@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):

    try:
        # Get A2A URLs from environment
        conversation_url = os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000")
        form_support_url = os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001")
        step_number = request.step_number or os.getenv("FORM_STEP_NUMBER", "step2-Eligibility")

        # Run the orchestrator logic
        output_event = await orchestrate_a2a(
            query=request.query, 
            conversation_agent_url=conversation_url, 
            form_support_agent_url=form_support_url,
            step_number=step_number,
            session_id=request.session_id
        )
        
        if output_event:
             # The result from orchestrate_a2a is a WorkflowOutputEvent object
             # We want to return something serializable. data is typically a list of messages.
             return InvokeResponse(
                 response=output_event,
                 session_id=request.session_id
             )
        else:
             return InvokeResponse(
                 response="No response from orchestrator.",
                 session_id=request.session_id
             )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.websocket("/ws")
async def invoke_agent_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            request = await websocket.receive_json()
            print(f"Websocket request object:   {request}")
            # request = json.loads(websocket_request)
            # print(f"Websocket parsed request object:   {request}")
            # Get A2A URLs from environment
            conversation_url = os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000")
            form_support_url = os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001")
            step_number = request['step_number'] or os.getenv("FORM_STEP_NUMBER", "step2-Eligibility")

            # Run the orchestrator logic
            output_event = await orchestrate_a2a(
                query=request['query'], 
                conversation_agent_url=conversation_url, 
                form_support_agent_url=form_support_url,
                step_number=step_number,
                session_id=request['session_id']
            )
            
            if output_event:
                # The result from orchestrate_a2a is a WorkflowOutputEvent object
                # We want to return something serializable. data is typically a list of messages.
                response = InvokeResponse(
                    response=output_event,
                    session_id=request['session_id']
                )
                await websocket.send_text(json.dumps(response.dict()))
            else:
                response = InvokeResponse(
                    response="No response from orchestrator.",
                    session_id=request['session_id']
                )
                await websocket.send_text(json.dumps(response.dict()))

    except WebSocketDisconnect:
        print("API Gateway disconnected from Orchestrator Websocket")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "OrchestratorAgent"}

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))
    
    print(f"Starting Orchestrator Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
