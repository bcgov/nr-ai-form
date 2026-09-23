"""Tenant-specific edge-case category templates and graceful-decline copy.

These are structured JSON assets (not LLM prompt Markdown), loaded from Azure
Blob Storage the same way agents/formsupportagent/services/formdefinitionservice.py
loads per-tenant form definitions: no local-file fallback, cached in process
memory keyed by (client_id, config_fingerprint, directory, filename) with a TTL.

fetch_edge_case_templates is only called for tenants with edgeCasePolicy=="custom".
fetch_graceful_decline_messages is independent of edgeCasePolicy - any tenant may
configure it, and it is safe to call unconditionally with directory=None.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from utils.blobservice import load_blob_text_required

logger = logging.getLogger(__name__)

_EDGE_CASE_ASSET_CACHE_TTL_SECONDS = float(os.getenv("EDGE_CASE_ASSET_CACHE_TTL_SECONDS", "300"))

TEMPLATES_BLOB_FILENAME = "templates.json"
GRACEFUL_DECLINE_BLOB_FILENAME = "messages.json"


@dataclass
class _CachedAsset:
    value: Any
    expires_at: float


_ASSET_CACHE: dict[tuple[str, str, str, str], _CachedAsset] = {}


def _cache_key(client_id: str, config_fingerprint: str, directory: str, filename: str) -> tuple[str, str, str, str]:
    return (client_id, config_fingerprint, directory.strip("/"), filename)


def _load_json_asset(
    *,
    connection_string: Optional[str],
    container_name: Optional[str],
    directory: Optional[str],
    blob_filename: str,
    client_id: str,
    config_fingerprint: str,
) -> Optional[Any]:
    if not directory:
        return None

    cache_key = _cache_key(client_id, config_fingerprint, directory, blob_filename)
    now = time.monotonic()
    cached = _ASSET_CACHE.get(cache_key)
    if _EDGE_CASE_ASSET_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
        return cached.value

    try:
        raw = load_blob_text_required(
            connection_string=connection_string,
            container_name=container_name,
            directory=directory,
            blob_filename=blob_filename,
        )
        value = json.loads(raw)
    except Exception as exc:
        logger.warning("Failed to load edge-case asset %s/%s: %s", directory, blob_filename, exc)
        return None

    if _EDGE_CASE_ASSET_CACHE_TTL_SECONDS > 0:
        _ASSET_CACHE[cache_key] = _CachedAsset(value=value, expires_at=now + _EDGE_CASE_ASSET_CACHE_TTL_SECONDS)
    return value


def fetch_edge_case_templates(
    *,
    connection_string: Optional[str],
    container_name: Optional[str],
    directory: Optional[str],
    client_id: str,
    config_fingerprint: str,
) -> Optional[dict[str, str]]:
    """Return this tenant's {category_key: reply_markdown} map, or None to fall back."""
    value = _load_json_asset(
        connection_string=connection_string,
        container_name=container_name,
        directory=directory,
        blob_filename=TEMPLATES_BLOB_FILENAME,
        client_id=client_id,
        config_fingerprint=config_fingerprint,
    )
    if not isinstance(value, dict) or not value:
        return None
    return value


def fetch_graceful_decline_messages(
    *,
    connection_string: Optional[str],
    container_name: Optional[str],
    directory: Optional[str],
    client_id: str,
    config_fingerprint: str,
) -> Optional[tuple[str, str]]:
    """Return (first_attempt, second_attempt) for this tenant, or None to fall back.

    second_attempt defaults to first_attempt when the tenant only configured one
    shared message.
    """
    value = _load_json_asset(
        connection_string=connection_string,
        container_name=container_name,
        directory=directory,
        blob_filename=GRACEFUL_DECLINE_BLOB_FILENAME,
        client_id=client_id,
        config_fingerprint=config_fingerprint,
    )
    if not isinstance(value, dict):
        return None

    first_attempt = value.get("first_attempt")
    if not first_attempt:
        return None
    second_attempt = value.get("second_attempt") or first_attempt
    return first_attempt, second_attempt
