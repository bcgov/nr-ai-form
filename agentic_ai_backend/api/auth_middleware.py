from __future__ import annotations

import base64
import binascii
import hmac
import os
from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response


API_BASIC_AUTH_USERNAME = os.getenv("API_BASIC_AUTH_USERNAME", "")
API_BASIC_AUTH_PASSWORD = os.getenv("API_BASIC_AUTH_PASSWORD", "")


def is_authorized_basic_auth(header_value: str | None) -> bool:
    if not API_BASIC_AUTH_USERNAME or not API_BASIC_AUTH_PASSWORD:
        return False

    if not header_value or not header_value.startswith("Basic "):
        return False

    token = header_value[6:].strip()
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False

    if ":" not in decoded:
        return False

    username, password = decoded.split(":", 1)
    return hmac.compare_digest(username, API_BASIC_AUTH_USERNAME) and hmac.compare_digest(password, API_BASIC_AUTH_PASSWORD)


def register_invoke_basic_auth_middleware(app) -> None:
    @app.middleware("http")
    async def basic_auth_invoke_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "POST" and request.url.path == "/invoke":
            auth_header = request.headers.get("Authorization")
            if not is_authorized_basic_auth(auth_header):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Unauthorized"},
                    headers={"WWW-Authenticate": "Basic"},
                )

        return await call_next(request)
