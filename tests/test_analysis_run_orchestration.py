"""Fail-closed contextual-orchestrator helper for analysis-run work."""

from __future__ import annotations

import pytest

from lineageweave.analysis_run_orchestration import (
    ContextualOrchestratorAnalysisRunClient,
    NullAnalysisRunOrchestrationClient,
    OrchestratorNotAvailable,
    request_auto_completion,
)
from lineageweave.http_client import HttpClientError


def test_null_client_is_unavailable_and_does_not_invent_a_completion() -> None:
    client = NullAnalysisRunOrchestrationClient()
    assert client.available is False
    with pytest.raises(RuntimeError, match="available"):
        client.complete("summarize this run")


def test_request_auto_completion_fails_closed_without_a_base_url() -> None:
    with pytest.raises(OrchestratorNotAvailable, match="base URL"):
        request_auto_completion(None, "hello")
    with pytest.raises(OrchestratorNotAvailable, match="base URL"):
        request_auto_completion("   ", "hello")
    with pytest.raises(OrchestratorNotAvailable, match="base URL"):
        ContextualOrchestratorAnalysisRunClient(base_url="")


def test_request_auto_completion_uses_mode_auto_and_extracts_content() -> None:
    recorded: dict[str, object] = {}

    def fake_poster(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        recorded["url"] = url
        recorded["payload"] = payload
        recorded["headers"] = headers
        recorded["timeout"] = timeout
        return {"choices": [{"message": {"content": "bounded summary"}}]}

    text = request_auto_completion(
        "https://orchestrator.example.test/",
        "summarize Demo Corp run",
        api_key="demo-key",
        timeout=12.0,
        poster=fake_poster,
    )
    assert text == "bounded summary"
    assert recorded["url"] == "https://orchestrator.example.test/v1/chat/completions"
    assert recorded["payload"]["mode"] == "auto"
    assert recorded["payload"]["mode"] != "verify"
    assert recorded["headers"]["authorization"] == "Bearer demo-key"

    def anonymous_poster(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        recorded["anonymous_headers"] = headers
        return {"choices": [{"message": {"content": "ok"}}]}

    assert (
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=anonymous_poster,
        )
        == "ok"
    )
    assert recorded["anonymous_headers"] == {}


def test_request_auto_completion_fails_closed_on_invalid_mode_and_non_2xx() -> None:
    def invalid_mode_poster(*_args, **_kwargs) -> dict:
        return {"error": "invalid_mode"}

    with pytest.raises(OrchestratorNotAvailable, match="invalid_mode"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=invalid_mode_poster,
        )

    def coded_invalid_mode(*_args, **_kwargs) -> dict:
        return {"code": "invalid_mode"}

    with pytest.raises(OrchestratorNotAvailable, match="invalid_mode"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=coded_invalid_mode,
        )

    def failing_poster(*_args, **_kwargs) -> dict:
        raise HttpClientError("HTTP 503 from orchestrator.example.test")

    with pytest.raises(OrchestratorNotAvailable, match="503"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=failing_poster,
        )

    def empty_poster(*_args, **_kwargs) -> dict:
        return {"choices": []}

    with pytest.raises(OrchestratorNotAvailable, match="content"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=empty_poster,
        )

    def blank_poster(*_args, **_kwargs) -> dict:
        return {"choices": [{"message": {"content": "   "}}]}

    with pytest.raises(OrchestratorNotAvailable, match="content"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=blank_poster,
        )

    def non_string_poster(*_args, **_kwargs) -> dict:
        return {"choices": [{"message": {"content": 12}}]}

    with pytest.raises(OrchestratorNotAvailable, match="content"):
        request_auto_completion(
            "https://orchestrator.example.test",
            "hello",
            poster=non_string_poster,
        )


def test_live_client_complete_uses_injected_auto_transport() -> None:
    def fake_poster(*_args, **_kwargs) -> dict:
        return {"choices": [{"message": {"content": "ok"}}]}

    client = ContextualOrchestratorAnalysisRunClient(
        base_url="https://orchestrator.example.test",
        api_key="demo-key",
        poster=fake_poster,
    )
    assert client.available is True
    assert client.complete("hello") == "ok"
