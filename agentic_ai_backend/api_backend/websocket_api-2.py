import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional
import uvicorn
import asyncio

# This is to connect to the agent server; not to be confused with FastAPI's WebSocket
import websockets

# This WebSocket is to receive frontend connections; not to be confused with the other websockets
# that initiate connections to the agent server.
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The URL of the agent server's WebSocket endpoint
AGENT_SERVER_WS_URL = os.getenv("AGENT_SERVER_WS_URL", "ws://localhost:8002/ws")
PORT = int(os.getenv("ORCHESTRATOR_PORT", "8002"))

# --- Models ---
class InvokeRequest(BaseModel):
    query: str
    session_id: str
    step_number: Optional[str] = None

class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None

# --- Global State ---
# Store active WebSocket connections: session_id -> WebSocket (Frontend)
frontend_websockets: Dict[str, WebSocket] = {}

# Store active WebSocket connections: session_id -> ClientWebSocket (Agent)
agent_websocket: Dict[str, websockets.WebSocketClientProtocol] = {}

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

    for session_id, ws in list(agent_websocket.items()):
        try:
            await ws.close()
            logger.info(f"Closed agent connection for session {session_id}")
        except Exception as e:
            logger.error(f"Error closing agent connection for {session_id}: {e}")
    agent_websocket.clear()

app = FastAPI(
    title="AI Agent WebSocket Gateway",
    description="Interface that routes requests via persistent WebSockets to the Agent Server.",
    version="1.0.0",
    lifespan=lifespan
)

async def connect_to_agent(session_id: str) -> websockets.WebSocketClientProtocol:
    """
    Get an existing WebSocket connection for the session, or establish a new one.
    """
    if session_id in agent_websocket:
        ws = agent_websocket[session_id]
        if not ws.closed:
            return ws
        else:
            # Clean up closed connection
            logger.info(f"Agent connection for {session_id} was closed. Removing from cache.")
            del agent_websocket[session_id]
    
    # Create new connection
    try:
        logger.info(f"Connecting to {AGENT_SERVER_WS_URL} for session {session_id}...")
        ws = await websockets.connect(AGENT_SERVER_WS_URL)
        agent_websocket[session_id] = ws
        logger.info(f"Connected to agent for session {session_id}")
        return ws
    except Exception as e:
        logger.error(f"Failed to connect to agent server: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to agent server: {str(e)}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint that proxies messages between the client and the agent server.
    Ensures a persistent connection to the agent server is maintained per session.
    """
    await websocket.accept()
    frontend_websockets[session_id] = websocket
    logger.info(f"Client connected to /ws for session {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            logger.info(f"Received message from client for session {session_id}: {message}")
            # We can use the session_id from the URL path
            message["session_id"] = session_id

            try:
                # Get or create connection to the agent server for this session
                agent_ws = await connect_to_agent(session_id)
                
                # Forward the client's message to the agent server
                await agent_ws.send(json.dumps(message))
                
                # Receive response from agent server
                # Note: This implementation assumes a request-response pattern.
                response_data = await agent_ws.recv()
                print(f"Received response from agent: {response_data}")
                
                # Send the agent server's response back to the client
                await websocket.send_text(response_data)

            except Exception as e:
                logger.error(f"Error communicating with agent server: {e}")
                # Try to clean up the cached connection if it failed
                if session_id in agent_websocket:
                    del agent_websocket[session_id]
                await websocket.send_text(json.dumps({"error": f"Agent server error: {str(e)}"}))

    except Exception as e:
        logger.info(f"WebSocket client disconnected or session error: {e}")
    finally:
        logger.info(f"WebSocket connection closed for session {session_id}")
        if session_id in frontend_websockets:
            del frontend_websockets[session_id]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "frontend_connections": len(frontend_websockets),
        "agent_connections": len(agent_websocket)
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)
