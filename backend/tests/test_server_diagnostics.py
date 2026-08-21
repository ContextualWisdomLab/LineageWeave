"""Buyer-safe API failures and bounded OpenTelemetry diagnostics."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Self

import pytest

from backend.app import main
from lineageweave import observability


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


def test_global_ask_provider_failure_is_buyer_safe_and_classified(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Known provider/schema errors produce a provider-unavailable signal."""
    counter_calls: list[tuple[int, dict[str, str]]] = []

    class _Counter:
        def add(self, value: int, attributes: dict[str, str]) -> None:
            counter_calls.append((value, attributes))

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


def test_global_ask_internal_failure_is_buyer_safe_and_keeps_stack_without_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unexpected defects are traceable without exposing their exception value."""
    caplog.set_level(logging.WARNING, logger="lineageweave.observability")
    sensitive = "internal prompt-like value must not escape"
    try:
        raise AttributeError(sensitive)
    except AttributeError as exc:
        _call_ask(monkeypatch, exc)

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.operation_code == "global_ask"
    assert record.failure_outcome == "internal_error"
    assert record.error_type == "AttributeError"
    assert record.stack_trace
    assert sensitive not in record.stack_trace
    assert sensitive not in caplog.text
