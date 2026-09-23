import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agents.formsupportagent.models.formsupportmodel import FormSupportAgentClientSettings
from utils.blobservice import BlobService, load_blob_text_required
from utils.tenantsettings import settings_cache_parts

logger = logging.getLogger(__name__)


@dataclass
class _CachedFormDefinition:
    value: Dict[str, Any]
    expires_at: float


_FORM_DEFINITION_CACHE: dict[tuple[str, str, str, str], _CachedFormDefinition] = {}
_FORM_DEFINITION_CACHE_TTL_SECONDS = float(os.getenv("FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS", "300"))


class FormDefinitionService:
    def __init__(
        self,
        blob_service: BlobService | None,
        container_name: str | None,
        client_settings: FormSupportAgentClientSettings,
        directory_path: Optional[str] = None,
    ):
        self.blob_service = blob_service
        self.container_name = container_name
        # Explicit arg wins for tests/manual wiring; tenant calls require this path in client_settings.config.
        self.directory_path = self._resolve_directory_path(directory_path, client_settings)
        self.client_id, self.config_fingerprint = settings_cache_parts(client_settings)

    def _resolve_directory_path(
        self,
        explicit_path: Optional[str],
        client_settings: dict,
    ) -> str:
        if explicit_path:
            return explicit_path
        if client_settings is not None:
            config = client_settings.get("config") or {}
            path = config.get("formDefinitionContainer")
            if path not in (None, ""):
                return path
            raise ValueError("client_settings.config.formDefinitionContainer is required.")

        return "formdefinitions"

    def _cache_key(self, definition_name: str) -> tuple[str, str, str, str]:
        return (
            self.client_id,
            self.config_fingerprint,
            self.directory_path.strip("/"),
            definition_name,
        )

    def fetch_form_definition(self, definition_name: str) -> Optional[Dict[str, Any]]:
        cache_key = self._cache_key(definition_name)
        now = time.monotonic()
        cached = _FORM_DEFINITION_CACHE.get(cache_key)
        if _FORM_DEFINITION_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
            return cached.value

        try:
            if not self.blob_service or not self.container_name:
                raise RuntimeError("Blob service is required for form definitions.")

            json_content = load_blob_text_required(
                connection_string=self.blob_service.connection_string,
                container_name=self.container_name,
                directory=self.directory_path,
                blob_filename=definition_name,
            )
            form_data = json.loads(json_content)
            _FORM_DEFINITION_CACHE[cache_key] = _CachedFormDefinition(
                value=form_data,
                expires_at=now + _FORM_DEFINITION_CACHE_TTL_SECONDS,
            )
            return form_data
        except Exception as e:
            print(f"Error fetching form definition {definition_name}: {e}")
            logger.warning("Error fetching form definition %s: %s", definition_name, e)
            return None

    def list_available_definitions(self) -> list[str]:
        try:
            blobs = self.blob_service.list_blobs(self.container_name, name_starts_with=self.directory_path)
            return [b for b in blobs if b.endswith(".json")]
        except Exception as e:
            print(f"Error listing form definitions: {e}")
            logger.warning("Error listing form definitions: %s", e)
            return []
