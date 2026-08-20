"""MCP regression for the explicit external-verification consent boundary."""

from __future__ import annotations

import pytest
from mcp.client import Client
from mcp.server.auth.provider import AccessToken

from backend.app import mcp_server
from backend.app.auth import CurrentAccount
from backend.app.config import Settings
from backend.app.global_ask import GlobalAskAnswer


def _settings() -> Settings:
    """Return a complete isolated MCP configuration."""
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
        searxng_base_url="",
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


class _Pool:
    """Minimal closeable pool used by the MCP lifespan."""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _MustNotRunVerifier:
    """Raise if the default closed-world call crosses the open-web boundary."""

    available = True

    def verify(self, question: str, answer_text: str):
        raise AssertionError(f"external verifier called for {question!r}: {answer_text!r}")


@pytest.mark.asyncio
async def test_global_ask_does_not_verify_external_evidence_without_explicit_opt_in() -> None:
    """Omitting ``verify_external`` must not transmit the question to Searxng."""
    cfg = _settings()
    pool = _Pool()
    account = CurrentAccount(
        "account",
        "subject",
        "Analyst",
        frozenset(),
        frozenset({"post_read"}),
    )

    async def pool_factory(database_url: str):
        assert database_url == cfg.database_url
        return pool

    async def account_resolver(candidate_pool, subject: str):
        assert candidate_pool is pool
        assert subject == "subject"
        return account

    async def answerer(candidate_pool, candidate_account, _chat_client, question, *, vision_client):
        assert candidate_pool is pool
        assert candidate_account is account
        assert question == "Private acquisition question"
        assert vision_client.available is False
        return GlobalAskAnswer(
            answer_text="Internal answer",
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
        external_verifier=_MustNotRunVerifier(),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "global_ask",
            {"question": "Private acquisition question"},
        )
        assert not result.is_error
        assert result.structured_content["external_verification_status"] == "not_requested"
        assert result.structured_content["external_evidence_urls"] == []
        assert result.structured_content["external_verification_rationale"] is None

    assert pool.closed is True
