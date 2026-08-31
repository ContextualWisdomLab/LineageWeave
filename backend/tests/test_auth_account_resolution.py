"""Account-scope resolution query tests."""

import asyncio
from types import SimpleNamespace

import pytest

from backend.app.auth import resolve_current_account


class _Connection:
    """Capture the single account projection query."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
        """Return one fully projected account row."""
        self.calls.append((query, args))
        return {
            "user_account_id": "account-1",
            "display_name": "Synthetic Analyst",
            "preferred_locale": "ko",
            "corporate_entity_ids": ["entity-1"],
            "process_unit_ids": ["unit-1"],
            "permission_codes": ["post_read"],
        }


class _Acquire:
    """Provide an async pool-acquire context."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _Connection:
        """Return the captured connection."""
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        """Leave the synthetic connection open."""


class _Pool:
    """Minimal pool used by account resolution."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    def acquire(self) -> _Acquire:
        """Return one acquisition context."""
        return _Acquire(self.connection)


@pytest.mark.parametrize("keyverse_required", [False, True])
def test_account_scope_uses_one_database_round_trip(keyverse_required: bool) -> None:
    """Account identity, scope, and permissions resolve in one query."""
    connection = _Connection()
    claims = {"sub": "subject-1"}
    if keyverse_required:
        claims.update({"org": "ORG", "workspace": "PU", "role": ["member"]})

    account = asyncio.run(
        resolve_current_account(
            _Pool(connection),  # type: ignore[arg-type]
            claims,
            SimpleNamespace(keyverse_claim_binding_required=keyverse_required),  # type: ignore[arg-type]
        )
    )

    assert len(connection.calls) == 1
    assert account.corporate_entity_ids == frozenset({"entity-1"})
    assert account.process_unit_ids == frozenset({"unit-1"})
    assert account.permission_codes == frozenset({"post_read"})
