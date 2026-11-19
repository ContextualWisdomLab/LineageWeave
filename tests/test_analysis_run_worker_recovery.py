"""Synthetic transient owner-lookup failures exercise the real worker/consumer."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, nullcontext
from types import SimpleNamespace

import asyncpg
import pytest
import redis.asyncio as redis

from backend.app import analysis_run_worker as worker

_RUN_ID = "00000000-0000-0000-0000-000000000001"
_SECRET = "synthetic-private-diagnostic-not-for-logs"


def _drive(monkeypatch, error):
    """Fail the first actual owner lookup, then deliver and cancel the loop."""
    calls = {"lookup": 0, "delivery": 0, "poll": [], "sleep": []}

    class Connection:
        async def fetchrow(self, query, run_id):
            assert "requested_by_account_id" in query
            assert run_id == _RUN_ID
            calls["lookup"] += 1
            if calls["lookup"] == 1:
                raise error
            return {"requested_by_account_id": "synthetic-account"}

    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield Connection()

    class Broker:
        async def xread(self, streams, *, count, block):
            assert (count, block) == (10, 1000)
            calls["poll"].append(dict(streams))
            if calls["delivery"]:
                raise asyncio.CancelledError
            return [("synthetic-outbox", [("1-0", {"analysis_run_id": _RUN_ID})])]

    async def deliver(pool, **kwargs):
        assert isinstance(pool, Pool)
        assert kwargs["account_id"] == "synthetic-account"
        assert kwargs["analysis_run_id"] == _RUN_ID
        assert kwargs["valkey_stream_entry_id"] == "1-0"
        calls["delivery"] += 1

    async def sleep(delay):
        calls["sleep"].append(delay)

    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(sleep=sleep))
    monkeypatch.setattr(worker, "deliver_queued_analysis_run", deliver)
    monkeypatch.setattr(worker, "traced", lambda *_args: nullcontext())

    async def scenario():
        await worker.run_analysis_run_worker(
            Broker(), Pool(), database_url="postgresql://synthetic",
            tepp_client=object(), adjudication_client=object(),
        )

    with pytest.raises(type(error) if not isinstance(error, _TRANSIENT) else asyncio.CancelledError) as caught:
        asyncio.run(asyncio.wait_for(scenario(), timeout=2.0))
    return calls, caught.value


_TRANSIENT = (
    asyncpg.PostgresConnectionError,
    asyncpg.exceptions.OperatorInterventionError,
    asyncpg.InterfaceError,
    redis.RedisError,
    OSError,
)


@pytest.mark.parametrize("error_type", [
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.AdminShutdownError,
    asyncpg.InterfaceError,
    redis.ConnectionError,
    OSError,
])
def test_transient_owner_lookup_failure_retries_without_losing_the_entry(monkeypatch, caplog, error_type):
    """DB/broker reconnection retains the cursor, delay and type-only logging."""
    caplog.set_level("WARNING", logger=worker.__name__)
    calls, _ = _drive(monkeypatch, error_type(_SECRET))
    assert calls["lookup"] == 2
    assert calls["delivery"] == 1
    assert calls["sleep"] == [worker._BROKER_RECOVERY_DELAY_SECONDS]
    key = worker.OUTBOX_STREAM_KEY
    assert calls["poll"] == [{key: "0-0"}, {key: "0-0"}, {key: "1-0"}]
    assert len(caplog.records) == 1
    assert error_type.__name__ in caplog.text
    assert _SECRET not in caplog.text


@pytest.mark.parametrize("error_type", [RuntimeError, asyncpg.exceptions.UndefinedTableError, asyncio.CancelledError])
def test_unexpected_schema_and_cancellation_failures_are_not_retried(monkeypatch, caplog, error_type):
    """Keep unknown/schema defects and cancellation observable, not infinite retries."""
    error = error_type(_SECRET)
    calls, caught = _drive(monkeypatch, error)
    assert caught is error
    assert calls["lookup"] == 1
    assert calls["delivery"] == 0
    assert calls["sleep"] == []
    assert caplog.records == []
