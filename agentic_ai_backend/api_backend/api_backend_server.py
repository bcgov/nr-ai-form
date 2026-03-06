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

import sys
from utils.redisservice import RedisService

# Ensure backend root is in PYTHONPATH to allow importing from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.redisservice import RedisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The URL of the agent server's WebSocket endpoint
ORCHESTRATOR_AGENT_WS_URL = os.getenv("ORCHESTRATOR_AGENT_WS_URL", "ws://localhost:8002/ws")
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
agent_websocket: websockets.WebSocketClientProtocol = None

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

    if agent_websocket:
        try:
            await agent_websocket.close()
            logger.info(f"Closed agent connection")
        except Exception as e:
            logger.error(f"Error closing agent connection: {e}")


app = FastAPI(
    title="AI Agent WebSocket Gateway",
    description="Interface that routes requests via persistent WebSockets to the Agent Server.",
    version="1.0.0",
    lifespan=lifespan
)

async def connect_to_agent() -> websockets.WebSocketClientProtocol:
    """
    Get an existing WebSocket connection for the session, or establish a new one.
    """
    global agent_websocket
    
    if agent_websocket:
        logger.info("Using existing agent connection {agent_websocket}")
        return agent_websocket
    # Create new connection
    try:
        logger.info(f"Connecting to {ORCHESTRATOR_AGENT_WS_URL}...")
        agent_websocket = await websockets.connect(ORCHESTRATOR_AGENT_WS_URL)
        logger.info(f"Connected to orchestrator agent")
        return agent_websocket
    except Exception as e:
        logger.error(f"Failed to connect to orchestrator agent server: {e}")
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
                agent_ws = await connect_to_agent()
                
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

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Load up the conversation history from Redis by threadId (which is the same as session_id).
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", "1234")
    ssl_str = os.getenv("REDIS_SSL", "False").lower()
    ssl = ssl_str in ("true", "1", "yes")

    redis_service = RedisService(host=host, port=port, password=password, ssl=ssl)
    try:
        data = await redis_service.load_thread(session_id)
        logger.info(f"data from redis: {data}")
        if data is None:
            logger.info(f"No data from redis: {data}")
            return {"session_id": session_id, "history": None, "message": "No history found for this session."}
        return {"session_id": session_id, "history": data}
    except Exception as e:
        logger.error(f"Error fetching history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load history: {str(e)}")
    finally:
        await redis_service.close()



@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "frontend_connections": len(frontend_websockets),
        "agent_connection": agent_websocket is not None
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)
