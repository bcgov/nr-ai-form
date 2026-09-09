"""
promptfoo custom provider — the *system under test*.

promptfoo calls `call_api(prompt, options, context)` for every test row. We
ignore the rendered `prompt` and instead read the structured vars (`query`,
`step_number`) so the backend receives exactly the payload it expects. The
GPT-5.1-powered orchestrator is the target here; grading is done separately by
the judge model configured in promptfooconfig.yaml (GPT-4.1).

Configure the target via env (see evaluation/.env.example):
    BACKEND_API_URL   default http://localhost:8002
    BACKEND_API_TIMEOUT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Make the shared client importable regardless of promptfoo's CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.backend_client import invoke, extract_text  # noqa: E402


def call_api(prompt: str, options: dict, context: dict) -> dict[str, Any]:
    vars_ = (context or {}).get("vars", {}) or {}
    query = vars_.get("query") or prompt
    step_number = vars_.get("step_number")

    try:
        body = invoke(query=query, step_number=step_number)
        text = extract_text(body.get("response", body))
        return {
            "output": text,
            "metadata": {
                "session_id": body.get("session_id"),
                "step_number": step_number,
            },
        }
    except Exception as e:  # surface as a graded failure rather than crashing the run
        return {"error": f"backend invoke failed: {e}"}
