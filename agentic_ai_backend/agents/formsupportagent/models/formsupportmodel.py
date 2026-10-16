
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional, TypedDict, Union


class FormSupportAgentConfig(TypedDict, total=False):
    """The 'config' block for a Form Support Agent sub-agent in the client profile."""

    formDefinitionContainer: str
    stepBasedPromptContainer: str
    azureOpenaiChatDeploymentName: str
    azureOpenaiApiVersion: str
    # Names of in-process MCP tool sets to give the agent (see local_mcp/toolregistry.py),
    # e.g. ["LIVESTOCK_WATER_CONSUMPTION_TOOLS", "FISHING_LICENCE_FEE_CALCULATION_TOOLS"].
    mcpTools: list[str]


class FormSupportAgentClientSettings(TypedDict):
    """The full client_settings dict passed to FormSupportAgent invoke requests."""

    agentType: str
    enabled: bool
    clientId: str
    configFingerprint: str
    promptPath: str
    config: FormSupportAgentConfig


class HistoryTurn(BaseModel):
    role: str
    text: str


class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Union[int, str]  # Required step identifier
    client_settings: FormSupportAgentClientSettings
    history: Optional[list[HistoryTurn]] = None


class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
