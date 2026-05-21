"""FastAPI API gateway for HTTP and WebSocket access to backend agents.

This service is the public entrypoint for clients and is responsible for:
- validating client auth (middleware registered from auth_middleware),
- proxying POST /invoke to the orchestrator agent,
- proxying WS /ws traffic to the orchestrator WebSocket endpoint,
- exposing health and service metadata endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any

import httpx
import websockets
from auth_middleware import (
    close_redis_client,
    is_authorized_basic_auth,
    register_invoke_basic_auth_middleware,
)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

load_dotenv()


class InvokeRequest(BaseModel):
    """Incoming invoke payload accepted by the gateway."""
    query: str
    session_id: str | None = None
    step_number: int | str | None = None


class InvokeResponse(BaseModel):
    """Gateway response wrapper returned to clients."""
    response: Any
    session_id: str | None = None


# Upstream service locations and gateway runtime settings.
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_AGENT_URL", "http://orchestrator-agent:8002")
ORCHESTRATOR_WS_URL = os.getenv("ORCHESTRATOR_AGENT_WS_URL", "ws://orchestrator-agent:8002/ws")
CONVERSATION_URL = os.getenv("CONVERSATION_AGENT_URL", "http://conversation-agent:8000")
FORM_SUPPORT_URL = os.getenv("FORM_SUPPORT_AGENT_URL", "http://formsupport-agent:8001")
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "90"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared gateway resources during app startup and shutdown."""
    # Create a shared async HTTP client for upstream proxy calls.
    app.state.http = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS)
    try:
        yield
    finally:
        # Release shared clients on shutdown.
        await app.state.http.aclose()
        await close_redis_client()

app = FastAPI(
    title="Agent API Gateway",
    description="Single FastAPI entrypoint that proxies requests to agent containers",
    version="1.0.0",
    lifespan=lifespan,
)


# Register HTTP middleware that enforces Basic Auth on POST /invoke.
register_invoke_basic_auth_middleware(app)


async def _forward_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Forward a JSON POST request to an upstream endpoint with consistent errors."""
    try:
        response = await app.state.http.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

    if response.status_code >= 400:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Upstream returned non-JSON response") from exc


@app.get("/")
async def root() -> dict[str, Any]:
    """Describe available gateway endpoints for quick discovery."""
    return {
        "name": "Agent API Gateway",
        "version": app.version,
        "endpoints": {
            "invoke": "/invoke",
            "websocket": "/ws",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Simple health status plus configured upstream targets."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "upstreams": {
            "orchestrator": ORCHESTRATOR_URL,
            "orchestrator_ws": ORCHESTRATOR_WS_URL,
            "conversation": CONVERSATION_URL,
            "formsupport": FORM_SUPPORT_URL,
        },
    }

# HTTP invoke endpoint that proxies requests to orchestrator /invoke.
@app.post("/invoke", response_model=InvokeResponse)
async def invoke_orchestrator(request: InvokeRequest) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    return await _forward_post(f"{ORCHESTRATOR_URL}/invoke", payload)

# WebSocket proxy endpoint for real-time client <-> orchestrator interaction.
@app.websocket("/ws")
async def websocket_orchestrator_proxy(client_ws: WebSocket):
    """Authorize client and relay WebSocket messages to/from orchestrator."""
    auth_header = client_ws.headers.get("authorization")
    if not await is_authorized_basic_auth(auth_header):
        await client_ws.close(code=1008)
        return

    await client_ws.accept()

    try:
        async with websockets.connect(ORCHESTRATOR_WS_URL) as upstream_ws:
            while True:
                try:
                    message = await client_ws.receive_text()
                except WebSocketDisconnect:
                    break

                await upstream_ws.send(message)
                upstream_response = await upstream_ws.recv()

                if isinstance(upstream_response, bytes):
                    await client_ws.send_bytes(upstream_response)
                else:
                    await client_ws.send_text(upstream_response)
    except Exception as exc:
        await client_ws.send_json({"error": f"WebSocket proxy error: {exc}"})
        await client_ws.close(code=1011)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="info")
