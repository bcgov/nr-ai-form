"""
FastAPI A2A Wrapper for Orchestrator Agent
"""
import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from clientprofiles import (
    ClientProfile,
    ClientIdRequiredError,
    ClientProfileNotFoundError,
    TenantAgentSettings,
    TenantConfigInvalidError,
    TenantConfigUnavailableError,
)
from orchestratoragent import orchestrate_a2a
from tenantconfigservice import get_tenant_config_service
from telemetry import EventTelemetry, OpenTelemetryAzureMonitorTelemetry

load_dotenv()

from models.orchestratormodel import InvokeResponse

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

# ---- Configure telemetry for the Orchestrator Agent API
telemetry = OpenTelemetryAzureMonitorTelemetry(service_name="orchestrator-agent")
telemetry.configure()
telemetry.set_common_context(
    service_name="orchestrator-agent",
    service_version=API_VERSION,
    environment=os.getenv("APP_ENVIRONMENT"),
    cloud_role="orchestrator-agent",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Container Apps scales this service to zero, so buffered telemetry has to be
    # pushed on shutdown or the final turns of a conversation are never exported.
    telemetry.flush()


# TODO ABIN: This is a temporary A2A endpoint. Later we
# will use a pub-sub mechanism from a queue.
app = FastAPI(version=API_VERSION, lifespan=lifespan)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Orchestrator Agent A2A API",
        "version": "1.0.0",
        "endpoints": {
            "manifest": "/.well-known/agent.json",
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



def _public_session_id(client_id: str, session_id: str | None) -> str:
    """Return the browser-facing session id without duplicated tenant prefixes."""
    public_session_id = session_id or str(uuid.uuid4())
    tenant_prefix = f"{client_id}:"
    while public_session_id.startswith(tenant_prefix):
        public_session_id = public_session_id[len(tenant_prefix):]
    return public_session_id


def _tenant_session_id(client_id: str, public_session_id: str) -> str:
    """Return the backend session key used for Redis/sub-agent memory."""
    return f"{client_id}:{public_session_id}"


# Sends one JSON reply for the request it was built for.
Reply = Callable[[dict], Awaitable[None]]

# Chat turns currently running. asyncio keeps only weak references to tasks, so hold them here.
_running_turns: set[asyncio.Task] = set()


def _ws_replier(websocket: WebSocket, send_lock: asyncio.Lock, request: dict) -> Reply:
    """Return a sender that tags every reply with the session it answers.

    The API gateway carries many browser sessions over one socket and matches each reply to
    its caller by client_id and session_id, so every reply needs both - errors included.
    """
    client_id = request.get("client_id")
    session_id = request.get("session_id")
    tags = {}
    if client_id and session_id:
        tags = {"client_id": client_id, "session_id": _public_session_id(client_id, session_id)}

    async def reply(body: dict) -> None:
        try:
            # Turns finish concurrently, so serialize writes to the shared socket.
            async with send_lock:
                await websocket.send_json({**body, **tags})
        except Exception:
            # The gateway disconnected mid-turn. Telemetry and Redis state for the turn are
            # already recorded; only delivery is lost.
            logger.warning("Could not deliver orchestrator reply; gateway socket closed", extra={"client_id": client_id})

    return reply


# Application Insights caps a single customDimensions value at 8192 characters.
_MAX_CONTENT_CHARS = 8192
_TRUNCATION_MARKER = "...[truncated]"

# Chat content is user-entered free text. Set TELEMETRY_LOG_CHAT_CONTENT=false to keep
# emitting turn metadata (timing, step, session, outcome) without the message bodies.
_LOG_CHAT_CONTENT = os.getenv("TELEMETRY_LOG_CHAT_CONTENT", "true").strip().lower() not in {"false", "0", "no"}


def _truncate(value: str) -> str:
    """Cap a value at the Application Insights property limit, marking what was cut."""
    if len(value) <= _MAX_CONTENT_CHARS:
        return value
    return value[: _MAX_CONTENT_CHARS - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


async def _track_chat_turn(
    *,
    client_id: str,
    session_id: str,
    step_number: str | None,
    query: str,
    response: str | None,
    duration_ms: float,
    success: bool,
    application_id: str | None,
    error: Exception | None = None,
) -> None:
    """Emit one ChatTurn custom event per user message.

    Lands in the Application Insights customEvents table rather than traces — see
    OpenTelemetryAzureMonitorTelemetry.track_event. Telemetry must never break the
    chat path, so every failure in here is swallowed.
    """
    try:
        properties: dict[str, Any] = {
            "chat.client_id": client_id,
            "chat.session_id": session_id,
            "chat.step_number": step_number,
            "chat.success": success,
            "chat.query.chars": len(query),
            "chat.response.chars": len(response) if response is not None else 0,
            "chat.content_logged": _LOG_CHAT_CONTENT,
            "chat.application_id": application_id,
        }
        if _LOG_CHAT_CONTENT:
            properties["chat.query"] = _truncate(query)
            if response is not None:
                properties["chat.response"] = _truncate(response)
        if error is not None:
            properties["error.type"] = type(error).__name__
            properties["error.message"] = _truncate(str(error))

        telemetry.track_event(
            EventTelemetry(
                name="AIFA-ChatThreads",
                properties=properties,
                measurements={"chat.duration_ms": duration_ms},
            )
        )
    except Exception:
        logger.debug("Failed to emit ChatTurn telemetry", exc_info=True)

def _client_id_from_ws_request(request: dict) -> str | None:
    # client_profile is forwarded by the API backend; validate it against the
    # explicit client_id before trusting tenant-specific runtime settings.
    client_id = request.get("client_id")
    raw_profile = request.get("client_profile")
    if not isinstance(raw_profile, dict):
        return client_id

    profile = ClientProfile.model_validate(raw_profile)
    if client_id and client_id != profile.clientId:
        raise ValueError("client_id does not match client_profile.clientId")
    return profile.clientId


def _tenant_settings_from_request(request: dict) -> TenantAgentSettings | None:
    # tenant_settings is the processed runtime view of the Cosmos profile.
    raw_settings = request.get("tenant_settings")
    if raw_settings is None:
        return None
    if not isinstance(raw_settings, dict):
        raise ValueError("tenant_settings must be an object")
    return TenantAgentSettings.model_validate(raw_settings)


async def _process_ws_request(
    reply: Reply,
    client_id: str,
    tenant_settings: TenantAgentSettings,
    request: dict,
):
    # Return the public session id to the frontend, but use a tenant-prefixed
    # key for backend memory so tenants cannot collide on the same session id.
    session_id = _public_session_id(client_id, request.get("session_id"))
    tenant_session_id = _tenant_session_id(client_id, session_id)
    application_id = request.get("application_id") or "unknown"
    step_number = request.get("step_number") or tenant_settings.orchestrator_runtime.formStepNumber

    form_data = request.get("form_data")
    if not isinstance(form_data, dict) or not form_data:
        form_data = None

    if not request.get("query"):
        await reply({"error": "query is required", "session_id": session_id})
        return

    query = request["query"]
    started = time.perf_counter()

    try:
        output_event = await orchestrate_a2a(
            query=query,
            conversation_agent_url=os.getenv("CONVERSATION_AGENT_A2A_URL", "http://localhost:8000"),
            form_support_agent_url=os.getenv("FORM_SUPPORT_AGENT_A2A_URL", "http://localhost:8001"),
            step_number=step_number,
            form_data=form_data,
            session_id=tenant_session_id,
            tenant_settings=tenant_settings,
        )
    except Exception as exc:
        # Record the failed turn before re-raising so the caller still reports the
        # error to the browser and logs the stack trace.
        await _track_chat_turn(
            client_id=client_id,
            session_id=session_id,
            step_number=step_number,
            query=query,
            response=None,
            duration_ms=(time.perf_counter() - started) * 1000,
            success=False,
            error=exc,
            application_id=application_id
        )
        raise

    response = InvokeResponse(
        response=output_event or "No response from orchestrator.",
        session_id=session_id,
    )
    await _track_chat_turn(
        client_id=client_id,
        session_id=session_id,
        step_number=step_number,
        query=query,
        response=response.response,
        duration_ms=(time.perf_counter() - started) * 1000,
        success=True,
        application_id=application_id
    )
    await reply(response.model_dump())


async def _resolve_ws_config(reply: Reply, client_id: str):
    try:
        return await get_tenant_config_service().get_config(client_id)
    except ClientIdRequiredError:
        await reply({"error": "client_id is required"})
    except ClientProfileNotFoundError:
        await reply({"error": f"Unknown client_id: {client_id}"})
    except TenantConfigInvalidError as exc:
        await reply({"error": f"Tenant configuration is invalid: {exc}"})
    except TenantConfigUnavailableError:
        await reply({"error": "Tenant configuration is temporarily unavailable"})
    return None


async def _resolve_ws_context(reply: Reply, request: dict) -> tuple[str | None, TenantAgentSettings | None]:
    try:
        client_id = _client_id_from_ws_request(request)
        tenant_settings = _tenant_settings_from_request(request)
    except (ValidationError, ValueError) as exc:
        await reply({"error": f"Tenant context is invalid: {exc}"})
        return None, None

    if not client_id:
        await reply({"error": "client_id is required"})
        return None, None

    if tenant_settings is not None:
        if tenant_settings.client_id != client_id:
            await reply({"error": "client_id does not match tenant_settings.client_id"})
            return None, None
        return client_id, tenant_settings

    # Backward-compatible fallback for internal callers that have not moved to
    # API-provided tenant context yet. API gateway websocket traffic includes
    # tenant_settings and does not use this Cosmos-backed path.
    tenant_config = await _resolve_ws_config(reply, client_id)
    if tenant_config is None:
        return None, None
    return tenant_config.profile.clientId, tenant_config.settings


async def _handle_ws_message(reply: Reply, request: dict) -> None:
    """Run one chat turn and send exactly one reply for it, success or error."""
    client_id = request.get("client_id")
    try:
        client_id, tenant_settings = await _resolve_ws_context(reply, request)
        if client_id is None or tenant_settings is None:
            return
        await _process_ws_request(reply, client_id, tenant_settings, request)
    except Exception as exc:
        logger.exception("WebSocket orchestration failed", extra={"client_id": client_id})
        await reply({"error": str(exc)})


@app.websocket("/ws")
async def invoke_agent_ws(websocket: WebSocket):
    """Internal WebSocket route.

    API gateway callers use this plain /ws route and send client_id in the
    message body. Browser callers should connect to the API gateway, which
    validates tenant Origin before forwarding here.

    The gateway keeps one long-lived connection and sends turns from many browser
    sessions over it, so each turn runs as its own task and replies are sent as
    turns finish, not in arrival order.
    """
    # Browser Origin headers are only accepted at the API backend, where tenant
    # CORS rules are available before proxying to this internal route.
    if websocket.headers.get("origin"):
        await websocket.close(code=1008, reason="Connect through API gateway /ws")
        return

    await websocket.accept()
    send_lock = asyncio.Lock()
    try:
        while True:
            request = await websocket.receive_json()
            turn = asyncio.create_task(_handle_ws_message(_ws_replier(websocket, send_lock, request), request))
            _running_turns.add(turn)
            turn.add_done_callback(_running_turns.discard)
    except WebSocketDisconnect:
        print("API Gateway disconnected from Orchestrator Websocket")
        logger.info("Internal websocket disconnected")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "OrchestratorAgent"}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))

    print(f"Starting Orchestrator Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
