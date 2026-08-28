"""Process-ownership tests for API and durable queue consumers."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

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


def test_worker_process_owns_all_configured_durable_consumers(monkeypatch) -> None:
    """Analysis, content, Ask, and configured influence work share one owner."""
    pool = _Closable()
    valkey = _Closable()
    calls: list[str] = []
    global_ask_kwargs: dict = {}
    settings = SimpleNamespace(
        database_url="db",
        valkey_url="valkey",
        tepp_transport_url="",
        tepp_api_key="",
        topic_influence_transport_url="http://measurement.test",
        topic_influence_api_key="synthetic-token",
        topic_influence_request_timeout_seconds=11,
        topic_influence_lease_timeout_seconds=17,
        topic_influence_poll_seconds=13,
        orchestrator_answer_timeout_seconds=570.0,
    )

    async def called(name: str, *_args, **_kwargs) -> None:
        calls.append(name)

    async def global_ask(*_args, **kwargs) -> None:
        global_ask_kwargs.update(kwargs)
        calls.append("global_ask")

    monkeypatch.setattr(worker, "load_settings", lambda: settings)
    monkeypatch.setattr(worker, "create_pool", lambda _url: _async_value(pool))
    monkeypatch.setattr(worker, "create_valkey_client", lambda _url: valkey)

    @asynccontextmanager
    async def lease(_pool):
        calls.append("lease_acquired")
        try:
            yield
        finally:
            calls.append("lease_released")

    monkeypatch.setattr(worker, "_single_worker_lease", lease)
    monkeypatch.setattr(worker, "configure_telemetry", lambda _name: None)
    monkeypatch.setattr(worker, "shutdown_telemetry", lambda: calls.append("shutdown"))
    monkeypatch.setattr(worker, "configured_tepp_client", lambda *_args: object())
    monkeypatch.setattr(worker, "_adjudication_client", object)
    monkeypatch.setattr(worker, "_vision_client", object)
    monkeypatch.setattr(worker, "_embedding_client", object)
    monkeypatch.setattr(worker, "_post_structure_client", object)
    monkeypatch.setattr(worker, "_post_chat_client", lambda **_kwargs: object())
    semantic_client = object()
    verification_client = object()
    monkeypatch.setattr(worker, "_semantic_query_client", lambda: semantic_client)
    monkeypatch.setattr(
        worker, "_claim_verification_client_factory", lambda: verification_client
    )
    monkeypatch.setattr(worker, "run_worker_heartbeat", lambda: _async_value(None))
    monkeypatch.setattr(
        worker, "run_analysis_run_worker", lambda *a, **kw: called("analysis", *a, **kw)
    )
    monkeypatch.setattr(
        worker, "run_post_content_worker", lambda *a, **kw: called("content", *a, **kw)
    )
    monkeypatch.setattr(worker, "run_global_ask_worker", global_ask)
    monkeypatch.setattr(
        worker,
        "run_topic_influence_worker",
        lambda *a, **kw: called("topic_influence", *a, **kw),
    )

    asyncio.run(worker.run_worker_process())

    assert calls[:5] == [
        "lease_acquired",
        "analysis",
        "content",
        "global_ask",
        "topic_influence",
    ]
    assert global_ask_kwargs["semantic_query_factory"]() is semantic_client
    assert global_ask_kwargs["claim_verification_factory"]() is verification_client
    assert calls[-2:] == ["lease_released", "shutdown"]
    assert pool.closed
    assert valkey.closed


def test_worker_process_lease_fails_closed_for_a_second_replica() -> None:
    """A PostgreSQL session lease enforces the single stream-consumer contract."""
    calls: list[str] = []

    class Connection:
        async def fetchval(self, query: str, name: str) -> bool:
            assert "hashtextextended($1, 0)" in query
            assert name == worker._WORKER_LEASE_NAME
            calls.append("unlock" if "unlock" in query else "lock")
            return calls == ["lock"]

    class Acquire:
        async def __aenter__(self):
            return Connection()

        async def __aexit__(self, *_args):
            return None

    class Pool:
        def acquire(self):
            return Acquire()

    async def accepted() -> None:
        async with worker._single_worker_lease(Pool()):
            calls.append("owned")

    asyncio.run(accepted())
    assert calls == ["lock", "owned", "unlock"]

    calls.clear()

    class RejectedConnection(Connection):
        async def fetchval(self, query: str, name: str) -> bool:
            assert "pg_try_advisory_lock" in query
            assert name == worker._WORKER_LEASE_NAME
            calls.append("rejected")
            return False

    class RejectedAcquire(Acquire):
        async def __aenter__(self):
            return RejectedConnection()

    class RejectedPool(Pool):
        def acquire(self):
            return RejectedAcquire()

    async def rejected() -> None:
        async with worker._single_worker_lease(RejectedPool()):
            raise AssertionError("a second worker must not start")

    with pytest.raises(RuntimeError, match="already owns the lease"):
        asyncio.run(rejected())
    assert calls == ["rejected"]


@pytest.mark.parametrize(
    ("request_timeout", "lease_timeout"),
    [(11, 11), (11, 10), (0, 17), (11, 0), (True, 17), (11, True)],
)
def test_topic_influence_lease_strictly_exceeds_request(
    request_timeout: object, lease_timeout: object
) -> None:
    """The declared lease retains time for persistence after request return."""
    settings = SimpleNamespace(
        topic_influence_request_timeout_seconds=request_timeout,
        topic_influence_lease_timeout_seconds=lease_timeout,
        topic_influence_poll_seconds=13,
    )

    with pytest.raises(ValueError, match="strictly greater"):
        worker._topic_influence_timeouts(settings)


def test_invalid_optional_topic_influence_config_is_isolated() -> None:
    """Invalid optional measurement config cannot stop unrelated consumers."""
    settings = SimpleNamespace(
        topic_influence_request_timeout_seconds=11,
        topic_influence_lease_timeout_seconds=11,
        topic_influence_poll_seconds=13,
    )

    assert worker._optional_topic_influence_timeouts(settings, configured=True) is None


@pytest.mark.parametrize("poll_seconds", [None, 0, -1, 1.5, True])
def test_topic_influence_poll_interval_must_be_declared(
    poll_seconds: object,
) -> None:
    """Claim retries cannot use an invented or invalid polling interval."""
    settings = SimpleNamespace(
        topic_influence_request_timeout_seconds=11,
        topic_influence_lease_timeout_seconds=17,
        topic_influence_poll_seconds=poll_seconds,
    )

    with pytest.raises(ValueError, match="poll interval"):
        worker._topic_influence_timeouts(settings)


async def _async_value(value):
    """Return one test double through an awaitable seam."""
    return value
