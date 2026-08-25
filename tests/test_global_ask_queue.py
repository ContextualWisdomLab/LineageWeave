"""Regressions for the Global Ask job queue's failure-settlement path."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from backend.app import global_ask_queue
from backend.app.global_ask_queue import load_job_visibility


class _AvailableClient:
    available = True


class _Connection:
    def __init__(self, row: dict[str, object] | None) -> None:
        self.row = row
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, *_args: object):
        return self.row

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _queued_row() -> dict[str, object]:
    return {
        "requesting_account_id": "00000000-0000-0000-0000-000000000001",
        "question_text": "What happened last week?",
    }


def test_question_embedding_finishes_before_global_ask_acquires_a_pool_slot(
    monkeypatch,
) -> None:
    """Provider latency must not consume the shared database pool."""
    connection = _Connection(None)

    class TrackingPool(_Pool):
        active = 0

        @asynccontextmanager
        async def acquire(self):
            self.active += 1
            try:
                yield self.connection
            finally:
                self.active -= 1

    pool = TrackingPool(connection)

    class EmbeddingClient:
        available = True
        resolved_model = "synthetic-embedding"

        def embed(self, _text: str) -> list[float]:
            assert pool.active == 0
            return [1.0, 0.0]

    async def fake_gather(_conn, *_args, **kwargs):
        assert pool.active == 1
        assert kwargs["question_embedding"] == (
            [1.0, 0.0],
            "synthetic-embedding",
            1.0,
        )
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            embedding_client=EmbeddingClient(),
        )
    )

    assert payload["source_post_ids"] == []
    assert pool.active == 0


def test_unexpected_job_failure_settles_with_a_generic_detail_not_the_raw_exception(
    monkeypatch,
) -> None:
    """Live bug (#361, reintroduced by the Valkey-queue restructuring): a raw
    orchestrator/provider exception once flowed straight into a client-visible
    field. `failure_detail` must never carry `str(exc)` -- only a bounded,
    generic message; the real exception is logged internally instead.
    """
    connection = _Connection(_queued_row())
    pool = _Pool(connection)
    secret_bearing_message = "upstream said: Bearer sk-super-secret-token-abc123 is invalid"

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise ConnectionResetError(secret_bearing_message)

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    settle_query, settle_args = connection.executed[-1]
    assert "failure_detail" in settle_query
    failure_detail = settle_args[-1]
    assert secret_bearing_message not in failure_detail
    assert failure_detail == (
        "Ask Agent is unavailable: contextual-orchestrator returned no complete evidence object"
    )


def test_permission_and_connection_errors_keep_their_pre_authored_safe_message(
    monkeypatch,
) -> None:
    """`PermissionError`/`ConnectionError` are raised locally with a
    pre-authored, safe message (permission state / missing config) -- unlike
    an arbitrary provider exception, `str(exc)` here is never a leak."""
    connection = _Connection(_queued_row())
    pool = _Pool(connection)

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise global_ask_queue._SafeJobError("account lacks the post_read permission")

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    _settle_query, settle_args = connection.executed[-1]
    assert settle_args[-1] == "account lacks the post_read permission"


def test_job_deadline_timeout_settles_with_a_specific_but_still_generic_detail(
    monkeypatch,
) -> None:
    """A bare `asyncio.TimeoutError` (no message) still gets a useful,
    non-empty detail rather than an empty string."""
    connection = _Connection(_queued_row())
    pool = _Pool(connection)

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    _settle_query, settle_args = connection.executed[-1]
    assert settle_args[-1] == f"job exceeded the {global_ask_queue.JOB_DEADLINE_SECONDS}s deadline"


def test_job_visibility_never_expands_past_queued_scope() -> None:
    """The worker uses stored scope rows, not every account affiliation."""

    class FakeConnection:
        async def fetch(self, query: str, *args):
            assert args == ("job-1", "account-1")
            if "corporate_entity_scope" in query:
                return [{"corporate_entity_id": "queued-entity"}]
            if "process_unit_scope" in query:
                return [{"process_unit_id": "queued-process"}]
            raise AssertionError(query)

        async def fetchval(self, query: str, *args):
            if "global_ask_job_process_unit_scope" in query:
                assert args == ("job-1",)
                return True
            assert "permission_code = 'post_read'" in query
            assert args == ("account-1",)
            return True

    entities, processes, process_scope_limited, has_post_read = asyncio.run(
        load_job_visibility(FakeConnection(), "job-1", "account-1")
    )

    assert entities == {"queued-entity"}
    assert processes == {"queued-process"}
    assert process_scope_limited is True
    assert has_post_read is True
