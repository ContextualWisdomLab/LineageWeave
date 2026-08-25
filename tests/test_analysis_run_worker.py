"""Synthetic checks for Valkey analysis-run wake-up consumption."""

from __future__ import annotations

import pytest

from backend.app import analysis_run_worker
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

    async def fake_deliver(conn, **kwargs):
        del conn
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
        tepp_client=TeppClient(),
        adjudication_client=NullAdjudicationClient(),
    )

    assert last_id == "2-1"
    assert delivered == ["00000000-0000-0000-0000-000000000002"]
