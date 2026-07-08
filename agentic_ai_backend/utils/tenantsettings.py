"""Helpers for resolving tenant-aware settings from request payloads."""

from typing import Any, Mapping


class MissingClientSettingError(ValueError):
    """Raised when a tenant request omits required client settings."""


def is_missing(value: Any) -> bool:
    return value in (None, "")


def setting_from_client_config(
    client_settings: Mapping[str, Any] | None,
    config_key: str,
    *,
    default: Any = None,
    required: bool = False,
) -> Any:
    """Read a config value from tenant client_settings only."""
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