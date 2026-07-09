"""
FastAPI A2A Wrapper for Orchestrator Agent
"""
import json
import logging
import os
import uuid
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from clientprofiles import (
    ClientIdRequiredError,
    ClientProfileNotFoundError,
    TenantConfigInvalidError,
    TenantConfigUnavailableError,
)
from orchestratoragent import orchestrate_a2a
from tenantconfigservice import get_tenant_config_service
from tenantcors import tenant_cors_middleware
from telemetry import OpenTelemetryAzureMonitorTelemetry, create_telemetry_middleware

load_dotenv()

from models.orchestratormodel import InvokeRequest, InvokeResponse

logger = logging.getLogger(__name__)

# TODO ABIN: This is a temporary A2A endpoint for testing and invoke. Later we
# will use a pub-sub mechanism from a queue.
app = FastAPI(version="1.0.0")

# ---- Configure telemetry for the Orchestrator Agent API
telemetry = OpenTelemetryAzureMonitorTelemetry(service_name="orchestrator-agent")
telemetry.configure()
telemetry.set_common_context(
    service_name="orchestrator-agent",
    service_version=app.version,
    environment=os.getenv("APP_ENVIRONMENT"),
    cloud_role="orchestrator-agent",
)
app.middleware("telemetry")(create_telemetry_middleware(telemetry))
app.middleware("http")(tenant_cors_middleware)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Orchestrator Agent A2A API",
        "version": "1.0.0",
        "endpoints": {
            "manifest": "/.well-known/agent.json",
            "invoke": "/tenants/{client_id}/invoke",
            "websocket": "/ws",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/.well-known/agent.json")
async def agent_manifest():
    manifest = os.path.join(os.path.dirname(__file__), "agentmanifest", "manifest.json")
    if not os.path.exists(manifest):
        raise HTTPException(status_code=404, detail="Manifest not found")
    with open(manifest, "r") as f:
        return json.load(f)


async def _resolve_config_or_http(client_id: str | None):
    try:
        tenant_config = await get_tenant_config_service().get_config(client_id)
        return tenant_config
    except ClientIdRequiredError:
        raise HTTPException(status_code=400, detail="client_id is required")
    except ClientProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown client_id: {client_id}")
    except TenantConfigInvalidError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant configuration is invalid: {exc}")
    except TenantConfigUnavailableError:
        raise HTTPException(status_code=503, detail="Tenant configuration is temporarily unavailable")



def _public_session_id(client_id: str, session_id: str | None) -> str:
    """Return the browser-facing session id without duplicated tenant prefixes."""
    public_session_id = session_id or str(uuid.uuid4())
    tenant_prefix = f"{client_id}:"
    while public_session_id.startswith(tenant_prefix):
        public_session_id = public_session_id[len(tenant_prefix):]
    return public_session_id


def _tenant_session_id(client_id: str, public_session_id: str) -> str:
    """Return the backend session key used for Redis/sub-agent memory.

    The browser keeps a plain session id, but backend state is namespaced by
    tenant so two tenants cannot collide if they send the same session id.
    """
    return f"{client_id}:{public_session_id}"

async def _invoke_agent_for_tenant(request: InvokeRequest, client_id: str | None) -> InvokeResponse:
    if request.client_id and client_id and request.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id in path and body do not match")

    effective_client_id = client_id or request.client_id
    tenant_config = await _resolve_config_or_http(effective_client_id)
    profile = tenant_config.profile

    conversation_url = os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000")
    form_support_url = os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001")
    step_number = request.step_number or tenant_config.settings.orchestrator_runtime.formStepNumber

    public_session_id = _public_session_id(profile.clientId, request.session_id)
    tenant_session_id = _tenant_session_id(profile.clientId, public_session_id)

    output_event = await orchestrate_a2a(
        query=request.query,
        conversation_agent_url=conversation_url,
        form_support_agent_url=form_support_url,
        step_number=step_number,
        session_id=tenant_session_id,
        tenant_settings=tenant_config.settings,
    )

    output = output_event if isinstance(output_event, list) else ([output_event] if output_event is not None else [])
    return InvokeResponse(
        response=output or "No response from orchestrator.",
        session_id=public_session_id,
    )


@app.post("/tenants/{client_id}/invoke", response_model=InvokeResponse)
async def invoke_agent_for_tenant(client_id: str, request: InvokeRequest):
    try:
        return await _invoke_agent_for_tenant(request, client_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Orchestrator invoke failed", extra={"client_id": client_id})
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# todo: to be removed after testing. This is a legacy route for internal server-to-server clients.
@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """Legacy invoke route. Production callers should use /tenants/{client_id}/invoke."""
    try:
        return await _invoke_agent_for_tenant(request, request.client_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Orchestrator legacy invoke failed")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


async def _process_ws_request(websocket: WebSocket, client_id: str, tenant_config, request: dict):
    profile = tenant_config.profile
    session_id = _public_session_id(client_id, request.get("session_id"))
    tenant_session_id = _tenant_session_id(client_id, session_id)
    step_number = request.get("step_number") or tenant_config.settings.orchestrator_runtime.formStepNumber

    if not request.get("query"):
        await websocket.send_json({"error": "query is required", "session_id": session_id})
        return

    output_event = await orchestrate_a2a(
        query=request["query"],
        conversation_agent_url=os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000"),
        form_support_agent_url=os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001"),
        step_number=step_number,
        session_id=tenant_session_id,
        tenant_settings=tenant_config.settings,
    )

    response = InvokeResponse(
        response=output_event or "No response from orchestrator.",
        session_id=session_id,
    )
    await websocket.send_json(response.model_dump())


async def _resolve_ws_config(websocket: WebSocket, client_id: str):
    try:
        return await get_tenant_config_service().get_config(client_id)
    except ClientIdRequiredError:
        await websocket.send_json({"error": "client_id is required"})
    except ClientProfileNotFoundError:
        await websocket.send_json({"error": f"Unknown client_id: {client_id}"})
    except TenantConfigInvalidError as exc:
        await websocket.send_json({"error": f"Tenant configuration is invalid: {exc}"})
    except TenantConfigUnavailableError:
        await websocket.send_json({"error": "Tenant configuration is temporarily unavailable"})
    return None


async def _handle_ws_messages(websocket: WebSocket, client_id: str, initial_request: dict | None = None):
    if initial_request is not None:
        # Resolve through TenantConfigService for every message. The service still
        # serves fresh cache hits, but long-lived WebSockets can pick up tenant
        # config changes once TENANT_PROFILE_FRESH_TTL_SECONDS expires.
        current_config = await _resolve_ws_config(websocket, client_id)
        if current_config is not None:
            try:
                await _process_ws_request(websocket, client_id, current_config, initial_request)
            except Exception as exc:
                logger.exception("WebSocket orchestration failed", extra={"client_id": client_id})
                await websocket.send_json({"error": str(exc)})

    while True:
        request = await websocket.receive_json()
        current_config = await _resolve_ws_config(websocket, client_id)
        if current_config is None:
            continue
        try:
            await _process_ws_request(websocket, client_id, current_config, request)
        except Exception as exc:
            logger.exception("WebSocket orchestration failed", extra={"client_id": client_id})
            await websocket.send_json({"error": str(exc)})



@app.websocket("/ws")
async def invoke_agent_ws(websocket: WebSocket):
    """Legacy internal WebSocket route.

    API gateway callers use this plain /ws route and send client_id in the
    message body. Browser callers should connect to the API gateway, which
    validates tenant Origin before forwarding here.
    """
    if websocket.headers.get("origin"):
        await websocket.close(code=1008, reason="Connect through API gateway /ws")
        return

    await websocket.accept()
    try:
        while True:
            request = await websocket.receive_json()
            client_id = request.get("client_id")
            tenant_config = await _resolve_ws_config(websocket, client_id)
            if tenant_config is None:
                continue

            await _handle_ws_messages(websocket, tenant_config.profile.clientId, initial_request=request)
    except WebSocketDisconnect:
        print("API Gateway disconnected from Orchestrator Websocket")
        logger.info("Legacy websocket disconnected")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "OrchestratorAgent"}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))

    print(f"Starting Orchestrator Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
