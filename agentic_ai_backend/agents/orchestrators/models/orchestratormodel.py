from pydantic import BaseModel
from typing import Any, Optional

class InvokeRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    step_number: Optional[str] = None
    # Optional only while the legacy POST /invoke route exists. Tenant routes
    # get client_id from the path; make this required or remove it with legacy invoke.
    client_id: Optional[str] = None

class InvokeResponse(BaseModel):
    response: Any
    session_id: Optional[str] = None
