"""Bounded OpenTelemetry spans for product and infrastructure operations.

The application emits useful correlation without placing post bodies, provider
credentials, actor identifiers, or arbitrary request paths in telemetry.
Export is opt-in through the standard OTLP environment variables.
"""

from __future__ import annotations

import logging
import os
import traceback
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext
from typing import Any

try:
    from opentelemetry import metrics, trace
    from opentelemetry.propagate import inject as _otel_inject
    from opentelemetry.trace import Status, StatusCode
except ImportError:  # pragma: no cover - dependency is declared by the project
    metrics = None  # type: ignore[assignment]
    trace = None  # type: ignore[assignment]
    _otel_inject = None
    Status = None  # type: ignore[assignment,misc]
    StatusCode = None  # type: ignore[assignment,misc]

_LOGGER = logging.getLogger(__name__)
_CONFIGURED = False
_TRACER_NAME = "lineageweave"
_FAILURE_COUNTER: Any = None
_TRACE_PROVIDER: Any = None
_METER_PROVIDER: Any = None
_LOG_PROVIDER: Any = None
_LOG_HANDLER: Any = None
_SERVER_FAILURE_OUTCOMES = {"provider_unavailable", "internal_error"}
_ALLOWED_ATTRIBUTE_KEYS = frozenset(
    {
        "db.operation.name",
        "db.system",
        "http.request.method",
        "http.response.status_code",
        "lineageweave.error_type",
        "lineageweave.failure_outcome",
        "lineageweave.operation_code",
        "lineageweave.session_id",
        "lineageweave.stream.kind",
        "service.peer.name",
    }
)
_ALLOWED_OPERATION_CODES = frozenset(
    {
        "global_ask",
        "http_get_json",
        "http_post_json",
        "post_chat",
        "post_content_ingestion",
        "unknown",
    }
)


def _bounded_session_id(value: object) -> str | None:
    """Return a short, printable session correlation value or ``None``."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or not value.isprintable():
        return None
    return value[:128]


def _otlp_trace_endpoint(endpoint: str) -> str:
    """Turn an OTLP base endpoint into the explicit HTTP traces endpoint."""
    return _otlp_signal_endpoint(endpoint, "traces")


def _otlp_signal_endpoint(endpoint: str, signal: str) -> str:
    """Turn an OTLP base endpoint into one explicit HTTP signal endpoint."""
    normalized = endpoint.rstrip("/")
    suffix = f"/v1/{signal}"
    if normalized.casefold().endswith(suffix):
        return normalized
    return f"{normalized}{suffix}"


def _otlp_metric_endpoint(endpoint: str) -> str:
    """Turn an OTLP base endpoint into the explicit HTTP metrics endpoint."""
    return _otlp_signal_endpoint(endpoint, "metrics")


def _otlp_log_endpoint(endpoint: str) -> str:
    """Turn an OTLP base endpoint into the explicit HTTP logs endpoint."""
    return _otlp_signal_endpoint(endpoint, "logs")


def _current_trace_ids() -> tuple[str, str]:
    """Return the active span's TraceId and SpanId as lowercase hex, or blanks."""
    getter = getattr(trace, "get_current_span", None) if trace is not None else None
    if getter is None:
        return "", ""
    span = getter()
    context_getter = getattr(span, "get_span_context", None)
    if span is None or context_getter is None:
        return "", ""
    context = context_getter()
    if context is None or not getattr(context, "is_valid", False):
        return "", ""
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


def current_session_id() -> str | None:
    """Return the current post-scoped session without exposing other metadata."""
    from .llm_context import current_llm_metadata

    metadata = current_llm_metadata() or {}
    value = metadata.get("lineageweave_post_session_id") or metadata.get("session_id")
    return _bounded_session_id(value)


def inject_trace_context(carrier: dict[str, str]) -> None:
    """Inject the active W3C trace context without adding request content."""
    if _otel_inject is not None:
        _otel_inject(carrier)


