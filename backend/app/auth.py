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

import json
from dataclasses import dataclass

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


def _jwks_cache_key(settings: Settings) -> tuple[str, str, str]:
    """Bind cached keys to the exact issuer and key-discovery configuration."""
    return (
        settings.oidc_issuer,
        settings.oidc_discovery_uri,
        settings.oidc_jwks_uri_override,
    )


def _jwks(settings: Settings, *, force_refresh: bool = False) -> dict:
    """Return provider JWKS, refreshing explicitly when signing keys rotate."""
    cache_key = _jwks_cache_key(settings)
    cached = None if force_refresh else _jwks_cache.get(cache_key)
    if cached is None:
        try:
            if settings.oidc_jwks_uri_override:
                jwks_uri = settings.oidc_jwks_uri_override
            else:
                metadata = get_json(
                    settings.oidc_discovery_uri,
                    timeout=10,
                    service_peer_name="oidc",
                )
                jwks_uri = metadata.get("jwks_uri")
                if not isinstance(jwks_uri, str) or not jwks_uri.strip():
                    raise ValueError("OIDC discovery document has no jwks_uri")
            cached = get_json(jwks_uri, timeout=10, service_peer_name="oidc")
        except (HttpClientError, OSError, ValueError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "could not fetch OIDC JWKS: identity provider unavailable",
            ) from exc
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token must include a non-empty kid")
    for key in jwks.get("keys", []):
        if not isinstance(key, dict) or key.get("kid") != kid:
            continue
        if key.get("kty") != "RSA":
            continue
        if key.get("alg") not in (None, "RS256"):
            continue
        if key.get("use") not in (None, "sig"):
            continue
        key_ops = key.get("key_ops")
        if key_ops is not None and (
            not isinstance(key_ops, list) or "verify" not in key_ops
        ):
            continue
        try:
            return RSAAlgorithm.from_jwk(json.dumps(key))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "matching JWKS key is invalid") from exc
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"no JWKS key matched kid={kid!r}")


def _signing_key(settings: Settings, token: str):
    """Resolve a signing key and refresh JWKS once when a new ``kid`` appears."""
    try:
        return _signing_key_from_jwks(_jwks(settings), token)
    except HTTPException as exc:
        if not str(exc.detail).startswith("no JWKS key matched kid="):
            raise
    return _signing_key_from_jwks(_jwks(settings, force_refresh=True), token)


@dataclass(frozen=True)
class CurrentAccount:
    """The provisioned account that a verified access token resolved to."""

    user_account_id: str
    external_subject_id: str
    display_name: str
    preferred_locale: str | None
    corporate_entity_ids: frozenset[str]
    process_unit_ids: frozenset[str]
    permission_codes: frozenset[str]

    def has_permission(self, permission_code: str) -> bool:
        """True when one of the account's roles grants ``permission_code``."""
        return permission_code in self.permission_codes


def _decode_access_token(token: str, settings: Settings) -> dict:
    """Validate signature, issuer, resource audience, time claims, and subject."""
    required_claims = ["exp", "sub"]
    if settings.keyverse_claim_binding_required:
        required_claims.insert(1, "iat")
    try:
        claims = jwt.decode(
            token,
            key=_signing_key(settings, token),
            algorithms=["RS256"],
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            leeway=settings.oidc_clock_skew_seconds,
            options={"require": required_claims},
        )
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access token") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access token has no subject")
    return claims


def _keyverse_account_claims(claims: dict) -> tuple[str, str, list[str]]:
    """Return Keyverse's atomic account scope, rejecting ambiguous wire shapes."""
    organization = claims.get("org")
    workspace = claims.get("workspace")
    roles = claims.get("role")
    valid_roles = (
        isinstance(roles, list)
        and bool(roles)
        and all(isinstance(role, str) and role.strip() for role in roles)
        and len({role.strip() for role in roles}) == len(roles)
    )
    if not (
        isinstance(organization, str)
        and organization.strip()
        and organization == organization.strip()
        and isinstance(workspace, str)
        and workspace.strip()
        and workspace == workspace.strip()
        and valid_roles
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Keyverse token must contain one org, one workspace, and unique roles",
        )
    return organization, workspace, [role.strip() for role in roles]


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    pool: asyncpg.Pool = Depends(get_pool),
) -> CurrentAccount:
    """Resolve the bearer token to a provisioned ``user_account`` row."""
    settings = load_settings()
    claims = _decode_access_token(credentials.credentials, settings)
    subject = claims["sub"]
    keyverse_scope = (
        _keyverse_account_claims(claims)
        if settings.keyverse_claim_binding_required
        else None
    )

    async with pool.acquire() as conn:
        if keyverse_scope:
            organization, workspace, token_roles = keyverse_scope
            account_row = await conn.fetchrow(
                """
                select account.user_account_id, account.display_name,
                       account.preferred_locale, affiliation.corporate_entity_id,
                       affiliation.process_unit_id
                  from user_account account
                  join account_affiliation affiliation
                    on affiliation.user_account_id = account.user_account_id
                  join corporate_entity entity
                    on entity.corporate_entity_id = affiliation.corporate_entity_id
                  join process_unit process
                    on process.process_unit_id = affiliation.process_unit_id
                   and process.corporate_entity_id = entity.corporate_entity_id
                 where account.external_subject_id = $1
                   and entity.corporate_entity_code = $2
                   and process.process_unit_code = $3
                """,
                subject,
                organization,
                workspace,
            )
        else:
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

        if keyverse_scope:
            entity_rows = [{"corporate_entity_id": account_row["corporate_entity_id"]}]
            process_rows = [{"process_unit_id": account_row["process_unit_id"]}]
            permission_rows = await conn.fetch(
                """
                select distinct permission.permission_code
                  from account_role_assignment assignment
                  join access_role role
                    on role.access_role_id = assignment.access_role_id
                  join role_permission permission
                    on permission.access_role_id = assignment.access_role_id
                 where assignment.user_account_id = $1
                   and role.role_code = any($2::text[])
                """,
                account_row["user_account_id"],
                token_roles,
            )
        else:
            entity_rows = await conn.fetch(
                "select corporate_entity_id from account_affiliation where user_account_id = $1",
                account_row["user_account_id"],
            )
            process_rows = []
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
        preferred_locale=account_row["preferred_locale"],
        corporate_entity_ids=frozenset(str(row["corporate_entity_id"]) for row in entity_rows),
        process_unit_ids=frozenset(str(row["process_unit_id"]) for row in process_rows),
        permission_codes=frozenset(row["permission_code"] for row in permission_rows),
    )
