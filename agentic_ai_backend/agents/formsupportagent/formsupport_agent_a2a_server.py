"""
FastAPI A2A Wrapper for Form Support Agent
This is a standalone wrapper that imports and exposes the FormSupportAgent via HTTP
"""
import asyncio
import os
import sys
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# Add parent directories to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agents.formsupportagent.formsupportagent import FormSupportAgent
from agents.formsupportagent.models.formsupportmodel import InvokeRequest, InvokeResponse
from utils.formutils import get_form_context

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Form Support Agent A2A Server",
    description="Agent-to-Agent API Server for BC Government's Water Permit Application Form Support",
    version="1.0.0"
)

# Cache of agent instances per step number (step_number -> agent_instance)
_agent_cache = {}

def get_agent(step_number: int = 2):
    """
    Get or create the agent instance for a specific step.
    
    Args:
        step_number: The form step number (e.g., 2 for step2.json)
    
    Returns:
        FormSupportAgent instance configured for the specified step
    """
    global _agent_cache
    
    # Return cached instance if available
    if step_number in _agent_cache:
        return _agent_cache[step_number]
    
    try:            
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        
        # Load Form Definitions dynamically based on step number
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "formdefinitions", f"step{step_number}.json")
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Form definition file not found: {json_path}")
             
        form_context_str = get_form_context(json_path)
        
        # Create and cache the agent instance
        agent_instance = FormSupportAgent(endpoint, api_key, deployment_name, form_context_str)
        _agent_cache[step_number] = agent_instance
        
        print(f"Created FormSupportAgent for step {step_number}")
        return agent_instance
        
    except Exception as e:
        raise RuntimeError(f"Failed to initialize agent for step {step_number}: {str(e)}")

@app.get("/.well-known/agent.json")
async def agent_manifest():
    """
    Provides the agent's manifest, describing its identity and skills.
    This is the standard A2A discovery endpoint.
    """
    import json
    manifest = os.path.join(os.path.dirname(__file__), "agentmanifest", "manifest.json")
    with open(manifest, "r") as f:
        return json.load(f)

@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """
    Main A2A endpoint to invoke the form support agent.
    Accepts a query, optional session_id, and optional step_number.
    Returns the agent's response based on the specified form step.
    """
    try:
        # Get the step number from request (defaults to 2)
        step_number = request.step_number if request.step_number else 2
        
        # Get agent instance for this step
        agent = get_agent(step_number)
        
        # Run the agent
        result = await agent.run(request.query)
        
        return InvokeResponse(
            response=result,
            session_id=request.session_id
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "FormSupportAgent",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "BC Water Permit Form Support Agent A2A Server",
        "version": "1.0.0",
        "endpoints": {
            "manifest": "/.well-known/agent.json",
            "invoke": "/invoke",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001")) # Using 8001 to avoid conflict with conversation agent
    
    print(f"Starting Form Support Agent A2A Server on {host}:{port}")
    print(f"Agent manifest: http://{host}:{port}/.well-known/agent.json")
    print(f"Invoke endpoint: http://{host}:{port}/invoke")
    print(f"Health check: http://{host}:{port}/health")
    print(f"API docs: http://{host}:{port}/docs")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
