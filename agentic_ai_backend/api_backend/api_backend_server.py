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
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# The URL of the agent server's WebSocket endpoint
ORCHESTRATOR_AGENT_WS_URL = os.getenv("ORCHESTRATOR_AGENT_WS_URL", "ws://localhost:8002/ws")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")


# --- Global State ---
# Store active WebSocket connections: session_id -> WebSocket (Frontend)
frontend_websockets: Dict[str, WebSocket] = {}

# Store active WebSocket connections: session_id -> ClientWebSocket (Agent)
agent_websocket: websockets.WebSocketClientProtocol = None

# Global Redis Utils instance
_redis_utils_instance = None

def get_redis_utils():
    global _redis_utils_instance
    if _redis_utils_instance is None:
        _redis_utils_instance = redisdbutils()
    return _redis_utils_instance

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """
    WebSocket endpoint that proxies messages between the client and the agent server.
    Ensures a persistent connection to the agent server is maintained per session.
    """
    await websocket.accept()
    logger.info(f"Client connected to /ws for session {session_id}")

    # If no session_id is provided, generate a new one
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
        await websocket.send_text(json.dumps({"event": "session_init", "session_id": session_id}))
    
    thread_id = session_id
    if session_id not in frontend_websockets:
        frontend_websockets[thread_id] = websocket
    
    logger.info(f"Client connected to /ws for session {thread_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            logger.info(f"Received message from client for session {thread_id}: {message}")
            # We can use the session_id from the URL path
            message["session_id"] = thread_id

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
                global agent_websocket
                if agent_websocket:
                    try:
                        await agent_websocket.close()
                    except Exception:
                        pass
                    agent_websocket = None
                await websocket.send_text(json.dumps({"error": f"Agent server error: {str(e)}"}))

    except Exception as e:
        logger.info(f"WebSocket client disconnected or session error: {e}")
    finally:
        logger.info(f"WebSocket connection closed for session {thread_id}")
        if thread_id in frontend_websockets:
            del frontend_websockets[thread_id]

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
        "frontend_connections": len(frontend_websockets),
        "agent_connection": agent_websocket is not None
    }

if __name__ == "__main__":
    print(f"Starting WebSocket Gateway on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)