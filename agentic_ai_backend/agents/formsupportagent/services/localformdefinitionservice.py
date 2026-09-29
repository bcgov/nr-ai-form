"""Local-filesystem loader for form definitions.

The blob-backed FormDefinitionService is the production path and has no local fallback by
design. This loader exists for the /validate endpoint, which currently reads the definitions
committed under ``formdefinitions/``. It deliberately mirrors FormDefinitionService's
``fetch_form_definition(name) -> dict | None`` shape so swapping to blob later is a
constructor change at the call site and nothing more.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class _CachedFormDefinition:
    value: Dict[str, Any]
    expires_at: float


_LOCAL_FORM_DEFINITION_CACHE: dict[str, _CachedFormDefinition] = {}
# Shares the blob services' TTL variable so both caches behave identically.
_CACHE_TTL_SECONDS = float(os.getenv("FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS", "300"))

_DEFAULT_DIRECTORY = Path(__file__).resolve().parent.parent / "formdefinitions"

# Step identifiers reach us straight from an untrusted request body and become a filename,
# so anything outside this alphabet is rejected before it touches the filesystem.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

# Field types that hold no applicant-supplied answer worth validating.
NON_DATA_FIELD_TYPES = frozenset(
    {"button", "link", "display", "popup", "action", "bot", "grid", "file", "upload", "confirm"}
)


def is_safe_step_key(step_key: str) -> bool:
    """Return True when a step identifier is safe to use as a filename."""
    return bool(step_key) and bool(_SAFE_NAME.match(step_key))


class LocalFormDefinitionService:
    def __init__(self, directory_path: Optional[str] = None):
        self.directory_path = Path(directory_path) if directory_path else _DEFAULT_DIRECTORY
        self._resolved_root = self.directory_path.resolve()

    def fetch_form_definition(self, definition_name: str) -> Optional[Dict[str, Any]]:
        """Load ``<directory>/<definition_name>``, or None when it is missing or unreadable."""
        stem = definition_name[:-5] if definition_name.endswith(".json") else definition_name
        if not is_safe_step_key(stem):
            logger.warning("Rejected unsafe form definition name %r", definition_name)
            return None

        now = time.monotonic()
        cached = _LOCAL_FORM_DEFINITION_CACHE.get(stem)
        if _CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
            return cached.value

        path = (self._resolved_root / f"{stem}.json").resolve()
        # Belt and braces: even with the alphabet check above, confirm we never escaped the root.
        if not str(path).startswith(str(self._resolved_root) + os.sep):
            logger.warning("Rejected form definition path outside the definitions root: %s", path)
            return None

        try:
            with open(path, "r", encoding="utf-8") as handle:
                form_definition = json.load(handle)
        except FileNotFoundError:
            logger.info("Form definition not found locally: %s", path.name)
            return None
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Error reading local form definition %s: %s", path.name, exc)
            return None

        if _CACHE_TTL_SECONDS > 0:
            _LOCAL_FORM_DEFINITION_CACHE[stem] = _CachedFormDefinition(
                value=form_definition,
                expires_at=now + _CACHE_TTL_SECONDS,
            )
        return form_definition

    def list_available_definitions(self) -> list[str]:
        try:
            return sorted(p.name for p in self._resolved_root.glob("*.json"))
        except OSError as exc:
            logger.warning("Error listing local form definitions: %s", exc)
            return []


def normalize_fields(form_definition: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Return a step's fields keyed by the identifier ``visibleIf`` conditions reference.

    The definitions are not uniform. Most use ``formfields``; three older ones
    (step0-Bot, step10-Complete, step9-Declarations) use ``properties``, which may be a dict
    or a list. Conditions always reference the *dict key*, which is not always the same as the
    field's own ``id`` - so the key is what we index on, and ``id`` is kept as an alias for
    looking values up in form_data.
    """
    if not isinstance(form_definition, dict):
        return {}

    raw = form_definition.get("formfields")
    if raw is None:
        raw = form_definition.get("properties")

    fields: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        for key, field in raw.items():
            if isinstance(field, dict):
                fields[str(key)] = field
    elif isinstance(raw, list):
        # A list has no dict key, so the field's own id is the only available identifier.
        for field in raw:
            if isinstance(field, dict):
                key = field.get("id") or field.get("ID")
                if key:
                    fields[str(key)] = field

    return fields
