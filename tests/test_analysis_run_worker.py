"""Synthetic checks for Valkey analysis-run wake-up consumption."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from backend.app import analysis_run_worker, post_content_worker
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
    )

    assert last_id == "1-1"
    assert calls == [
        {
            "analysis_run_id": "00000000-0000-0000-0000-000000000001",
            "account_id": "synthetic-account",
            "affiliated_entity_ids": [],
            "tepp_client": calls[0]["tepp_client"],
            "adjudication_client": calls[0]["adjudication_client"],
            "valkey_stream_entry_id": "1-0",
        }
    ]
