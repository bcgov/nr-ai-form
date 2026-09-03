"""
Async BackendClient shim for the red-team orchestrator.

Jatinder's orchestrator expects `BackendClient().invoke(query=, step_number=)`.
We back it with our shared functional client so there is a single source of
truth for the `/invoke` contract.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # evaluation/

from shared.backend_client import invoke as _invoke, health_check as _health  # noqa: E402


class BackendClient:
    """Thin async adapter over shared.backend_client."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url

    async def invoke(
        self, *, query: str, step_number: Optional[str] = None, session_id: Optional[str] = None
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            _invoke, query, step_number, session_id, self.base_url
        )

    async def health_check(self) -> bool:
        return await asyncio.to_thread(_health, self.base_url)
