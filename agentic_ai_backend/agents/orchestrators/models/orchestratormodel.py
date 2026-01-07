from pydantic import BaseModel
from typing import Any, Optional

class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Optional[str] = None

class InvokeResponse(BaseModel):
    response: Any
    session_id: Optional[str] = None
