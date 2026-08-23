"""Synthetic checks for Valkey analysis-run wake-up consumption."""

from __future__ import annotations

import pytest

from backend.app import analysis_run_worker
from lineageweave.adjudication_client import NullAdjudicationClient
from lineageweave.embedding_client import NullEmbeddingClient
from lineageweave.tepp_client import TeppClient


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _Connection:
    def transaction(self):
        return _Transaction()

    async def fetchrow(self, _query, _analysis_run_id):
        return {"requested_by_account_id": "synthetic-account"}


class _Acquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *_args):
        return False


class _Pool:
    def acquire(self):
        return _Acquire(_Connection())


class _Valkey:
    async def xread(self, _streams, *, count, block):
        assert (count, block) == (10, 1000)
        return [
            (
                "analysis-run-outbox",
                [
                    ("1-0", {"analysis_run_id": "00000000-0000-0000-0000-000000000001"}),
                    ("1-1", {}),
                ],
            )
        ]


@pytest.mark.anyio
async def test_consumer_forwards_valid_event_and_skips_malformed_event(monkeypatch):
    calls = []

    async def fake_deliver(conn, **kwargs):
        del conn
        calls.append(kwargs)

    monkeypatch.setattr(analysis_run_worker, "deliver_queued_analysis_run", fake_deliver)

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _Valkey(),
        _Pool(),
        last_id="0-0",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
        embedding_client=NullEmbeddingClient(),
    )

    assert last_id == "1-1"
    assert calls == [
        {
            "analysis_run_id": "00000000-0000-0000-0000-000000000001",
            "account_id": "synthetic-account",
            "affiliated_entity_ids": [],
            "tepp_client": calls[0]["tepp_client"],
            "adjudication_client": calls[0]["adjudication_client"],
            "embedding_client": calls[0]["embedding_client"],
            "valkey_stream_entry_id": "1-0",
        }
    ]


@pytest.mark.anyio
async def test_a_bad_delivery_is_logged_and_does_not_kill_the_consumer(monkeypatch):
    """A judge()/delivery failure on one run must not propagate out of the
    consume loop -- that would kill the whole worker task and stop every
    other queued run from ever being delivered.
    """

    async def fake_deliver(conn, **kwargs):
        del conn, kwargs
        raise RuntimeError("adjudication response had no parseable confidence score")

    monkeypatch.setattr(analysis_run_worker, "deliver_queued_analysis_run", fake_deliver)

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _Valkey(),
        _Pool(),
        last_id="0-0",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
        embedding_client=NullEmbeddingClient(),
    )

    assert last_id == "1-1"


@pytest.mark.anyio
async def test_a_deleted_run_is_skipped_without_attempting_delivery(monkeypatch):
    """A valid stale wake-up must not fabricate an owner or delivery."""

    class MissingRunConnection(_Connection):
        """Return no durable run for the otherwise valid stream UUID."""

        async def fetchrow(self, _query, _analysis_run_id):
            """Model a run deleted before its wake-up was inspected."""
            return

    class MissingRunPool:
        """Yield the missing-run connection."""

        def acquire(self):
            """Return one synthetic acquisition context."""
            return _Acquire(MissingRunConnection())

    async def unexpected_delivery(*_args, **_kwargs):
        """Fail if a stale wake-up reaches the durable delivery function."""
        raise AssertionError("deleted run must not be delivered")

    monkeypatch.setattr(
        analysis_run_worker, "deliver_queued_analysis_run", unexpected_delivery
    )

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _Valkey(),
        MissingRunPool(),
        last_id="0-0",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
        embedding_client=NullEmbeddingClient(),
    )

    assert last_id == "1-1"


@pytest.mark.anyio
async def test_worker_starts_from_the_full_stream_and_passes_updated_cursor(
    monkeypatch,
):
    """The long-running worker must delegate with its initial durable cursor."""

    class StopWorker(Exception):
        """Terminate the intentionally infinite loop after one iteration."""

    observed: list[str] = []

    async def consume_once(*_args, last_id, **_kwargs):
        """Capture the initial cursor and stop the infinite worker."""
        observed.append(last_id)
        raise StopWorker

    monkeypatch.setattr(
        analysis_run_worker, "consume_analysis_run_stream_once", consume_once
    )

    with pytest.raises(StopWorker):
        await analysis_run_worker.run_analysis_run_worker(
            _Valkey(),
            _Pool(),
            tepp_client=TeppClient(),
            adjudication_client=NullAdjudicationClient(),
            embedding_client=NullEmbeddingClient(),
        )

    assert observed == ["0-0"]
