"""Worker regressions for bounded, evidence-complete post ingestion."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from backend.app import post_content_worker
from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_MAX_ATTEMPTS,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    source_body_sha256,
)

_BODY = "A synthetic post body with a retrieval unit."
_DIGEST = source_body_sha256(_BODY)


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
        self.queries: list[str] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, query: str, *args: object):
        self.queries.append(" ".join(query.split()))
        if "attempt_count = $3" in query and self.row is not None:
            if int(self.row["job_attempt_count"]) != int(args[2]):
                return None
            if str(self.row["job_source_body_sha256"]) != str(args[1]):
                return None
            if str(self.row["job_status_code"]) != str(args[3]):
                return None
        return self.row

    async def fetchval(self, query: str, *_args: object):
        if "returning attempt_count" in query and self.row is not None:
            return int(self.row["job_attempt_count"]) + 1
        if self.values:
            return self.values.pop(0)
        if "status_ordinal" in query:
            return 0
        return False

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        if query.lstrip().startswith("update"):
            return "UPDATE 1"
        if query.lstrip().startswith("insert"):
            return "INSERT 0 1"
        return "OK"


class _Pool:
    def __init__(self, connection: _Connection):
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _row(
    status: str,
    attempt_count: int,
    *,
    cycle_attempt_count: int | None = None,
    started_at: object = None,
) -> dict[str, object]:
    return {
        "job_status_code": status,
        "job_attempt_count": attempt_count,
        "job_cycle_attempt_count": (
            attempt_count if cycle_attempt_count is None else cycle_attempt_count
        ),
        "job_source_body_sha256": _DIGEST,
        "job_started_at": started_at,
        "job_queued_at": "queued-at",
        "source_detail_state_code": "A",
        "post_body": _BODY,
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
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is None
    assert connection.executed == []


@pytest.mark.parametrize("source_detail_state_code", ["W", " w "])
def test_worker_drops_a_writing_post_even_if_a_stale_job_row_leaks_through(
    source_detail_state_code: str,
) -> None:
    connection = _Connection(
        {**_row(QUEUED, 0), "source_detail_state_code": source_detail_state_code}
    )

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
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
            _DIGEST,
            embedding_model_code="",
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
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is not None
    assert claimed["job_attempt_count"] == 2
    assert claimed["job_cycle_attempt_count"] == 2
    assert any(args[1] == RUNNING for query, args in connection.executed if len(args) > 1 and "set status_code" in query)


def test_worker_claim_locks_source_before_job() -> None:
    connection = _Connection(_row(QUEUED, 0))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is not None
    assert "from source_post" in connection.queries[0]
    assert "post_content_ingestion_job" not in connection.queries[0]
    assert "from post_content_ingestion_job" in connection.queries[1]
    assert "source_post" not in connection.queries[1]


def test_fresh_retry_cycle_preserves_a_high_monotonic_claim_identity() -> None:
    connection = _Connection(_row(QUEUED, 41, cycle_attempt_count=0))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is not None
    assert claimed["job_attempt_count"] == 42
    assert claimed["job_cycle_attempt_count"] == 1


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
            _DIGEST,
            embedding_model_code="embedding-model",
            require_structure=True,
        )
    )

    assert claimed is not None
    assert calls == ["checked"]


def test_incomplete_provider_output_is_requeued_with_a_failure_code(monkeypatch) -> None:
    connection = _Connection(_row(RUNNING, 2, cycle_attempt_count=2))
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 2, cycle_attempt_count=2)

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
            embedding_model="embedding-model",
            orchestrator_base_url="gateway",
            orchestrator_api_key="key",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest=_DIGEST,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == QUEUED and args[6] == "post_content_ingestion_incomplete" for args in updates)


def test_transient_provider_error_is_requeued_before_attempt_limit(monkeypatch) -> None:
    connection = _Connection(_row(RUNNING, 2, cycle_attempt_count=2))
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 2, cycle_attempt_count=2)

    async def persist(*_args, **_kwargs):
        raise TimeoutError("provider timeout")

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
            source_body_digest=_DIGEST,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == QUEUED and args[6] == "post_content_ingestion_failed" for args in updates)
    assert all("provider timeout" not in str(args) for args in updates)


def test_failure_at_attempt_limit_is_terminal_and_visible() -> None:
    connection = _Connection(
        _row(RUNNING, 19, cycle_attempt_count=POST_CONTENT_MAX_ATTEMPTS)
    )

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="provider outage",
            expected_source_body_sha256=_DIGEST,
            expected_attempt_count=19,
            cycle_attempt_count=POST_CONTENT_MAX_ATTEMPTS,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == FAILED and args[6] == "post_content_ingestion_attempt_limit" for args in updates)


def test_stale_worker_cannot_retry_after_lease_recovery() -> None:
    connection = _Connection(_row(RUNNING, 2, cycle_attempt_count=2))

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="late provider failure",
            expected_source_body_sha256=_DIGEST,
            expected_attempt_count=1,
            cycle_attempt_count=1,
        )
    )

    assert not any("set status_code" in query for query, _args in connection.executed)


def test_worker_retry_clock_queries_cast_database_timestamps() -> None:
    class RecordingConnection(_Connection):
        def __init__(self, row):
            super().__init__(row)
            self.queries: list[str] = []

        async def fetchval(self, query: str, *_args: object):
            self.queries.append(query)
            return False

    connection = RecordingConnection(_row(QUEUED, 1))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is None
    assert any("$1::timestamptz + $2::interval" in query for query in connection.queries)


def test_duplicate_wakeup_cannot_fail_a_fresh_running_final_attempt() -> None:
    connection = _Connection(
        _row(
            RUNNING,
            POST_CONTENT_MAX_ATTEMPTS,
            cycle_attempt_count=POST_CONTENT_MAX_ATTEMPTS,
            started_at="fresh-start",
        ),
        values=[False],
    )

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is None
    assert not any("set status_code" in query for query, _args in connection.executed)


def test_supervised_worker_restarts_after_unexpected_error(monkeypatch) -> None:
    calls = 0

    async def run_once(*_args, **_kwargs) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient worker failure")
        raise asyncio.CancelledError

    async def no_delay(_seconds: float) -> None:
        return None

    monkeypatch.setattr(post_content_worker, "run_post_content_worker", run_once)
    monkeypatch.setattr(post_content_worker.asyncio, "sleep", no_delay)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            post_content_worker.run_post_content_worker_supervised(
                SimpleNamespace(),
                SimpleNamespace(),
                vision_factory=lambda: SimpleNamespace(),
                embedding_factory=lambda: SimpleNamespace(),
                structure_factory=lambda: SimpleNamespace(),
            )
        )

    assert calls == 2


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
            expected_source_body_sha256=_DIGEST,
            expected_attempt_count=1,
        )
    )

    assert not any("insert into post_content_ingestion_job_status_event" in query for query, _args in connection.executed)


def test_completion_transition_rechecks_running_digest_and_attempt() -> None:
    connection = _Connection(_row(RUNNING, 7, cycle_attempt_count=1))

    asyncio.run(
        post_content_worker._finish_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            SUCCEEDED,
            expected_source_body_sha256=_DIGEST,
            expected_attempt_count=7,
        )
    )

    query, args = next(
        (query, args)
        for query, args in connection.executed
        if "update post_content_ingestion_job" in query
    )
    assert "source_body_sha256 = $10" in query
    assert "status_code = $11" in query
    assert args[8:] == (7, _DIGEST, RUNNING)
    assert "from source_post" in connection.queries[0]
    assert "post_content_ingestion_job" not in connection.queries[0]
    assert "from post_content_ingestion_job" in connection.queries[1]


def test_claim_rejects_a_job_digest_that_no_longer_matches_the_locked_source() -> None:
    connection = _Connection(
        {**_row(QUEUED, 4, cycle_attempt_count=0), "post_body": "A newer source revision."}
    )

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            _DIGEST,
            embedding_model_code="",
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_worker_passes_immutable_claim_fence_to_persistence(monkeypatch) -> None:
    connection = _Connection()
    captured: dict[str, object] = {}

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 11, cycle_attempt_count=1)

    async def stale_persist(*_args, **kwargs):
        captured.update(kwargs)

    async def must_not_check(*_args, **_kwargs):
        raise AssertionError("a rejected persistence claim must stop processing")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", stale_persist)
    monkeypatch.setattr(post_content_worker, "post_content_is_complete", must_not_check)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(connection),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest=_DIGEST,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert captured["expected_source_body_sha256"] == _DIGEST
    assert captured["expected_attempt_count"] == 11
    assert not connection.executed
