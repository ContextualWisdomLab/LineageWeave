"""Regression for Global Ask liveness versus elapsed-time cancellation."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from backend.app import global_ask_queue


_CLAIMED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


class _AvailableClient:
    available = True


class _Connection:
    def __init__(self) -> None:
        self.generation = _CLAIMED_AT
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *_args: object):
        if "job_status_code = $3" in query:
            return {
                "requesting_account_id": "00000000-0000-0000-0000-000000000001",
                "question_text": "Continue the live Ask operation",
                "verify_external_requested": False,
                "knowledge_cutoff": None,
                "updated_at": self.generation,
            }
        if "returning updated_at" in query:
            self.generation += timedelta(milliseconds=5)
            return {"updated_at": self.generation}
        raise AssertionError(query)

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "UPDATE 1"


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def test_live_heartbeat_operation_is_not_cancelled_by_elapsed_time(monkeypatch) -> None:
    """A renewing owner remains live until completion, cancellation, or claim loss."""
    connection = _Connection()
    pool = _Pool(connection)

    async def _load_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _long_but_live_answer(*_args, **_kwargs):
        await asyncio.sleep(0.03)
        return {"answer_text": "completed by live owner"}

    monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 0.005)
    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _load_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _long_but_live_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-live",
            chat_factory=_AvailableClient,
        )
    )

    settle_query, settle_args = connection.executed[-1]
    assert "answer_payload" in settle_query
    assert "failure_detail" not in settle_query
    assert settle_args[3:] == (global_ask_queue.RUNNING, connection.generation)
