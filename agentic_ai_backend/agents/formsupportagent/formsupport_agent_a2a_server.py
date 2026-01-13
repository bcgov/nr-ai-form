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

from agents.formsupportagent.formsupportagent import (
    FormSupportAgent, 
    extract_step_from_query, 
    resolve_agent_assets
)
from agents.formsupportagent.models.formsupportmodel import InvokeRequest, InvokeResponse
from utils.formutils import get_form_context
from typing import Union
from services.formdefinitionservice import FormDefinitionService
from services.prompttemplateservice import PromptTemplateService
from utils.blobservice import BlobService

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Form Support Agent A2A Server",
    description="Agent-to-Agent API Server for BC Government's Water Permit Application Form Support",
    version="1.0.0"
)

# Initialize Blob Services
blob_connection_string = os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
blob_container = os.getenv("AZURE_BLOBSTORAGE_CONTAINER")
form_def_service = None
prompt_temp_service = None

if blob_connection_string and blob_container:
    try:
        blob_service = BlobService(blob_connection_string)
        form_def_service = FormDefinitionService(blob_service, blob_container)
        prompt_temp_service = PromptTemplateService(blob_service, blob_container)
        print(f"Initialized Blob Services for container: {blob_container}")
    except Exception as e:
        print(f"Failed to initialize Blob Services: {e}")

# Cache of agent instances per step number (step_number -> agent_instance)
_agent_cache = {}

def get_agent(step_identifier: Union[int, str]):
    """
    Get or create the agent instance for a specific step.
    
    Args:
        step_identifier: The form step identifier (e.g., "step3-Add-Well")
    
    Returns:
        FormSupportAgent instance configured for the specified step
    """
    global _agent_cache#TODO ABIN: Need to implement agent caching on an distributed cache. 
    
    # Convert to string for consistent lookup
    step_key = str(step_identifier)
    
    # Return cached instance if available
    if step_key in _agent_cache:
        return _agent_cache[step_key]
    
    try:            
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        
        # Load assets using shared utility
        form_definition, custom_instructions, step_key = resolve_agent_assets(
            step_identifier, 
            form_definition_service=form_def_service, 
            prompt_template_service=prompt_temp_service
        )
        
        if not form_definition:
            raise FileNotFoundError(f"Form definition not found for identifier: {step_key}")

        # get_form_context handles dict or string path (though we expect dict from service or dict/content from local fallback now)
        form_context_str = get_form_context(form_definition)
        
        if not custom_instructions:
            raise FileNotFoundError(f"No prompt template found for step: {step_key}. A specialized prompt is required.")
        
        # Create and cache the agent instance
        agent_instance = FormSupportAgent(endpoint, api_key, deployment_name, form_context_str, instructions=custom_instructions)
        _agent_cache[step_key] = agent_instance #TODO ABIN: Need to implement agent caching on an distributed cache. 
        
        print(f"Created FormSupportAgent for step {step_key}")
        return agent_instance
        
    except Exception as e:
        raise RuntimeError(f"Failed to initialize agent for step {step_key}: {str(e)}")

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
        # Try to extract step from query string (e.g. "step3: my query")
        extracted_step, cleaned_query = extract_step_from_query(request.query)
        
        # Use the most specific identifier available
        step_identifier = extracted_step or request.step_number
        query = cleaned_query
        
        # Verify step_identifier is present
        if not step_identifier:
            raise HTTPException(status_code=400, detail="step_number is required either in the request body or as a prefix in the query (e.g. 'step1: query')")
            
        # Get agent instance for this step
        agent = get_agent(step_identifier)
        
        # Run the agent with the cleaned query (or original if no step was found)
        result = await agent.run(query)
        
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
