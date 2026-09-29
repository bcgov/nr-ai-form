
# Pydantic models for the LLM-backed form validation endpoint.
#
# Two families live here:
#   * the wire contract (ValidateRequest/ValidateResponse) shared with the api_backend gateway
#   * the structured-output models the LLM is asked to fill (LlmIssue/LlmIssueList)
# They are deliberately separate: the model should never be asked to echo back the step id or
# any other value the server already knows and can stamp itself.

from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

from agents.formsupportagent.models.formsupportmodel import FormSupportAgentClientSettings


# Severity is advisory only. "info" is an observation worth a glance; "warning" is an
# observation the applicant would probably want to act on. Neither blocks submission.
Severity = Literal["info", "warning"]

# "ok" means the model ran and its (possibly empty) issue list is trustworthy.
# "unavailable" means validation degraded - timeout, auth failure, bad model output - and
# the caller should show nothing at all. It is never an error to the user.
ValidationStatus = Literal["ok", "unavailable"]

# Hard ceiling on issues returned for one step, enforced server-side after the model replies.
MAX_ISSUES = 3

# Messages longer than this are truncated rather than dropped.
MAX_MESSAGE_LENGTH = 300


class ValidateRequest(BaseModel):
    """Request body for POST /validate."""

    step_number: str
    form_data: dict[str, Any]
    session_id: Optional[str] = None
    # Optional: when the caller is tenant-aware the deployment name and API version come from
    # here, otherwise the validator falls back to the deployment-owned environment variables.
    client_settings: Optional[FormSupportAgentClientSettings] = None


class ValidationIssue(BaseModel):
    """One advisory observation about a single field."""

    stepId: str
    fieldId: str
    severity: Severity
    message: str
    suggestedValue: Optional[str] = None


class ValidateResponse(BaseModel):
    """Response body for POST /validate. `issues` is always empty when status is 'unavailable'."""

    stepId: str
    status: ValidationStatus
    issues: list[ValidationIssue]


# --- Structured output models -------------------------------------------------------------
# Field descriptions below are not documentation: they are serialized into the JSON schema
# sent to the model and do real prompting work. Same convention as the orchestrator's
# IntentListModel (agents/orchestrators/models/intentmodel.py).


class LlmIssue(BaseModel):
    fieldId: str = Field(
        description="The exact field id from the supplied field list. Never invent one."
    )
    severity: Severity = Field(
        description=(
            "'warning' if the applicant would likely want to revisit this answer, "
            "'info' for a lighter observation."
        )
    )
    message: str = Field(
        description=(
            "One short, observational sentence addressed to the applicant. Describe what you "
            "noticed; never assert that the answer is invalid, wrong, or legally incorrect."
        )
    )
    suggestedValue: Optional[str] = Field(
        default=None,
        description=(
            "A concrete replacement value, only when an obvious one exists. Omit otherwise. "
            "For a field with a fixed option list, this must be one of those options."
        ),
    )


class LlmIssueList(BaseModel):
    issues: list[LlmIssue] = Field(
        description=(
            "Observations worth surfacing, at most 3, most important first. "
            "Return an empty list when nothing is worth raising - that is the normal outcome."
        )
    )
