"""OIDC-validated login. A bearer access token is verified against
Keycloak's own live JWKS (real signature verification, not a shared-secret
shortcut) and resolved to a user_account row via external_subject_id --
corp_code/pu_code are attributes read from the DB's account_affiliation,
never trusted directly off the token, per the schema's design (see
migrations/0001_initial_schema.sql).

JWKS is fetched through ``lineageweave.http_client.get_json`` (http(s)
allowlist) so a mis-set KEYCLOAK_BASE_URL cannot become a file-scheme read.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import asyncpg
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm

from backend.app.config import Settings, load_settings
from backend.app.db import get_pool
from lineageweave.http_client import HttpClientError, get_json

_bearer_scheme = HTTPBearer(auto_error=True)
_jwks_cache: dict[str, dict[str, Any]] = {}


class _SigningKeyNotFound(ValueError):
    """No unique RSA signing key matches a structurally valid token header."""


def _jwks(settings: Settings) -> dict[str, Any]:
    """Return the realm JWKS, cached per URI for the process lifetime."""
    cached = _jwks_cache.get(settings.keycloak_jwks_uri)
    if cached is None:
        try:
            payload = get_json(settings.keycloak_jwks_uri, timeout=10)
        except (HttpClientError, OSError, ValueError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"could not fetch JWKS from {settings.keycloak_jwks_uri}: {exc}",
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "issuer JWKS is not an object")
        cached = payload
        _jwks_cache[settings.keycloak_jwks_uri] = cached
    return cached


def _signing_key_from_jwks(jwks: dict[str, Any], token: str):
    """Return the sole RSA signing key matching the token's mandatory ``kid``."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token header: {exc}") from exc
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token: missing kid")
    matches = [
        key
        for key in jwks.get("keys", [])
        if isinstance(key, dict)
        and key.get("kid") == kid
        and key.get("kty") == "RSA"
        and key.get("use") in {None, "sig"}
    ]
    if len(matches) != 1:
        raise _SigningKeyNotFound(f"expected one RSA signing key for kid={kid!r}")
    try:
        return RSAAlgorithm.from_jwk(json.dumps(matches[0]))
    except (KeyError, TypeError, ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token signing key") from exc


def decode_access_token(
    token: str,
    settings: Settings,
    *,
    audience: str | None = None,
) -> dict[str, Any]:
    """Validate signature, issuer, time claims, and an optional resource audience."""
    try:
        try:
            signing_key = _signing_key_from_jwks(_jwks(settings), token)
        except _SigningKeyNotFound:
            # A new issuer key may have appeared after this process cached JWKS.
            # Refresh exactly once; persistent ambiguity/miss is still a 401.
            _jwks_cache.pop(settings.keycloak_jwks_uri, None)
            try:
                signing_key = _signing_key_from_jwks(_jwks(settings), token)
            except _SigningKeyNotFound as exc:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}"
                ) from exc
        return jwt.decode(
            token,
            key=signing_key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            audience=audience,
            options={"verify_aud": audience is not None},
        )
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc


def _decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Backward-compatible REST decoder; MCP uses an exact audience instead."""
    return decode_access_token(token, settings)


@dataclass(frozen=True)
class CurrentAccount:
    """The provisioned account that a verified access token resolved to."""

    user_account_id: str
    external_subject_id: str
    display_name: str
    corporate_entity_ids: frozenset[str]
    permission_codes: frozenset[str]

    def has_permission(self, permission_code: str) -> bool:
        """True when one of the account's roles grants ``permission_code``."""
        return permission_code in self.permission_codes


async def resolve_current_account(pool: asyncpg.Pool, subject: str) -> CurrentAccount:
    """Resolve one verified subject to DB-owned affiliations and permissions."""
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token has no subject")
    async with pool.acquire() as conn:
        account_row = await conn.fetchrow(
            "select user_account_id, display_name from user_account where external_subject_id = $1",
            subject,
        )
        if account_row is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "token is valid but no user_account is provisioned for this subject "
                "(run scripts/seed_demo_data.py, or provision the account, first)",
            )
        entity_rows = await conn.fetch(
            "select corporate_entity_id from account_affiliation where user_account_id = $1",
            account_row["user_account_id"],
        )
        permission_rows = await conn.fetch(
            """
            select distinct rp.permission_code
            from account_role_assignment ara
            join role_permission rp on rp.access_role_id = ara.access_role_id
            where ara.user_account_id = $1
            """,
            account_row["user_account_id"],
        )
    return CurrentAccount(
        user_account_id=str(account_row["user_account_id"]),
        external_subject_id=subject,
        display_name=account_row["display_name"],
        corporate_entity_ids=frozenset(str(row["corporate_entity_id"]) for row in entity_rows),
        permission_codes=frozenset(str(row["permission_code"]) for row in permission_rows),
    )


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    pool: asyncpg.Pool = Depends(get_pool),
) -> CurrentAccount:
    """Resolve the REST bearer token to a provisioned ``user_account`` row."""
    settings = load_settings()
    claims = _decode_access_token(credentials.credentials, settings)
    subject = claims.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token has no subject")
    return await resolve_current_account(pool, subject)