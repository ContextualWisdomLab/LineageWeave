"""Transport-parity tests for the durable Global Ask application service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException

from backend.app import global_ask_service
from backend.app.auth import CurrentAccount


class Acquire:
    """Async context manager for a fake database connection."""

    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        """Return the configured connection."""
        return self.connection

    async def __aexit__(self, *_args):
        """Leave without suppressing exceptions."""
        return False


class Pool:
    """Expose one deterministic connection through acquire()."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def acquire(self):
        """Return the async connection context."""
        return Acquire(self.connection)


class Connection:
    """Return a fixed database clock and optional job row."""

    def __init__(self, row=None) -> None:
        self.row = row

    async def fetchval(self, _sql):
        """Return a stable UTC database clock."""
        return datetime(2026, 8, 26, tzinfo=UTC)

    async def fetchrow(self, _sql, _job_id):
        """Return the configured job row."""
        return self.row


def account(*, permitted=True) -> CurrentAccount:
    """Build one synthetic provisioned account."""
    return CurrentAccount(
        "account-1",
        "subject-1",
        "Analyst",
        None,
        frozenset({"entity-1"}),
        frozenset({"unit-1"}),
        frozenset({"post_read"}) if permitted else frozenset(),
    )


@pytest.mark.anyio
async def test_submit_normalizes_and_forwards_current_contract(monkeypatch) -> None:
    """Submission passes the exact current scope, cutoff, and opt-in once."""
    calls = []

    async def enqueue(*args, **kwargs):
        calls.append((args, kwargs))
        return UUID("00000000-0000-0000-0000-000000000123")

    monkeypatch.setattr(global_ask_service, "enqueue_global_ask_job", enqueue)
    result = await global_ask_service.submit_global_ask(
        pool=Pool(Connection()),
        valkey=object(),
        account=account(),
        question="  What changed? ",
        verify_external=True,
        knowledge_cutoff="2026-08-25T00:00:00Z",
        service_available=True,
    )
    assert result["job_status_code"] == "queued"
    assert calls[0][1]["question_text"] == "What changed?"
    assert calls[0][1]["corporate_entity_ids"] == frozenset({"entity-1"})
    assert calls[0][1]["process_unit_ids"] == frozenset({"unit-1"})


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("kwargs", "status_code"),
    [
        ({"question": " "}, 422),
        ({"question": "x", "knowledge_cutoff": "bad"}, 422),
        ({"question": "x", "knowledge_cutoff": "2026-08-27T00:00:00Z"}, 422),
        ({"question": "x", "service_available": False}, 503),
    ],
)
async def test_submit_fails_before_enqueue(monkeypatch, kwargs, status_code) -> None:
    """Invalid or unavailable submission states never enqueue work."""

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("enqueue must not run")

    monkeypatch.setattr(global_ask_service, "enqueue_global_ask_job", forbidden)
    values = {
        "question": "x",
        "verify_external": False,
        "knowledge_cutoff": None,
        "service_available": True,
    }
    values.update(kwargs)
    with pytest.raises(HTTPException) as caught:
        await global_ask_service.submit_global_ask(
            pool=Pool(Connection()), valkey=object(), account=account(), **values
        )
    assert caught.value.status_code == status_code


@pytest.mark.anyio
async def test_permission_and_owner_scope_fail_closed() -> None:
    """Both operations enforce permission and non-enumerable ownership."""
    with pytest.raises(HTTPException) as denied:
        await global_ask_service.read_global_ask_job(
            pool=Pool(Connection()),
            account=account(permitted=False),
            ask_job_id=UUID(int=1),
        )
    assert denied.value.status_code == 403
    row = {
        "requesting_account_id": "other",
        "job_status_code": "queued",
        "answer_payload": None,
        "failure_detail": None,
    }
    with pytest.raises(HTTPException) as absent:
        await global_ask_service.read_global_ask_job(
            pool=Pool(Connection(row)), account=account(), ask_job_id=UUID(int=1)
        )
    assert absent.value.status_code == 404
    with pytest.raises(HTTPException) as submit_denied:
        await global_ask_service.submit_global_ask(
            pool=Pool(Connection()),
            valkey=object(),
            account=account(permitted=False),
            question="question",
            verify_external=False,
            knowledge_cutoff=None,
            service_available=True,
        )
    assert submit_denied.value.status_code == 403


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            {
                "requesting_account_id": "account-1",
                "job_status_code": "succeeded",
                "answer_payload": '{"answer_text":"ok"}',
                "failure_detail": None,
            },
            {"answer": {"answer_text": "ok"}},
        ),
        (
            {
                "requesting_account_id": "account-1",
                "job_status_code": "failed",
                "answer_payload": None,
                "failure_detail": "unavailable",
            },
            {"failure_detail": "unavailable"},
        ),
    ],
)
async def test_read_preserves_persisted_terminal_payload(row, expected) -> None:
    """Reading adds no second semantic interpretation."""
    result = await global_ask_service.read_global_ask_job(
        pool=Pool(Connection(row)), account=account(), ask_job_id=UUID(int=1)
    )
    assert result | expected == result
