"""Load orchestrator prompt/skill Markdown, preferring Azure Blob Storage.

The dispatcher's `system.md` and the aggregator's `user.md` are authored remotely
in the same blob container that holds the form definitions and prompt templates
(see `utils.blobservice.BlobService`). This module fetches them from blob when the
`AGENTPROMPTS_*` environment variables are configured, and transparently falls back
to the bundled local copies under `skills/` otherwise (or on any blob error).

Loading is intentionally lazy: `skillsregistry` and `aggregator` are imported before
`load_dotenv()` runs in the server/agent entry points, so the blob credentials are
only guaranteed to be present by the time a prompt is first needed at request time.
"""

import os
from functools import lru_cache
from pathlib import Path

from utils.blobservice import BlobService

_SKILLS_DIR = Path(__file__).parent / "skills"


def _blob_container() -> str | None:
    return os.getenv("AGENTPROMPTS_CONTAINER_NAME")


@lru_cache(maxsize=1)
def _blob_service() -> BlobService | None:
    """Build a singleton BlobService, or return None when unconfigured/unavailable."""
    connection_string = os.getenv("AGENTPROMPTS_BLOBSTORAGE_CONNECTIONSTRING")
    if not connection_string:
        return None
    try:
        return BlobService(connection_string)
    except Exception as exc:
        print(f"Prompt blob service init failed, using local prompts: {exc}")
        return None


def load_prompt(blob_path_env: str, blob_filename: str, local_rel_path: str) -> str:
    """Return prompt Markdown text from blob storage, falling back to the local file.

    Args:
        blob_path_env: env var holding the blob directory prefix (e.g.
            ``AGENT_DISPATCHER_PROMPTS_PATH``).
        blob_filename: file name within that directory (e.g. ``system.md``).
        local_rel_path: path relative to ``skills/`` used as the fallback.
    """
    service = _blob_service()
    container = _blob_container()
    directory = os.getenv(blob_path_env)

    if service and container and directory:
        blob_name = f"{directory.strip('/')}/{blob_filename}"
        try:
            text = service.read_blob_text(container, blob_name)
            print(f"Loaded prompt from blob: {container}/{blob_name}")
            return text
        except Exception as exc:
            print(f"Failed to load prompt from blob {blob_name}, using local: {exc}")

    return (_SKILLS_DIR / local_rel_path).read_text(encoding="utf-8")
