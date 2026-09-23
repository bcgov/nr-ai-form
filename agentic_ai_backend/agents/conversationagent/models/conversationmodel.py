
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional

from models.client_settings_type import ConversationAgentClientSettings


class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    client_settings: ConversationAgentClientSettings


class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
