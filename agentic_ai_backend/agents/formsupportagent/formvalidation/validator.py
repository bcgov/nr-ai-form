"""LLM-backed advisory validation of one form step's answers.

The contract with every caller is that this module never raises. Any failure - timeout, auth,
rate limit, malformed model output - resolves to ``([], "unavailable")``, because a validation
outage must be invisible to the applicant and must never impede the form.

Follows the structured-output pattern established by the orchestrator's Dispatcher: the raw
``openai`` SDK, ``chat.completions.parse`` with a Pydantic ``response_format``, and server-side
re-validation of whatever comes back.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from openai import AsyncAzureOpenAI

from agents.formsupportagent.formvalidation.fieldvisibility import (
    build_field_payload,
    resolve_validatable_fields,
)
from agents.formsupportagent.models.formvalidationmodel import (
    MAX_ISSUES,
    MAX_MESSAGE_LENGTH,
    LlmIssueList,
    ValidationIssue,
)
from utils.tenantsettings import (
    AZURE_OPENAI_API_KEY_ENV,
    AZURE_OPENAI_API_VERSION_ENV,
    AZURE_OPENAI_CHAT_DEPLOYMENT_ENV,
    AZURE_OPENAI_ENDPOINT_ENV,
    environment_setting,
    setting_from_client_config,
)

logger = logging.getLogger(__name__)

_INSTRUCTIONS_PATH = Path(__file__).resolve().parent / "validation-instructions.md"
_VALIDATION_TIMEOUT_SECONDS = float(os.getenv("FORM_VALIDATION_TIMEOUT_SECONDS", "20"))

_ALLOWED_SEVERITIES = frozenset({"info", "warning"})

_instructions_cache: Optional[str] = None
_client: Optional[AsyncAzureOpenAI] = None
_client_signature: Optional[tuple[str, str, str, str]] = None


def _load_instructions() -> str:
    global _instructions_cache
    if _instructions_cache is None:
        _instructions_cache = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    return _instructions_cache


def _resolve_openai_settings(client_settings: Optional[dict]) -> tuple[Any, Any, Any, Any]:
    """Endpoint and key are deployment-owned; deployment name and API version prefer the tenant.

    /validate is currently untenanted, so both tenant-owned values fall back to environment
    variables. Passing client_settings keeps the tenant-aware path working unchanged.
    """
    endpoint = environment_setting(AZURE_OPENAI_ENDPOINT_ENV)
    api_key = environment_setting(AZURE_OPENAI_API_KEY_ENV)

    deployment = setting_from_client_config(client_settings, "azureOpenaiChatDeploymentName")
    if not deployment:
        deployment = environment_setting(AZURE_OPENAI_CHAT_DEPLOYMENT_ENV)

    api_version = setting_from_client_config(client_settings, "azureOpenaiApiVersion")
    if not api_version:
        api_version = environment_setting(AZURE_OPENAI_API_VERSION_ENV)

    return api_key, endpoint, deployment, api_version


def _get_or_create_client(
    client_settings: Optional[dict],
) -> tuple[Optional[AsyncAzureOpenAI], Optional[str]]:
    global _client, _client_signature

    api_key, endpoint, deployment, api_version = _resolve_openai_settings(client_settings)
    if not (api_key and endpoint and deployment and api_version):
        logger.warning(
            "Form validation is not configured; missing one of endpoint/key/deployment/api_version."
        )
        return None, None

    signature = (api_key, endpoint, deployment, api_version)
    if _client is None or _client_signature != signature:
        _client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            azure_deployment=deployment,
        )
        _client_signature = signature

    return _client, deployment


def _sanitize(
    parsed: LlmIssueList,
    step_id: str,
    fields: Dict[str, Dict[str, Any]],
) -> list[ValidationIssue]:
    """Re-validate the model's output server-side. Assume it misbehaves."""
    issues: list[ValidationIssue] = []
    seen: set[str] = set()

    for candidate in parsed.issues or []:
        field_id = (candidate.fieldId or "").strip()
        # The model occasionally invents a field or comments on one we filtered out.
        if field_id not in fields or field_id in seen:
            continue

        message = (candidate.message or "").strip()
        if not message:
            continue
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[: MAX_MESSAGE_LENGTH - 1].rstrip() + "…"

        severity = candidate.severity if candidate.severity in _ALLOWED_SEVERITIES else "info"

        suggested = (candidate.suggestedValue or "").strip() or None
        options = fields[field_id].get("enum")
        if suggested and isinstance(options, list) and options:
            # A suggestion outside the field's own option list is unusable in the UI.
            if not any(str(option).strip().casefold() == suggested.casefold() for option in options):
                suggested = None

        issues.append(
            ValidationIssue(
                stepId=step_id,
                fieldId=field_id,
                severity=severity,
                message=message,
                suggestedValue=suggested,
            )
        )
        seen.add(field_id)

        if len(issues) >= MAX_ISSUES:
            break

    return issues


async def validate_step(
    step_id: str,
    form_definition: Dict[str, Any],
    form_data: Dict[str, Any],
    client_settings: Optional[dict] = None,
) -> tuple[list[ValidationIssue], str]:
    """Review one step's answers. Returns (issues, status) and never raises."""
    fields = resolve_validatable_fields(form_definition, form_data)
    if not fields:
        # Nothing on this step carries an answer worth looking at - a clean, confident result.
        logger.info("Form validation step=%s: no validatable fields, skipping LLM call", step_id)
        return [], "ok"

    client, deployment = _get_or_create_client(client_settings)
    if client is None:
        return [], "unavailable"

    user_payload = {
        "step": step_id,
        "formName": form_definition.get("formName"),
        "formDescription": form_definition.get("formDescription"),
        "fields": build_field_payload(fields, form_data),
    }

    started = time.monotonic()
    try:
        completion = await asyncio.wait_for(
            client.chat.completions.parse(
                model=deployment,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": _load_instructions()},
                    {"role": "user", "content": json.dumps(user_payload, default=str)},
                ],
                response_format=LlmIssueList,
            ),
            timeout=_VALIDATION_TIMEOUT_SECONDS,
        )
        parsed = completion.choices[0].message.parsed
    except asyncio.TimeoutError:
        logger.warning(
            "Form validation timed out after %.1fs step=%s", _VALIDATION_TIMEOUT_SECONDS, step_id
        )
        return [], "unavailable"
    except Exception as exc:
        # Auth, rate limit, transport, schema refusal - all degrade identically.
        logger.warning("Form validation LLM call failed step=%s: %s", step_id, exc)
        return [], "unavailable"

    latency_ms = int((time.monotonic() - started) * 1000)

    if parsed is None:
        logger.warning("Form validation returned no parsed output step=%s", step_id)
        return [], "unavailable"

    issues = _sanitize(parsed, step_id, fields)
    logger.info(
        "Form validation step=%s fields=%d raw_issues=%d kept_issues=%d latency_ms=%d",
        step_id,
        len(fields),
        len(parsed.issues or []),
        len(issues),
        latency_ms,
    )
    return issues, "ok"
