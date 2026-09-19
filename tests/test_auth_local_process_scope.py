"""Local OIDC authorization must preserve the DB-owned process-unit boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.app.auth import resolve_current_account
from backend.app.post_eligibility import source_post_visible


class _Connection:
    """Minimal asyncpg-shaped connection for the account-resolution contract."""

    def __init__(self, affiliation_rows: list[dict[str, str | None]]) -> None:
        self.affiliation_rows = affiliation_rows

    async def fetchrow(self, query: str, *args: object):
        assert "from user_account" in query
        assert args == ("local-subject",)
        return {
            "user_account_id": "account-1",
            "display_name": "Local Viewer",
            "preferred_locale": "ko",
        }

    async def fetch(self, query: str, *args: object):
        assert args == ("account-1",)
        if "from account_affiliation" in query:
            return self.affiliation_rows
        if "permission_code" in query:
            return [{"permission_code": "post_read"}]
        raise AssertionError(f"unexpected account-resolution query: {query}")


class _Acquire:
    """Async context manager returned by ``Pool.acquire``."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _Connection:
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class _Pool:
    """Minimal asyncpg-shaped pool for deterministic authorization tests."""

    def __init__(self, affiliation_rows: list[dict[str, str | None]]) -> None:
        self.connection = _Connection(affiliation_rows)

    def acquire(self) -> _Acquire:
        return _Acquire(self.connection)


def _resolve(affiliation_rows: list[dict[str, str | None]]):
    settings = SimpleNamespace(keyverse_claim_binding_required=False)
    return asyncio.run(
        resolve_current_account(
            _Pool(affiliation_rows), {"sub": "local-subject"}, settings
        )
    )


def test_local_oidc_account_keeps_db_process_unit_scope() -> None:
    """A PU-scoped local subject must not silently become corporate-wide."""
    account = _resolve(
        [{"corporate_entity_id": "corp-1", "process_unit_id": "pu-1"}]
    )

    assert account.corporate_entity_ids == frozenset({"corp-1"})
    assert account.process_unit_ids == frozenset({"pu-1"})
    assert account.permission_codes == frozenset({"post_read"})
    assert not source_post_visible(
        {
            "visibility_code": "private",
            "corporate_entity_id": "corp-1",
            "process_unit_id": "pu-2",
        },
        account.corporate_entity_ids,
        account.process_unit_ids,
    )


def test_local_oidc_null_process_affiliation_remains_corporate_wide() -> None:
    """An explicit NULL PU affiliation keeps the existing corporate-wide meaning."""
    account = _resolve(
        [
            {"corporate_entity_id": "corp-1", "process_unit_id": None},
            {"corporate_entity_id": "corp-1", "process_unit_id": "pu-1"},
        ]
    )

    assert account.corporate_entity_ids == frozenset({"corp-1"})
    assert account.process_unit_ids == frozenset()
    assert source_post_visible(
        {
            "visibility_code": "private",
            "corporate_entity_id": "corp-1",
            "process_unit_id": "pu-2",
        },
        account.corporate_entity_ids,
        account.process_unit_ids,
    )
