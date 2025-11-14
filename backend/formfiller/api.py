
"""
FastAPI endpoints for the form-filling agent.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID
from .graph import FormField, chat_analyze_form

router = APIRouter()

class ChatRequest(BaseModel):
    user_message: str
    form_fields: Optional[List[Dict[str, Any]]] = None
    filled_fields: Optional[List[Dict[str, Any]]] = None
    missing_fields: Optional[List[Dict[str, Any]]] = None
    current_field: Optional[list] = None
    conversation_history: Optional[list] = None
    status: Optional[str] = None
    response_message: Optional[str] = None
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    thread_id: str
    response_message: str
    status: str
    filled_fields: Optional[List[Dict[str, Any]]] = None
    missing_fields: Optional[list] = None
    current_field: Optional[list] = None
    conversation_history: Optional[list] = None

# Request and response models
class StartFormRequest(BaseModel):
    """Request model for starting a new form-filling session"""
    message: str
    formFields: Optional[List[dict]] = None

class ContinueFormRequest(BaseModel):
    """Request model for continuing an existing form-filling session"""
    thread_id: str
    message: str

class FormResponse(BaseModel):
    """Response model for form-filling operations"""
    thread_id: str
    response: str
    status: str
    filled_fields: Optional[List[dict]] = None
    missing_fields: Optional[List[dict]] = None
    current_field: Optional[dict] = None
    next_field: Optional[dict] = None
    conversation_history: Optional[List[dict]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    New /chat endpoint: sends every request to analyze_form orchestrator agent.
    Accepts the new payload structure (user_message required, others optional).
    """
    # Build state dict from request, only including provided fields
    state = {k: v for k, v in request.dict().items() if v is not None}
    if "user_message" not in state:
        raise HTTPException(status_code=422, detail="user_message is required")
    try:
        result = await chat_analyze_form(state)
        # Ensure filled_fields is always a list of dicts
        raw_filled = result.get("filled_fields", [])
        if isinstance(raw_filled, dict):
            filled_fields = [raw_filled]
        elif isinstance(raw_filled, list):
            filled_fields = raw_filled
        else:
            filled_fields = []

        # Ensure current_field is always a list
        current_field = result.get("current_field", [])
        if current_field is None:
            current_field = []
        elif isinstance(current_field, dict):
            current_field = [current_field]
        elif not isinstance(current_field, list):
            current_field = [current_field]

        # Update form_fields with filled_fields if filled_fields is not empty
        form_fields = result.get("form_fields", [])
        if filled_fields:
            # Update form_fields with values from filled_fields
            updated_form_fields = []
            for field in form_fields:
                data_id = field.get("data_id") or field.get("field_id")
                match = next((f for f in filled_fields if (f.get("data_id") or f.get("field_id")) == data_id), None)
                if data_id and match:
                    updated = {**field, **match}
                    updated_form_fields.append(updated)
                else:
                    updated_form_fields.append(field)
            form_fields = updated_form_fields

        return ChatResponse(
            thread_id=result.get("thread_id", ""),
            response_message=result.get("response_message", ""),
            status=result.get("status", ""),
            filled_fields=filled_fields,
            missing_fields=result.get("missing_fields", []),
            current_field=current_field,
            conversation_history=result.get("conversation_history", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in /chat: {str(e)}")
@router.get("/schema")
def get_schema():
    """Get the expected schema for API requests"""
    return {
        "start_request": {
            "message": "string - the user's initial query",
            "formFields": [
                {
                    "data_id": "string - unique identifier for this field",
                    "fieldLabel": "string - human-readable label for the field",
                    "fieldType": "string - type of input (text, radio, select, etc.)",
                    "field_value": "string - initial value (empty string by default)",
                    "is_required": "boolean - whether this field must be filled",
                    "options": "array of strings - possible values for dropdown/radio fields (optional)"
                }
            ]
        },
        "continue_request": {
            "thread_id": "string - the session ID returned from start request",
            "message": "string - the user's response to previous agent message"
        },
        "example": {
            "message": "I need to apply for a fee exemption",
            "formFields": [
                {
                    "data_id": "V1IsEligibleForFeeExemption",
                    "fieldLabel": "Are you eligible for fee exemption?",
                    "fieldType": "radio",
                    "field_value": "",
                    "is_required": True,
                    "options": ["Yes", "No"]
                }
            ]
        }
    }