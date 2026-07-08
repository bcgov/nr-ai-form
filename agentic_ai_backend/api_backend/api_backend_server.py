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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from clientprofiles import (
    ClientIdRequiredError,
    ClientProfileNotFoundError,
    TenantConfigService,
    TenantConfigUnavailableError,
    get_client_profile_store,
    is_origin_allowed,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The base URL of the orchestrator agent WebSocket endpoint. The path is always /ws.
ORCHESTRATOR_AGENT_WS_BASE_URL = os.getenv("ORCHESTRATOR_AGENT_WS_BASE_URL", "ws://localhost:8002")


# --- Global State ---
# Store active WebSocket connections: session_id -> WebSocket (Frontend)
frontend_websockets: Dict[str, WebSocket] = {}


# Global Redis Utils instance
_redis_utils_instance = None
_tenant_config_service: TenantConfigService | None = None

def get_redis_utils():
    global _redis_utils_instance
    if _redis_utils_instance is None:
        _redis_utils_instance = redisdbutils()
    return _redis_utils_instance

def get_tenant_config_service() -> TenantConfigService:
    global _tenant_config_service
    if _tenant_config_service is None:
        _tenant_config_service = TenantConfigService(get_client_profile_store())
    return _tenant_config_service


def _orchestrator_ws_url() -> str:
    """Return the orchestrator WebSocket URL without tenant id in the path."""
    base_url = ORCHESTRATOR_AGENT_WS_BASE_URL.rstrip("/")
    if base_url.endswith("/ws"):
        return base_url
    return f"{base_url}/ws"


async def _resolve_profile_for_ws(websocket: WebSocket, client_id: str):
    try:
        return await get_tenant_config_service().get_profile(client_id)
    except ClientProfileNotFoundError:
        await websocket.close(code=1008, reason="Unknown tenant")
    except (ClientIdRequiredError, TenantConfigUnavailableError):
        await websocket.close(code=1013, reason="Tenant configuration unavailable")
    return None


async def _proxy_to_orchestrator(
    websocket: WebSocket,
    agent_url: str,
    session_id: str,
    client_id: str,
    initial_message: dict | None = None,
) -> None:
    """Proxy browser WebSocket messages to the orchestrator plain /ws route."""
    async with websockets.connect(agent_url) as agent_ws:
        if initial_message is not None:
            initial_message["session_id"] = session_id
            initial_message["client_id"] = client_id
            await agent_ws.send(json.dumps(initial_message))
            await websocket.send_text(await agent_ws.recv())

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            message["session_id"] = session_id
            message["client_id"] = client_id
            await agent_ws.send(json.dumps(message))
            await websocket.send_text(await agent_ws.recv())
# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup: Close all open connections on shutdown
    for session_id, ws in list(frontend_websockets.items()):
        try:
            await ws.close()
            logger.info(f"Closed frontend connection for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing frontend connection for {session_id}: {e}")
    frontend_websockets.clear()

app = FastAPI(
    title="AI Agent WebSocket Gateway",
    description="Interface that routes WebSocket requests to the Agent Server.",
    version="1.0.0",
    lifespan=lifespan
)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """Browser-facing WebSocket endpoint without tenant id in the URL.

    Because the tenant id is not in the URL, the first JSON message must include
    client_id. The socket is accepted first, then immediately closed with 1008 if
    the tenant is unknown or the Origin is not allowed for that tenant.
    """
    await websocket.accept()

    public_session_id = session_id or str(uuid.uuid4())
    frontend_websockets[public_session_id] = websocket
    logger.info(f"Client connected to /ws for session {public_session_id}")

    try:
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

        profile = await _resolve_profile_for_ws(websocket, client_id)
        if profile is None:
            return

        origin = websocket.headers.get("origin")
        if not is_origin_allowed(origin, profile.corsOrigins):
            logger.warning("Rejected gateway websocket origin client_id=%r origin=%r allowed_origins=%r", client_id, origin, profile.corsOrigins)
            await websocket.close(code=1008, reason="Origin not allowed")
            return

        if not session_id:
            await websocket.send_text(json.dumps({"event": "session_init", "session_id": public_session_id}))

        await _proxy_to_orchestrator(
            websocket,
            _orchestrator_ws_url(),
            public_session_id,
            profile.clientId,
            initial_message=message,
        )
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for session {public_session_id}")
    except Exception as exc:
        logger.exception("WebSocket proxy failed")
        try:
            await websocket.send_text(json.dumps({"error": "Agent server error"}))
        except Exception:
            pass
    finally:
        logger.info(f"WebSocket connection closed for session {public_session_id}")
        frontend_websockets.pop(public_session_id, None)

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Load up the conversation history from Redis by threadId (which is the same as session_id).
    """
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

            # 5. Apply Role-Specific Formatting
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



@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "frontend_connections": len(frontend_websockets)
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)
