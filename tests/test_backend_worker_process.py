"""Process-ownership tests for API and durable queue consumers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.app import main, worker


class _Closable:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True


def test_api_lifespan_opens_clients_without_starting_queue_workers(monkeypatch) -> None:
    """Serving HTTP never competes with the dedicated durable worker service."""
    pool = _Closable()
    valkey = _Closable()
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: SimpleNamespace(database_url="db", valkey_url="valkey"),
    )
    monkeypatch.setattr(main, "create_pool", lambda _url: _async_value(pool))
    monkeypatch.setattr(main, "create_valkey_client", lambda _url: valkey)
    monkeypatch.setattr(main, "configure_telemetry", lambda _name: None)
    monkeypatch.setattr(main, "shutdown_telemetry", lambda: None)
    app = SimpleNamespace(state=SimpleNamespace())

    async def exercise() -> None:
        async with main.lifespan(app):
            assert app.state.pool is pool
            assert app.state.valkey is valkey
            assert not hasattr(app.state, "post_content_worker")
            assert not hasattr(app.state, "analysis_run_worker")
            assert not hasattr(app.state, "global_ask_worker")

    asyncio.run(exercise())
    assert pool.closed
    assert valkey.closed


def test_worker_process_owns_all_three_durable_consumers(monkeypatch) -> None:
    """Analysis, post-content, and Global Ask queues share one worker owner."""
    pool = _Closable()
    valkey = _Closable()
    calls: list[str] = []
    settings = SimpleNamespace(
        database_url="db",
        valkey_url="valkey",
        tepp_transport_url="",
        tepp_api_key="",
        orchestrator_answer_timeout_seconds=570.0,
    )

    async def called(name: str, *_args, **_kwargs) -> None:
        calls.append(name)

    monkeypatch.setattr(worker, "load_settings", lambda: settings)
    monkeypatch.setattr(worker, "create_pool", lambda _url: _async_value(pool))
    monkeypatch.setattr(worker, "create_valkey_client", lambda _url: valkey)
    monkeypatch.setattr(worker, "configure_telemetry", lambda _name: None)
    monkeypatch.setattr(worker, "shutdown_telemetry", lambda: calls.append("shutdown"))
    monkeypatch.setattr(worker, "configured_tepp_client", lambda *_args: object())
    monkeypatch.setattr(worker, "_adjudication_client", lambda: object())
    monkeypatch.setattr(worker, "_vision_client", lambda: object())
    monkeypatch.setattr(worker, "_embedding_client", lambda: object())
    monkeypatch.setattr(worker, "_post_structure_client", lambda: object())
    monkeypatch.setattr(worker, "_post_chat_client", lambda **_kwargs: object())
    monkeypatch.setattr(worker, "run_worker_heartbeat", lambda: _async_value(None))
    monkeypatch.setattr(
        worker, "run_analysis_run_worker", lambda *a, **kw: called("analysis", *a, **kw)
    )
    monkeypatch.setattr(
        worker, "run_post_content_worker", lambda *a, **kw: called("content", *a, **kw)
    )
    monkeypatch.setattr(
        worker, "run_global_ask_worker", lambda *a, **kw: called("global_ask", *a, **kw)
    )

    asyncio.run(worker.run_worker_process())

    assert calls[:3] == ["analysis", "content", "global_ask"]
    assert calls[-1] == "shutdown"
    assert pool.closed
    assert valkey.closed


async def _async_value(value):
    """Return one test double through an awaitable seam."""
    return value
