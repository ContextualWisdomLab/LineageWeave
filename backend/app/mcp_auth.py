"""OAuth resource-server token verification for the LineageWeave MCP endpoint."""

from __future__ import annotations

import asyncio
import hashlib
from functools import partial
from typing import Any

import asyncpg
from fastapi import HTTPException
from mcp.server.auth.provider import AccessToken, TokenVerifier

from backend.app.auth import decode_access_token
from backend.app.config import Settings


def _scopes_from_claim(claim: Any) -> list[str]:
    """Normalize Keycloak's string or array scope claim without inventing scopes."""
    if isinstance(claim, str):
        return [scope for scope in claim.split() if scope]
    if isinstance(claim, list):
        return [scope for scope in claim if isinstance(scope, str) and scope]
    return []


class KeycloakMcpTokenVerifier(TokenVerifier):
    """Validate a Keycloak/Keyverse JWT for the exact MCP resource audience."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_key_pool: Any | None = None

    def bind_api_key_pool(self, pool: Any) -> None:
        """Bind the process-lifetime pool used by LineageWeave API keys."""
        self._api_key_pool = pool

    def unbind_api_key_pool(self, pool: Any) -> None:
        """Release the pool only when it is the currently bound instance."""
        if self._api_key_pool is pool:
            self._api_key_pool = None

    async def _verify_api_key(self, token: str) -> AccessToken | None:
        """Resolve one hashed application key to its provisioned account subject."""
        if self._api_key_pool is None:
            return None
        key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        try:
            row = await self._api_key_pool.fetchrow(
                """
                select api_key.mcp_api_key_id,
                       api_key.user_account_id,
                       account.external_subject_id,
                       extract(epoch from api_key.expires_at) as expires_at
                  from mcp_api_key api_key
                  join user_account account
                    on account.user_account_id = api_key.user_account_id
                 where api_key.key_hash = $1
                   and api_key.revoked_at is null
                   and (api_key.expires_at is null or api_key.expires_at > now())
                """,
                key_hash,
            )
        except asyncpg.UndefinedTableError:
            # The key-management stack may be deployed after this MCP stack.
            return None
        if row is None:
            return None
        subject = row["external_subject_id"]
        if not isinstance(subject, str) or not subject:
            return None
        expires_at = row["expires_at"]
        return AccessToken(
            token=token,
            client_id="lineageweave-mcp-api-key",
            scopes=list(self._settings.mcp_required_scopes),
            expires_at=int(expires_at) if expires_at is not None else None,
            resource=self._settings.mcp_audience,
            subject=subject,
            claims={
                "auth_method": "mcp_api_key",
                "mcp_api_key_id": str(row["mcp_api_key_id"]),
                "user_account_id": str(row["user_account_id"]),
            },
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return MCP access metadata for a valid token; otherwise fail closed."""
        if token.startswith("lw_mcp_"):
            return await self._verify_api_key(token)
        try:
            claims = await asyncio.to_thread(
                partial(
                    decode_access_token,
                    token,
                    self._settings,
                    audience=self._settings.mcp_audience,
                )
            )
        except HTTPException:
            return None
        subject = claims.get("sub")
        client_id = claims.get("azp") or claims.get("client_id")
        expires_at = claims.get("exp")
        if not isinstance(subject, str) or not subject or not isinstance(client_id, str) or not client_id:
            return None
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=_scopes_from_claim(claims.get("scope")),
            expires_at=int(expires_at) if isinstance(expires_at, (int, float)) else None,
            resource=self._settings.mcp_audience,
            subject=subject,
            claims={"iss": claims.get("iss"), "aud": claims.get("aud")},
        )
