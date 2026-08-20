from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from backend.app import post_content_worker
from backend.app.post_content_queue import FAILED, QUEUED, RUNNING


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self, row: dict[str, object] | None = None, *, values: list[object] | None = None):
        self.row = row
        self.values = list(values or [])
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, _query: str, *_args: object):
        return self.row

    async def fetchval(self, query: str, *_args: object):
        if self.values:
            return self.values.pop(0)
        if "status_ordinal" in query:
            return 0
        return False

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"


class _Pool:
    def __init__(self, connection: _Connection):
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _row(status: str, attempt_count: int, *, queued_at: object = "queued-at") -> dict[str, object]:
    return {
        "job_status_code": status,
        "job_attempt_count": attempt_count,
        "job_started_at": None,
        "job_queued_at": queued_at,
        "post_body": "A real post body.",
        "post_title": "A real post title",
    }


def test_claim_rejects_a_stale_duplicate_wakeup_before_retry_delay() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[False])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "digest",
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_claim_allows_a_due_retry_and_increments_attempts() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[True, 0])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "digest",
        )
    )

    assert claimed is not None
    assert any("attempt_count = attempt_count + 1" in query for query, _args in connection.executed)
    assert any(
        len(args) > 1 and args[1] == RUNNING
        for query, args in connection.executed
        if "update post_content_ingestion_job" in query
    )


def test_terminal_failed_job_ignores_every_stale_wakeup() -> None:
    connection = _Connection(_row(FAILED, 3))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "digest",
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_incomplete_provider_output_is_requeued_with_explicit_reason(monkeypatch) -> None:
    connection = _Connection(values=[1, 0])
    pool = _Pool(connection)
    row = _row(RUNNING, 1)

    async def claim(*_args, **_kwargs):
        return row

    async def persist(*_args, **_kwargs):
        return 1

    async def complete(*_args, **_kwargs):
        return False

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(post_content_worker, "_post_content_is_complete", complete)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(embedding_model="embedding-model"),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())

    client = SimpleNamespace(available=True)
    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="digest",
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    status_updates = [
        args for query, args in connection.executed if "update post_content_ingestion_job" in query
    ]
    assert any(args[1] == QUEUED and args[6] == "post_content_ingestion_incomplete" for args in status_updates)


def test_transient_provider_error_is_requeued_before_the_attempt_limit(monkeypatch) -> None:
    connection = _Connection(values=[1, 0])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        raise TimeoutError("provider timeout")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(embedding_model="embedding-model"),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())

    client = SimpleNamespace(available=True)
    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="digest",
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    status_updates = [
        args for query, args in connection.executed if "update post_content_ingestion_job" in query
    ]
    assert any(args[1] == QUEUED and args[6] == "post_content_ingestion_failed" for args in status_updates)


def test_failure_at_attempt_limit_is_terminal_and_visible() -> None:
    connection = _Connection(values=[3, 0])

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="provider outage",
        )
    )

    status_updates = [
        args for query, args in connection.executed if "update post_content_ingestion_job" in query
    ]
    assert any(args[1] == FAILED and args[6] == "post_content_ingestion_attempt_limit" for args in status_updates)
