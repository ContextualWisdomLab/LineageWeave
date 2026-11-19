"""Keep ordinary Ask round diagnostics within the ADR 0122 logging boundary."""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import asyncpg
import pytest
import redis.asyncio as redis

from backend.app import global_ask_queue as queue


@pytest.mark.parametrize("phase", ["recovery", "consume"])
@pytest.mark.parametrize("failure_type", [
    redis.ConnectionError, asyncpg.ConnectionDoesNotExistError, RuntimeError,
    type("Synthetic" + "Long" * 40, (RuntimeError,), {}),
], ids=["broker", "database", "unexpected", "long-type"])
def test_round_failure_is_type_only_and_retains_retry_cursor(
    monkeypatch, caplog, phase, failure_type,
):
    """Raw values and chained causes never reach the actual logging formatter."""
    sentinel = "synthetic-private-round-value"
    cause_marker = "synthetic-private-chained-cause"
    error = failure_type(sentinel)
    error.__cause__ = ValueError(cause_marker)
    cancellation = asyncio.CancelledError()
    calls = []
    failed = False
    consumed = False

    async def tail(_client):
        calls.append("tail")
        return "123-7"

    async def recover(_client, _pool):
        nonlocal failed
        calls.append("recovery")
        if phase == "recovery" and not failed:
            failed = True
            raise error

    async def consume(_client, _pool, *, last_id, **_kwargs):
        nonlocal failed, consumed
        calls.append(("consume", last_id))
        if phase == "consume" and not failed:
            failed = True
            raise error
        if consumed:
            raise cancellation
        consumed = True
        return "200-0"

    async def delay(seconds):
        calls.append(("delay", seconds))
        await asyncio.sleep(0)

    monkeypatch.setattr(queue, "_stream_tail", tail)
    monkeypatch.setattr(queue, "republish_queued_global_ask_jobs", recover)
    monkeypatch.setattr(queue, "consume_global_ask_stream_once", consume)
    monkeypatch.setattr(queue, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    monkeypatch.setattr(queue, "asyncio", SimpleNamespace(
        Semaphore=asyncio.Semaphore, Task=asyncio.Task,
        CancelledError=asyncio.CancelledError, sleep=delay, gather=asyncio.gather,
    ))
    caplog.set_level(logging.WARNING, logger=queue.__name__)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(asyncio.wait_for(queue.run_global_ask_worker(
            object(), object(), chat_factory=lambda: None,
        ), 2))
    assert caught.value is cancellation
    expected = ["tail", "recovery"]
    expected += ([("delay", 5), "recovery"] if phase == "recovery" else
                 [("consume", "123-7"), ("delay", 5)])
    expected += [("consume", "123-7"), ("consume", "200-0")]
    assert calls == expected
    records = [r for r in caplog.records if r.name == queue.__name__]
    assert len(records) == 1
    assert sentinel not in caplog.text and cause_marker not in caplog.text
    assert records[0].exc_info is None and records[0].stack_info is None
    assert records[0].levelno == logging.ERROR
    assert records[0].getMessage() == (
        "global ask worker round failed; retrying (error_type=%s)"
        % failure_type.__name__[:128]
    )


@pytest.mark.parametrize("phase", ["recovery", "consume"])
def test_round_cancellation_is_silent_and_not_retried(monkeypatch, caplog, phase):
    """The cancellation object propagates without another retry or warning."""
    cancellation = asyncio.CancelledError()
    calls = []

    async def tail(_client):
        calls.append("tail")
        return "123-7"

    async def recover(_client, _pool):
        calls.append("recovery")
        if phase == "recovery":
            raise cancellation

    async def consume(_client, _pool, **_kwargs):
        calls.append("consume")
        raise cancellation

    async def delay(_seconds):
        pytest.fail("cancellation must not enter retry")

    monkeypatch.setattr(queue, "_stream_tail", tail)
    monkeypatch.setattr(queue, "republish_queued_global_ask_jobs", recover)
    monkeypatch.setattr(queue, "consume_global_ask_stream_once", consume)
    monkeypatch.setattr(queue, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    monkeypatch.setattr(queue, "asyncio", SimpleNamespace(
        Semaphore=asyncio.Semaphore, Task=asyncio.Task,
        CancelledError=asyncio.CancelledError, sleep=delay, gather=asyncio.gather,
    ))
    caplog.set_level(logging.WARNING, logger=queue.__name__)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(queue.run_global_ask_worker(object(), object(), chat_factory=lambda: None))
    assert caught.value is cancellation
    assert calls == ["tail", "recovery"] + (["consume"] if phase == "consume" else [])
    assert not [r for r in caplog.records if r.name == queue.__name__]
