"""Tenant-aware HTTP CORS middleware for orchestrator tenant routes."""

import logging
import re
from urllib.parse import unquote

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from clientprofiles import (
    ClientIdRequiredError,
    ClientProfileNotFoundError,
    TenantConfigUnavailableError,
    is_origin_allowed,
)
from tenantconfigservice import get_tenant_config_service

logger = logging.getLogger(__name__)

_TENANT_PATH_RE = re.compile(r"^/tenants/([^/]+)/(?:invoke|ws)(?:/)?$")


def _client_id_from_path(path: str) -> str | None:
    match = _TENANT_PATH_RE.match(path)
    return unquote(match.group(1)) if match else None


def _add_cors_headers(response: Response, origin: str, requested_headers: str | None = None) -> Response:
    # Echo the validated Origin. Do not use '*' when credentials may be used.
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = requested_headers or "authorization,content-type"
    response.headers["Access-Control-Max-Age"] = "600"
    response.headers["Vary"] = "Origin"
    return response


async def tenant_cors_middleware(request: Request, call_next):
    """Apply tenant-specific CORS for /tenants/{client_id}/... HTTP routes.

    CORS preflight has no JSON body, so the tenant must be available in the URL
    path. This middleware resolves only the raw profile so CORS does not depend
    on downstream agent-setting validation.
    """
    origin = request.headers.get("origin")
    path = request.url.path
    method = request.method
    client_id = _client_id_from_path(path)

    if not origin or not client_id:
        return await call_next(request)

    try:
        profile = await get_tenant_config_service().get_profile(client_id)
    except ClientProfileNotFoundError:
        resp = Response(status_code=404)
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        return resp
    except (ClientIdRequiredError, TenantConfigUnavailableError):
        resp = Response(status_code=503)
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        return resp
    except Exception as exc:
        resp = Response(status_code=500)
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        return resp

    allowed = is_origin_allowed(origin, profile.corsOrigins)

    if not allowed:
        logger.warning(
            "Rejected HTTP origin",
            extra={"client_id": client_id, "origin": origin},
        )
        return Response(status_code=403)

    requested_headers = request.headers.get("access-control-request-headers")

    if method == "OPTIONS":
        return _add_cors_headers(Response(status_code=204), origin, requested_headers)
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(
            "Tenant route handler failed before a response was created",
            extra={"client_id": client_id, "origin": origin, "path": path},
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Unhandled orchestrator error. Check server logs for traceback.",
                "errorType": type(exc).__name__,
                "error": str(exc),
            },
        )
    return _add_cors_headers(response, origin, requested_headers)
