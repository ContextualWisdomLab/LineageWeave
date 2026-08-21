"""Application-owned MCP API-key lifecycle behind Keyverse OIDC identity.

Keyverse authenticates the account. LineageWeave stores only a digest of the
random application key and returns the raw value once at creation time.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

import asyncpg
from pydantic import BaseModel

KEY_PREFIX = "lw_mcp_"


class CreateMcpApiKeyRequest(BaseModel):
    """Buyer-supplied label and optional expiry for one MCP key."""

    display_name: str
    expires_at: datetime | None = None


def _hash_api_key(raw_key: str) -> str:
    """Return the non-reversible digest persisted for ``raw_key``."""
    return hashlib.sha256(raw_key.encode("ascii")).hexdigest()


def _serialize_key(row: asyncpg.Record) -> dict[str, Any]:
    """Serialize metadata without exposing a stored digest."""
    return {
        "mcp_api_key_id": str(row["mcp_api_key_id"]),
        "display_name": row["display_name"],
        "key_prefix": row["key_prefix"],
        "created_at": row["created_at"].isoformat(),
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] is not None else None,
        "revoked_at": row["revoked_at"].isoformat() if row["revoked_at"] is not None else None,
    }


def _validated_request(request: CreateMcpApiKeyRequest) -> tuple[str, datetime | None]:
    """Normalize the label and reject expired or timezone-less input."""
    display_name = request.display_name.strip()
    if not display_name or len(display_name) > 120:
        raise ValueError("display_name must contain 1 to 120 non-space characters")
    expires_at = request.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")
        if expires_at <= datetime.now(UTC):
            raise ValueError("expires_at must be in the future")
    return display_name, expires_at


async def create_mcp_api_key(
    conn: asyncpg.Connection,
    user_account_id: str,
    request: CreateMcpApiKeyRequest,
) -> dict[str, Any]:
    """Create one key and return its raw secret exactly once."""
    display_name, expires_at = _validated_request(request)
    raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    row = await conn.fetchrow(
        """
        insert into mcp_api_key (user_account_id, display_name, key_prefix, key_hash, expires_at)
        values ($1, $2, $3, $4, $5)
        returning mcp_api_key_id, display_name, key_prefix, created_at, expires_at, revoked_at
        """,
        user_account_id,
        display_name,
        KEY_PREFIX,
        _hash_api_key(raw_key),
        expires_at,
    )
    if row is None:
        raise RuntimeError("MCP API key insert returned no row")
    return {**_serialize_key(row), "api_key": raw_key}


async def list_mcp_api_keys(conn: asyncpg.Connection, user_account_id: str) -> list[dict[str, Any]]:
    """List one account's metadata without returning any secret material."""
    rows = await conn.fetch(
        """
        select mcp_api_key_id, display_name, key_prefix, created_at, expires_at, revoked_at
          from mcp_api_key
         where user_account_id = $1
         order by created_at desc, mcp_api_key_id
        """,
        user_account_id,
    )
    return [_serialize_key(row) for row in rows]


async def revoke_mcp_api_key(
    conn: asyncpg.Connection,
    user_account_id: str,
    mcp_api_key_id: str,
) -> dict[str, Any] | None:
    """Revoke an owned key; return ``None`` for an unknown or foreign key."""
    row = await conn.fetchrow(
        """
        update mcp_api_key
           set revoked_at = coalesce(revoked_at, now())
         where mcp_api_key_id = $1 and user_account_id = $2
        returning mcp_api_key_id, display_name, key_prefix, created_at, expires_at, revoked_at
        """,
        mcp_api_key_id,
        user_account_id,
    )
    return _serialize_key(row) if row is not None else None


async def resolve_mcp_api_key(
    conn: asyncpg.Connection,
    raw_key: str,
) -> dict[str, str] | None:
    """Resolve a live raw key to its owning account for an MCP adapter."""
    if not raw_key.startswith(KEY_PREFIX):
        return None
    row = await conn.fetchrow(
        """
        select key.mcp_api_key_id, key.user_account_id, account.display_name
          from mcp_api_key key
          join user_account account on account.user_account_id = key.user_account_id
         where key.key_hash = $1
           and key.revoked_at is null
           and (key.expires_at is null or key.expires_at > now())
        """,
        _hash_api_key(raw_key),
    )
    if row is None:
        return None
    return {
        "mcp_api_key_id": str(row["mcp_api_key_id"]),
        "user_account_id": str(row["user_account_id"]),
        "display_name": row["display_name"],
    }
