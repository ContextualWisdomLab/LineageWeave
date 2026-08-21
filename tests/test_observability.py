"""Tests for prompt-safe session propagation and tracing boundaries."""

from lineageweave import http_client, observability
from lineageweave.llm_context import use_llm_metadata
from lineageweave.observability import (
    _bounded_session_id,
    _safe_attributes,
    _otlp_trace_endpoint,
    current_session_id,
    shutdown_telemetry,
    traced,
)


def test_post_json_sends_post_session_header(monkeypatch):
    """One post session reaches the orchestrator as a transport header."""
    captured = {}

    def fake_request(method, url, *, body, headers, timeout):
        captured.update(method=method, headers=headers)
        return 200, b"{}"

    def fake_inject(headers):
        headers["traceparent"] = "00-11111111111111111111111111111111-2222222222222222-01"

    monkeypatch.setattr(http_client, "_request", fake_request)
    monkeypatch.setattr(http_client, "inject_trace_context", fake_inject)
    with use_llm_metadata({"lineageweave_post_session_id": "post-session-1"}):
        http_client.post_json(
            "https://orchestrator.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert captured["method"] == "POST"
    assert captured["headers"]["x-lineageweave-session-id"] == "post-session-1"
    assert captured["headers"]["traceparent"].startswith("00-1111")


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


def test_otlp_base_endpoint_gets_trace_signal_path():
    """A configured collector base URL receives the HTTP traces signal path."""
    assert _otlp_trace_endpoint("http://collector:4318") == "http://collector:4318/v1/traces"
    assert _otlp_trace_endpoint("http://collector:4318/v1/traces/") == "http://collector:4318/v1/traces"


def test_shutdown_telemetry_flushes_configured_providers(monkeypatch):
    """Application shutdown flushes traces and metrics without a raw error."""
    calls = []

    class _Provider:
        def __init__(self, name):
            self.name = name

        def shutdown(self):
            calls.append(self.name)

    monkeypatch.setattr(observability, "_TRACE_PROVIDER", _Provider("trace"))
    monkeypatch.setattr(observability, "_METER_PROVIDER", _Provider("metric"))
    monkeypatch.setattr(observability, "_FAILURE_COUNTER", object())

    shutdown_telemetry()

    assert calls == ["trace", "metric"]
    assert observability._TRACE_PROVIDER is None
    assert observability._METER_PROVIDER is None
    assert observability._FAILURE_COUNTER is None
