"""Synthetic checks for Valkey analysis-run wake-up consumption."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
import redis.asyncio as redis

from backend.app import analysis_run_worker, post_content_worker
from backend.app.analysis_run_start import AnalysisRunStartError
from lineageweave.adjudication_client import NullAdjudicationClient
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


class _IdleValkey:
    async def xread(self, _streams, *, count, block):
        assert (count, block) == (10, 1000)
        return []


@pytest.mark.anyio
async def test_idle_worker_reads_do_not_emit_empty_spans(monkeypatch):
    """Blocking poll timeouts stay silent until a real batch arrives."""
    analysis_trace = Mock()
    post_content_trace = Mock()
    monkeypatch.setattr(analysis_run_worker, "traced", analysis_trace)
    monkeypatch.setattr(post_content_worker, "traced", post_content_trace)

    assert await analysis_run_worker.consume_analysis_run_stream_once(
        _IdleValkey(),
        _Pool(),
        last_id="0-0",
        database_url="postgresql://synthetic",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
    ) == "0-0"
    assert await post_content_worker.consume_post_content_stream_once(
        _IdleValkey(),
        _Pool(),
        last_id="0-0",
        vision_factory=lambda: None,
        embedding_factory=lambda: None,
        structure_factory=lambda: None,
    ) == "0-0"
    analysis_trace.assert_not_called()
    post_content_trace.assert_not_called()


@pytest.mark.anyio
async def test_xread_failures_emit_diagnostic_spans_but_preserve_errors(monkeypatch):
    """Broker failures are traced without turning idle polls into spans."""
    analysis_trace_names = []
    post_content_trace_names = []

    @contextmanager
    def analysis_trace(name, _attributes):
        analysis_trace_names.append(name)
        yield None

    @contextmanager
    def post_content_trace(name, _attributes):
        post_content_trace_names.append(name)
        yield None

    class FailingValkey:
        async def xread(self, _streams, *, count, block):
            assert (count, block) == (10, 1000)
            raise RuntimeError("synthetic broker outage")

    monkeypatch.setattr(analysis_run_worker, "traced", analysis_trace)
    monkeypatch.setattr(post_content_worker, "traced", post_content_trace)

    with pytest.raises(RuntimeError, match="synthetic broker outage"):
        await analysis_run_worker.consume_analysis_run_stream_once(
            FailingValkey(),
            _Pool(),
            last_id="0-0",
            database_url="postgresql://synthetic",
            tepp_client=TeppClient(),
            adjudication_client=NullAdjudicationClient(),
        )
    with pytest.raises(RuntimeError, match="synthetic broker outage"):
        await post_content_worker.consume_post_content_stream_once(
            FailingValkey(),
            _Pool(),
            last_id="0-0",
            vision_factory=lambda: None,
            embedding_factory=lambda: None,
            structure_factory=lambda: None,
        )

    assert analysis_trace_names == ["lineageweave.valkey.analysis_outbox_xread"]
    assert post_content_trace_names == ["lineageweave.valkey.post_content_xread"]


@pytest.mark.anyio
async def test_workers_retry_transient_broker_errors_without_dropping_the_task(monkeypatch):
    """A transient Valkey outage is retried; cancellation still stops each worker."""
    analysis_calls = 0
    post_content_calls = 0

    class RecoveringAnalysisValkey:
        async def xread(self, _streams, *, count, block):
            nonlocal analysis_calls
            assert (count, block) == (10, 1000)
            analysis_calls += 1
            if analysis_calls == 1:
                raise redis.RedisError("synthetic broker outage")
            raise asyncio.CancelledError

    class RecoveringPostContentValkey:
        async def xrevrange(self, _stream, *, count):
            assert count == 1
            return []

        async def xread(self, _streams, *, count, block):
            nonlocal post_content_calls
            assert (count, block) == (10, 1000)
            post_content_calls += 1
            if post_content_calls == 1:
                raise redis.RedisError("synthetic broker outage")
            raise asyncio.CancelledError

    async def no_sleep(*_args):
        return None

    async def no_republish(*_args, **_kwargs):
        return 0

    monkeypatch.setattr(analysis_run_worker.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(post_content_worker.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(
        post_content_worker, "republish_queued_post_content_jobs", no_republish
    )

    with pytest.raises(asyncio.CancelledError):
        await analysis_run_worker.run_analysis_run_worker(
            RecoveringAnalysisValkey(),
            _Pool(),
            database_url="postgresql://synthetic",
            tepp_client=TeppClient(),
            adjudication_client=NullAdjudicationClient(),
        )
    with pytest.raises(asyncio.CancelledError):
        await post_content_worker.run_post_content_worker(
            RecoveringPostContentValkey(),
            _Pool(),
            vision_factory=lambda: None,
            embedding_factory=lambda: None,
            structure_factory=lambda: None,
        )

    assert analysis_calls == 2
    assert post_content_calls == 2


@pytest.mark.anyio
async def test_post_content_batch_advances_past_a_malformed_event(monkeypatch):
    """A real batch is traced and malformed wake-up data stays untrusted."""
    calls = []

    async def fake_process(_pool, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(post_content_worker, "process_post_content_job", fake_process)

    class MalformedValkey:
        async def xread(self, _streams, *, count, block):
            assert (count, block) == (10, 1000)
            return [
                (
                    "post-content",
                    [
                        ("1-0", {"post_id": "not-a-uuid"}),
                        (
                            "1-1",
                            {
                                "post_id": "00000000-0000-0000-0000-000000000001",
                                "source_body_sha256": "a" * 64,
                            },
                        ),
                    ],
                )
            ]

    assert await post_content_worker.consume_post_content_stream_once(
        MalformedValkey(),
        _Pool(),
        last_id="0-0",
        vision_factory=lambda: None,
        embedding_factory=lambda: None,
        structure_factory=lambda: None,
    ) == "1-1"
    assert calls[0]["post_id"] == "00000000-0000-0000-0000-000000000001"
    assert calls[0]["source_body_digest"] == "a" * 64


@pytest.mark.anyio
async def test_consumer_forwards_valid_event_and_skips_malformed_event(monkeypatch):
    calls = []

    pool = _Pool()

    async def fake_deliver(delivery_pool, **kwargs):
        assert delivery_pool is pool
        calls.append(kwargs)

    monkeypatch.setattr(analysis_run_worker, "deliver_queued_analysis_run", fake_deliver)

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _Valkey(),
        pool,
        last_id="0-0",
        database_url="postgresql://synthetic",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
    )

    assert last_id == "1-1"
    assert calls == [
        {
            "analysis_run_id": "00000000-0000-0000-0000-000000000001",
            "database_url": "postgresql://synthetic",
            "account_id": "synthetic-account",
            "affiliated_entity_ids": [],
            "tepp_client": calls[0]["tepp_client"],
            "adjudication_client": calls[0]["adjudication_client"],
            "valkey_stream_entry_id": "1-0",
        }
    ]


class _TwoRunsValkey:
    async def xread(self, _streams, *, count, block):
        del count, block
        return [
            (
                "analysis-run-outbox",
                [
                    ("2-0", {"analysis_run_id": "00000000-0000-0000-0000-000000000001"}),
                    ("2-1", {"analysis_run_id": "00000000-0000-0000-0000-000000000002"}),
                ],
            )
        ]


@pytest.mark.anyio
async def test_one_refused_delivery_does_not_end_the_worker(monkeypatch):
    """A fail-closed refusal (e.g. channel weights not estimated, ADR 0145)
    on one run must advance the cursor and still deliver the next run --
    a raised refusal would otherwise end the worker task and halt every
    later run's delivery.
    """
    delivered = []

    async def fake_deliver(_pool, **kwargs):
        if kwargs["analysis_run_id"].endswith("1"):
            raise AnalysisRunStartError(
                503, "Channel weights are not estimated yet."
            )
        delivered.append(kwargs["analysis_run_id"])

    monkeypatch.setattr(analysis_run_worker, "deliver_queued_analysis_run", fake_deliver)

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _TwoRunsValkey(),
        _Pool(),
        last_id="0-0",
        database_url="postgresql://synthetic",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
    )

    assert last_id == "2-1"
    assert delivered == ["00000000-0000-0000-0000-000000000002"]


@pytest.mark.anyio
async def test_one_unexpected_delivery_failure_does_not_end_the_worker(monkeypatch):
    """A malformed provider reply must not stop later durable deliveries."""
    delivered = []

    async def fake_deliver(conn, **kwargs):
        del conn
        if kwargs["analysis_run_id"].endswith("1"):
            raise RuntimeError("malformed provider reply")
        delivered.append(kwargs["analysis_run_id"])

    monkeypatch.setattr(analysis_run_worker, "deliver_queued_analysis_run", fake_deliver)

    last_id = await analysis_run_worker.consume_analysis_run_stream_once(
        _TwoRunsValkey(),
        _Pool(),
        last_id="0-0",
        database_url="postgresql://synthetic",
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
    )

    assert last_id == "2-1"
    assert delivered == ["00000000-0000-0000-0000-000000000002"]
