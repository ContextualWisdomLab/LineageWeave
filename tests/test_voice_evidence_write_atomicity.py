"""Transaction contract for authorization-sensitive Voice assignment writes."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.auth import CurrentAccount


class _FakeConnection:
    """Expose whether the endpoint owns a transaction across its write boundary."""

    def __init__(self) -> None:
        self.transaction_depth = 0

    @asynccontextmanager
    async def transaction(self):
        self.transaction_depth += 1
        try:
            yield
        finally:
            self.transaction_depth -= 1


class _FakePool:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def test_voice_assignment_reauthorization_shares_the_write_transaction(monkeypatch):
    """A post-write 409 must still be able to roll back the candidate assignment."""
    connection = _FakeConnection()
    observations: list[tuple[str, bool]] = []

    async def visible_post(*_args, **_kwargs):
        return {"post_id": "synthetic"}

    async def persist(conn, **_kwargs):
        observations.append(("persist", conn.transaction_depth > 0))

    async def reload(conn, *_args, **_kwargs):
        observations.append(("reauthorize", conn.transaction_depth > 0))
        return []

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "persist_additional_voice_assignment", persist)
    monkeypatch.setattr(main, "_load_post_voice_types", reload)

    account = CurrentAccount(
        str(uuid4()),
        "synthetic-subject",
        "Synthetic reviewer",
        None,
        frozenset(),
        frozenset(),
        frozenset({"post_admin"}),
    )
    request = main.CreatePostVoiceAssignmentRequest(
        voice_type_code="vops",
        truth_status_code="truth_proposed",
        evidence_post_id=uuid4(),
    )

    async def exercise() -> None:
        with pytest.raises(HTTPException) as exc_info:
            await main.create_post_voice_assignment(
                str(uuid4()),
                request,
                account=account,
                pool=_FakePool(connection),
                valkey=object(),
            )
        assert exc_info.value.status_code == 409

    asyncio.run(exercise())

    assert observations == [("persist", True), ("reauthorize", True)]
