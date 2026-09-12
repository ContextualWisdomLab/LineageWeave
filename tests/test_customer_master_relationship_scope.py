from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from backend.app import main
from backend.app.auth import CurrentAccount


class EmptyConnection:
    """Minimal asyncpg-shaped connection for caller-scope wiring tests."""

    async def fetch(self, _sql: str, *_args: Any) -> list[dict[str, Any]]:
        """Return no source rows so only relationship-scope forwarding is observed."""
        return []


class AcquireConnection:
    """Async context manager exposing one deterministic test connection."""

    def __init__(self, conn: EmptyConnection) -> None:
        """Retain the connection returned by the fake pool acquisition."""
        self.conn = conn

    async def __aenter__(self) -> EmptyConnection:
        """Return the retained connection on context entry."""
        return self.conn

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        """Leave the fake acquisition context without suppressing failures."""
        return None


class EmptyPool:
    """Pool double that preserves one connection across the application call."""

    def __init__(self) -> None:
        """Create the connection observed by the application boundary."""
        self.conn = EmptyConnection()

    def acquire(self) -> AcquireConnection:
        """Return an async acquisition wrapper for the retained connection."""
        return AcquireConnection(self.conn)


def test_customer_master_passes_authenticated_process_scope(monkeypatch) -> None:
    """Customer Master must forward the authenticated process-unit scope unchanged."""
    account = CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000001",
        external_subject_id="scope-test",
        display_name="Scope Test",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"00000000-0000-0000-0000-000000000010"}),
        process_unit_ids=frozenset({"00000000-0000-0000-0000-000000000020"}),
        permission_codes=frozenset({"post_read"}),
    )
    observed: dict[str, object] = {}

    async def no_real_source_context(_conn: object, _entity_ids: list[str]) -> bool:
        """Keep the test on the relationship-network scope-forwarding path."""
        return False

    async def no_labels(_conn: object, _codes: list[str]) -> dict[str, str]:
        """Avoid unrelated lookup-label data in the returned read model."""
        return {}

    async def capture_relationship_network(
        _conn: object,
        corporate_entity_ids: list[object],
        process_unit_ids: Iterable[str],
    ) -> list[dict[str, Any]]:
        """Capture both scopes exactly as the application passes them downstream."""
        observed["corporate_entity_ids"] = corporate_entity_ids
        observed["process_unit_ids"] = frozenset(process_unit_ids)
        return []

    monkeypatch.setattr(main, "has_real_source_context", no_real_source_context)
    monkeypatch.setattr(main, "labels_for_codes", no_labels)
    monkeypatch.setattr(main, "fetch_relationship_network", capture_relationship_network)

    payload = asyncio.run(main.read_customer_master(account=account, pool=EmptyPool()))

    assert payload["relationship_network"] == []
    assert observed == {
        "corporate_entity_ids": [],
        "process_unit_ids": account.process_unit_ids,
    }
