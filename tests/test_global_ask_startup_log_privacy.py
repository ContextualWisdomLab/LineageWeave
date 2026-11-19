"""Exercise actual startup-tail diagnostics without serializing exception values."""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest
import redis.asyncio as redis

from backend.app import global_ask_queue as queue


@pytest.mark.parametrize("failure_type", [
    redis.ConnectionError, redis.BusyLoadingError, OSError, RuntimeError,
])
def test_startup_tail_failure_logs_type_only_and_preserves_retry(monkeypatch, caplog, failure_type):
    """The new startup retry path keeps private values out of real log records."""
    sentinel = "synthetic-private-startup-response"
    error = failure_type(sentinel)
    calls = []
    tail_count = 0
    cancellation = asyncio.CancelledError()

    async def tail(_client):
        nonlocal tail_count
        tail_count += 1
        calls.append("tail")
        if tail_count == 1:
            raise error
        return "123-7"

    async def recover(_client, _pool):
        calls.append("recovery")

    async def consume(_client, _pool, *, last_id, **_kwargs):
        calls.append(("consume", last_id))
        raise cancellation

    async def delay(seconds):
        calls.append(("delay", seconds))
        await asyncio.sleep(0)

    monkeypatch.setattr(queue, "_stream_tail", tail)
    monkeypatch.setattr(queue, "republish_queued_global_ask_jobs", recover)
    monkeypatch.setattr(queue, "consume_global_ask_stream_once", consume)
    monkeypatch.setattr(queue, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    monkeypatch.setattr(queue, "asyncio", SimpleNamespace(
        Semaphore=asyncio.Semaphore, Task=asyncio.Task, CancelledError=asyncio.CancelledError,
        sleep=delay, gather=asyncio.gather,
    ))
    caplog.set_level(logging.WARNING, logger=queue.__name__)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(asyncio.wait_for(queue.run_global_ask_worker(
            object(), object(), chat_factory=lambda: None,
        ), 2))
    assert caught.value is cancellation
    assert calls == ["tail", ("delay", 5), "tail", "recovery", ("consume", "123-7")]
    records = [row for row in caplog.records if row.name == queue.__name__]
    assert len(records) == 1
    assert records[0].exc_info is None
    assert sentinel not in caplog.text
    assert records[0].getMessage() == (
        "global ask worker startup tail failed; retrying (error_type=%s)" % failure_type.__name__
    )


def test_startup_tail_cancellation_is_silent_and_not_retried(monkeypatch, caplog):
    """Cancellation retains object identity without producing a retry diagnostic."""
    cancellation = asyncio.CancelledError()
    calls = []

    async def tail(_client):
        calls.append("tail")
        raise cancellation

    monkeypatch.setattr(queue, "_stream_tail", tail)
    caplog.set_level(logging.WARNING, logger=queue.__name__)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(queue.run_global_ask_worker(object(), object(), chat_factory=lambda: None))
    assert caught.value is cancellation
    assert calls == ["tail"]
    assert not [row for row in caplog.records if row.name == queue.__name__]
