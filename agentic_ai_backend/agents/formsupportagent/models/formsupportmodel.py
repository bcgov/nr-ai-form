
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional, TypedDict, Union


class FormSupportAgentConfig(TypedDict, total=False):
    """The 'config' block for a Form Support Agent sub-agent in the client profile."""

    formDefinitionContainer: str
    stepBasedPromptContainer: str
    azureOpenaiChatDeploymentName: str
    azureOpenaiApiVersion: str

class FormSupportAgentClientSettings(TypedDict):
    """The full client_settings dict passed to FormSupportAgent invoke requests."""

    agentType: str
    enabled: bool
    clientId: str
    configFingerprint: str
    promptPath: str
    config: FormSupportAgentConfig


class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Union[int, str]  # Required step identifier
    client_settings: FormSupportAgentClientSettings


class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
