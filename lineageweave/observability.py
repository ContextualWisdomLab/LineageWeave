"""Bounded OpenTelemetry spans for product and infrastructure operations.

The application emits useful correlation without placing post bodies, provider
credentials, actor identifiers, or arbitrary request paths in telemetry.
Export is opt-in through the standard OTLP environment variables.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
except ImportError:  # pragma: no cover - dependency is declared by the project
    trace = None  # type: ignore[assignment]
    Status = None  # type: ignore[assignment,misc]
    StatusCode = None  # type: ignore[assignment,misc]

_LOGGER = logging.getLogger(__name__)
_CONFIGURED = False
_TRACER_NAME = "lineageweave"


def current_session_id() -> str | None:
    """Return the current post-scoped session without exposing other metadata."""
    from .llm_context import current_llm_metadata

    metadata = current_llm_metadata() or {}
    value = metadata.get("lineageweave_post_session_id") or metadata.get("session_id")
    return value if isinstance(value, str) and value else None


def _safe_attributes(
    attributes: Mapping[str, Any] | None,
) -> dict[str, str | int | float | bool]:
    """Keep telemetry attributes scalar, bounded, and explicitly non-content."""
    result: dict[str, str | int | float | bool] = {}
    for key, value in (attributes or {}).items():
        if (
            not isinstance(key, str)
            or not key
            or isinstance(value, (dict, list, tuple, set))
        ):
            continue
        if isinstance(value, str):
            result[key] = value[:256]
        elif isinstance(value, (bool, int, float)):
            result[key] = value
    session_id = current_session_id()
    if session_id:
        result.setdefault("lineageweave.session_id", session_id)
    return result


def configure_telemetry(service_name: str = "lineageweave") -> None:
    """Configure one OTLP trace provider when an operator supplied an endpoint."""
    global _CONFIGURED
    if _CONFIGURED or os.getenv("OTEL_SDK_DISABLED", "").lower() == "true":
        return
    _CONFIGURED = True
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if trace is None or not endpoint:
        return
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - guarded by the runtime extra
        _LOGGER.warning("OpenTelemetry SDK/exporter is unavailable")
        return

    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
        "service.namespace": "contextualwisdomlab",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)


@contextmanager
def traced(
    name: str,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Any]:
    """Create a span and a prompt-safe log event for one bounded operation."""
    if trace is None:  # pragma: no cover - dependency is declared by the project
        yield None
        return
    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name) as span:
        safe = _safe_attributes(attributes)
        for key, value in safe.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            if Status is not None and StatusCode is not None:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
            _LOGGER.warning(
                "telemetry.operation_failed operation=%s error_type=%s session_id=%s",
                name,
                type(exc).__name__,
                safe.get("lineageweave.session_id", ""),
            )
            raise
