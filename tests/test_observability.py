"""Tests for prompt-safe session propagation and tracing boundaries."""

from __future__ import annotations

import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from lineageweave import http_client, observability
from lineageweave.llm_context import use_llm_metadata
from lineageweave.observability import (
    _bounded_session_id,
    _otlp_log_endpoint,
    _otlp_trace_endpoint,
    _safe_attributes,
    current_session_id,
    record_server_failure,
    shutdown_telemetry,
    traced,
)


def attach_inmemory_tracer(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Drive the shipped tracer through a real in-memory SDK exporter."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(observability.trace, "get_tracer", provider.get_tracer)
    return exporter


def test_post_json_sends_post_session_header(monkeypatch):
    """One post session reaches the orchestrator as a transport header."""
    captured = {}

    def fake_request(method, url, *, body, headers, timeout, response_control_headers):
        captured.update(method=method, headers=headers)
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", fake_request)
    attach_inmemory_tracer(monkeypatch)
    with use_llm_metadata({"lineageweave_post_session_id": "post-session-1"}):
        http_client.post_json(
            "https://orchestrator.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert captured["method"] == "POST"
    assert captured["headers"]["x-lineageweave-session-id"] == "post-session-1"
    assert captured["headers"]["traceparent"].startswith("00-")
    _version, trace_id, span_id, _flags = captured["headers"]["traceparent"].split("-")
    assert len(trace_id) == 32
    assert len(span_id) == 16
    assert trace_id != "0" * 32


def test_post_json_marks_http_and_decode_failures_inside_the_span(monkeypatch):
    """HTTP and invalid-body failures end the active client span as errors."""
    for status, raw, error_type in (
        (503, b"{}", "503"),
        (200, b"not-json", "HttpClientError"),
    ):
        captured = {"attributes": {}}

        class _Span:
            def set_attribute(self, key, value):
                captured["attributes"][key] = value

        class _SpanContext:
            def __enter__(self):
                return _Span()

            def __exit__(self, exception_type, *_args):
                captured["exception_type"] = exception_type
                return False

        monkeypatch.setattr(http_client, "traced", lambda *_args, **_kwargs: _SpanContext())
        monkeypatch.setattr(
            http_client,
            "_request",
            lambda *_args, **_kwargs: (status, raw),
        )

        try:
            http_client.post_json(
                "https://orchestrator.example/v1/chat/completions",
                {},
                headers={},
                timeout=1,
            )
        except http_client.HttpClientError:
            pass
        else:  # pragma: no cover
            raise AssertionError("invalid provider responses must fail closed")

        assert captured["exception_type"] is http_client.HttpClientError
        assert captured["attributes"]["error.type"] == error_type


def test_current_session_id_reads_existing_context():
    """Telemetry reuses the existing normalized LLM context, not a new store."""
    with use_llm_metadata({"lineageweave_post_session_id": "post-session-2"}):
        assert current_session_id() == "post-session-2"


def test_session_correlation_is_printable_and_bounded():
    """Session correlation rejects controls and caps values before export."""
    assert _bounded_session_id("  session-3  ") == "session-3"
    assert _bounded_session_id("session\n3") is None
    assert _bounded_session_id("session\x7f3") is None
    assert _bounded_session_id("x" * 129) == "x" * 128
    assert _bounded_session_id(3) is None


def test_safe_attributes_drops_unknown_keys_and_invalid_session_values():
    """Telemetry keeps only the allowlisted scalar boundary attributes."""
    assert _safe_attributes(
        {
            "request.path": "/private/synthetic",
            "lineageweave.session_id": "bad\nvalue",
            "service.peer.name": "tepp",
            "http.response.status_code": 503,
        }
    ) == {
        "service.peer.name": "tepp",
        "http.response.status_code": 503,
    }


def test_traced_rethrows_provider_errors():
    """Observability never converts a failed provider operation into success."""
    try:
        with traced("lineageweave.test.failure"):
            raise RuntimeError("provider failure")
    except RuntimeError as exc:
        assert str(exc) == "provider failure"
    else:  # pragma: no cover
        raise AssertionError("traced must preserve operation failures")


def test_traced_disables_automatic_exception_recording(monkeypatch):
    """OTel must not serialize an exception value or implicit stack trace."""
    captured = {}

    class _Span:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def set_attribute(self, _key, _value):
            pass

        def add_event(self, name, attributes):
            captured["event"] = (name, attributes)

        def set_status(self, _status):
            pass

    class _Tracer:
        def start_as_current_span(self, name, **kwargs):
            captured["span"] = (name, kwargs)
            return _Span()

    class _Trace:
        def get_tracer(self, _name):
            return _Tracer()

    monkeypatch.setattr(observability, "trace", _Trace())
    try:
        with observability.traced("lineageweave.test.sensitive"):
            raise RuntimeError("secret provider response")
    except RuntimeError:
        pass

    assert captured["span"] == (
        "lineageweave.test.sensitive",
        {"record_exception": False, "set_status_on_exception": False},
    )
    assert captured["event"][1] == {"exception.type": "RuntimeError"}


def test_safe_attributes_keeps_allowlisted_operation_code():
    """Endpoint spans retain the bounded operation dimension."""
    assert _safe_attributes(
        {"lineageweave.operation_code": "post_chat"}
    ) == {"lineageweave.operation_code": "post_chat"}


def test_otlp_base_endpoint_gets_trace_signal_path():
    """A configured collector base URL receives the HTTP traces signal path."""
    assert _otlp_trace_endpoint("http://collector:4318") == "http://collector:4318/v1/traces"
    assert _otlp_trace_endpoint("http://collector:4318/v1/traces/") == "http://collector:4318/v1/traces"


def test_otlp_base_endpoint_gets_log_signal_path():
    """A configured collector base URL receives the HTTP logs signal path."""
    assert _otlp_log_endpoint("http://collector:4318") == "http://collector:4318/v1/logs"
    assert _otlp_log_endpoint("http://collector:4318/v1/logs") == "http://collector:4318/v1/logs"


def test_shutdown_telemetry_flushes_configured_providers(monkeypatch):
    """Application shutdown flushes traces, metrics, and logs without a raw error."""
    calls = []

    class _Provider:
        def __init__(self, name):
            self.name = name

        def shutdown(self):
            calls.append(self.name)

    class _Handler:
        pass

    monkeypatch.setattr(observability, "_TRACE_PROVIDER", _Provider("trace"))
    monkeypatch.setattr(observability, "_METER_PROVIDER", _Provider("metric"))
    monkeypatch.setattr(observability, "_LOG_PROVIDER", _Provider("log"))
    monkeypatch.setattr(observability, "_LOG_HANDLER", _Handler())
    monkeypatch.setattr(observability, "_FAILURE_COUNTER", object())
    monkeypatch.setattr(observability, "_CONFIGURED", True)

    shutdown_telemetry()

    assert calls == ["trace", "metric", "log"]
    assert observability._TRACE_PROVIDER is None
    assert observability._METER_PROVIDER is None
    assert observability._LOG_PROVIDER is None
    assert observability._LOG_HANDLER is None
    assert observability._FAILURE_COUNTER is None
    assert observability._CONFIGURED is False


def test_record_server_failure_shares_trace_ids_with_active_span(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Classified failures annotate the API span and log the same TraceId/SpanId."""
    exporter = attach_inmemory_tracer(monkeypatch)
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "secret prompt and source body must not escape"

    try:
        with traced(
            "lineageweave.api.global_ask",
            {"lineageweave.operation_code": "global_ask"},
        ):
            try:
                raise ValueError(sensitive)
            except ValueError as exc:
                record_server_failure("global_ask", exc, outcome="provider_unavailable")
                raise
    except ValueError:
        pass

    spans = exporter.get_finished_spans()
    api_span = next(
        span for span in spans if span.name == "lineageweave.api.global_ask"
    )
    assert api_span.status.status_code == StatusCode.ERROR
    assert api_span.attributes["lineageweave.operation_code"] == "global_ask"
    assert api_span.attributes["lineageweave.failure_outcome"] == "provider_unavailable"
    assert api_span.attributes["lineageweave.error_type"] == "ValueError"
    assert not any(span.name == "lineageweave.server.failure" for span in spans)

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    expected_trace = format(api_span.get_span_context().trace_id, "032x")
    expected_span = format(api_span.get_span_context().span_id, "016x")
    assert record.trace_id == expected_trace
    assert record.span_id == expected_span
    assert record.operation_code == "global_ask"
    assert record.failure_outcome == "provider_unavailable"
    assert sensitive not in caplog.text
    assert sensitive not in str(api_span.attributes)
    for event in api_span.events:
        assert sensitive not in str(event.attributes)


def test_record_server_failure_distinguishes_internal_error_outcome(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unexpected faults keep a stack without serializing the exception value."""
    exporter = attach_inmemory_tracer(monkeypatch)
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "internal prompt-like value must not escape"

    try:
        with traced(
            "lineageweave.api.post_chat",
            {"lineageweave.operation_code": "post_chat"},
        ):
            try:
                raise AttributeError(sensitive)
            except AttributeError as exc:
                record_server_failure("post_chat", exc, outcome="internal_error")
                raise
    except AttributeError:
        pass

    spans = exporter.get_finished_spans()
    api_span = next(span for span in spans if span.name == "lineageweave.api.post_chat")
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "internal_error"
    assert record.stack_trace
    assert record.trace_id == format(api_span.get_span_context().trace_id, "032x")
    assert record.span_id == format(api_span.get_span_context().span_id, "016x")
    assert api_span.attributes["lineageweave.failure_outcome"] == "internal_error"
    assert sensitive not in record.stack_trace
    assert sensitive not in caplog.text


def test_unknown_operation_code_maps_to_fallback(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Caller strings that are not allowlisted become the fixed unknown code."""
    attach_inmemory_tracer(monkeypatch)
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    with traced("lineageweave.test.unknown"):
        record_server_failure(
            "not-an-allowed-code", RuntimeError("x"), outcome="internal_error"
        )
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.operation_code == "unknown"


def test_configure_telemetry_ignores_blank_endpoint(monkeypatch) -> None:
    """Whitespace-only OTLP configuration must not latch a half-configured SDK."""
    monkeypatch.setattr(observability, "_CONFIGURED", False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "   ")
    observability.configure_telemetry()
    assert observability._CONFIGURED is False
    assert observability._TRACE_PROVIDER is None
    assert observability._LOG_PROVIDER is None
