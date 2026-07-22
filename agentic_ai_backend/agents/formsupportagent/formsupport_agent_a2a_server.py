"""
FastAPI A2A Wrapper for Form Support Agent
This is a standalone wrapper that imports and exposes the FormSupportAgent via HTTP
"""
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from agent_framework import AgentSession, Message
from dotenv import load_dotenv

# Add parent directories to path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agents.formsupportagent.formsupportagent import (
    FormSupportAgent,
    extract_step_from_query,
    resolve_agent_assets
)
from agents.formsupportagent.models.formsupportmodel import (
    FormSupportAgentClientSettings,
    InvokeRequest,
    InvokeResponse,
)
from typing import Union
from services.formdefinitionservice import FormDefinitionService
from services.prompttemplateservice import PromptTemplateService
from utils.blobservice import BlobService
from utils.tenantsettings import (
    AZURE_BLOB_CONNECTION_STRING_ENV,
    AZURE_BLOB_CONTAINER_ENV,
    AZURE_OPENAI_API_KEY_ENV,
    AZURE_OPENAI_ENDPOINT_ENV,
    environment_setting,
    setting_from_client_config,
    settings_cache_parts,
)

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Form Support Agent A2A Server",
    description="Agent-to-Agent API Server for BC Government's Permit Application Form Support Agent",
    version="1.0.0"
)

# Per-session history storage keyed on (session_id, step_identifier)
_session_threads: dict[tuple[str, str], AgentSession] = {}


@dataclass
class _CachedAgent:
    agent: FormSupportAgent
    expires_at: float


_agent_cache: dict[tuple[str, str, str], _CachedAgent] = {}
# Agent cache TTL in seconds. Default is 300s (5 minutes).
# - Set to 0 to disable caching (every request rebuilds the agent from blob — useful during
#   active prompt development so changes take effect immediately).
# - Set to a larger value (e.g. 600) in production when prompts are stable, to reduce blob reads.
# - The cache is keyed on (client_id, config_fingerprint, step_key), so different tenants
#   and different steps each get their own cache entry.
# - Changing a prompt in blob storage will NOT take effect until the TTL expires for that entry.
_AGENT_CACHE_TTL_SECONDS = float(os.getenv("FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS", "300"))


def _agent_cache_key(step_key: str, client_settings: FormSupportAgentClientSettings) -> tuple[str, str, str]:
    client_id, fingerprint = settings_cache_parts(client_settings)
    return (client_id, fingerprint, step_key)


# Source ID the framework's auto-injected InMemoryHistoryProvider reads/writes under.
# History must be seeded into session.state[_HISTORY_SOURCE_ID]["messages"], NOT the
# top-level session.state["messages"], because providers receive a source-scoped state dict
# (see agent_framework _agents.py: state=provider_session.state.setdefault(provider.source_id, {})).
_HISTORY_SOURCE_ID = "in_memory"


def _seed_messages(history) -> list[Message]:
    """Convert orchestrator-provided {role, text} turns into MAF Message objects."""
    return [Message(turn.role, [turn.text]) for turn in history if turn.text and turn.role in ("user", "assistant")]


def _evict_expired_agents() -> None:
    """Remove expired entries from the agent cache to prevent unbounded growth."""
    now = time.monotonic()
    expired = [k for k, v in _agent_cache.items() if now >= v.expires_at]
    for k in expired:
        del _agent_cache[k]



def _resolve_blob_settings(client_settings: FormSupportAgentClientSettings):
    connection_string = environment_setting(AZURE_BLOB_CONNECTION_STRING_ENV, required=True)
    container_name = environment_setting(AZURE_BLOB_CONTAINER_ENV, required=True)
    return connection_string, container_name


