from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any

# types for telemetry data structures 
from telemetry.telemetry_interface import (
    DependencyTelemetry,
    EventTelemetry,
    ExceptionTelemetry,
    ITelemetry,
    MetricTelemetry,
    RequestTelemetry,
    TelemetryProperties,
)

logger = logging.getLogger(__name__)

class OpenTelemetryAzureMonitorTelemetry(ITelemetry):
    """Azure Monitor-backed ITelemetry implementation using OpenTelemetry."""

    _azure_monitor_configured = False

    def __init__(
        self,
        *,
        service_name: str,
        connection_string_env: str = "APPLICATIONINSIGHTS_CONNECTION_STRING",
    ) -> None:
        self._service_name = service_name
        self._connection_string_env = connection_string_env
        self._service_version: str | None = None
        self._environment: str | None = None
        self._cloud_role: str | None = None
        self._default_properties: dict[str, Any] = {}
        self._tracer = None
        self._meter = None
        self._histograms: dict[str, Any] = {}
        self._counters: dict[str, Any] = {}

    def configure(self) -> None:
        connection_string = os.getenv(self._connection_string_env)
        if not connection_string:
            logger.warning(
                "%s is not set. Telemetry export to Application Insights is disabled.",
                self._connection_string_env,
            )
            return

        try:
            if not self.__class__._azure_monitor_configured:
                from azure.monitor.opentelemetry import configure_azure_monitor

                configure_azure_monitor(connection_string=connection_string)
                self.__class__._azure_monitor_configured = True

            trace_api, metrics_api = self._get_otel_apis()
            self._tracer = trace_api.get_tracer(self._service_name)
            self._meter = metrics_api.get_meter(self._service_name)
        except Exception as exc:
            logger.error("Failed to configure Azure Monitor OpenTelemetry: %s", exc)

    def set_common_context(
        self,
        *,
        service_name: str,
        service_version: str | None = None,
        environment: str | None = None,
        cloud_role: str | None = None,
        default_properties: TelemetryProperties | None = None,
    ) -> None:
        self._service_name = service_name
        self._service_version = service_version
        self._environment = environment
        self._cloud_role = cloud_role
        self._default_properties = dict(default_properties or {})

        try:
            trace_api, metrics_api = self._get_otel_apis()
            self._tracer = trace_api.get_tracer(service_name)
            self._meter = metrics_api.get_meter(service_name)
        except Exception:
            logger.debug("OpenTelemetry APIs are not available while setting common context.")

    def track_request(self, telemetry: RequestTelemetry) -> None:
        span = self.start_span(
            telemetry.name,
            kind="server",
            attributes=self._merge_attributes(
                telemetry.properties,
                {
                    "http.method": telemetry.method,
                    "http.url": telemetry.url,
                    "http.status_code": str(telemetry.response_code),
                    "app.session_id": telemetry.session_id,
                    "enduser.id": telemetry.user_id,
                    "app.operation_id": telemetry.operation_id,
                },
            ),
        )
        self._record_histogram(
            "http.server.duration",
            telemetry.duration_ms,
            self._merge_attributes(telemetry.properties, telemetry.measurements),
        )
        if span is None:
            return
        self.end_span(
            span,
            success=telemetry.success,
            attributes={"http.status_code": str(telemetry.response_code)},
        )

    def track_dependency(self, telemetry: DependencyTelemetry) -> None:
        span = self.start_span(
            telemetry.name,
            kind="client",
            attributes=self._merge_attributes(
                telemetry.properties,
                {
                    "dependency.type": telemetry.dependency_type,
                    "server.address": telemetry.target,
                    "dependency.data": telemetry.data,
                    "dependency.result_code": telemetry.result_code,
                    "app.operation_id": telemetry.operation_id,
                },
            ),
        )
        self._record_histogram(
            "dependency.duration",
            telemetry.duration_ms,
            self._merge_attributes(telemetry.properties, telemetry.measurements),
        )
        if span is None:
            return
        self.end_span(
            span,
            success=telemetry.success,
            attributes={"dependency.result_code": telemetry.result_code},
        )

    def track_event(self, telemetry: EventTelemetry) -> None:
        """Emit a custom event to the Application Insights customEvents table.

        Azure Monitor routes any OTel log record that carries the
        'microsoft.custom_event.name' attribute to customEvents instead of traces,
        making it queryable in the Events blade and as a metric via
        ``customEvents | summarize ...``.
        """
        try:
            from time import time_ns
            from opentelemetry._logs import get_logger_provider
            from opentelemetry._logs._internal import LogRecord, SeverityNumber

            event_attributes = self._sanitize_attributes(
                self._merge_attributes(telemetry.properties, telemetry.measurements)
            )
            # This attribute is the Azure Monitor signal that routes the log record to customEvents.
            event_attributes["microsoft.custom_event.name"] = telemetry.name

            log_record = LogRecord(
                timestamp=time_ns(),
                severity_number=SeverityNumber.INFO,
                body=telemetry.name,
                attributes=event_attributes,
            )
            get_logger_provider().get_logger(self._service_name).emit(log_record)
        except Exception as exc:
            logger.error("Failed to emit custom event '%s': %s", telemetry.name, exc)

    def track_metric(self, telemetry: MetricTelemetry) -> None:
        self._record_counter(
            telemetry.name,
            telemetry.value,
            self._merge_attributes(telemetry.properties, {"metric.unit": telemetry.unit}),
        )

    def track_exception(self, telemetry: ExceptionTelemetry) -> None:
        span = self._get_current_span()
        if span is None:
            span = self.start_span("exception", kind="internal")
        if span is None:
            logger.exception("Unhandled telemetry exception", exc_info=telemetry.exception)
            return

        self.set_span_attributes(
            span,
            self._merge_attributes(
                telemetry.properties,
                {
                    "exception.handled": telemetry.handled,
                    "app.operation_id": telemetry.operation_id,
                },
            ),
        )
        try:
            span.record_exception(telemetry.exception)
        except Exception:
            logger.exception("Failed to record exception on active span", exc_info=telemetry.exception)

    def start_span(
        self,
        name: str,
        *,
        kind: str = "internal",
        attributes: TelemetryProperties | None = None,
        parent_context: Any | None = None,
    ) -> Any:
        tracer = self._get_tracer()
        if tracer is None:
            return None

        span_kind = self._get_span_kind(kind)
        span = tracer.start_span(name=name, context=parent_context, kind=span_kind)
        self.set_span_attributes(span, attributes or {})
        return span

    def end_span(
        self,
        span: Any,
        *,
        success: bool | None = None,
        attributes: TelemetryProperties | None = None,
    ) -> None:
        if span is None:
            return

        self.set_span_attributes(span, attributes or {})

        try:
            status_api = self._get_status_api()
            if success is True:
                span.set_status(status_api.Status(status_api.StatusCode.OK))
            elif success is False:
                span.set_status(status_api.Status(status_api.StatusCode.ERROR))
            span.end()
        except Exception as exc:
            logger.error("Failed to end telemetry span: %s", exc)

    def add_span_event(
        self,
        span: Any,
        name: str,
        *,
        attributes: TelemetryProperties | None = None,
    ) -> None:
        if span is None:
            return
        try:
            span.add_event(name, attributes=self._sanitize_attributes(attributes or {}))
        except Exception as exc:
            logger.error("Failed to add telemetry event '%s': %s", name, exc)

    def set_span_attributes(self, span: Any, attributes: TelemetryProperties) -> None:
        if span is None:
            return
        for key, value in self._sanitize_attributes(attributes).items():
            try:
                span.set_attribute(key, value)
            except Exception as exc:
                logger.debug("Skipping span attribute %s due to %s", key, exc)

    def flush(self) -> None:
        try:
            trace_api, metrics_api = self._get_otel_apis()
            tracer_provider = trace_api.get_tracer_provider()
            meter_provider = metrics_api.get_meter_provider()

            if hasattr(tracer_provider, "force_flush"):
                tracer_provider.force_flush()
            if hasattr(meter_provider, "force_flush"):
                meter_provider.force_flush()
        except Exception as exc:
            logger.debug("Telemetry flush skipped: %s", exc)

    def shutdown(self) -> None:
        try:
            trace_api, metrics_api = self._get_otel_apis()
            tracer_provider = trace_api.get_tracer_provider()
            meter_provider = metrics_api.get_meter_provider()

            if hasattr(tracer_provider, "shutdown"):
                tracer_provider.shutdown()
            if hasattr(meter_provider, "shutdown"):
                meter_provider.shutdown()
        except Exception as exc:
            logger.debug("Telemetry shutdown skipped: %s", exc)

    # internal helper methods for managing OpenTelemetry API interactions and abstractions
    def _get_tracer(self) -> Any:
        if self._tracer is None:
            try:
                trace_api, _ = self._get_otel_apis()
                self._tracer = trace_api.get_tracer(self._service_name)
            except Exception as exc:
                logger.debug("OpenTelemetry tracer is unavailable: %s", exc)
                return None
        return self._tracer

    def _get_meter(self) -> Any:
        if self._meter is None:
            try:
                _, metrics_api = self._get_otel_apis()
                self._meter = metrics_api.get_meter(self._service_name)
            except Exception as exc:
                logger.debug("OpenTelemetry meter is unavailable: %s", exc)
                return None
        return self._meter

    def _record_histogram(
        self,
        name: str,
        value: float,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        meter = self._get_meter()
        if meter is None:
            return
        instrument = self._histograms.get(name)
        if instrument is None:
            instrument = meter.create_histogram(name, unit="ms")
            self._histograms[name] = instrument
        instrument.record(value, attributes=self._sanitize_attributes(attributes or {}))

    def _record_counter(
        self,
        name: str,
        value: float,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        meter = self._get_meter()
        if meter is None:
            return
        instrument = self._counters.get(name)
        if instrument is None:
            instrument = meter.create_counter(name)
            self._counters[name] = instrument
        instrument.add(value, attributes=self._sanitize_attributes(attributes or {}))

    def _get_current_span(self) -> Any:
        try:
            trace_api, _ = self._get_otel_apis()
            span = trace_api.get_current_span()
            if getattr(span, "is_recording", None) and span.is_recording():
                return span
        except Exception as exc:
            logger.debug("No active span is available: %s", exc)
        return None

    def _get_span_kind(self, kind: str) -> Any:
        trace_types = self._get_trace_types_api()
        normalized = kind.lower()
        if normalized == "server":
            return trace_types.SpanKind.SERVER
        if normalized == "client":
            return trace_types.SpanKind.CLIENT
        if normalized == "producer":
            return trace_types.SpanKind.PRODUCER
        if normalized == "consumer":
            return trace_types.SpanKind.CONSUMER
        return trace_types.SpanKind.INTERNAL

    def _get_otel_apis(self) -> tuple[Any, Any]:
        from opentelemetry import metrics, trace

        return trace, metrics

    def _get_trace_types_api(self) -> Any:
        from opentelemetry.trace import SpanKind

        return type("TraceTypes", (), {"SpanKind": SpanKind})

    def _get_status_api(self) -> Any:
        from opentelemetry.trace import StatusCode
        from opentelemetry.trace.status import Status

        return type("StatusApi", (), {"Status": Status, "StatusCode": StatusCode})

    def _merge_attributes(self, *attribute_sets: Mapping[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "service.name": self._service_name,
            **self._default_properties,
        }

        if self._service_version:
            merged["service.version"] = self._service_version
        if self._environment:
            merged["deployment.environment"] = self._environment
        if self._cloud_role:
            merged["cloud.role"] = self._cloud_role

        for attributes in attribute_sets:
            if not attributes:
                continue
            merged.update(attributes)
        return self._sanitize_attributes(merged)

    def _sanitize_attributes(self, attributes: Mapping[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in attributes.items():
            if value is None:
                continue
            if isinstance(value, (bool, int, float, str)):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized