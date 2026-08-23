"""Regression tests for reader-visible stale summary continuity."""

import asyncio

import pytest

from backend.app import main
from backend.app.post_summary_ingestion import fetch_persisted_summary


class _StaleSummaryConnection:
    """Minimal asyncpg-shaped fake containing one previous-contract summary."""

    async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
        return {
            "korean_summary": "Previously persisted evidence.",
            "summary_contract_version": 18,
        }

    async def fetch(self, query: str, post_id: str) -> list[dict[str, object]]:
        return []


def test_stale_summary_is_hidden_by_default() -> None:
    """Current-contract reads must not silently present legacy semantics."""
    result = asyncio.run(fetch_persisted_summary(_StaleSummaryConnection(), "post-id"))
    assert result is None


def test_stale_summary_can_be_returned_with_explicit_status() -> None:
    """The continuity path exposes the old contract so the UI can label it."""
    result = asyncio.run(
        fetch_persisted_summary(_StaleSummaryConnection(), "post-id", allow_stale=True)
    )
    assert result is not None
    assert result["summary_status"] == "stale"
    assert result["summary_contract_version"] == 18
    assert result["korean_summary"] == "Previously persisted evidence."


def test_reader_returns_stale_summary_without_waiting_for_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A popup read must not block on two slow provider calls when evidence exists."""

    class Connection:
        async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
            assert "select post_body" in query
            return {"post_body": "Synthetic release chronology."}

    class Acquire:
        async def __aenter__(self) -> Connection:
            return Connection()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Pool:
        def acquire(self) -> Acquire:
            return Acquire()

    async def load_visible_post(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"post_title": "Synthetic release chronology"}

    async def persisted_summary(
        _conn: object,
        _post_id: str,
        *,
        allow_stale: bool = False,
    ) -> dict[str, object] | None:
        if not allow_stale:
            return None
        return {
            "summary_status": "stale",
            "summary_contract_version": 18,
            "korean_summary": "Previously persisted evidence.",
        }

    monkeypatch.setattr(main, "_load_visible_post", load_visible_post)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "fetch_persisted_summary", persisted_summary)
    monkeypatch.setattr(
        main,
        "_post_summary_client",
        lambda: (_ for _ in ()).throw(AssertionError("orchestrator must not be called")),
    )

    result = asyncio.run(
        main.read_post_summary(
            "00000000-0000-0000-0000-000000000001",
            account=object(),
            pool=Pool(),
            valkey=None,
        )
    )

    assert result["summary_status"] == "stale"
    assert result["summary_contract_version"] == 18
