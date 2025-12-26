
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional

class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Optional[int] = 2  # Default to step 2 for backward compatibility

class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None