import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional
import uvicorn
from dotenv import load_dotenv
import uuid
import ast
load_dotenv()

from utils.threadmanagement.redisdbutils import redisdbutils


# This is to connect to the agent server; not to be confused with FastAPI's WebSocket
import websockets

# This WebSocket is to receive frontend connections; not to be confused with the other websockets
# that initiate connections to the agent server.
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from clientprofiles import (
    ClientIdRequiredError,
    ClientProfileNotFoundError,
    TenantConfigInvalidError,
    TenantConfigService,
    TenantConfigUnavailableError,
    get_client_profile_store,
    is_origin_allowed,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Full WebSocket URL used by the API backend to connect to the orchestrator.
ORCHESTRATOR_AGENT_WS_URL = os.getenv("ORCHESTRATOR_AGENT_WS_URL", "ws://localhost:8002/ws")


# --- Global State ---
# Store active WebSocket connections: tenant_session_id -> WebSocket (Frontend)
frontend_websockets: Dict[str, WebSocket] = {}

# Store the single active WebSocket connection to the orchestrator agent.
agent_websocket: websockets.WebSocketClientProtocol | None = None
agent_websocket_lock = asyncio.Lock()

# Global Redis Utils instance
_redis_utils_instance = None
_tenant_config_service: TenantConfigService | None = None

def get_redis_utils():
    """Create or reuse the Redis thread-state utility for history lookups."""
    global _redis_utils_instance
    if _redis_utils_instance is None:
        _redis_utils_instance = redisdbutils()
    return _redis_utils_instance

def get_tenant_config_service() -> TenantConfigService:
    """Create or reuse the service that loads tenant profiles and settings."""
    # Keep one Cosmos-backed tenant service instance for websocket and history requests.
    global _tenant_config_service
    if _tenant_config_service is None:
        _tenant_config_service = TenantConfigService(get_client_profile_store())
    return _tenant_config_service


async def _resolve_config_for_ws(websocket: WebSocket, client_id: str):
    """Resolve tenant config for a WebSocket request or close with a policy code."""
    # WebSocket routes cannot raise normal HTTP responses after accept, so map
    # tenant lookup failures to close codes the browser can handle.
    try:
        return await get_tenant_config_service().get_config(client_id)
    except ClientProfileNotFoundError:
        await websocket.close(code=1008, reason="Unknown tenant")
    except TenantConfigInvalidError:
        await websocket.close(code=1013, reason="Tenant configuration invalid")
    except (ClientIdRequiredError, TenantConfigUnavailableError):
        await websocket.close(code=1013, reason="Tenant configuration unavailable")
    return None


def _tenant_context_payload(tenant_config) -> dict:
    """Build the tenant context forwarded to the orchestrator for each request."""
    # Send both source profile metadata and validated runtime settings so the
    # orchestrator can run normal gateway traffic without another Cosmos read.
    return {
        "client_profile": tenant_config.profile.model_dump(mode="json", exclude_none=True),
        "tenant_settings": tenant_config.settings.model_dump(mode="json", exclude_none=True),
    }


def _attach_tenant_context(message: dict, session_id: str, client_id: str, tenant_context: dict) -> dict:
    """Attach tenant and session fields before proxying a browser message upstream."""
    # Start from the browser payload, then overwrite trusted gateway-managed fields.
    payload = dict(message)
    payload["session_id"] = session_id
    payload["client_id"] = client_id
    payload.update(tenant_context)
    return payload


async def connect_to_agent() -> websockets.WebSocketClientProtocol:
    """Return the shared API-backend-to-orchestrator WebSocket connection."""
    global agent_websocket

    if agent_websocket and not getattr(agent_websocket, "closed", False):
        logger.info(f"Using existing agent connection {agent_websocket}")
        return agent_websocket

    # Create new connection
    try:
        logger.info(f"Connecting to {ORCHESTRATOR_AGENT_WS_URL}...")
        agent_websocket = await websockets.connect(ORCHESTRATOR_AGENT_WS_URL)
        connection_message = "Orchestrator WebSocket connected"
        logger.info(connection_message)
        print(connection_message)
        return agent_websocket
    except Exception as exc:
        logger.error(f"Failed to connect to orchestrator agent server: {exc}")
        agent_websocket = None
        raise HTTPException(status_code=503, detail=f"Failed to connect to agent server: {str(exc)}") from exc


async def close_agent_websocket() -> None:
    """Close and clear the shared orchestrator WebSocket connection."""
    # Used when the shared upstream socket errors so the next request reconnects cleanly.
    global agent_websocket
    if not agent_websocket:
        return
    try:
        await agent_websocket.close()
        disconnect_message = "Orchestrator WebSocket disconnected"
        logger.info(disconnect_message)
        print(disconnect_message)
    except Exception as exc:
        logger.error("Error closing orchestrator agent websocket: %s", exc)
    finally:
        agent_websocket = None


async def _send_to_orchestrator(payload: dict) -> str:
    """Send one request over the shared upstream websocket and return one response."""
    global agent_websocket

    # One upstream WebSocket carries many browser sessions, so serialize each
    # request/response pair to keep responses matched to the correct caller.
    async with agent_websocket_lock:
        agent_ws = await connect_to_agent()
        try:
            await agent_ws.send(json.dumps(payload))
            return await agent_ws.recv()
        except Exception:
            # If the persistent orchestrator socket is stale, reconnect once and retry
            # the same request before surfacing an error to the frontend.
            logger.exception("Error communicating with orchestrator agent; reconnecting once")
            await close_agent_websocket()
            agent_ws = await connect_to_agent()
            await agent_ws.send(json.dumps(payload))
            return await agent_ws.recv()


async def _proxy_to_orchestrator(
    websocket: WebSocket,
    session_id: str,
    client_id: str,
    tenant_context: dict,
    initial_message: dict | None = None,
) -> None:
    """Proxy browser WebSocket messages to the single orchestrator WebSocket."""
    if initial_message is not None:
        # websocket_endpoint already consumed the first browser message to resolve
        # tenant config, so forward that same message before entering the receive loop.
        payload = _attach_tenant_context(initial_message, session_id, client_id, tenant_context)
        await websocket.send_text(await _send_to_orchestrator(payload))

    while True:
        # After the tenant is validated, this loop mirrors the feature branch:
        # receive browser JSON, send it to orchestrator, return the orchestrator response.
        data = await websocket.receive_text()
        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
            continue

        payload = _attach_tenant_context(message, session_id, client_id, tenant_context)
        await websocket.send_text(await _send_to_orchestrator(payload))

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cleanly close frontend and orchestrator WebSockets during shutdown."""
    global agent_websocket
    yield
    # Cleanup: Close all open connections on shutdown
    for session_id, ws in list(frontend_websockets.items()):
        try:
            await ws.close()
            logger.info(f"Closed frontend connection for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing frontend connection for {session_id}: {e}")
    frontend_websockets.clear()

    if agent_websocket:
        try:
            await agent_websocket.close()
            disconnect_message = "Orchestrator WebSocket disconnected during shutdown"
            logger.info(disconnect_message)
            print(disconnect_message)
        except Exception as e:
            logger.error(f"Error closing agent connection: {e}")
        finally:
            agent_websocket = None

app = FastAPI(
    title="AI Agent WebSocket Gateway",
    description="Interface that routes WebSocket requests to the Agent Server.",
    version="1.0.0",
    lifespan=lifespan
)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """Browser-facing WebSocket endpoint for frontend chat traffic.

    The first JSON message must include client_id so the API layer can load the
    tenant profile and validate the Origin before proxying to the orchestrator.
    """
    await websocket.accept()

    # Preserve the feature-branch session behavior: reuse the provided session_id
    # or create one for a new chat thread.
    public_session_id = session_id or str(uuid.uuid4())
    tenant_connection_id = None
    connection_message = f"Frontend WebSocket connected session={public_session_id}"
    logger.info(connection_message)
    print(connection_message)

    try:
        # The first message carries client_id so we can resolve tenant config
        # and Origin before proxying any traffic to the orchestrator.
        try:
            message = json.loads(await websocket.receive_text())
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
            await websocket.close(code=1008, reason="Invalid JSON")
            return

        client_id = message.get("client_id")
        if not client_id:
            await websocket.send_text(json.dumps({"error": "client_id is required"}))
            await websocket.close(code=1008, reason="client_id is required")
            return

        # Load tenant profile/settings in the API layer before forwarding to orchestrator.
        tenant_config = await _resolve_config_for_ws(websocket, client_id)
        if tenant_config is None:
            return
        profile = tenant_config.profile

        # Replace global CORS middleware with tenant-specific Origin validation.
        origin = websocket.headers.get("origin")
        if not is_origin_allowed(origin, profile.corsOrigins):
            logger.warning("Rejected gateway websocket origin client_id=%r origin=%r allowed_origins=%r", client_id, origin, profile.corsOrigins)
            await websocket.close(code=1008, reason="Origin not allowed")
            return

        # Namespace active browser sockets by tenant to prevent same-session-id
        # collisions across different client applications.
        tenant_connection_id = _tenant_session_id(profile.clientId, public_session_id)
        frontend_websockets[tenant_connection_id] = websocket
        registration_message = f"Frontend WebSocket registered tenant_session={tenant_connection_id}"
        logger.info(registration_message)
        print(registration_message)

        if not session_id:
            # Tell the frontend about the generated browser-visible session id.
            await websocket.send_text(json.dumps({"event": "session_init", "session_id": public_session_id}))

        # Continue with the same proxy behavior as the feature branch, with tenant
        # context attached to every upstream orchestrator request.
        await _proxy_to_orchestrator(
            websocket,
            public_session_id,
            profile.clientId,
            _tenant_context_payload(tenant_config),
            initial_message=message,
        )
    except WebSocketDisconnect:
        disconnect_message = f"Frontend WebSocket disconnected session={public_session_id} tenant_session={tenant_connection_id}"
        logger.info(disconnect_message)
        print(disconnect_message)
    except Exception as exc:
        logger.exception("WebSocket proxy failed")
        try:
            await websocket.send_text(json.dumps({"error": "Agent server error"}))
        except Exception:
            pass
    finally:
        close_message = f"Frontend WebSocket closed session={public_session_id} tenant_session={tenant_connection_id}"
        logger.info(close_message)
        print(close_message)
        if tenant_connection_id:
            frontend_websockets.pop(tenant_connection_id, None)


def _public_session_id(client_id: str, session_id: str | None) -> str:
    """Return the browser-visible session id without a tenant namespace prefix."""
    # Frontend stores plain session ids; strip any older tenant prefix if a
    # backend-namespaced id is accidentally passed back in.
    public_session_id = session_id or str(uuid.uuid4())
    tenant_prefix = f"{client_id}:"
    while public_session_id.startswith(tenant_prefix):
        public_session_id = public_session_id[len(tenant_prefix):]
    return public_session_id


def _tenant_session_id(client_id: str, public_session_id: str) -> str:
    """Return the tenant-scoped session id used for backend state and sockets."""
    # Redis/thread state and active socket lookup use this namespaced id.
    return f"{client_id}:{public_session_id}"


async def _resolve_profile_for_http(client_id: str):
    """Resolve tenant profile for HTTP routes and map lookup errors to HTTP responses."""
    try:
        return await get_tenant_config_service().get_profile(client_id)
    except ClientProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown client_id: {client_id}")
    except ClientIdRequiredError:
        raise HTTPException(status_code=400, detail="client_id is required")
    except TenantConfigUnavailableError:
        raise HTTPException(status_code=503, detail="Tenant configuration unavailable")


def _apply_tenant_cors_headers(request: Request, response: Response, allowed_origins: list[str]) -> None:
    """Validate the request Origin and apply tenant-specific CORS response headers."""
    origin = request.headers.get("origin")
    if not origin:
        return
    if not is_origin_allowed(origin, allowed_origins):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"


async def _get_flattened_history(session_id: str):
    """Load Redis thread state and flatten stored chat messages for the frontend."""
    db_utils = get_redis_utils()
    try:
        data = await db_utils.get_thread_state_as_dict(session_id)
        logger.info(f"data from redis: {data}")
        if data is None:
            logger.info(f"No data from redis: {data}")
            return []

        messages = data.get("state", {}).get("in_memory", {}).get("messages", []) if isinstance(data, dict) else []

        flattened_history = []
        logger.info("=============================================================")
        logger.info(f"messages: {messages}")

        for msg in messages:
            role = msg.get("role")
            contents = msg.get("contents", [])
            text = ""

            # Extract the base text
            if contents and isinstance(contents, list):
                for item in contents:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        break

            # Apply Role-Specific Formatting
            if text:
                if role == "user":
                    # Split by the FIRST colon and take everything after it
                    if ":" in text:
                        text = text.split(":", 1)[1]

                elif role == "assistant":
                    # Check if the text looks like a dictionary/JSON object
                    text_stripped = text.strip()
                    if text_stripped.startswith("{") and text_stripped.endswith("}"):
                        try:
                            # Attempt standard JSON parse first
                            parsed_dict = json.loads(text_stripped)
                            text = parsed_dict.get("response", text)
                        except json.JSONDecodeError:
                            try:
                                # Fallback for stringified Python dicts (single quotes)
                                parsed_dict = ast.literal_eval(text_stripped)
                                if isinstance(parsed_dict, dict):
                                    text = parsed_dict.get("response", text)
                            except (ValueError, SyntaxError):
                                # If all parsing fails, gracefully fall back to the raw text
                                logger.error("Failed to parse history string as JSON")
                                return []

            # Append the cleaned up payload
            flattened_history.append({
                "role": role,
                "text": text
            })

        logger.info("=============================================================")
        logger.info(f"flattened_history: {flattened_history}")
        return flattened_history
    except Exception as e:
        logger.error(f"Error fetching history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load history: {str(e)}")


@app.get("/tenants/{client_id}/history/{session_id}")
async def get_tenant_history(client_id: str, session_id: str, request: Request, response: Response):
    """Return conversation history from the tenant-scoped session namespace."""
    # Resolve profile first so history reads use the same tenant boundary as websocket traffic.
    profile = await _resolve_profile_for_http(client_id)
    _apply_tenant_cors_headers(request, response, profile.corsOrigins)

    public_session_id = _public_session_id(profile.clientId, session_id)
    return await _get_flattened_history(_tenant_session_id(profile.clientId, public_session_id))



@app.get("/health")
async def health_check():
    """Report gateway health and active WebSocket connection counts."""
    return {
        "status": "healthy",
        "frontend_connections": len(frontend_websockets),
        "agent_connection": agent_websocket is not None,
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)
