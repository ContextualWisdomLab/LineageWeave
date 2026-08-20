"""Hash-only API keys for non-OIDC MCP clients.

Key management is authorized by the Keyverse-backed OIDC account. The raw
key is returned only at issuance; database rows contain only a SHA-256 digest.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

API_KEY_PREFIX = "lw_mcp_"
API_KEY_SCOPE = "mcp:read"


@dataclass(frozen=True)
class IssuedApiKey:
    value: str
    key_prefix: str
    secret_digest: str


@dataclass(frozen=True)
class ApiKeyPrincipal:
    api_client_key_id: str
    user_account_id: str
    scopes: frozenset[str]


def digest_api_key(value: str) -> str:
    """Return the non-reversible lookup digest for an issued key."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_api_key() -> IssuedApiKey:
    """Create a high-entropy key whose value is never persisted by callers."""
    value = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return IssuedApiKey(
        value=value,
        key_prefix=value[: len(API_KEY_PREFIX) + 8],
        secret_digest=digest_api_key(value),
    )


async def resolve_mcp_api_key(conn: Any, value: str) -> ApiKeyPrincipal | None:
    """Resolve an active MCP key and touch its last-used timestamp.

    This narrow resolver is the handoff seam for an MCP transport. It is not
    a general bearer-token fallback, so an MCP key cannot authenticate the
    ordinary OIDC-protected product routes.
    """
    if not value.startswith(API_KEY_PREFIX):
        return None
    rows = await conn.fetch(
        """
        select key.api_client_key_id,
               key.user_account_id,
               scope.scope_code
          from api_client_key key
          join api_client_key_scope scope
            on scope.api_client_key_id = key.api_client_key_id
          join account_role_assignment assignment
            on assignment.user_account_id = key.user_account_id
          join role_permission permission
            on permission.access_role_id = assignment.access_role_id
         where key.secret_digest = $1
           and key.revoked_at is null
           and (key.expires_at is null or key.expires_at > now())
           and permission.permission_code = 'post_read'
        """,
        digest_api_key(value),
    )
    if not rows:
        return None
    key_id = str(rows[0]["api_client_key_id"])
    await conn.execute(
        "update api_client_key set last_used_at = now() where api_client_key_id = $1",
        rows[0]["api_client_key_id"],
    )
    return ApiKeyPrincipal(
        api_client_key_id=key_id,
        user_account_id=str(rows[0]["user_account_id"]),
        scopes=frozenset(row["scope_code"] for row in rows),
    )
