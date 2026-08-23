"""Reader-safe API failures and bounded OpenTelemetry diagnostics."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Self

import pytest

from backend.app import main
from lineageweave import observability
from tests.test_observability import attach_inmemory_tracer


class _Pool:
    """Minimal async pool boundary for the endpoint unit tests."""

    def acquire(self) -> Self:
        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class _FailingClient:
    """Orchestrator-shaped client that raises one controlled exception."""

    available = True

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def answer(self, question: str, sources: object) -> object:
        raise self._exc


def _call_ask(monkeypatch: pytest.MonkeyPatch, exc: BaseException) -> None:
    async def _sources(*args: object, **kwargs: object) -> list[object]:
        return [SimpleNamespace(post_id="synthetic-post-1")]

    account = SimpleNamespace(
        corporate_entity_ids=(),
        has_permission=lambda permission: permission == "post_read",
    )
    monkeypatch.setattr(main, "gather_global_chat_sources", _sources)
    monkeypatch.setattr(main, "_post_chat_client", lambda: _FailingClient(exc))
    with pytest.raises(main.HTTPException) as raised:
        asyncio.run(
            main.ask_agent(
                main.GlobalAskRequest(question="synthetic question"),
                account=account,
                pool=_Pool(),
            )
        )
    assert raised.value.status_code == 503
    assert raised.value.detail == (
        "Ask Agent is temporarily unavailable. Saved evidence is still available."
    )


def test_global_ask_provider_failure_is_reader_safe_and_classified(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Known provider/schema errors produce a provider-unavailable signal."""
    counter_calls: list[tuple[int, dict[str, str]]] = []

    class _Counter:
        def add(self, value: int, attributes: dict[str, str]) -> None:
            counter_calls.append((value, attributes))

    exporter = attach_inmemory_tracer(monkeypatch)
    monkeypatch.setattr(observability, "_FAILURE_COUNTER", _Counter())
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "provider response body must not escape"
    _call_ask(monkeypatch, ValueError(sensitive))

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.operation_code == "global_ask"
    assert record.failure_outcome == "provider_unavailable"
    assert record.error_type == "ValueError"
    assert record.stack_trace == ""
    assert record.trace_id
    assert record.span_id
    assert sensitive not in caplog.text
    assert counter_calls == [
        (
            1,
            {
                "lineageweave.operation_code": "global_ask",
                "lineageweave.failure_outcome": "provider_unavailable",
            },
        )
    ]
    api_span = next(
        span
        for span in exporter.get_finished_spans()
        if span.name == "lineageweave.api.global_ask"
    )
    assert record.trace_id == format(api_span.get_span_context().trace_id, "032x")
    assert record.span_id == format(api_span.get_span_context().span_id, "016x")
    assert api_span.attributes["lineageweave.failure_outcome"] == "provider_unavailable"
    assert not any(
        span.name == "lineageweave.server.failure"
        for span in exporter.get_finished_spans()
    )


def test_global_ask_internal_failure_is_reader_safe_and_keeps_stack_without_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unexpected defects are traceable without exposing their exception value."""
    exporter = attach_inmemory_tracer(monkeypatch)
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "internal prompt-like value must not escape"
    try:
        raise AttributeError(sensitive)
    except AttributeError as exc:
        _call_ask(monkeypatch, exc)

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    api_span = next(
        span
        for span in exporter.get_finished_spans()
        if span.name == "lineageweave.api.global_ask"
    )
    assert record.operation_code == "global_ask"
    assert record.failure_outcome == "internal_error"
    assert record.error_type == "AttributeError"
    assert record.stack_trace
    assert record.trace_id == format(api_span.get_span_context().trace_id, "032x")
    assert record.span_id == format(api_span.get_span_context().span_id, "016x")
    assert api_span.attributes["lineageweave.failure_outcome"] == "internal_error"
    assert sensitive not in record.stack_trace
    assert sensitive not in caplog.text


def test_global_ask_source_gather_failure_is_classified(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Source assembly failures share the Ask span instead of escaping as 500."""
    exporter = attach_inmemory_tracer(monkeypatch)
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "source body must not escape"

    async def _sources(*args: object, **kwargs: object) -> list[object]:
        raise ValueError(sensitive)

    account = SimpleNamespace(
        corporate_entity_ids=(),
        has_permission=lambda permission: permission == "post_read",
    )
    monkeypatch.setattr(main, "gather_global_chat_sources", _sources)
    monkeypatch.setattr(
        main, "_post_chat_client", lambda: _FailingClient(RuntimeError("unused"))
    )
    with pytest.raises(main.HTTPException) as raised:
        asyncio.run(
            main.ask_agent(
                main.GlobalAskRequest(question="synthetic question"),
                account=account,
                pool=_Pool(),
            )
        )
    assert raised.value.status_code == 503
    assert raised.value.detail == (
        "Ask Agent is temporarily unavailable. Saved evidence is still available."
    )
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    api_span = next(
        span
        for span in exporter.get_finished_spans()
        if span.name == "lineageweave.api.global_ask"
    )
    assert record.failure_outcome == "provider_unavailable"
    assert record.trace_id == format(api_span.get_span_context().trace_id, "032x")
    assert record.span_id == format(api_span.get_span_context().span_id, "016x")
    assert sensitive not in caplog.text
    assert sensitive not in raised.value.detail


def test_global_ask_timeout_is_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Timeouts are classified as provider unavailability, not internal defects."""
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    _call_ask(monkeypatch, TimeoutError("synthetic orchestrator timeout"))
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "provider_unavailable"
    assert record.error_type == "TimeoutError"


def test_telemetry_without_endpoint_does_not_latch_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disabled first call still permits a later operator configuration."""
    monkeypatch.setattr(observability, "_CONFIGURED", False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    observability.configure_telemetry()
    assert observability._CONFIGURED is False
