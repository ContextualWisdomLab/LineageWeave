"""Exercise terminal consumer reporting through the actual ASGI lifespan."""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from backend.app import main

_WORKERS = ("analysis_run", "post_content", "global_ask")
_SECRET = "synthetic-private-worker-exception-value"


@pytest.mark.parametrize("worker_name", _WORKERS)
@pytest.mark.parametrize("termination", ["exception", "return"])
def test_lifespan_reports_terminal_consumer_without_disrupting_siblings(
    monkeypatch, caplog, worker_name, termination,
):
    """One dead consumer emits one type-only record while siblings remain owned."""
    caplog.set_level(logging.ERROR, logger=main.__name__)
    events = []
    tasks = {}
    failure = RuntimeError(_SECRET)

    async def scenario():
        release = asyncio.Event()
        started = {name: asyncio.Event() for name in _WORKERS}

        class Pool:
            async def close(self):
                events.append("pool.close")

        class Valkey:
            async def aclose(self):
                events.append("valkey.close")

        async def pool_factory(_url):
            return Pool()

        def worker(name):
            async def run(*_args, **_kwargs):
                tasks[name] = asyncio.current_task()
                started[name].set()
                if name == worker_name:
                    await release.wait()
                    if termination == "exception":
                        raise failure
                    return
                try:
                    await asyncio.Future()
                finally:
                    events.append(name + ".settled")
            return run

        monkeypatch.setattr(main, "configure_telemetry", lambda *_args: events.append("telemetry.start"))
        monkeypatch.setattr(main, "shutdown_telemetry", lambda: events.append("telemetry.stop"))
        monkeypatch.setattr(main, "load_settings", lambda: SimpleNamespace(
            database_url="postgresql://synthetic", valkey_url="redis://synthetic",
            tepp_transport_url=None, tepp_api_key=None,
        ))
        monkeypatch.setattr(main, "create_pool", pool_factory)
        monkeypatch.setattr(main, "create_valkey_client", lambda _url: Valkey())
        monkeypatch.setattr(main, "configured_tepp_client", lambda *_args: object())
        monkeypatch.setattr(main, "_adjudication_client", lambda: object())
        for name in _WORKERS:
            monkeypatch.setattr(main, "run_" + name + "_worker", worker(name))
        app = SimpleNamespace(state=SimpleNamespace())
        async with main.lifespan(app):
            await asyncio.wait_for(asyncio.gather(*(e.wait() for e in started.values())), 2)
            assert not any(t.done() for t in tasks.values())
            release.set()
            # Event-loop turns settle the real task and its completion callback;
            # no wall-clock sleeps or monkeypatching shared asyncio functions.
            for _ in range(4):
                await asyncio.sleep(0)
            assert tasks[worker_name].done()
            assert all(not task.done() for name, task in tasks.items() if name != worker_name)
            assert await main.healthz() == {"status": "ok"}
            records = [r for r in caplog.records if r.name == main.__name__]
            assert len(records) == 1
            record = records[0]
            assert record.getMessage() == (
                "background consumer terminated (worker=%s, error_type=%s)" % (
                    worker_name, "RuntimeError" if termination == "exception" else "unexpected_return",
                )
            )
            assert record.exc_info is None
            assert _SECRET not in caplog.text
            assert len(tasks) == 3  # No implicit restart or competing consumer.
        assert all(task.done() for task in tasks.values())
        if termination == "exception":
            assert tasks[worker_name].exception() is failure
        else:
            assert tasks[worker_name].result() is None
        assert events.count("pool.close") == 1
        assert events.count("valkey.close") == 1
        assert events.count("telemetry.stop") == 1
        assert len([r for r in caplog.records if r.name == main.__name__]) == 1
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    asyncio.run(scenario())


def test_lifespan_graceful_cancellation_is_silent_and_settles_every_consumer(monkeypatch, caplog):
    """Routine shutdown neither logs false failure nor abandons child tasks."""
    caplog.set_level(logging.ERROR, logger=main.__name__)
    events = []
    tasks = []

    async def scenario():
        started = asyncio.Event()

        class Pool:
            async def close(self):
                events.append("pool")

        class Valkey:
            async def aclose(self):
                events.append("valkey")

        async def pool_factory(_url):
            return Pool()

        async def worker(*_args, **_kwargs):
            tasks.append(asyncio.current_task())
            if len(tasks) == 3:
                started.set()
            await asyncio.Future()

        monkeypatch.setattr(main, "configure_telemetry", lambda *_args: None)
        monkeypatch.setattr(main, "shutdown_telemetry", lambda: events.append("telemetry"))
        monkeypatch.setattr(main, "load_settings", lambda: SimpleNamespace(
            database_url="postgresql://synthetic", valkey_url="redis://synthetic",
            tepp_transport_url=None, tepp_api_key=None,
        ))
        monkeypatch.setattr(main, "create_pool", pool_factory)
        monkeypatch.setattr(main, "create_valkey_client", lambda _url: Valkey())
        monkeypatch.setattr(main, "configured_tepp_client", lambda *_args: object())
        monkeypatch.setattr(main, "_adjudication_client", lambda: object())
        for name in _WORKERS:
            monkeypatch.setattr(main, "run_" + name + "_worker", worker)
        async with main.lifespan(SimpleNamespace(state=SimpleNamespace())):
            await asyncio.wait_for(started.wait(), 2)
            assert all(not task.done() for task in tasks)
            assert caplog.records == []
        assert len(tasks) == 3 and all(task.cancelled() for task in tasks)
        assert events == ["pool", "valkey", "telemetry"]
        assert caplog.records == []
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    asyncio.run(scenario())
