
# Pydantic models for request/response

from pydantic import BaseModel
from typing import Optional, Union

class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Union[int, str]  # Required step identifier

class InvokeResponse(BaseModel):
    response: str
    session_id: Optional[str] = None