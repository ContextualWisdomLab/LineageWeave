"""Tests for prompt-safe session propagation and tracing boundaries."""

from lineageweave import http_client
from lineageweave.llm_context import use_llm_metadata
from lineageweave.observability import (
    _otlp_trace_endpoint,
    current_session_id,
    traced,
)


def test_post_json_sends_post_session_header(monkeypatch):
    """One post session reaches the orchestrator as a transport header."""
    captured = {}

    def fake_request(method, url, *, body, headers, timeout):
        captured.update(method=method, headers=headers)
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", fake_request)
    with use_llm_metadata({"lineageweave_post_session_id": "post-session-1"}):
        http_client.post_json(
            "https://orchestrator.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert captured["method"] == "POST"
    assert captured["headers"]["x-lineageweave-session-id"] == "post-session-1"


def test_current_session_id_reads_existing_context():
    """Telemetry reuses the existing normalized LLM context, not a new store."""
    with use_llm_metadata({"lineageweave_post_session_id": "post-session-2"}):
        assert current_session_id() == "post-session-2"


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
