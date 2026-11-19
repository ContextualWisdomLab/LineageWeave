"""Keep startup-tail admission inside each consumer's existing retry boundary."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import redis.asyncio as redis

from backend.app import global_ask_queue, post_content_worker


@pytest.mark.parametrize("kind", ["post_content", "global_ask"])
@pytest.mark.parametrize("failure", [redis.ConnectionError, redis.BusyLoadingError, OSError])
def test_startup_tail_retries_before_recovery_or_consume(monkeypatch, kind, failure):
    module = post_content_worker if kind == "post_content" else global_ask_queue
    calls = []
    tail_calls = 0
    warning_calls = []
    expected_delay = post_content_worker._BROKER_RECOVERY_DELAY_SECONDS if kind == "post_content" else 5

    async def tail(_client):
        nonlocal tail_calls
        tail_calls += 1
        calls.append("tail")
        if tail_calls == 1:
            raise failure("synthetic-private-diagnostic")
        return "123-7"

    async def recover(_client, _pool):
        calls.append("recovery")

    async def consume(_client, _pool, *, last_id, **_kwargs):
        calls.append(("consume", last_id))
        raise asyncio.CancelledError

    async def delay(seconds):
        calls.append(("delay", seconds))
        await asyncio.sleep(0)

    monkeypatch.setattr(module, "_stream_tail", tail)
    monkeypatch.setattr(module, "republish_queued_" + kind + "_jobs", recover)
    monkeypatch.setattr(module, "consume_" + kind + "_stream_once", consume)
    monkeypatch.setattr(module, "asyncio", SimpleNamespace(
        sleep=delay, CancelledError=asyncio.CancelledError,
        Semaphore=asyncio.Semaphore, Task=asyncio.Task, gather=asyncio.gather,
    ))
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    monkeypatch.setattr(module, "_logger", SimpleNamespace(
        warning=lambda *args: warning_calls.append(args),
        exception=lambda *args: warning_calls.append(args),
    ))
    kwargs = {"vision_factory": lambda: None, "embedding_factory": lambda: None,
              "structure_factory": lambda: None} if kind == "post_content" else {"chat_factory": lambda: None}
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(getattr(module, "run_" + kind + "_worker")(object(), object(), **kwargs), 2))
    assert calls == ["tail", ("delay", expected_delay), "tail", "recovery", ("consume", "123-7")]
    assert len(warning_calls) == 1


@pytest.mark.parametrize("kind", ["post_content", "global_ask"])
@pytest.mark.parametrize("initial_tail", ["0-0", "123-7"])
def test_successful_tail_is_sampled_only_once_across_rounds(monkeypatch, kind, initial_tail):
    module = post_content_worker if kind == "post_content" else global_ask_queue
    calls = []
    async def tail(_client):
        calls.append("tail")
        return initial_tail
    async def recover(_client, _pool):
        calls.append("recovery")
    async def consume(_client, _pool, *, last_id, **_kwargs):
        calls.append(("consume", last_id))
        if sum(isinstance(c, tuple) for c in calls) == 2:
            raise asyncio.CancelledError
        return "456-8"
    monkeypatch.setattr(module, "_stream_tail", tail)
    monkeypatch.setattr(module, "republish_queued_" + kind + "_jobs", recover)
    monkeypatch.setattr(module, "consume_" + kind + "_stream_once", consume)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    kwargs = {"vision_factory": lambda: None, "embedding_factory": lambda: None,
              "structure_factory": lambda: None} if kind == "post_content" else {"chat_factory": lambda: None}
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(getattr(module, "run_" + kind + "_worker")(object(), object(), **kwargs), 2))
    assert calls == ["tail", "recovery", ("consume", initial_tail), ("consume", "456-8")]


@pytest.mark.parametrize("kind", ["post_content", "global_ask"])
def test_tail_cancellation_never_retries_or_dispatches(monkeypatch, kind):
    module = post_content_worker if kind == "post_content" else global_ask_queue
    failure = asyncio.CancelledError()
    calls = []
    async def tail(_client):
        calls.append("tail")
        raise failure
    monkeypatch.setattr(module, "_stream_tail", tail)
    kwargs = {"vision_factory": lambda: None, "embedding_factory": lambda: None,
              "structure_factory": lambda: None} if kind == "post_content" else {"chat_factory": lambda: None}
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(getattr(module, "run_" + kind + "_worker")(object(), object(), **kwargs))
    assert caught.value is failure
    assert calls == ["tail"]


def test_post_content_unknown_startup_error_is_not_retried(monkeypatch):
    failure = RuntimeError("synthetic-invariant")
    async def tail(_client):
        raise failure
    monkeypatch.setattr(post_content_worker, "_stream_tail", tail)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(post_content_worker.run_post_content_worker(
            object(), object(), vision_factory=lambda: None,
            embedding_factory=lambda: None, structure_factory=lambda: None,
        ))
    assert caught.value is failure
