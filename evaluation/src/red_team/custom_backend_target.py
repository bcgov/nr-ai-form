"""Custom PyRIT PromptTarget for attacking custom backend API."""

import asyncio
import aiohttp
from typing import Any
import uuid
from pyrit.prompt_target import PromptTarget
from pyrit.models import Message
import structlog

logger = structlog.get_logger(__name__)


class CustomBackendTarget(PromptTarget):
    """
    PyRIT PromptTarget that attacks a custom backend API.
    
    Sends red-teaming prompts to a custom /invoke endpoint instead of Azure OpenAI.
    """

    def __init__(
        self,
        endpoint: str,
        session_id: str = None,
        step_number: int = 2,
    ):
        """
        Initialize CustomBackendTarget.
        
        Args:
            endpoint: Full URL to the backend API endpoint (e.g., https://your-api.com/invoke)
            session_id: Session ID for the backend (defaults to generated UUID)
            step_number: Form step number (default: 2)
        """
        super().__init__()
        
        # Store endpoint as-is (should include /invoke or appropriate path)
        self.endpoint = endpoint.rstrip("/") if endpoint else endpoint
        self.session_id = session_id or str(uuid.uuid4())
        self.step_number = step_number
        self._conversation_id = str(uuid.uuid4())
        
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
                    prompt="No user message found in conversation",
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
            
            # Make async HTTP POST request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    invoke_url,
                    json=request_payload,
                    timeout=aiohttp.ClientTimeout(total=30),
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
                            prompt=f"Error {response.status}: {error_text}",
                            role="assistant"
                        )
                        return [error_response]
                        
        except asyncio.TimeoutError:
            logger.error("backend_timeout", endpoint=self.endpoint, session_id=self.session_id)
            error_response = Message.from_prompt(
                prompt="Timeout connecting to backend",
                role="assistant"
            )
            return [error_response]
        except Exception as e:
            logger.error("backend_connection_error", error=str(e), endpoint=self.endpoint)
            error_response = Message.from_prompt(
                prompt=f"Connection error: {str(e)}",
                role="assistant"
            )
            return [error_response]

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
