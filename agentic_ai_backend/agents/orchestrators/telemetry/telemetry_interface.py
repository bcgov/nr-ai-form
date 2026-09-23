from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------- Telemetry data structures and interface definitions ----------
TelemetryProperties = Mapping[str, Any]
TelemetryMeasurements = Mapping[str, float]

@dataclass(slots=True)
class RequestTelemetry:
	name: str
	url: str
	duration_ms: float
	response_code: int | str
	success: bool
	method: str | None = None
	timestamp_utc: datetime | None = None
	operation_id: str | None = None
	session_id: str | None = None
	user_id: str | None = None
	properties: dict[str, Any] = field(default_factory=dict)
	measurements: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class DependencyTelemetry:
	name: str
	target: str
	dependency_type: str
	duration_ms: float
	success: bool
	data: str | None = None
	result_code: str | None = None
	timestamp_utc: datetime | None = None
	operation_id: str | None = None
	properties: dict[str, Any] = field(default_factory=dict)
	measurements: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class EventTelemetry:
	name: str
	timestamp_utc: datetime | None = None
	operation_id: str | None = None
	properties: dict[str, Any] = field(default_factory=dict)
	measurements: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class MetricTelemetry:
	name: str
	value: float
	timestamp_utc: datetime | None = None
	unit: str | None = None
	operation_id: str | None = None
	properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExceptionTelemetry:
	exception: Exception
	timestamp_utc: datetime | None = None
	operation_id: str | None = None
	handled: bool | None = None
	properties: dict[str, Any] = field(default_factory=dict)
	measurements: dict[str, float] = field(default_factory=dict)


# ---------- Telemetry interface contract ----------
class ITelemetry(ABC):
	"""Library-agnostic telemetry contract for Azure Application Insights targets.

	Concrete implementations may use OpenTelemetry, the Azure Monitor SDK, or any
	other library as long as they can map these operations to Application Insights.
	"""

	@abstractmethod
	def configure(self) -> None:
		"""Initialize the telemetry client/exporter for the current service."""

	@abstractmethod
	def set_common_context(
		self,
		*,
		service_name: str,
		service_version: str | None = None,
		environment: str | None = None,
		cloud_role: str | None = None,
		default_properties: TelemetryProperties | None = None,
	) -> None:
		"""Set shared context that should be attached to all emitted telemetry."""

	@abstractmethod
	def track_request(self, telemetry: RequestTelemetry) -> None:
		"""Record an inbound HTTP or RPC request."""

	@abstractmethod
	def track_dependency(self, telemetry: DependencyTelemetry) -> None:
		"""Record an outbound dependency call such as HTTP, Redis, or Cosmos DB."""

	@abstractmethod
	def track_event(self, telemetry: EventTelemetry) -> None:
		"""Record a custom business or workflow event."""

	@abstractmethod
	def track_metric(self, telemetry: MetricTelemetry) -> None:
		"""Record a numeric metric or measurement."""

	@abstractmethod
	def track_exception(self, telemetry: ExceptionTelemetry) -> None:
		"""Record an exception with optional telemetry context."""

	@abstractmethod
	def start_span(
		self,
		name: str,
		*,
		kind: str = "internal",
		attributes: TelemetryProperties | None = None,
		parent_context: Any | None = None,
	) -> Any:
		"""Start and return a span or operation handle from the underlying library."""

	@abstractmethod
	def end_span(
		self,
		span: Any,
		*,
		success: bool | None = None,
		attributes: TelemetryProperties | None = None,
	) -> None:
		"""Complete a previously started span or operation."""

	@abstractmethod
	def add_span_event(
		self,
		span: Any,
		name: str,
		*,
		attributes: TelemetryProperties | None = None,
	) -> None:
		"""Add an event/annotation to an active span."""

	@abstractmethod
	def set_span_attributes(self, span: Any, attributes: TelemetryProperties) -> None:
		"""Attach attributes or tags to an active span."""

	@abstractmethod
	def flush(self) -> None:
		"""Flush buffered telemetry to the exporter immediately when supported."""

	@abstractmethod
	def shutdown(self) -> None:
		"""Cleanly stop exporters and release telemetry resources."""