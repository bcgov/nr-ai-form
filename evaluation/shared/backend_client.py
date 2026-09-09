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

import asyncio
import json
import os
import uuid
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8002")
DEFAULT_TIMEOUT = int(os.getenv("BACKEND_API_TIMEOUT", "60"))
INVOKE_PATH = "/invoke"


def _is_ws(url: str) -> bool:
    return url.startswith(("ws://", "wss://"))


def _base(url: Optional[str]) -> str:
    raw = (url or DEFAULT_BASE_URL).rstrip("/")
    return raw[: -len(INVOKE_PATH)] if raw.endswith(INVOKE_PATH) else raw


def health_check(base_url: Optional[str] = None, timeout: int = 10) -> bool:
    """Return True if the backend /health endpoint responds 200."""
    base = _base(base_url)
    if _is_ws(base):
        # The gateway exposes no /health; a successful handshake is the probe.
        try:
            _invoke_ws("ping", None, None, base, timeout)
            return True
        except Exception:
            return False
    try:
        r = httpx.get(f"{base}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


async def _invoke_ws_async(
    query: str,
    step_number: Optional[str],
    session_id: Optional[str],
    url: str,
    timeout: int,
) -> dict[str, Any]:
    import websockets

    payload = {
        "client_id": os.getenv("BACKEND_WS_CLIENT_ID", str(uuid.uuid4())),
        "query": query,
        "step_number": step_number or os.getenv("BACKEND_WS_STEP", "step2-Eligibility"),
        "session_id": session_id or str(uuid.uuid4()),
        "application_id": int(os.getenv("BACKEND_WS_APPLICATION_ID", "234554")),
    }
    origin = os.getenv("BACKEND_WS_ORIGIN") or None

    async with websockets.connect(url, origin=origin, open_timeout=30, max_size=None) as ws:
        await ws.send(json.dumps(payload))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError("no answer frame before timeout")
            frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
            if frame.get("event") == "session_init":
                continue
            if "response" in frame:
                return frame


def _invoke_ws(
    query: str,
    step_number: Optional[str],
    session_id: Optional[str],
    url: str,
    timeout: int,
) -> dict[str, Any]:
    return asyncio.run(_invoke_ws_async(query, step_number, session_id, url, timeout))


def invoke(
    query: str,
    step_number: Optional[str] = None,
    session_id: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """Call the backend and return the parsed JSON body.

    Transport is chosen from the URL scheme: ws/wss uses the WebSocket gateway,
    anything else uses POST /invoke.
    """
    base = _base(base_url)
    timeout = timeout or DEFAULT_TIMEOUT
    if _is_ws(base):
        return _invoke_ws(query, step_number, session_id, base, timeout)
    payload: dict[str, Any] = {"query": query}
    if step_number:
        payload["step_number"] = step_number
    if session_id:
        payload["session_id"] = session_id
    r = httpx.post(f"{base}{INVOKE_PATH}", json=payload, timeout=timeout)
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
