from typing import Any, Optional

from pydantic import BaseModel


class InvokeResponse(BaseModel):
    response: Any
    session_id: Optional[str] = None
