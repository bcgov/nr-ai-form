"""Custom Azure OpenAI Chat Target for PyRIT with proper API key authentication."""

import asyncio
import aiohttp
import json
from typing import Optional
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_configuration import TargetConfiguration
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
from pyrit.models import Message
import structlog

logger = structlog.get_logger(__name__)


class CustomAzureOpenAITarget(PromptTarget):
    """Custom target for Azure OpenAI with proper api-key header authentication."""

    # Declare capabilities for this target
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
        api_key: str = "",
        deployment: str = "gpt-5.1",
        api_version: str = "2024-10-21",
        timeout: int = 180,
    ):
        """
        Initialize custom Azure OpenAI target.

        Args:
            endpoint: Base endpoint URL (without /openai/deployments path)
            api_key: API key for authentication. If empty, Azure AD (az login)
                     is used via DefaultAzureCredential.
            deployment: Model deployment name
            api_version: Azure API version
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.timeout = timeout
        self._token_provider = None
        if not self.api_key:
            # Azure AD auth (az login) — matches our GPT-5.1 Foundry judge setup.
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            self._token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )

        logger.info(
            "custom_azure_openai_target_initialized",
            endpoint=self.endpoint,
            deployment=deployment,
            api_version=api_version,
            auth="api_key" if self.api_key else "azure_ad",
        )

    async def _send_prompt_to_target_async(
        self,
        *,
        normalized_conversation: list[Message],
    ) -> list[Message]:
        """
        Send prompt to Azure OpenAI endpoint and get response.
        
        Args:
            normalized_conversation: List of Message objects in conversation
            
        Returns:
            List of Message objects with response
        """
        try:
            # Get the last user message from the conversation
            last_message = None
            for msg in reversed(normalized_conversation):
                if hasattr(msg, 'api_role') and msg.api_role == "user":
                    last_message = msg
                    break
            
            if not last_message:
                error_response = Message.from_prompt(
                    prompt="No user message found in conversation",
                    role="assistant"
                )
                return [error_response]
            
            # Extract prompt text from message
            prompt = str(last_message.get_value())
            
            # Construct full URL for Azure OpenAI
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
            
            # Build request payload
            # Convert message history to Azure OpenAI format
            messages = []
            for msg in normalized_conversation:
                messages.append({
                    "role": msg.api_role,
                    "content": str(msg.get_value())
                })
            
            payload = {"messages": messages}
            
            # Headers with auth: api-key header, or AAD bearer token (az login).
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["api-key"] = self.api_key
            else:
                headers["Authorization"] = f"Bearer {self._token_provider()}"
            
            logger.info(
                "sending_azure_openai_request",
                url=url,
                num_messages=len(messages),
            )
            
            # Make async request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"Azure OpenAI API error {response.status}: {error_text}"
                        logger.error(
                            "azure_openai_request_failed",
                            status=response.status,
                            error=error_text,
                        )
                        error_response = Message.from_prompt(
                            prompt=error_msg,
                            role="assistant"
                        )
                        return [error_response]
                    
                    result = await response.json()
                    
                    # Extract response content
                    response_content = result["choices"][0]["message"]["content"]
                    
                    logger.info(
                        "azure_openai_request_success",
                        response_length=len(response_content),
                    )
                    
                    # Create response message
                    response_message = Message.from_prompt(
                        prompt=response_content,
                        role="assistant"
                    )
                    
                    return [response_message]
                    
        except Exception as e:
            error_msg = f"Error querying Azure OpenAI: {str(e)}"
            logger.error(
                "azure_openai_request_exception",
                error=str(e),
            )
            error_response = Message.from_prompt(
                prompt=error_msg,
                role="assistant"
            )
            return [error_response]

    @property
    def prompt_target_name(self) -> str:
        """Return target name."""
        return "CustomAzureOpenAI"

