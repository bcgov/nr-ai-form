"""Shared gateway WebSocket transport and optional legacy HTTP /invoke client."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from dotenv import load_dotenv
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.typing import Origin

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_BASE_URL = "ws://localhost:8000/ws"
DEFAULT_TIMEOUT = 180
INVOKE_PATH = "/invoke"
logger = logging.getLogger(__name__)


class BackendError(RuntimeError):
    """The backend did not return a valid assistant response."""


def _base(url: str | None) -> str:
    raw = (url or os.getenv("BACKEND_API_URL") or DEFAULT_BASE_URL).rstrip("/")
    if raw.startswith(("http://", "https://")) and raw.endswith(INVOKE_PATH):
        return raw[: -len(INVOKE_PATH)]
    return raw


class BackendClient:
    """Keep one backend conversation on a persistent WebSocket, as in Jatinder's client."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        session_id: str | None = None,
        *,
        client_id: str | None = None,
        origin: str | None = None,
        application_id: int | None = None,
    ) -> None:
        self.base_url = _base(base_url)
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"ws", "wss", "http", "https"} or not parsed.hostname:
            raise ValueError("BACKEND_API_URL must be an http(s) or ws(s) URL")
        self.is_websocket = parsed.scheme in {"ws", "wss"}
        self.timeout = timeout if timeout is not None else float(
            os.getenv("BACKEND_API_TIMEOUT", str(DEFAULT_TIMEOUT))
        )
        if self.timeout <= 0:
            raise ValueError("BACKEND_API_TIMEOUT must be positive")
        self.session_id = session_id or dict(parse_qsl(parsed.query)).get("session_id") or str(uuid.uuid4())
        self.client_id = client_id if client_id is not None else os.getenv("BACKEND_WS_CLIENT_ID", "")
        self.origin = origin if origin is not None else os.getenv("BACKEND_WS_ORIGIN", "")
        self.application_id = application_id if application_id is not None else int(
            os.getenv("BACKEND_WS_APPLICATION_ID", "234554")
        )
        if self.is_websocket and (not self.client_id or not self.origin):
            raise ValueError(
                "Gateway evaluations require BACKEND_WS_CLIENT_ID for a configured tenant "
                "and BACKEND_WS_ORIGIN allowed by that tenant"
            )
        self._websocket: ClientConnection | None = None

    async def invoke(
        self,
        query: str,
        step_number: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if session_id and session_id != self.session_id:
            await self.close()
            self.session_id = session_id
        payload: dict[str, Any] = {
            "query": query,
            "step_number": step_number or os.getenv("BACKEND_WS_STEP", "step2-Eligibility"),
            "session_id": self.session_id,
        }
        if self.is_websocket:
            payload.update(client_id=self.client_id, application_id=self.application_id)
            try:
                return await asyncio.wait_for(self._invoke_websocket(payload), timeout=self.timeout)
            except TimeoutError as exc:
                await self.close()
                raise BackendError(f"Backend timed out after {self.timeout:g}s") from exc
            except ConnectionClosed as exc:
                await self.close()
                close = exc.rcvd or exc.sent
                raise BackendError(
                    f"WebSocket closed: code={close.code if close else 'unknown'} "
                    f"reason={close.reason if close else 'no close frame'}"
                ) from exc
            except (OSError, WebSocketException) as exc:
                await self.close()
                raise BackendError(f"WebSocket connection failed: {exc}") from exc
            except BackendError:
                await self.close()
                raise
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}{INVOKE_PATH}", json=payload)
            response.raise_for_status()
            return self._validate_response(response.json())

    async def _invoke_websocket(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._websocket is None:
            parsed = urlsplit(self.base_url)
            # The gateway reads session_id from the connection query, not the JSON body.
            params = [(key, value) for key, value in parse_qsl(parsed.query) if key != "session_id"]
            params.append(("session_id", self.session_id))
            url = urlunsplit(parsed._replace(query=urlencode(params)))
            self._websocket = await connect(
                url, origin=Origin(self.origin), open_timeout=min(30, self.timeout), max_size=None
            )
        await self._websocket.send(json.dumps(payload))
        while True:
            raw = await self._websocket.recv()
            try:
                frame = json.loads(raw)
            except (ValueError, TypeError) as exc:
                raise BackendError("Backend returned invalid JSON") from exc
            if isinstance(frame, dict) and frame.get("event") == "session_init":
                if not frame.get("session_id"):
                    raise BackendError("Backend session_init has no session_id")
                self.session_id = str(frame["session_id"])
                continue
            return self._validate_response(frame)

    @staticmethod
    def _validate_response(frame: Any) -> dict[str, Any]:
        if not isinstance(frame, dict):
            raise BackendError("Backend response must be a JSON object")
        if "error" in frame:
            raise BackendError(f"Backend error: {frame['error']}")
        if "response" not in frame or not extract_text(frame["response"]).strip():
            raise BackendError("Backend returned no assistant response")
        return frame

    async def close(self) -> None:
        if self._websocket is not None:
            websocket, self._websocket = self._websocket, None
            await websocket.close()


async def invoke_async(
    query: str,
    step_number: str | None = None,
    session_id: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    client = BackendClient(base_url, timeout, session_id)
    try:
        return await client.invoke(query, step_number)
    finally:
        await client.close()


def invoke(
    query: str,
    step_number: str | None = None,
    session_id: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    return asyncio.run(invoke_async(query, step_number, session_id, base_url, timeout))


def health_check(base_url: str | None = None, timeout: int = 10) -> bool:
    """Check the HTTP stand-in or validate a complete gateway request."""
    try:
        base = _base(base_url)
        if base.startswith(("ws://", "wss://")):
            invoke("What is a water licence?", base_url=base, timeout=timeout)
            return True
        response = httpx.get(f"{base}/health", timeout=timeout)
        response.raise_for_status()
        return True
    except (BackendError, httpx.HTTPError, ValueError) as exc:
        logger.error("Backend health check failed: %s", exc)
        return False


def extract_text(obj: Any) -> str:
    """Flatten an assistant response for grading."""
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
        return "\n".join(part for item in obj if (part := extract_text(item)))
    return str(obj)


def invoke_text(
    query: str,
    step_number: str | None = None,
    session_id: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> str:
    body = invoke(query, step_number, session_id, base_url, timeout)
    return extract_text(body["response"])
