"""FastAPI gateway that fronts the agent containers."""

from __future__ import annotations

import os
from typing import Any

import httpx
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

load_dotenv()


class InvokeRequest(BaseModel):
    query: str
    session_id: str | None = None
    step_number: int | str | None = None


class InvokeResponse(BaseModel):
    response: Any
    session_id: str | None = None


ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_AGENT_URL", "http://orchestrator-agent:8002")
ORCHESTRATOR_WS_URL = os.getenv("ORCHESTRATOR_AGENT_WS_URL", "ws://orchestrator-agent:8002/ws")
CONVERSATION_URL = os.getenv("CONVERSATION_AGENT_URL", "http://conversation-agent:8000")
FORM_SUPPORT_URL = os.getenv("FORM_SUPPORT_AGENT_URL", "http://formsupport-agent:8001")
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "90"))

app = FastAPI(
    title="Agent API Gateway",
    description="Single FastAPI entrypoint that proxies requests to agent containers",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    app.state.http = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await app.state.http.aclose()


async def _forward_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
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

# regular POST endpoint to invoke the orchestrator agent
async def invoke_orchestrator(request: InvokeRequest) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    return await _forward_post(f"{ORCHESTRATOR_URL}/invoke", payload)

# websocket proxy endpoint for real-time interactions
@app.websocket("/ws")
async def websocket_orchestrator_proxy(client_ws: WebSocket):
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
