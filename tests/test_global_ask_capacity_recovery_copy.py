"""Buyer-action contract for Global Ask active-capacity rejection."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app import global_ask_service
from backend.app.auth import CurrentAccount
from backend.app.global_ask_queue import GlobalAskOutstandingLimitExceeded


class _Acquire:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    async def __aenter__(self) -> object:
        return self.connection

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _Pool:
    def acquire(self) -> _Acquire:
        return _Acquire(object())


def _account() -> CurrentAccount:
    return CurrentAccount(
        "00000000-0000-0000-0000-000000000001",
        "subject-1",
        "Analyst",
        None,
        frozenset({"entity-1"}),
        frozenset({"unit-1"}),
        frozenset({"post_read"}),
    )


@pytest.mark.anyio
async def test_active_capacity_rejection_names_only_an_available_recovery_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not advertise cancellation until the product exposes a cancel command."""

    async def reject(*_args: object, **_kwargs: object) -> str:
        raise GlobalAskOutstandingLimitExceeded

    monkeypatch.setattr(global_ask_service, "enqueue_global_ask_job", reject)

    with pytest.raises(HTTPException) as caught:
        await global_ask_service.submit_global_ask(
            pool=_Pool(),
            valkey=object(),
            account=_account(),
            question="What changed?",
            verify_external=False,
            knowledge_cutoff=None,
            service_available=True,
            question_max_bytes=1024,
            max_outstanding_jobs=1,
            quota_request_limit=10,
            quota_window_seconds=60,
            quota_already_consumed=True,
        )

    assert caught.value.status_code == 429
    detail = str(caught.value.detail).lower()
    assert "cancel" not in detail
    assert "finish" in detail or "wait" in detail
