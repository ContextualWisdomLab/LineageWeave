"""Worker regressions for bounded, evidence-complete post ingestion."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from backend.app import post_content_worker
from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_MAX_ATTEMPTS,
    QUEUED,
    RUNNING,
    SUCCEEDED,
)


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _Connection:
    def __init__(self, row: dict[str, object] | None = None, values: list[object] | None = None):
        self.row = row
        self.values = list(values or [])
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, *_args: object):
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


def _row(status: str, attempt_count: int, *, started_at: object = None) -> dict[str, object]:
    return {
        "job_status_code": status,
        "job_attempt_count": attempt_count,
        "job_started_at": started_at,
        "job_queued_at": "queued-at",
        "post_body": "A synthetic post body with a retrieval unit.",
        "post_title": "Synthetic post title",
    }


def test_worker_starts_after_historical_stream_tail() -> None:
    class Client:
        async def xrevrange(self, key: str, *, count: int):
            assert key == post_content_worker.POST_CONTENT_STREAM_KEY
            assert count == 1
            return [("123-0", {})]

    assert asyncio.run(post_content_worker._stream_tail(Client())) == "123-0"


def test_terminal_failed_job_ignores_a_stale_duplicate_wakeup() -> None:
    connection = _Connection(_row(FAILED, POST_CONTENT_MAX_ATTEMPTS))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_duplicate_wakeup_before_retry_delay_is_not_claimable() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[False])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_due_retry_is_claimed_and_attempt_is_incremented() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[True])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is not None
    assert any("attempt_count = attempt_count + 1" in query for query, _args in connection.executed)
    assert any(args[1] == RUNNING for query, args in connection.executed if len(args) > 1 and "set status_code" in query)


def test_successful_job_reclaims_when_configured_evidence_is_incomplete(monkeypatch) -> None:
    connection = _Connection(_row(SUCCEEDED, 0), values=[False])
    calls: list[str] = []

    async def incomplete(*_args, **_kwargs) -> bool:
        calls.append("checked")
        return False

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", incomplete)
    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=True,
            require_structure=True,
        )
    )

    assert claimed is not None
    assert calls == ["checked"]


def test_incomplete_provider_output_is_requeued_with_a_failure_code(monkeypatch) -> None:
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        return 1

    async def incomplete(*_args, **_kwargs):
        return False

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(post_content_worker, "post_content_is_complete", incomplete)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="gateway",
            orchestrator_api_key="key",
        ),
    )
    monkeypatch.setattr(
        post_content_worker,
        "normalize_post_body",
        lambda *_args: SimpleNamespace(text="synthetic source body"),
    )
    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorOperationsCaseAnalysisClient",
        lambda *_args: SimpleNamespace(analyze=lambda *_values: ()),
    )
    monkeypatch.setattr(post_content_worker, "persist_operations_cases", persist)
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == QUEUED and args[6] == "post_content_ingestion_incomplete" for args in updates)


def test_missing_source_body_is_not_reported_as_a_provider_failure(monkeypatch, caplog) -> None:
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1) | {"post_body": "   "}

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="embedding-model",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    client = SimpleNamespace(available=True)

    with caplog.at_level("WARNING", logger=post_content_worker._logger.name):
        asyncio.run(
            post_content_worker.process_post_content_job(
                pool,
                post_id="00000000-0000-0000-0000-000000000001",
                source_body_digest="a" * 64,
                vision_factory=lambda: client,
                embedding_factory=lambda: client,
                structure_factory=lambda: client,
            )
        )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(
        args[1] == FAILED
        and args[6] == "post_content_source_body_missing"
        and args[7] == "source post has no body"
        for args in updates
    )
    assert any(
        "source post has no body" in record.message for record in caplog.records
    ), "empty-body skip must still emit a diagnostic log line"


def test_transient_provider_error_is_requeued_before_attempt_limit(monkeypatch, caplog) -> None:
    caplog.set_level("WARNING", logger="lineageweave.observability")
    connection = _Connection(values=[2])
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
        lambda: SimpleNamespace(
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(
        args[1] == QUEUED
        and args[6] == "post_content_ingestion_failed"
        and args[7] == post_content_worker._UNEXPECTED_FAILURE_DETAIL
        for args in updates
    )
    assert all("provider timeout" not in str(args) for args in updates)
    assert "provider timeout" not in caplog.text
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "provider_unavailable"


def test_unexpected_worker_error_is_classified_as_internal(monkeypatch, caplog) -> None:
    """Unexpected worker defects stay internal while their value remains private."""
    caplog.set_level("ERROR", logger="lineageweave.observability")
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        raise TypeError("internal worker detail")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="embedding-model",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "internal_error"
    assert "internal worker detail" not in caplog.text


def test_failure_at_attempt_limit_is_terminal_and_visible() -> None:
    connection = _Connection(values=[POST_CONTENT_MAX_ATTEMPTS])

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="provider outage",
            expected_attempt_count=POST_CONTENT_MAX_ATTEMPTS,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == FAILED and args[6] == "post_content_ingestion_attempt_limit" for args in updates)


def test_stale_worker_cannot_retry_after_lease_recovery() -> None:
    connection = _Connection(values=[2])

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="late provider failure",
            expected_attempt_count=1,
        )
    )

    assert not any("set status_code" in query for query, _args in connection.executed)


def test_stale_worker_cannot_mark_recovered_attempt_succeeded() -> None:
    class StaleConnection(_Connection):
        async def execute(self, query: str, *args: object) -> str:
            self.executed.append((query, args))
            return "UPDATE 0" if "update post_content_ingestion_job" in query else "OK"

    connection = StaleConnection()

    asyncio.run(
        post_content_worker._finish_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            SUCCEEDED,
            expected_attempt_count=1,
        )
    )

    assert not any("insert into post_content_ingestion_job_status_event" in query for query, _args in connection.executed)
