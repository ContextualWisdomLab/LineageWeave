"""Unit contracts for the Buyer project-history HTTP boundary."""

from __future__ import annotations

import asyncio

from backend.app import main
from backend.app.auth import CurrentAccount


class _Acquire:
    """Minimal async context manager for a route-level database seam."""

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Pool:
    """Pool-shaped test double that does not create a database connection."""

    def acquire(self) -> _Acquire:
        return _Acquire()


def test_history_route_preserves_display_identity_case(monkeypatch) -> None:
    """Validation normalizes for matching but the buyer response keeps its key."""

    captured: dict[str, object] = {}

    async def fake_projection(connection, **kwargs):
        captured.update(kwargs)
        return {"project_key": kwargs["project_key"]}

    monkeypatch.setattr(main, "fetch_project_history_projection", fake_projection)
    account = CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Synthetic analyst",
        preferred_locale="en",
        corporate_entity_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )

    result = asyncio.run(
        main.read_project_history(
            project_key="P-100",
            focus_post_id=None,
            knowledge_cutoff=None,
            limit=64,
            account=account,
            pool=_Pool(),
        )
    )

    assert captured["project_key"] == "P-100"
    assert result["project_key"] == "P-100"