def get_agent(step_identifier: Union[int, str], client_settings: FormSupportAgentClientSettings):
    """
    Get or create the agent instance for a specific step.

    Args:
        step_identifier: The form step identifier (e.g., "step3-Add-Well")
        client_settings: Tenant-specific client settings from the orchestrator/Cosmos profile

    Returns:
        FormSupportAgent instance configured for the specified step
    """
    # Convert to string for consistent lookup
    step_key = str(step_identifier)
    cache_key = _agent_cache_key(step_key, client_settings)
    cached = _agent_cache.get(cache_key)
    now = time.monotonic()
    if _AGENT_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
        return cached.agent
    try:
        endpoint = environment_setting(AZURE_OPENAI_ENDPOINT_ENV, required=True)
        api_key = environment_setting(AZURE_OPENAI_API_KEY_ENV, required=True)
        deployment_name = setting_from_client_config(client_settings, "azureOpenaiChatDeploymentName", required=True)
        api_version = setting_from_client_config(client_settings, "azureOpenaiApiVersion", required=True)

        # Load assets from Azure Blob Storage using tenant-aware blob settings
        connection_string, container_name = _resolve_blob_settings(client_settings)
        blob_service = None
        if connection_string and container_name:
            blob_service = BlobService(connection_string)

        form_def_service = FormDefinitionService(blob_service, container_name, client_settings=client_settings) if blob_service else None
        prompt_temp_service = PromptTemplateService(blob_service, container_name, client_settings=client_settings) if blob_service else None

        form_definition, custom_instructions, step_key = resolve_agent_assets(
            step_identifier,
            form_definition_service=form_def_service,
            prompt_template_service=prompt_temp_service,
        )

        if not form_definition:
            raise FileNotFoundError(f"Form definition not found for identifier: {step_key}")


        #form_context_str = get_form_context(form_definition)
        form_context_str = json.dumps(form_definition)

        if not custom_instructions:
            raise FileNotFoundError(f"No prompt template found for step: {step_key}. A specialized prompt is required.")

        # Create and cache the agent instance when caching is enabled.
        # Evict stale entries before inserting to prevent unbounded growth.
        if _AGENT_CACHE_TTL_SECONDS > 0:
            _evict_expired_agents()
        agent_instance = FormSupportAgent(
            endpoint,
            api_key,
            deployment_name,
            api_version,
            form_context_str,
            instructions=custom_instructions,
            client_settings=client_settings,
        )
        if _AGENT_CACHE_TTL_SECONDS > 0:
            _agent_cache[cache_key] = _CachedAgent(
                agent=agent_instance,
                expires_at=time.monotonic() + _AGENT_CACHE_TTL_SECONDS,
            )
        return agent_instance

    except Exception as e:
        raise RuntimeError(f"Failed to initialize agent for step {step_key}: {str(e)}")

@app.get("/.well-known/agent.json")
async def agent_manifest():
    """
    Provides the agent's manifest, describing its identity and skills.
    This is the standard A2A discovery endpoint.
    """
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
        agent = get_agent(step_identifier, client_settings=request.client_settings)

        # Resolve session for this session+step combination
        print(f"[HISTDEBUG] invoke session={request.session_id} step={step_identifier} "
              f"history_turns={len(request.history) if request.history else 0}")
        session = None
        if request.session_id:
            session_key = (request.session_id, str(step_identifier))
            session = _session_threads.get(session_key)
            if session is None:
                session = agent.agent.create_session(session_id=request.session_id)
                if request.history:
                    for turn in request.history:
                        if turn.role in ("user", "assistant") and turn.text:
                            print(f"[HISTDEBUG] cache MISS -> seeding session {session_key} with turn: role={turn.role}, text={turn.text}")
                    seeded = _seed_messages(request.history)
                    # Seed into the history provider's source-scoped state, not the top-level
                    # state dict — the InMemoryHistoryProvider only reads state["in_memory"]["messages"].
                    session.state.setdefault(_HISTORY_SOURCE_ID, {})["messages"] = seeded
                    print(f"[HISTDEBUG] cache MISS -> seeded new session {session_key} "
                          f"with {len(seeded)} messages")
                else:
                    print(f"[HISTDEBUG] cache MISS -> new session {session_key}, no history provided")
                # Persist the freshly created session so subsequent turns reuse it (cache HIT)
                # and the framework's after_run-saved history accumulates across requests.
                _session_threads[session_key] = session
            else:
                print(f"[HISTDEBUG] cache HIT for {session_key} (using existing in-memory session)")
        # Run the agent with the cleaned query (or original if no step was found)
        result = await agent.run(query, session=session)

        return InvokeResponse(
            response=result,
            session_id=request.session_id
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception('Form Support Agent invoke exception')
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
        "name": "BC Government Permit Form Support Agent A2A Server",
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
