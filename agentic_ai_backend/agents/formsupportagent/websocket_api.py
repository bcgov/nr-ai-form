
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

import requests
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The URL of the agent server's WebSocket endpoint
AGENT_SERVER_WS_URL = os.getenv("AGENT_SERVER_WS_URL", "ws://localhost:8001/invoke-web")
PORT = int(os.getenv("PORT", "8002"))

# --- Models ---
class InvokeRequest(BaseModel):
    query: str
    session_id: str
    step_number: Optional[str] = None

class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None

# --- Global State ---
# Store active WebSocket connections: session_id -> ClientWebSocket
# In a production environment with multiple instances, this would need external storage (e.g. Redis)
# or sticky sessions. For this single-instance implementation, in-memory is fine.
active_websockets: Dict[str, websockets.WebSocketClientProtocol] = {}

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup: Close all open connections on shutdown
    for session_id, ws in active_websockets.items():
        try:
            await ws.close()
            logger.info(f"Closed connection for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing connection for {session_id}: {e}")
    active_websockets.clear()

app = FastAPI(
    title="Form Support Agent WebSocket Gateway",
    description="HTTP Interface that routes requests via persistent WebSockets to the Agent Server.",
    version="1.0.0",
    lifespan=lifespan
)

async def get_or_create_connection(session_id: str) -> websockets.WebSocketClientProtocol:
    """
    Get an existing WebSocket connection for the session, or establish a new one.
    """
    if session_id in active_websockets:
        ws = active_websockets[session_id]
        if not ws.closed:
            return ws
        else:
            # Clean up closed connection
            logger.info(f"Connection for {session_id} was closed. Removing from cache.")
            del active_websockets[session_id]
    
    # Create new connection
    try:
        logger.info(f"Connecting to {AGENT_SERVER_WS_URL} for session {session_id}...")
        ws = await websockets.connect(AGENT_SERVER_WS_URL)
        active_websockets[session_id] = ws
        logger.info(f"Connected for session {session_id}")
        return ws
    except Exception as e:
        logger.error(f"Failed to connect to agent server: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to agent server: {str(e)}")

@app.post("/invoke-websocket", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """
    Receives an HTTP POST request, forwards it to the agent via WebSocket,
    and returns the response. Maintains the WebSocket connection for the session.
    """
    try:
        ws = await get_or_create_connection(request.session_id)
        
        # Prepare payload
        payload = request.dict()
        
        # Send to agent server
        await ws.send(json.dumps(payload))
        
        # Wait for response
        # Note: This implementation assumes a strictly synchronous request-response pattern 
        # over the WebSocket for simplicity (1 request -> 1 response).
        # If the agent sends intermediate messages or out-of-order responses, 
        # a more complex correlation mechanism (e.g., using message IDs) would be required.
        response_data = await ws.recv()
        
        # Parse response
        response_json = json.loads(response_data)
        
        # Handle errors returned from server
        if "error" in response_json:
             raise HTTPException(status_code=500, detail=response_json["error"])

        return InvokeResponse(**response_json)

    except websockets.exceptions.ConnectionClosed as e:
        # Connection lost, try to remove from cache
        if request.session_id in active_websockets:
            del active_websockets[request.session_id]
        raise HTTPException(status_code=503, detail="Connection to agent server lost. Please retry.")
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "active_connections": len(active_websockets)
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
