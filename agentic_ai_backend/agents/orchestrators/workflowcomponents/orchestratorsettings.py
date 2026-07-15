"""Helpers for request-scoped orchestrator runtime settings."""

import os
from typing import Any

from clientprofiles import OrchestratorRuntimeSettings


def runtime_value(
    settings: OrchestratorRuntimeSettings | None,
    field_name: str,
    *,
    default: Any = None,
) -> Any:
    """Read a value from tenant runtime settings only."""
    if settings is None:
        return default

    value = getattr(settings, field_name, None)
    return default if value in (None, "") else value


def runtime_int_value(
    settings: OrchestratorRuntimeSettings | None,
    field_name: str,
    *,
    default: int,
) -> int:
    value = runtime_value(settings, field_name, default=default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def openai_common_settings(
    settings: OrchestratorRuntimeSettings | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Return api_key, endpoint, deployment, and api_version for orchestrator LLM calls."""
    return (
        os.getenv("AZURE_OPENAI_API_KEY"),
        os.getenv("AZURE_OPENAI_ENDPOINT"),
        runtime_value(settings, "azureOpenAIChatDeploymentName"),
        runtime_value(settings, "azureOpenAIApiVersion"),
    )