def _safe_attributes(
    attributes: Mapping[str, Any] | None,
) -> dict[str, str | int | float | bool]:
    """Keep telemetry attributes scalar, bounded, and explicitly non-content."""
    result: dict[str, str | int | float | bool] = {}
    for key, value in (attributes or {}).items():
        if not isinstance(key, str) or key not in _ALLOWED_ATTRIBUTE_KEYS:
            continue
        if key == "lineageweave.session_id":
            value = _bounded_session_id(value)
            if value is None:
                continue
        if isinstance(value, (dict, list, tuple, set)):
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
    """Configure OTLP traces, metrics, and correlated logs when enabled."""
    global _CONFIGURED, _TRACE_PROVIDER, _METER_PROVIDER, _LOG_PROVIDER, _LOG_HANDLER
    if _CONFIGURED or os.getenv("OTEL_SDK_DISABLED", "").lower() == "true":
        return
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
        _LOGGER.warning("OpenTelemetry trace SDK/exporter is unavailable")
        return

    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
        "service.namespace": "contextualwisdomlab",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=_otlp_trace_endpoint(endpoint))
        )
    )
    trace.set_tracer_provider(provider)
    _TRACE_PROVIDER = provider
    _CONFIGURED = True
    if metrics is not None:
        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        except ImportError:  # pragma: no cover - guarded by the runtime extra
            _LOGGER.warning("OpenTelemetry metric SDK/exporter is unavailable")
        else:
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[
                    PeriodicExportingMetricReader(
                        OTLPMetricExporter(endpoint=_otlp_metric_endpoint(endpoint))
                    )
                ],
            )
            metrics.set_meter_provider(meter_provider)
            _METER_PROVIDER = meter_provider
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.instrumentation.logging.handler import LoggingHandler
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    except ImportError:  # pragma: no cover - guarded by the runtime extra
        _LOGGER.warning("OpenTelemetry log SDK/exporter is unavailable")
        return
    try:
        log_provider = LoggerProvider(resource=resource)
        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=_otlp_log_endpoint(endpoint))
            )
        )
        set_logger_provider(log_provider)
        handler = LoggingHandler(level=logging.WARNING, logger_provider=log_provider)
        _LOGGER.addHandler(handler)
        _LOG_PROVIDER = log_provider
        _LOG_HANDLER = handler
    except Exception:  # noqa: BLE001 - export must stay fail-open
        _LOGGER.warning("OpenTelemetry log exporter is unavailable")


def shutdown_telemetry() -> None:
    """Flush configured OTLP providers without masking application shutdown."""
    global _CONFIGURED, _TRACE_PROVIDER, _METER_PROVIDER, _LOG_PROVIDER
    global _LOG_HANDLER, _FAILURE_COUNTER
    if _LOG_HANDLER is not None:
        _LOGGER.removeHandler(_LOG_HANDLER)
        _LOG_HANDLER = None
    for provider_name, provider in (
        ("trace", _TRACE_PROVIDER),
        ("metric", _METER_PROVIDER),
        ("log", _LOG_PROVIDER),
    ):
        if provider is None:
            continue
        try:
            provider.shutdown()
        except Exception:  # noqa: BLE001 - telemetry must not mask shutdown
            _LOGGER.warning(
                "telemetry.provider_shutdown_failed provider=%s",
                provider_name,
            )
    _TRACE_PROVIDER = None
    _METER_PROVIDER = None
    _LOG_PROVIDER = None
    _FAILURE_COUNTER = None
    _CONFIGURED = False


def _failure_counter() -> Any:
    """Return the OTel counter without making telemetry a request dependency."""
    global _FAILURE_COUNTER
    if _FAILURE_COUNTER is None and metrics is not None:
        _FAILURE_COUNTER = metrics.get_meter(_TRACER_NAME).create_counter(
            "lineageweave.server.failures",
            description="Server failures classified by operation and outcome",
        )
    return _FAILURE_COUNTER


