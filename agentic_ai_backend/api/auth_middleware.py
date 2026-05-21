"""Redis-backed Basic Auth helpers and middleware registration.

This module centralizes auth behavior for the API gateway:
- parses Basic Auth headers,
- validates client credentials against Redis-stored client config,
- registers HTTP middleware that protects POST /invoke,
- and exposes cleanup for the shared Redis client.
"""

from __future__ import annotations

import base64
import binascii
import hmac
import os
from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from redis.asyncio import Redis


# Redis connection settings for the dedicated auth client-config database.
REDIS_HOST = os.getenv("API_AUTH_REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("API_AUTH_REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("API_AUTH_REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("API_AUTH_REDIS_DB", "1"))
REDIS_KEY_PREFIX = os.getenv("API_AUTH_REDIS_KEY_PREFIX", "client_config:")

# Lazy singleton Redis client shared across requests.
_redis_client: Redis | None = None


def _redis_connection_kwargs() -> dict:
    """Build Redis client kwargs from environment configuration."""
    kwargs = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "decode_responses": True,
    }
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    return kwargs


def get_redis_client() -> Redis:
    """Return a cached Redis client, creating it on first use."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(**_redis_connection_kwargs())
    return _redis_client


async def close_redis_client() -> None:
    """Close and clear the cached Redis client during app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def _parse_basic_credentials(header_value: str | None) -> tuple[str, str] | None:
    """Decode a Basic Auth header into (username, password), or None if invalid."""
    if not header_value or not header_value.startswith("Basic "):
        return None

    token = header_value[6:].strip()
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    if ":" not in decoded:
        return None

    username, password = decoded.split(":", 1)
    return username, password


async def is_authorized_basic_auth(header_value: str | None) -> bool:
    """Validate Basic Auth credentials against Redis client configuration.

    Expected key format: <REDIS_KEY_PREFIX><username>
    Expected hash fields:
    - password: client secret to compare against Basic Auth password
    - enabled: optional flag, truthy values are true/1/yes
    """
    credentials = _parse_basic_credentials(header_value)
    if not credentials:
        return False

    username, password = credentials
    client_key = f"{REDIS_KEY_PREFIX}{username}"

    client_config = await get_redis_client().hgetall(client_key)
    if not client_config:
        return False

    if client_config.get("enabled", "true").lower() not in {"true", "1", "yes"}:
        return False

    stored_password = client_config.get("password", "")
    if not stored_password:
        return False

    return hmac.compare_digest(password, stored_password)


def register_invoke_basic_auth_middleware(app) -> None:
    """Register middleware on the FastAPI app for protecting POST /invoke."""

    @app.middleware("http")
    async def basic_auth_invoke_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Gate only the orchestrator invoke route; other routes remain unaffected.
        if request.method == "POST" and request.url.path == "/invoke":
            auth_header = request.headers.get("Authorization")
            if not await is_authorized_basic_auth(auth_header):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Unauthorized"},
                    headers={"WWW-Authenticate": "Basic"},
                )

        return await call_next(request)
