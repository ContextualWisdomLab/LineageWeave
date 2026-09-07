"""Cancellation contracts for the Global Ask claim-heartbeat boundary."""

from __future__ import annotations

import asyncio

import pytest

from backend.app import global_ask_queue


def test_external_cancellation_reaches_active_ask_operation(monkeypatch) -> None:
    """Cancelling the owner task must not leave its Ask operation detached."""
    operation_started = asyncio.Event()
    operation_cancelled = asyncio.Event()

    async def operation() -> None:
        operation_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            operation_cancelled.set()

    async def exercise() -> None:
        monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 3600.0)
        owner = asyncio.create_task(
            global_ask_queue._run_with_ask_claim_heartbeat(
                object(),
                "job-1",
                [object()],
                operation(),
            )
        )
        await operation_started.wait()
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        await asyncio.sleep(0)
        assert operation_cancelled.is_set(), (
            "owner cancellation left compute_global_ask_answer detached from the "
            "claim heartbeat lifecycle"
        )

    asyncio.run(exercise())


def test_dead_heartbeat_aborts_live_ask_operation(monkeypatch) -> None:
    """A heartbeat that ends while compute is running must not keep the owner live."""
    operation_started = asyncio.Event()
    operation_cancelled = asyncio.Event()

    async def operation() -> str:
        operation_started.set()
        try:
            await asyncio.Event().wait()
            return "should-not-settle"
        finally:
            operation_cancelled.set()

    async def exploding_renew(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("heartbeat storage unavailable")

    async def exercise() -> None:
        monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 0.01)
        monkeypatch.setattr(global_ask_queue, "_renew_ask_claim", exploding_renew)
        owner = asyncio.create_task(
            global_ask_queue._run_with_ask_claim_heartbeat(
                object(),
                "job-heartbeat-dead",
                [object()],
                operation(),
            )
        )
        await operation_started.wait()
        with pytest.raises(global_ask_queue._LostAskClaim):
            await asyncio.wait_for(owner, timeout=1.0)
        await asyncio.sleep(0)
        assert operation_cancelled.is_set(), (
            "a dead claim heartbeat left compute_global_ask_answer running "
            "without renewals"
        )

    asyncio.run(exercise())