def _stack_trace_without_exception(exc: BaseException) -> str:
    """Bound a stack trace while excluding the exception value/message."""
    if exc.__traceback__ is None:
        return ""
    return "".join(traceback.format_tb(exc.__traceback__))[:4096]


def _annotate_failure_span(
    span: Any,
    operation_code: str,
    outcome: str,
    error_type: str,
    stack_trace: str,
) -> None:
    """Attach only bounded classification data to an active span."""
    safe = _safe_attributes(
        {
            "lineageweave.operation_code": operation_code,
            "lineageweave.failure_outcome": outcome,
            "lineageweave.error_type": error_type,
        }
    )
    for key, value in safe.items():
        span.set_attribute(key, value)
    event_attributes: dict[str, str] = {"exception.type": error_type}
    if stack_trace:
        event_attributes["exception.stacktrace"] = stack_trace
    span.add_event("exception", event_attributes)
    if Status is not None and StatusCode is not None:
        span.set_status(Status(StatusCode.ERROR))


def record_server_failure(
    operation_code: str,
    exc: BaseException,
    *,
    outcome: str,
) -> None:
    """Record a classified server failure without storing exception content.

    ``provider_unavailable`` and ``internal_error`` are the only metric
    outcomes. The error class is retained in logs and spans, while the
    exception value is intentionally never serialized.
    """
    if outcome not in _SERVER_FAILURE_OUTCOMES:
        raise ValueError(f"unsupported server failure outcome: {outcome}")
    bounded_operation = operation_code.strip() if isinstance(operation_code, str) else "unknown"
    if bounded_operation not in _ALLOWED_OPERATION_CODES:
        bounded_operation = "unknown"
    error_type = type(exc).__name__[:128]
    session_id = current_session_id() or ""
    counter = _failure_counter()
    if counter is not None:
        try:
            counter.add(
                1,
                {
                    "lineageweave.operation_code": bounded_operation,
                    "lineageweave.failure_outcome": outcome,
                },
            )
        except Exception:  # noqa: BLE001  # telemetry failure must not mask API failure
            _LOGGER.warning("telemetry.metric_recording_failed")

    stack_trace = (
        _stack_trace_without_exception(exc) if outcome == "internal_error" else ""
    )
    current = trace.get_current_span() if trace is not None else None
    span_context: Any = nullcontext()
    if current is not None and current.is_recording():
        _annotate_failure_span(
            current, bounded_operation, outcome, error_type, stack_trace
        )
    elif trace is not None:
        span_context = trace.get_tracer(_TRACER_NAME).start_as_current_span(
            "lineageweave.server.failure",
            record_exception=False,
            set_status_on_exception=False,
        )

    with span_context as span:
        if span is not None:
            _annotate_failure_span(
                span, bounded_operation, outcome, error_type, stack_trace
            )
        trace_id, span_id = _current_trace_ids()
        _LOGGER.log(
            logging.ERROR if outcome == "internal_error" else logging.WARNING,
            "lineageweave.server_failure",
            extra={
                "operation_code": bounded_operation,
                "failure_outcome": outcome,
                "error_type": error_type,
                "session_id": session_id,
                "stack_trace": stack_trace,
                "trace_id": trace_id,
                "span_id": span_id,
            },
        )


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
    with tracer.start_as_current_span(
        name, record_exception=False, set_status_on_exception=False
    ) as span:
        safe = _safe_attributes(attributes)
        for key, value in safe.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            if Status is not None and StatusCode is not None:
                span.add_event(
                    "exception",
                    {"exception.type": type(exc).__name__[:128]},
                )
                span.set_status(Status(StatusCode.ERROR))
            trace_id, span_id = _current_trace_ids()
            _LOGGER.warning(
                "telemetry.operation_failed operation=%s error_type=%s "
                "session_id=%s trace_id=%s span_id=%s",
                name,
                type(exc).__name__,
                safe.get("lineageweave.session_id", ""),
                trace_id,
                span_id,
            )
            raise
