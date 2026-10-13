"""
Shared DeepEval fixtures.

- `judge`  : the configured Azure evaluation model (skips the module if creds are
             missing so collection never hard-fails in CI without secrets).
- Live-mode tests fail when the configured backend is unreachable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from azure_judge import AzureJudge  # noqa: E402
from dataset_loader import is_live  # noqa: E402
from shared.backend_client import health_check  # noqa: E402


@pytest.fixture(scope="session")
def judge() -> AzureJudge:
    # Auth is Azure AD (az login) by default; only the endpoint is strictly
    # required. An API key is optional and used only if explicitly set.
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        if is_live():
            pytest.fail("EVAL_LIVE=1 requires AZURE_OPENAI_ENDPOINT for the judge")
        pytest.skip("AZURE_OPENAI_ENDPOINT not set — skipping LLM-judged metrics")
    return AzureJudge()


@pytest.fixture(scope="session", autouse=True)
def _require_backend_when_live():
    if is_live() and not health_check(timeout=int(os.getenv("BACKEND_API_TIMEOUT", "180"))):
        pytest.fail("EVAL_LIVE=1 but the configured backend failed its health check")
