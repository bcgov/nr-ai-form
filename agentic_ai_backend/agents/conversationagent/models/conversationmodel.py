
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional

class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None