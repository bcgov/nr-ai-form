"""
Thin client for the orchestrator backend `/invoke` endpoint.

Contract (agents/orchestrators/orchestrator_agent_server.py):
    POST /invoke  {query, step_number?, session_id?}  ->  {response, session_id}

`response` is a serialized Agent-Framework WorkflowOutputEvent. It is commonly
one of:
    - a plain string
    - a list of message dicts (each may carry {"response": "..."} or
      {"text": "..."} / {"content": "..."})
    - a dict with a "response"/"content"/"data" field
`extract_text` flattens all of these to a single string for grading.

Used by both the promptfoo python provider and DeepEval live-mode tests.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8002")
DEFAULT_TIMEOUT = int(os.getenv("BACKEND_API_TIMEOUT", "60"))
INVOKE_PATH = "/invoke"


def _base(url: Optional[str]) -> str:
    raw = (url or DEFAULT_BASE_URL).rstrip("/")
    return raw[: -len(INVOKE_PATH)] if raw.endswith(INVOKE_PATH) else raw


def health_check(base_url: Optional[str] = None, timeout: int = 10) -> bool:
    """Return True if the backend /health endpoint responds 200."""
    try:
        r = httpx.get(f"{_base(base_url)}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def invoke(
    query: str,
    step_number: Optional[str] = None,
    session_id: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """Call POST /invoke and return the parsed JSON body."""
    payload: dict[str, Any] = {"query": query}
    if step_number:
        payload["step_number"] = step_number
    if session_id:
        payload["session_id"] = session_id
    r = httpx.post(
        f"{_base(base_url)}{INVOKE_PATH}",
        json=payload,
        timeout=timeout or DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def extract_text(obj: Any) -> str:
    """Flatten an /invoke `response` payload into a single plain-text string."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for key in ("response", "content", "text", "message", "data"):
            if key in obj and obj[key] is not None:
                return extract_text(obj[key])
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, list):
        parts = [extract_text(x) for x in obj]
        return "\n".join(p for p in parts if p)
    return str(obj)


def invoke_text(
    query: str,
    step_number: Optional[str] = None,
    session_id: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Convenience: invoke and return only the flattened response text."""
    body = invoke(query, step_number, session_id, base_url, timeout)
    return extract_text(body.get("response", body))
