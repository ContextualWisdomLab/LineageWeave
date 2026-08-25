"""OAuth resource-server token verification for LineageWeave MCP."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

from fastapi import HTTPException
from mcp.server.auth.provider import AccessToken, TokenVerifier

from backend.app.auth import decode_access_token
from backend.app.config import Settings


def _scopes_from_claim(claim: Any) -> list[str]:
    """Normalize string or array scope claims without inventing scopes."""
    if isinstance(claim, str):
        return [scope for scope in claim.split() if scope]
    if isinstance(claim, list):
        return [scope for scope in claim if isinstance(scope, str) and scope]
    return []


class KeyverseMcpTokenVerifier(TokenVerifier):
    """Validate a JWT for the exact configured MCP resource audience."""

    def __init__(self, settings: Settings) -> None:
        """Retain immutable identity and MCP audience settings."""
        self._settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return MCP access metadata for a valid token; otherwise fail closed."""
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
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(client_id, str)
            or not client_id
        ):
            return None
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=_scopes_from_claim(claims.get("scope")),
            expires_at=int(expires_at)
            if isinstance(expires_at, (int, float))
            else None,
            resource=self._settings.mcp_audience,
            subject=subject,
            claims=claims,
        )
