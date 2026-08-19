"""Custom PyRIT PromptTarget for attacking custom backend API via WebSocket."""

import asyncio
import inspect
import json
import os
import websockets
from typing import Any
import uuid
from urllib.parse import urlparse
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_configuration import TargetConfiguration
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
from pyrit.models import Message
import structlog

logger = structlog.get_logger(__name__)

BACKEND_META_MARKER = "__BACKEND_META__::"

MAX_BACKEND_RETRIES = 2
RETRYABLE_EXCEPTIONS = (
    websockets.exceptions.WebSocketException,
    asyncio.TimeoutError,
)
LOCAL_PROXY_ENV_VARS = (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "WS_PROXY",
    "ws_proxy",
    "WSS_PROXY",
    "wss_proxy",
)


class CustomBackendTarget(PromptTarget):
    """
    PyRIT PromptTarget that attacks a custom backend API via WebSocket.
    
    Sends red-teaming prompts to a custom WebSocket endpoint instead of Azure OpenAI.
    Maintains a persistent WebSocket connection for the duration of the evaluation.
    """

    # Declare capabilities for this target (required for multi-turn attacks like Crescendo)
    _DEFAULT_CONFIGURATION: TargetConfiguration = TargetConfiguration(
        capabilities=TargetCapabilities(
            supports_multi_turn=True,
            supports_editable_history=True,
            supports_system_prompt=True,
        )
    )

    def __init__(
        self,
        *,
        endpoint: str,
        session_id: str = None,
        step_number: str = "step2-Eligibility",
        client_id: str = "11111111-1111-4111-8111-111111111111",
        application_id: int = 234554,
        origin: str = "https://train.j200.gov.bc.ca",
    ):
        """
        Initialize CustomBackendTarget with WebSocket connection.
        
        Args:
            endpoint: WebSocket endpoint URL (e.g., wss://your-api.com/ws or https://your-api.com/ws)
            session_id: Session ID for the backend (defaults to generated UUID)
            step_number: Form step identifier (default: step2-Eligibility)
            client_id: Client identifier required by backend
            application_id: Application identifier required by backend
            origin: Origin header for WebSocket handshake (default: https://train.j200.gov.bc.ca)
        """
        super().__init__()
        
        # Convert HTTP endpoint to WebSocket if needed
        self.endpoint = self._convert_to_websocket_url(endpoint)
        self.session_id = session_id or str(uuid.uuid4())
        self.step_number = step_number
        self.client_id = client_id
        self.application_id = application_id
        self.origin = origin
        self._conversation_id = str(uuid.uuid4())
        
        # WebSocket connection state (lazy-loaded on first send)
        self._websocket = None
        
        logger.info(
            "custom_backend_target_initialized",
            endpoint=self.endpoint,
            session_id=self.session_id,
            step_number=step_number,
            client_id=client_id,
            application_id=application_id,
            origin=origin
        )

    def _convert_to_websocket_url(self, endpoint: str) -> str:
        """
        Convert HTTP endpoint to WebSocket URL.
        
        Args:
            endpoint: HTTP or WebSocket endpoint URL
            
        Returns:
            WebSocket URL (wss:// scheme)
        """
        if not endpoint:
            raise ValueError("Endpoint cannot be empty")
        
        endpoint = endpoint.strip().rstrip("/")

        # Normalize common single-slash scheme typos from env values
        # (e.g., wss:/host -> wss://host, https:/host -> https://host).
        scheme_fixes = {
            "wss:/": "wss://",
            "ws:/": "ws://",
            "https:/": "https://",
            "http:/": "http://",
        }
        for bad_prefix, fixed_prefix in scheme_fixes.items():
            if endpoint.startswith(bad_prefix) and not endpoint.startswith(fixed_prefix):
                endpoint = endpoint.replace(bad_prefix, fixed_prefix, 1)
                break
        
        # Already a WebSocket URL
        if endpoint.startswith("wss://"):
            return endpoint
        if endpoint.startswith("ws://"):
            return endpoint
        
        # Convert HTTP to WebSocket
        if endpoint.startswith("https://"):
            ws_endpoint = endpoint.replace("https://", "wss://", 1)
        elif endpoint.startswith("http://"):
            ws_endpoint = endpoint.replace("http://", "ws://", 1)
        else:
            raise ValueError(f"Invalid endpoint URL scheme: {endpoint}")
        
        # Ensure path ends with /ws
        if not ws_endpoint.endswith("/ws"):
            if ws_endpoint.endswith("/"):
                ws_endpoint = ws_endpoint + "ws"
            else:
                ws_endpoint = ws_endpoint + "/ws"
        
        return ws_endpoint

    @staticmethod
    def _is_local_endpoint(endpoint: str) -> bool:
        """Return True when the endpoint points to a local host that should bypass proxy env vars."""
        if not endpoint:
            return False
        try:
            host = urlparse(endpoint).hostname or ""
        except ValueError:
            return False
        normalized = host.lower()
        return normalized in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or normalized.startswith("localhost.")

    def _disable_proxy_for_local_endpoint(self) -> None:
        """Clear inherited proxy variables for localhost traffic so SOCKS settings don't intercept local backend calls."""
        if not self._is_local_endpoint(self.endpoint):
            return
        for key in LOCAL_PROXY_ENV_VARS:
            os.environ.pop(key, None)

    async def _ensure_websocket_connected(self) -> None:
        """
        Ensure WebSocket connection is established.
        Lazy-loads connection on first use and reuses for subsequent calls.
        """
        if self._websocket is not None:
            # Connection already established
            return

        self._disable_proxy_for_local_endpoint()
        
        try:
            logger.info(
                "connecting_websocket",
                endpoint=self.endpoint,
                origin=self.origin
            )

            # Build connect kwargs to support multiple websockets versions.
            connect_sig = inspect.signature(websockets.connect)
            connect_kwargs: dict[str, Any] = {}

            if "additional_headers" in connect_sig.parameters:
                connect_kwargs["additional_headers"] = {"Origin": self.origin}
            else:
                connect_kwargs["extra_headers"] = {"Origin": self.origin}

            if "open_timeout" in connect_sig.parameters:
                connect_kwargs["open_timeout"] = 30
            else:
                connect_kwargs["timeout"] = 30

            # Ignore process proxy variables when this parameter is available.
            # This prevents SOCKS dependency issues in proxy-configured terminals.
            if "proxy" in connect_sig.parameters:
                connect_kwargs["proxy"] = None

            # Create WebSocket connection with custom origin header
            self._websocket = await websockets.connect(self.endpoint, **connect_kwargs)
            
            logger.info(
                "websocket_connected",
                endpoint=self.endpoint,
                session_id=self.session_id
            )
        except Exception as e:
            logger.error(
                "websocket_connection_failed",
                endpoint=self.endpoint,
                error=str(e),
                origin=self.origin
            )
            raise

    async def _send_prompt_to_target_async(
        self,
        *,
        normalized_conversation: list[Message],
    ) -> list[Message]:
        """
        Send prompt to custom backend API via WebSocket.
        
        Args:
            normalized_conversation: List of Message objects in conversation
            
        Returns:
            List of Message objects with backend response
        """
        try:
            # Ensure WebSocket is connected (lazy-load on first call)
            await self._ensure_websocket_connected()
            
            # Get the last user message from the conversation
            last_message = None
            for msg in reversed(normalized_conversation):
                # Check api_role instead of role
                if hasattr(msg, 'api_role') and msg.api_role == "user":
                    last_message = msg
                    break
            
            if not last_message:
                error_response = Message.from_prompt(
                    prompt="No user message found in conversation",
                    role="assistant"
                )
                return [error_response]
            
            # Extract prompt text from message using get_value()
            prompt = str(last_message.get_value())
            
            # Build request payload matching your backend API
            request_payload = {
                "client_id": self.client_id,
                "query": prompt,
                "step_number": str(self.step_number),
                "session_id": self.session_id,
                "application_id": self.application_id,
            }
            
            logger.info(
                "sending_websocket_prompt",
                endpoint=self.endpoint,
                query_length=len(prompt),
                session_id=self.session_id
            )
            
            # Send and receive with retry for transient failures
            for attempt in range(MAX_BACKEND_RETRIES + 1):
                try:
                    # Send request payload
                    await self._websocket.send(json.dumps(request_payload))
                    
                    response_text = None
                    response_meta: dict[str, Any] = {}
                    # Some backends emit session_init/meta events before the actual
                    # aggregator response. Keep reading until a final response arrives.
                    for _ in range(5):
                        raw_response = await asyncio.wait_for(
                            self._websocket.recv(),
                            timeout=30
                        )

                        response_data = json.loads(raw_response)
                        response_text, response_meta = self._extract_response(response_data)
                        if response_text is not None:
                            break

                    if response_text is None:
                        response_text = "INFRA_ERROR::NO_FINAL_RESPONSE"
                    
                    logger.info(
                        "backend_response_received",
                        session_id=self.session_id,
                        response_length=len(response_text)
                    )

                    if response_meta:
                        response_text = (
                            f"{response_text}\n{BACKEND_META_MARKER}"
                            f"{json.dumps(response_meta, sort_keys=True)}"
                        )
                    
                    # Return list of Message objects in PyRIT format
                    response_message = Message.from_prompt(
                        prompt=response_text,
                        role="assistant"
                    )
                    return [response_message]
                    
                except asyncio.TimeoutError:
                    logger.error(
                        "websocket_timeout",
                        endpoint=self.endpoint,
                        session_id=self.session_id,
                        attempt=attempt + 1,
                    )
                    if attempt < MAX_BACKEND_RETRIES:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    
                    error_response = Message.from_prompt(
                        prompt="INFRA_ERROR::BACKEND_TIMEOUT",
                        role="assistant"
                    )
                    return [error_response]
                    
                except websockets.exceptions.ConnectionClosed as e:
                    logger.error(
                        "websocket_connection_closed",
                        endpoint=self.endpoint,
                        session_id=self.session_id,
                        attempt=attempt + 1,
                        code=e.rcvd.code if e.rcvd else None,
                        reason=e.rcvd.reason if e.rcvd else None,
                    )
                    
                    # Reset connection to allow reconnect
                    self._websocket = None
                    
                    if attempt < MAX_BACKEND_RETRIES:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        # Reconnect for next attempt
                        await self._ensure_websocket_connected()
                        continue
                    
                    error_response = Message.from_prompt(
                        prompt="INFRA_ERROR::WEBSOCKET_CONNECTION_CLOSED",
                        role="assistant"
                    )
                    return [error_response]
                    
                except websockets.exceptions.WebSocketException as e:
                    logger.error(
                        "websocket_error",
                        endpoint=self.endpoint,
                        session_id=self.session_id,
                        error=str(e),
                        attempt=attempt + 1,
                    )
                    if attempt < MAX_BACKEND_RETRIES:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    
                    error_response = Message.from_prompt(
                        prompt=f"INFRA_ERROR::WEBSOCKET_ERROR::{str(e)[:300]}",
                        role="assistant"
                    )
                    return [error_response]
                    
                except json.JSONDecodeError as e:
                    logger.error(
                        "response_json_decode_error",
                        endpoint=self.endpoint,
                        session_id=self.session_id,
                        error=str(e),
                    )
                    error_response = Message.from_prompt(
                        prompt=f"INFRA_ERROR::INVALID_JSON_RESPONSE::{str(e)[:300]}",
                        role="assistant"
                    )
                    return [error_response]
                    
        except Exception as e:
            logger.error(
                "websocket_send_error",
                error=str(e),
                endpoint=self.endpoint,
                session_id=self.session_id
            )
            error_response = Message.from_prompt(
                prompt=f"INFRA_ERROR::WEBSOCKET_ERROR::{str(e)[:300]}",
                role="assistant"
            )
            return [error_response]

    def _extract_response(self, response_data: dict) -> tuple[str | None, dict[str, Any]]:
        """
        Extract response text from backend response format.
        
        Args:
            response_data: Response from backend WebSocket endpoint
            
        Returns:
            Extracted response text
        """
        # Handle session bootstrap/meta events that aren't final responses.
        if isinstance(response_data, dict) and response_data.get("event") == "session_init":
            session_id = response_data.get("session_id")
            if session_id:
                self.session_id = str(session_id)
            return None, {"session_id": str(session_id)} if session_id else {}

        # Handle aggregator response format
        if isinstance(response_data, dict) and "response" in response_data:
            response_list = response_data.get("response", [])
            metadata: dict[str, Any] = {}
            if isinstance(response_data.get("session_id"), str):
                metadata["session_id"] = response_data["session_id"]
            
            # Look for aggregator response
            if isinstance(response_list, list) and len(response_list) > 0:
                agg_response = response_list[0]
                if isinstance(agg_response, dict):
                    if isinstance(agg_response.get("source"), str):
                        metadata["source"] = agg_response["source"]
                    if isinstance(agg_response.get("category"), str):
                        metadata["category"] = agg_response["category"]

                    # Second item often contains thread metadata
                    if len(response_list) > 1 and isinstance(response_list[1], dict):
                        if isinstance(response_list[1].get("thread_id"), str):
                            metadata["thread_id"] = response_list[1]["thread_id"]

                    # Check if it has response field (primary)
                    if "response" in agg_response:
                        return str(agg_response["response"]) or "(empty response)", metadata
                    # Check original_results (fallback)
                    if "original_results" in agg_response:
                        results = agg_response["original_results"]
                        if isinstance(results, list) and len(results) > 0:
                            return str(results[0].get("response", "(empty)")), metadata

        # Explicit backend errors should be surfaced to the report.
        if isinstance(response_data, dict) and "error" in response_data:
            return str(response_data.get("error")), {}

        # Metadata-only payloads should not terminate the receive loop.
        if isinstance(response_data, dict) and (
            "thread_id" in response_data or "session_id" in response_data
        ):
            metadata = {}
            if isinstance(response_data.get("thread_id"), str):
                metadata["thread_id"] = response_data["thread_id"]
            if isinstance(response_data.get("session_id"), str):
                metadata["session_id"] = response_data["session_id"]
            return None, metadata
        
        # Fallback: return entire response as string
        return str(response_data), {}

    @property
    def supported_chat_message_roles(self) -> list[str]:
        """Supported chat message roles."""
        return ["user", "assistant", "system"]

    def _get_identifier(self) -> str:
        """Unique identifier for this target."""
        return f"CustomBackendTarget::{self._conversation_id}"

    async def close_async(self) -> None:
        """Clean up resources and close WebSocket connection."""
        try:
            if self._websocket is not None:
                await self._websocket.close()
                logger.info(
                    "websocket_closed",
                    session_id=self.session_id
                )
                self._websocket = None
        except Exception as e:
            logger.warning(
                "websocket_close_error",
                error=str(e),
                session_id=self.session_id
            )