"""Local OIDC authorization must preserve the DB-owned process-unit boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.app.auth import resolve_current_account


class _Connection:
    """Minimal asyncpg-shaped connection for the account-resolution contract."""

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
        if "corporate_entity_id" in query:
            return [{"corporate_entity_id": "corp-1"}]
        if "process_unit_id" in query:
            return [{"process_unit_id": "pu-1"}]
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

    def acquire(self) -> _Acquire:
        return _Acquire(_Connection())


def test_local_oidc_account_keeps_db_process_unit_scope() -> None:
    """Local Keycloak subjects must not become corporate-wide by losing PU scope."""
    settings = SimpleNamespace(keyverse_claim_binding_required=False)
    account = asyncio.run(
        resolve_current_account(_Pool(), {"sub": "local-subject"}, settings)
    )

    assert account.corporate_entity_ids == frozenset({"corp-1"})
    assert account.process_unit_ids == frozenset({"pu-1"})
    assert account.permission_codes == frozenset({"post_read"})
