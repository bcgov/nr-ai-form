"""Custom PyRIT PromptTarget for attacking custom backend API."""

import asyncio
import aiohttp
import json
from typing import Any
import uuid
import os
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_configuration import TargetConfiguration
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
from pyrit.models import Message
import structlog

logger = structlog.get_logger(__name__)

# PyRIT requires an assistant message even on failure, so transport failures are
# returned as text. This marker lets the runner tell them apart from real answers.
INFRA_ERROR_PREFIX = "INFRA_ERROR::"


class CustomBackendTarget(PromptTarget):
    """
    PyRIT PromptTarget that attacks a custom backend API.
    
    Sends red-teaming prompts to a custom /invoke endpoint instead of Azure OpenAI.
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
        step_number: int = 2,
        timeout: int = None,
    ):
        """
        Initialize CustomBackendTarget.
        
        Args:
            endpoint: Full URL to the backend API endpoint (e.g., https://your-api.com/invoke)
            session_id: Session ID for the backend (defaults to generated UUID)
            step_number: Form step number (default: 2)
            timeout: Request timeout in seconds. Defaults to BACKEND_API_TIMEOUT
                     env (or 180) — GPT-5.1 reasoning routinely exceeds 30s.
        """
        super().__init__()
        
        # Store endpoint as-is (should include /invoke or appropriate path)
        self.endpoint = endpoint.rstrip("/") if endpoint else endpoint
        self.session_id = session_id or str(uuid.uuid4())
        self.step_number = step_number
        self.timeout = timeout or int(os.getenv("BACKEND_API_TIMEOUT", "180"))
        self._conversation_id = str(uuid.uuid4())
        # The public gateway speaks WebSocket; the orchestrator speaks HTTP /invoke.
        self.is_websocket = str(self.endpoint or "").startswith(("ws://", "wss://"))
        self.ws_origin = os.getenv("BACKEND_WS_ORIGIN", "")
        self.ws_step = os.getenv("BACKEND_WS_STEP", "step2-Eligibility")
        self.ws_client_id = os.getenv("BACKEND_WS_CLIENT_ID", str(uuid.uuid4()))
        self.ws_application_id = int(os.getenv("BACKEND_WS_APPLICATION_ID", "234554"))
        
        logger.info(
            "custom_backend_target_initialized",
            endpoint=self.endpoint,
            session_id=self.session_id,
            step_number=step_number
        )

    async def _send_prompt_to_target_async(
        self,
        *,
        normalized_conversation: list[Message],
    ) -> list[Message]:
        """
        Send prompt to custom backend API.
        
        Args:
            normalized_conversation: List of Message objects in conversation
            
        Returns:
            List of Message objects with backend response
        """
        try:
            # Get the last user message from the conversation
            last_message = None
            for msg in reversed(normalized_conversation):
                # Check api_role instead of role
                if hasattr(msg, 'api_role') and msg.api_role == "user":
                    last_message = msg
                    break
            
            if not last_message:
                error_response = Message.from_prompt(
                    prompt=f"{INFRA_ERROR_PREFIX}NO_USER_MESSAGE::No user message found in conversation",
                    role="assistant"
                )
                return [error_response]
            
            # Extract prompt text from message using get_value()
            prompt = str(last_message.get_value())
            
            # Build request payload matching your backend API
            request_payload = {
                "query": prompt,
                "session_id": self.session_id,
                "step_number": str(self.step_number),
            }
            
            # Use endpoint as-is (assumes it already has /invoke or appropriate path)
            invoke_url = self.endpoint
            
            logger.info(
                "sending_backend_prompt",
                url=invoke_url,
                query_length=len(prompt),
                session_id=self.session_id
            )

            if self.is_websocket:
                response_data = await self._invoke_websocket(prompt)
                response_text = self._extract_response(response_data)
                logger.info(
                    "backend_response_received",
                    transport="websocket",
                    session_id=self.session_id,
                    response_length=len(response_text),
                )
                return [Message.from_prompt(prompt=response_text, role="assistant")]

            # Make async HTTP POST request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    invoke_url,
                    json=request_payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Extract response text from backend format
                        response_text = self._extract_response(response_data)
                        
                        logger.info(
                            "backend_response_received",
                            status=response.status,
                            session_id=self.session_id,
                            response_length=len(response_text)
                        )
                        
                        # Return list of Message objects in PyRIT format
                        response_message = Message.from_prompt(
                            prompt=response_text,
                            role="assistant"
                        )
                        return [response_message]
                    else:
                        error_text = await response.text()
                        logger.error(
                            "backend_error",
                            status=response.status,
                            error=error_text
                        )
                        
                        error_response = Message.from_prompt(
                            prompt=f"{INFRA_ERROR_PREFIX}BACKEND_HTTP_{response.status}::Error {response.status}: {error_text}",
                            role="assistant"
                        )
                        return [error_response]
                        
        except asyncio.TimeoutError:
            logger.error("backend_timeout", endpoint=self.endpoint, session_id=self.session_id)
            error_response = Message.from_prompt(
                prompt=f"{INFRA_ERROR_PREFIX}BACKEND_TIMEOUT::Timeout connecting to backend",
                role="assistant"
            )
            return [error_response]
        except Exception as e:
            logger.error("backend_connection_error", error=str(e), endpoint=self.endpoint)
            error_response = Message.from_prompt(
                prompt=f"{INFRA_ERROR_PREFIX}BACKEND_CONNECTION::Connection error: {str(e)}",
                role="assistant"
            )
            return [error_response]

    async def _invoke_websocket(self, prompt: str) -> dict:
        """Send one turn over the WebSocket gateway and return the answer frame.

        The gateway emits a `session_init` frame first and assigns its own
        session id, which we adopt so multi-turn attacks stay on one thread.
        """
        payload = {
            "client_id": self.ws_client_id,
            "query": prompt,
            "step_number": self.ws_step,
            "session_id": self.session_id,
            "application_id": self.ws_application_id,
        }
        headers = {"Origin": self.ws_origin} if self.ws_origin else None

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                self.endpoint,
                headers=headers,
                timeout=aiohttp.ClientWSTimeout(ws_close=self.timeout),
                heartbeat=None,
            ) as ws:
                await ws.send_json(payload)
                deadline = asyncio.get_running_loop().time() + self.timeout
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise asyncio.TimeoutError("no answer frame before timeout")
                    msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
                    if msg.type is not aiohttp.WSMsgType.TEXT:
                        raise ConnectionError(
                            f"websocket closed: {msg.type.name} "
                            f"code={msg.data!r} reason={msg.extra!r}"
                        )
                    frame = json.loads(msg.data)
                    if frame.get("event") == "session_init":
                        self.session_id = frame.get("session_id", self.session_id)
                        continue
                    if "response" in frame:
                        return frame

    def _extract_response(self, response_data: dict) -> str:
        """
        Extract response text from backend response format.
        
        Args:
            response_data: Response from backend /invoke endpoint
            
        Returns:
            Extracted response text
        """
        # Handle aggregator response format
        if isinstance(response_data, dict) and "response" in response_data:
            response_list = response_data.get("response", [])
            
            # Look for aggregator response
            if isinstance(response_list, list) and len(response_list) > 0:
                agg_response = response_list[0]
                if isinstance(agg_response, dict):
                    # Check if it has response field
                    if "response" in agg_response:
                        return str(agg_response["response"]) or "(empty response)"
                    # Check original_results
                    if "original_results" in agg_response:
                        results = agg_response["original_results"]
                        if isinstance(results, list) and len(results) > 0:
                            return str(results[0].get("response", "(empty)"))
        
        # Fallback: return entire response as string
        return str(response_data)

    @property
    def supported_chat_message_roles(self) -> list[str]:
        """Supported chat message roles."""
        return ["user", "assistant", "system"]

    def _get_identifier(self) -> str:
        """Unique identifier for this target."""
        return f"CustomBackendTarget::{self._conversation_id}"

    async def close_async(self) -> None:
        """Clean up resources."""
        pass
