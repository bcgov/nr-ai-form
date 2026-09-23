"""Load tenant orchestrator prompt/skill Markdown from Azure Blob Storage.

Dispatcher and aggregator prompts are resolved only from tenant-configured Azure
Blob Storage. There is no local-file fallback; missing blob connection settings,
container name, prompt path, missing blobs, or empty blobs fail fast.

Prompt text is cached in process memory by tenant config fingerprint, container,
prompt directory, and filename. ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS controls
the TTL, defaults to 300 seconds, and can be set to 0 to disable this cache.
"""

import os
import time
from dataclasses import dataclass, field

from utils.blobservice import BlobService


@dataclass
class _CachedPrompt:
    text: str
    expires_at: float


_PROMPT_CACHE: dict[tuple[str, str, str, str], _CachedPrompt] = {}
_PROMPT_CACHE_TTL_SECONDS = float(os.getenv("ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS", "300"))


def _prompt_cache_key(
    cache_namespace: str,
    container_name: str,
    directory: str,
    blob_filename: str,
) -> tuple[str, str, str, str]:
    return (cache_namespace, container_name, directory.strip("/"), blob_filename)


def _load_prompt_cached(
    *,
    cache_namespace: str,
    connection_string: str,
    container_name: str,
    directory: str,
    blob_filename: str,
) -> str:
    now = time.monotonic()
    key = _prompt_cache_key(cache_namespace, container_name, directory, blob_filename)
    cached = _PROMPT_CACHE.get(key)
    if _PROMPT_CACHE_TTL_SECONDS > 0 and cached and now < cached.expires_at:
        return cached.text

    service = BlobService(connection_string)
    blob_name = f"{directory.strip('/')}/{blob_filename}"
    text = service.read_blob_text(container_name, blob_name)
    if not text.strip():
        raise RuntimeError(f"Orchestrator prompt blob {container_name}/{blob_name} is empty.")

    if _PROMPT_CACHE_TTL_SECONDS > 0:
        _PROMPT_CACHE[key] = _CachedPrompt(text=text, expires_at=now + _PROMPT_CACHE_TTL_SECONDS)
    return text


@dataclass(frozen=True)
class PromptSource:
    """Tenant-safe prompt source for one orchestrator request.

    cache_namespace should be the tenant config fingerprint. It keeps raw secrets
    out of cache keys while forcing a new cache entry whenever tenant config changes.
    """

    connection_string: str | None = None
    container_name: str | None = None
    prompt_directories: dict[str, str] = field(default_factory=dict)
    cache_namespace: str = "default"

    def load_prompt(self, blob_path_env: str, blob_filename: str, local_rel_path: str) -> str:
        """Return prompt Markdown text from tenant-configured Azure Blob Storage only.

        local_rel_path is intentionally ignored. It remains in the signature for
        older call sites, but production multitenant prompt loading must come
        from Azure Blob Storage and the TTL cache above.
        """
        connection_string = self.connection_string
        container = self.container_name
        directory = self.prompt_directories.get(blob_path_env)

        if not connection_string or not container or not directory:
            raise RuntimeError(f"Orchestrator prompt blob config is required for {blob_filename}.")

        return _load_prompt_cached(
            cache_namespace=self.cache_namespace,
            connection_string=connection_string,
            container_name=container,
            directory=directory,
            blob_filename=blob_filename,
        )


DEFAULT_PROMPT_SOURCE = PromptSource(cache_namespace="missing-tenant-config")
