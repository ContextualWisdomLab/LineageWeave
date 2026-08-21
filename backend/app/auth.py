"""OIDC-validated login. A bearer access token is verified against the
configured provider's live JWKS (Keyverse in production, local Keycloak in
Compose development; never a shared-secret shortcut) and resolved to a
user_account row via external_subject_id --
corp_code/pu_code are attributes read from the DB's account_affiliation,
never trusted directly off the token, per the schema's design (see
migrations/0001_initial_schema.sql).

JWKS is fetched through OIDC discovery or an explicit JWKS URI using
``lineageweave.http_client.get_json``. The HTTP client rejects non-http(s)
schemes, so provider configuration cannot become a file-scheme read.
"""

from __future__ import annotations

import asyncio
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
_jwks_cache: dict[tuple[str, str, str], dict] = {}


class _SigningKeyNotFound(HTTPException):
    """No unique acceptable RSA signing key matched the token header."""

    def __init__(self, detail: str) -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


def _jwks_cache_key(settings: Settings) -> tuple[str, str, str]:
    """Bind cached keys to the exact issuer and key-discovery configuration."""
    return (
        settings.oidc_issuer,
        settings.oidc_discovery_uri,
        settings.oidc_jwks_uri_override,
    )


def _jwks(settings: Settings, *, force_refresh: bool = False) -> dict[str, Any]:
    """Return provider JWKS, refreshing explicitly when signing keys rotate."""
    cache_key = _jwks_cache_key(settings)
    cached = None if force_refresh else _jwks_cache.get(cache_key)
    if cached is None:
        try:
            if settings.oidc_jwks_uri_override:
                jwks_uri = settings.oidc_jwks_uri_override
            else:
                metadata = get_json(settings.oidc_discovery_uri, timeout=10)
                jwks_uri = metadata.get("jwks_uri")
                if not isinstance(jwks_uri, str) or not jwks_uri.strip():
                    raise ValueError("OIDC discovery document has no jwks_uri")
            cached = get_json(jwks_uri, timeout=10)
        except (HttpClientError, OSError, ValueError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "could not fetch OIDC JWKS from the configured identity provider",
            ) from exc
        if not isinstance(cached, dict):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "issuer JWKS is not an object",
            )
        if not isinstance(cached.get("keys"), list):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "issuer JWKS keys is not an array",
            )
        _jwks_cache[cache_key] = cached
    return cached


def _signing_key_from_jwks(jwks: dict, token: str):
    """Require a non-empty JWT ``kid`` and an exact acceptable RSA key match."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access-token header") from exc
    if header.get("alg") != "RS256":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token must use RS256")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token: missing kid")
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "issuer JWKS keys is not an array",
        )
    matches = [
        key
        for key in keys
        if isinstance(key, dict)
        and key.get("kid") == kid
        and key.get("kty") == "RSA"
        and key.get("alg") in (None, "RS256")
        and key.get("use") in (None, "sig")
        and (
            key.get("key_ops") is None
            or isinstance(key.get("key_ops"), list)
            and "verify" in key["key_ops"]
        )
    ]
    if len(matches) != 1:
        raise _SigningKeyNotFound(f"expected one RSA signing key for kid={kid!r}")
    try:
        return RSAAlgorithm.from_jwk(json.dumps(matches[0]))
    except (KeyError, TypeError, ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token signing key") from exc


def _signing_key(settings: Settings, token: str):
    """Resolve a signing key and refresh JWKS once when a new ``kid`` appears."""
    try:
        return _signing_key_from_jwks(_jwks(settings), token)
    except _SigningKeyNotFound:
        try:
            return _signing_key_from_jwks(_jwks(settings, force_refresh=True), token)
        except _SigningKeyNotFound as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"invalid token: {exc.detail}",
            ) from exc


@dataclass(frozen=True)
class CurrentAccount:
    """The provisioned account that a verified access token resolved to."""

    user_account_id: str
    external_subject_id: str
    display_name: str
    corporate_entity_ids: frozenset[str]
    permission_codes: frozenset[str]
    preferred_locale: str | None = None

    def has_permission(self, permission_code: str) -> bool:
        """True when one of the account's roles grants ``permission_code``."""
        return permission_code in self.permission_codes


def decode_access_token(
    token: str,
    settings: Settings,
    *,
    audience: str | None = None,
) -> dict[str, Any]:
    """Validate a token for the REST audience or an explicit resource audience."""
    try:
        claims = jwt.decode(
            token,
            key=_signing_key(settings, token),
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            audience=audience or settings.oidc_audience,
            leeway=settings.oidc_clock_skew_seconds,
        )
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access token") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token has no subject")
    if "exp" not in claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token: missing exp")
    return claims


def _decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Validate a REST bearer token against the configured API audience."""
    return decode_access_token(token, settings)


async def resolve_current_account(pool: asyncpg.Pool, subject: str) -> CurrentAccount:
    """Resolve one verified subject to database-owned affiliations and permissions."""
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token has no subject")

    async with pool.acquire() as conn:
        account_row = await conn.fetchrow(
            "select user_account_id, display_name, preferred_locale from user_account where external_subject_id = $1",
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
        preferred_locale=account_row.get("preferred_locale"),
        corporate_entity_ids=frozenset(str(row["corporate_entity_id"]) for row in entity_rows),
        permission_codes=frozenset(str(row["permission_code"]) for row in permission_rows),
    )


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    pool: asyncpg.Pool = Depends(get_pool),
) -> CurrentAccount:
    """Resolve the bearer token to a provisioned ``user_account`` row."""
    settings = load_settings()
    claims = await asyncio.to_thread(_decode_access_token, credentials.credentials, settings)
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token has no subject")
    return await resolve_current_account(pool, subject)
