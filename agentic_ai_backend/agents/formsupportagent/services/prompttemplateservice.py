import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from agents.formsupportagent.models.formsupportmodel import FormSupportAgentClientSettings
from utils.blobservice import BlobService, load_blob_text_required
from utils.tenantsettings import settings_cache_parts

logger = logging.getLogger(__name__)


@dataclass
class _CachedPromptTemplate:
    value: str
    expires_at: float


_PROMPT_TEMPLATE_CACHE: dict[tuple[str, str, str, str], _CachedPromptTemplate] = {}
_PROMPT_TEMPLATE_CACHE_TTL_SECONDS = float(os.getenv("FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS", "300"))


class PromptTemplateService:
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
            path = config.get("stepBasedPromptContainer")
            if path not in (None, ""):
                return path
            raise ValueError("client_settings.config.stepBasedPromptContainer is required.")

        return "prompttemplates"

    def _cache_key(self, template_name: str) -> tuple[str, str, str, str]:
        return (
            self.client_id,
            self.config_fingerprint,
            self.directory_path.strip("/"),
            template_name,
        )

    def fetch_prompt_template(self, template_name: str) -> Optional[str]:
        cache_key = self._cache_key(template_name)
        now = time.monotonic()
        cached = _PROMPT_TEMPLATE_CACHE.get(cache_key)
        if _PROMPT_TEMPLATE_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
            return cached.value

        try:
            if not self.blob_service or not self.container_name:
                raise RuntimeError("Blob service is required for prompt templates.")

            template_content = load_blob_text_required(
                connection_string=self.blob_service.connection_string,
                container_name=self.container_name,
                directory=self.directory_path,
                blob_filename=template_name,
            )
            _PROMPT_TEMPLATE_CACHE[cache_key] = _CachedPromptTemplate(
                value=template_content,
                expires_at=now + _PROMPT_TEMPLATE_CACHE_TTL_SECONDS,
            )
            return template_content
        except Exception as e:
            print(f"Error fetching prompt template {template_name}: {e}")
            logger.warning("Error fetching prompt template %s: %s", template_name, e)
            return None

    def list_available_templates(self) -> list[str]:
        try:
            blobs = self.blob_service.list_blobs(self.container_name, name_starts_with=self.directory_path)
            return [b for b in blobs if b.endswith(".md")]
        except Exception as e:
            print(f"Error listing prompt templates: {e}")
            logger.warning("Error listing prompt templates: %s", e)
            return []
