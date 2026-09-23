"""Helpers for resolving tenant-aware settings from request payloads."""

import os
from typing import Any, Mapping


AZURE_OPENAI_ENDPOINT_ENV = "AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_API_KEY_ENV = "AZURE_OPENAI_API_KEY"
AZURE_SEARCH_API_KEY_ENV = "AZURE_SEARCH_API_KEY"
AZURE_SEARCH_ENDPOINT_ENV = "AZURE_SEARCH_ENDPOINT"
AZURE_BLOB_CONNECTION_STRING_ENV = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
AZURE_BLOB_CONTAINER_ENV = "AZURE_BLOBSTORAGE_CONTAINER"


class MissingClientSettingError(ValueError):
    """Raised when a tenant request omits required client settings."""


def is_missing(value: Any) -> bool:
    return value in (None, "")


def environment_setting(
    env_name: str,
    *,
    required: bool = False,
) -> Any:
    """Read a deployment-owned setting from environment only."""
    value = os.getenv(env_name)
    if is_missing(value):
        if required:
            raise MissingClientSettingError(f"{env_name} is required in environment.")
        return None
    return value


def setting_from_client_config(
    client_settings: Mapping[str, Any] | None,
    config_key: str,
    *,
    default: Any = None,
    required: bool = False,
) -> Any:
    """Read a tenant config value from client_settings only."""
    if client_settings is None:
        if required:
            raise MissingClientSettingError(f"client_settings.config.{config_key} is required.")
        return default

    cfg = client_settings.get("config") or {}
    value = cfg.get(config_key, default)
    source = f"client_settings.config.{config_key}"

    if is_missing(value):
        if required:
            raise MissingClientSettingError(f"{source} is required.")
        return default
    return value


def top_level_setting_from_client(
    client_settings: Mapping[str, Any] | None,
    client_key: str,
    *,
    required: bool = False,
) -> Any:
    """Read a top-level tenant setting from client_settings only."""
    if client_settings is None:
        if required:
            raise MissingClientSettingError(f"client_settings.{client_key} is required.")
        return None

    value = client_settings.get(client_key)
    source = f"client_settings.{client_key}"

    if is_missing(value):
        if required:
            raise MissingClientSettingError(f"{source} is required.")
        return None
    return value


def settings_cache_parts(client_settings: Mapping[str, Any] | None) -> tuple[str, str]:
    """Return secret-safe tenant cache-key parts from settings metadata."""
    if client_settings is None:
        return ("missing-client-settings", "missing-fingerprint")
    return (
        str(client_settings.get("clientId") or "unknown"),
        str(client_settings.get("configFingerprint") or "unfingerprinted"),
    )