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


def test_answer_completion_drains_inflight_claim_renewal(monkeypatch) -> None:
    """A committed renewal must reach settlement even if the answer finishes first."""
    renewal_started = asyncio.Event()
    answer_finished = asyncio.Event()
    renewal_cancelled = asyncio.Event()
    original_generation = object()
    committed_generation = object()
    lease = [original_generation]

    async def renew(*_args):
        renewal_started.set()
        try:
            await answer_finished.wait()
            # Model the DB driver's response arriving after the committed UPDATE.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return committed_generation
        except asyncio.CancelledError:
            renewal_cancelled.set()
            raise

    async def operation():
        await renewal_started.wait()
        answer_finished.set()
        return "completed answer"

    async def exercise():
        monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 0.001)
        monkeypatch.setattr(global_ask_queue, "_renew_ask_claim", renew)
        result = await global_ask_queue._run_with_ask_claim_heartbeat(
            object(), "job-renewal-race", lease, operation()
        )
        assert result == "completed answer"
        assert not renewal_cancelled.is_set()
        assert lease[0] is committed_generation

    asyncio.run(exercise())


def test_simultaneous_answer_and_failed_renewal_rejects_answer(monkeypatch) -> None:
    """An answer cannot hide a renewal failure in the same event-loop turn."""
    renewal_started = asyncio.Event()
    answer_finished = asyncio.Event()

    async def renew(*_args):
        renewal_started.set()
        await answer_finished.wait()
        raise RuntimeError("renewal result unavailable")

    async def operation():
        await renewal_started.wait()
        answer_finished.set()
        return "answer without confirmed ownership"

    async def exercise():
        monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 0.001)
        monkeypatch.setattr(global_ask_queue, "_renew_ask_claim", renew)
        with pytest.raises(global_ask_queue._LostAskClaim):
            await global_ask_queue._run_with_ask_claim_heartbeat(
                object(), "job-simultaneous-completion", [object()], operation()
            )

    asyncio.run(exercise())


def test_owner_cancellation_interrupts_completion_drain(monkeypatch) -> None:
    """Draining a renewal never detaches it from native owner cancellation."""
    renewal_started = asyncio.Event()
    renewal_cancelled = asyncio.Event()
    answer_finished = asyncio.Event()

    async def renew(*_args):
        renewal_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            renewal_cancelled.set()

    async def operation():
        await renewal_started.wait()
        answer_finished.set()
        return "completed answer"

    async def exercise():
        monkeypatch.setattr(global_ask_queue, "_CLAIM_HEARTBEAT_SECONDS", 0.001)
        monkeypatch.setattr(global_ask_queue, "_renew_ask_claim", renew)
        owner = asyncio.create_task(global_ask_queue._run_with_ask_claim_heartbeat(
            object(), "job-cancel-drain", [object()], operation()
        ))
        await answer_finished.wait()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert renewal_cancelled.is_set()

    asyncio.run(exercise())
