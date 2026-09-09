"""
Shared DeepEval fixtures.

- `judge`  : the Azure GPT-4.1 evaluation model (skips the module if creds are
             missing so collection never hard-fails in CI without secrets).
- Live-mode tests are skipped automatically when the backend is unreachable.
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
        pytest.skip("AZURE_OPENAI_ENDPOINT not set — skipping LLM-judged metrics")
    return AzureJudge()


@pytest.fixture(scope="session", autouse=True)
def _require_backend_when_live():
    if is_live() and not health_check():
        pytest.skip("EVAL_LIVE=1 but backend /health is unreachable")
