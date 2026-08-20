"""Security-focused tests for the Keyverse-authenticated MCP key boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.app.mcp_api_keys import (
    KEY_PREFIX,
    CreateMcpApiKeyRequest,
    create_mcp_api_key,
    list_mcp_api_keys,
    resolve_mcp_api_key,
    revoke_mcp_api_key,
)


class _Connection:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.fetchrow_args = None

    async def fetchrow(self, query: str, *args):
        self.fetchrow_args = (query, args)
        return self.row

    async def fetch(self, _query: str, *_args):
        return self.rows


def _row(*, revoked_at=None):
    now = datetime.now(UTC)
    return {
        "mcp_api_key_id": "key-id",
        "user_account_id": "account-id",
        "display_name": "automation",
        "key_prefix": f"{KEY_PREFIX}abc",
        "created_at": now,
        "expires_at": now + timedelta(days=30),
        "revoked_at": revoked_at,
    }


def test_create_returns_raw_secret_once_and_persists_only_digest() -> None:
    conn = _Connection(_row())
    created = asyncio.run(
        create_mcp_api_key(
            conn,
            "account-id",
            CreateMcpApiKeyRequest(display_name="  automation  ", expires_at=datetime.now(UTC) + timedelta(days=1)),
        )
    )

    assert created["api_key"].startswith(KEY_PREFIX)
    assert "key_hash" not in created
    assert conn.fetchrow_args is not None
    query, args = conn.fetchrow_args
    assert "insert into mcp_api_key" in query
    assert args[1] == "automation"
    assert len(args[3]) == 64
    assert args[3] != created["api_key"]


def test_list_never_returns_secret_or_digest() -> None:
    listed = asyncio.run(list_mcp_api_keys(_Connection(rows=[_row()]), "account-id"))
    assert listed[0]["display_name"] == "automation"
    assert "api_key" not in listed[0]
    assert "key_hash" not in listed[0]


def test_revoke_is_scoped_to_current_account() -> None:
    revoked = asyncio.run(revoke_mcp_api_key(_Connection(_row()), "account-id", "key-id"))
    assert revoked is not None
    foreign = asyncio.run(revoke_mcp_api_key(_Connection(None), "other-account", "key-id"))
    assert foreign is None


def test_resolve_rejects_non_mcp_key_and_returns_account_for_live_key() -> None:
    conn = _Connection(_row())
    assert asyncio.run(resolve_mcp_api_key(conn, "not-a-lineageweave-key")) is None
    resolved = asyncio.run(resolve_mcp_api_key(conn, f"{KEY_PREFIX}secret"))
    assert resolved == {"mcp_api_key_id": "key-id", "user_account_id": "account-id", "display_name": "automation"}


def test_schema_has_owner_foreign_key_and_no_secret_column() -> None:
    sql = (Path(__file__).parents[1] / "migrations" / "0051_mcp_api_keys.sql").read_text()
    assert "references user_account(user_account_id)" in sql
    assert "key_hash text" in sql
    assert "api_key text" not in sql
