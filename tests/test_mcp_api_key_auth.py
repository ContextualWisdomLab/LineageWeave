"""Regression tests for the LineageWeave-managed MCP API-key boundary."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import asyncpg
import pytest

from backend.app.mcp_auth import KeycloakMcpTokenVerifier


class FakePool:
    """Small asyncpg-pool substitute that records the hashed lookup input."""

    def __init__(self, row: dict[str, object] | None) -> None:
        self.row = row
        self.received_hash: str | None = None

    async def fetchrow(self, _query: str, key_hash: str) -> dict[str, object] | None:
        self.received_hash = key_hash
        return self.row


class MissingKeyTablePool:
    """Pool substitute for a deployment where PR #333 is not applied yet."""

    async def fetchrow(self, _query: str, _key_hash: str) -> None:
        raise asyncpg.UndefinedTableError("mcp_api_key is not installed")


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        mcp_required_scopes=("post_read",),
        mcp_audience="https://lineageweave.example/mcp",
    )


@pytest.mark.asyncio
async def test_api_key_resolves_to_the_provisioned_account_subject() -> None:
    token = "lw_mcp_test-secret"
    pool = FakePool(
        {
            "mcp_api_key_id": "key-id",
            "user_account_id": "account-id",
            "external_subject_id": "keyverse-subject",
            "expires_at": 1_900_000_000,
        }
    )
    verifier = KeycloakMcpTokenVerifier(_settings())  # type: ignore[arg-type]
    verifier.bind_api_key_pool(pool)

    access_token = await verifier.verify_token(token)

    assert pool.received_hash == hashlib.sha256(token.encode()).hexdigest()
    assert access_token is not None
    assert access_token.subject == "keyverse-subject"
    assert access_token.scopes == ["post_read"]
    assert access_token.expires_at == 1_900_000_000
    assert access_token.claims == {
        "auth_method": "mcp_api_key",
        "mcp_api_key_id": "key-id",
        "user_account_id": "account-id",
    }


@pytest.mark.asyncio
async def test_api_key_is_unavailable_before_the_mcp_lifespan_binds_a_pool() -> None:
    verifier = KeycloakMcpTokenVerifier(_settings())  # type: ignore[arg-type]

    assert await verifier.verify_token("lw_mcp_not-bound") is None


@pytest.mark.asyncio
async def test_missing_key_table_fails_closed_without_affecting_oidc_verification() -> None:
    verifier = KeycloakMcpTokenVerifier(_settings())  # type: ignore[arg-type]
    verifier.bind_api_key_pool(MissingKeyTablePool())

    assert await verifier.verify_token("lw_mcp_schema-not-ready") is None
