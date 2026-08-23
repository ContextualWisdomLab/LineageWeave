"""MCP Global Ask must not enter the open-web lane without explicit opt-in."""

from __future__ import annotations

import pytest
from mcp.client import Client
from mcp.server.auth.provider import AccessToken

from backend.app import mcp_server
from backend.app.auth import CurrentAccount
from backend.app.config import Settings
from backend.app.global_ask import GlobalAskAnswer


class _AllowRateLimiter:
    async def consume(self, account_id: str) -> None:
        assert account_id == "account"

    async def close(self) -> None:
        return None


class FakePool:
    """Minimal lifespan pool for the opt-in boundary regression."""

    async def close(self) -> None:
        """Mirror the production pool lifecycle contract."""


class ForbiddenExternalVerifier:
    """Fail the test if default Global Ask attempts any external verification."""

    available = True

    def verify(self, question: str, answer_text: str):
        """External verification must not run unless the tool argument opts in."""
        raise AssertionError("external verifier must not run when verify_external is false")


def _settings() -> Settings:
    """Return a closed-world-by-default MCP configuration."""
    return Settings(
        database_url="postgresql://example",
        keycloak_base_url="https://issuer.example",
        keycloak_realm="realm",
        keycloak_client_id="frontend",
        keycloak_issuer="https://issuer.example/realms/realm",
        oidc_issuer="https://issuer.example/realms/realm",
        oidc_client_id="frontend",
        oidc_audience="lineageweave-api",
        oidc_discovery_uri="https://issuer.example/realms/realm/.well-known/openid-configuration",
        oidc_jwks_uri_override="https://issuer.example/realms/realm/protocol/openid-connect/certs",
        oidc_clock_skew_seconds=5,
        frontend_origins=[],
        orchestrator_base_url="",
        orchestrator_api_key="",
        embedding_model="",
        valkey_url="redis://example",
        searxng_base_url="https://search.example",
        tepp_transport_url="",
        tepp_api_key="",
        caldav_base_url="",
        rankweave_disabled=False,
        mcp_resource_url="https://lineage.example/mcp",
        mcp_audience="https://lineage.example/mcp",
        mcp_required_scopes=[],
        mcp_allowed_hosts=["testserver"],
        mcp_allowed_origins=[],
    )


@pytest.mark.asyncio
async def test_default_global_ask_never_calls_external_verifier() -> None:
    """Omitting verify_external keeps the tool closed-world and reports not_requested."""
    cfg = _settings()
    pool = FakePool()

    async def pool_factory(_database_url: str):
        return pool

    account = CurrentAccount(
        "account",
        "subject",
        "Analyst",
        frozenset(),
        frozenset({"post_read"}),
    )

    async def account_resolver(_pool, subject: str):
        assert subject == "subject"
        return account

    async def answerer(_pool, _account, _chat_client, question, *, vision_client):
        assert question == "What happened?"
        assert vision_client.available is False
        return GlobalAskAnswer(
            answer_text="Grounded",
            anchor_post_id="post-1",
            cited_post_ids=("post-1",),
            cited_posts=({"post_id": "post-1", "post_title": "Evidence"},),
            source_post_ids=("post-1",),
        )

    token = AccessToken(
        token="token",
        client_id="codex",
        scopes=[],
        subject="subject",
        resource=cfg.mcp_audience,
    )
    server = mcp_server.build_mcp_server(
        cfg,
        pool_factory=pool_factory,
        account_resolver=account_resolver,
        answerer=answerer,
        access_token_provider=lambda: token,
        external_verifier=ForbiddenExternalVerifier(),
        rate_limiter_factory=lambda _url, requests, window: _AllowRateLimiter(),
    )

    async with Client(server) as client:
        result = await client.call_tool("global_ask", {"question": "What happened?"})

    assert not result.is_error
    assert result.structured_content["external_verification_status"] == "not_requested"
    assert result.structured_content["external_evidence_urls"] == []
    assert result.structured_content["external_verification_rationale"] is None
