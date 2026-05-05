from __future__ import annotations

import json
import time
from fastapi import Request, Response
from telemetry.telemetry_interface import ExceptionTelemetry
from telemetry.azure_monitor_telemetry import OpenTelemetryAzureMonitorTelemetry


def create_telemetry_middleware(telemetry: OpenTelemetryAzureMonitorTelemetry):
    """Return a FastAPI HTTP middleware function."""

    # This middleware captures telemetry for incoming HTTP requests, including timing, success/failure, and request/response payloads.
    async def telemetry_middleware(request: Request, call_next):
        if request.url.path not in {"/invoke"}:
            return await call_next(request)

        # Start a telemetry span for the incoming request, and record timing and attributes
        request.state.telemetry_start = time.perf_counter()
        request.state.telemetry_span = telemetry.start_span(
            f"{request.method} {request.url.path}",
            kind="server",
            attributes={
                "http.method": request.method,
                "http.route": request.url.path,
                "http.url": str(request.url),
            },
        )

        try:
            # Combine request + response into a JSON array stored as a single span attribute.
            request_body = await request.body()
            response = await call_next(request)
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk if isinstance(chunk, bytes) else chunk.encode()
            duration_ms = (time.perf_counter() - request.state.telemetry_start) * 1000
            payload = json.dumps(
                [_safe_parse_json(request_body), _safe_parse_json(response_body)],
                separators=(",", ":"),
            )
            # End the telemetry span with success/failure and rich attributes for request/response details and timing.
            telemetry.end_span(
                request.state.telemetry_span,
                success=response.status_code < 500,
                attributes={
                    "http.status_code": response.status_code,
                    "http.server.duration_ms": duration_ms,
                    "invoke.payload": payload[:5000],
                    "request.body.bytes": len(request_body),
                    "response.body.bytes": len(response_body),
                },
            )
            # Re-wrap and return the response since body_iterator has been consumed.
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Capture and log any exceptions that occur during request processing
        except Exception as exc:
            telemetry.track_exception(
                ExceptionTelemetry(
                    exception=exc,
                    handled=False,
                    properties={
                        "http.route": request.url.path,
                        "http.method": request.method,
                    },
                )
            )
            telemetry.end_span(request.state.telemetry_span, success=False)
            raise
        
    # safe-parse JSON bodies for telemetry attributes, falling back to truncated string if parsing fails or payload is too large
    def _safe_parse_json(raw: bytes) -> object:
        """Return parsed JSON object, or the raw decoded string on failure."""
        try:
            return json.loads(raw)
        except Exception:
            return raw.decode("utf-8", errors="replace")

    return telemetry_middleware
