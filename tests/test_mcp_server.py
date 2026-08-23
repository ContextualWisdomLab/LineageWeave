from __future__ import annotations

from dataclasses import replace

import pytest
from mcp.client import Client
from mcp.server.auth.provider import AccessToken
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from backend.app import mcp_server
from backend.app.auth import CurrentAccount
from backend.app.config import Settings
from backend.app.global_ask import GlobalAskAnswer
from backend.app.global_ask_media import GlobalAskContentBlock
from backend.app.global_ask_verification import (
    STATUS_SUPPORTED,
    ExternalVerificationResult,
)
from lineageweave.post_chat import (
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
)


def settings() -> Settings:
    """Return one test-only MCP resource configuration."""
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


class FakePool:
    """Tracks whether the MCP lifespan closes its database pool."""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeExternalVerifier:
    """Deterministic external verification used by MCP surface tests."""

    available = True

    def verify(self, question: str, answer_text: str) -> ExternalVerificationResult:
        assert question == "What happened?"
        assert answer_text == "Grounded"
        return ExternalVerificationResult(
            status_code=STATUS_SUPPORTED,
            evidence_urls=("https://evidence.example/fact",),
            rationale="Independent evidence supports the material claim.",
        )


class FakeRateLimiter:
    def __init__(self) -> None:
        self.accounts: list[str] = []
        self.closed = False

    async def consume(self, account_id: str) -> None:
        self.accounts.append(account_id)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [(None, None), (37, "37")],
)
def test_retry_after_header_is_request_scoped_to_exceeded_quota(
    retry_after: int | None,
    expected: str | None,
) -> None:
    """Success and non-quota errors cannot inherit retry advice."""

    async def sdk_response(scope, receive, send) -> None:
        if retry_after is not None:
            scope.setdefault("state", {})[mcp_server._RETRY_AFTER_STATE_KEY] = retry_after
        await JSONResponse({"jsonrpc": "2.0", "result": {}})(scope, receive, send)

    client = TestClient(mcp_server.McpRetryAfterHeaderApp(sdk_response))
    response = client.get("/")

    assert response.headers.get("retry-after") == expected


def test_mcp_quota_error_codes_are_outside_json_rpc_reserved_range() -> None:
    """Application-defined MCP errors do not occupy JSON-RPC reserved codes."""
    assert not -32768 <= mcp_server._MCP_RATE_LIMIT_EXCEEDED <= -32000
    assert not -32768 <= mcp_server._MCP_RATE_LIMITER_UNAVAILABLE <= -32000


@pytest.mark.asyncio
async def test_global_ask_tool_is_read_only_structured_and_closes_lifespan() -> None:
    cfg = settings()
    pool = FakePool()
    limiter = FakeRateLimiter()

    async def pool_factory(database_url: str):
        assert database_url == cfg.database_url
        return pool

    account = CurrentAccount("account", "subject", "Analyst", frozenset(), frozenset({"post_read"}))

    async def account_resolver(candidate_pool, subject: str):
        assert candidate_pool is pool
        assert subject == "subject"
        return account

    async def answerer(candidate_pool, candidate_account, chat_client, question, *, vision_client):
        assert candidate_pool is pool
        assert candidate_account is account
        assert isinstance(chat_client, NullPostChatClient)
        assert question == "What happened?"
        assert vision_client.available is False
        return GlobalAskAnswer(
            answer_text="Grounded",
            anchor_post_id="post-1",
            cited_post_ids=("post-1",),
            cited_posts=({"post_id": "post-1", "post_title": "Evidence"},),
            source_post_ids=("post-1",),
            content_blocks=(
                GlobalAskContentBlock(type="text", text="Grounded"),
                GlobalAskContentBlock(
                    type="image",
                    post_id="post-1",
                    unit_index=0,
                    mime_type="image/png",
                    data_base64="c3ludGhldGljLWltYWdl",
                    alt_text="Evidence - source image 1",
                    caption="Evidence",
                ),
            ),
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
        external_verifier=FakeExternalVerifier(),
        rate_limiter_factory=lambda _url, requests, window: limiter,
    )
    async with Client(server) as client:
        listed = await client.list_tools()
        tool = next(item for item in listed.tools if item.name == "global_ask")
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.idempotent_hint is True
        assert tool.annotations.open_world_hint is True
        assert tool.output_schema is not None
        result = await client.call_tool(
            "global_ask",
            {"question": "What happened?", "verify_external": True},
        )
        assert not result.is_error
        assert result.content[0].type == "text"
        assert result.content[0].text == "Grounded"
        assert result.content[1].type == "image"
        assert result.content[1].mime_type == "image/png"
        assert result.content[1].data == "c3ludGhldGljLWltYWdl"
        assert result.structured_content == {
            "answer_text": "Grounded",
            "anchor_post_id": "post-1",
            "cited_post_ids": ["post-1"],
            "cited_posts": [{"post_id": "post-1", "post_title": "Evidence"}],
            "source_post_ids": ["post-1"],
            "timeline": [],
            "content_blocks": [
                {
                    "type": "text",
                    "text": "Grounded",
                    "post_id": None,
                    "unit_index": None,
                    "mime_type": None,
                    "data_base64": None,
                    "alt_text": None,
                    "caption": None,
                },
                {
                    "type": "image",
                    "text": None,
                    "post_id": "post-1",
                    "unit_index": 0,
                    "mime_type": "image/png",
                    "data_base64": "c3ludGhldGljLWltYWdl",
                    "alt_text": "Evidence - source image 1",
                    "caption": "Evidence",
                },
            ],
            "external_verification_status": "supported",
            "external_evidence_urls": ["https://evidence.example/fact"],
            "external_verification_rationale": "Independent evidence supports the material claim.",
        }
    assert pool.closed is True
    assert limiter.accounts == ["account"]
    assert limiter.closed is True


@pytest.mark.asyncio
async def test_mcp_lifespan_closes_pool_when_rate_limiter_creation_fails() -> None:
    """A partial MCP startup cannot leak its opened database pool."""
    cfg = settings()
    pool = FakePool()

    async def pool_factory(_database_url: str):
        return pool

    def fail_rate_limiter(_url: str, _requests: int, _window: int):
        raise RuntimeError("synthetic limiter startup failure")

    server = mcp_server.build_mcp_server(
        cfg,
        pool_factory=pool_factory,
        rate_limiter_factory=fail_rate_limiter,
    )

    with pytest.raises(RuntimeError, match="synthetic limiter startup failure"):
        async with Client(server):
            pass

    assert pool.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "access_token",
    [None, AccessToken(token="token", client_id="codex", scopes=[], subject="")],
)
async def test_global_ask_tool_fails_without_authenticated_subject(access_token) -> None:
    pool = FakePool()
    limiter = FakeRateLimiter()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(
        settings(),
        pool_factory=pool_factory,
        access_token_provider=lambda: access_token,
        rate_limiter_factory=lambda _url, _requests, _window: limiter,
    )
    async with Client(server) as client:
        result = await client.call_tool("global_ask", {"question": "question"})
        assert result.is_error
        assert "authenticated MCP principal" in result.content[0].text
    assert pool.closed is True
    assert limiter.accounts == []


def test_chat_client_factory_uses_null_or_configured_orchestrator() -> None:
    cfg = settings()
    assert isinstance(mcp_server._chat_client(cfg), NullPostChatClient)
    configured = replace(
        cfg,
        orchestrator_base_url="https://orchestrator.example",
        orchestrator_api_key="secret",
    )
    assert isinstance(mcp_server._chat_client(configured), ContextualOrchestratorPostChatClient)


def test_external_verifier_factory_requires_both_search_and_orchestrator() -> None:
    cfg = settings()
    assert mcp_server._external_verifier(cfg).available is False
    configured = replace(
        cfg,
        searxng_base_url="https://search.example",
        orchestrator_base_url="https://orchestrator.example",
        orchestrator_api_key="secret",
    )
    assert mcp_server._external_verifier(configured).available is True


def _initialize_request() -> dict[str, object]:
    """Return one protocol-valid MCP initialize request body."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }


def test_streamable_http_rejects_unauthenticated_request() -> None:
    cfg = settings()
    pool = FakePool()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(cfg, pool_factory=pool_factory)
    app = mcp_server.build_mcp_http_app(server, cfg)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=_initialize_request(),
            headers={"MCP-Protocol-Version": "2025-11-25"},
        )
    assert response.status_code == 401
    assert "resource_metadata" in response.headers["www-authenticate"]
    assert pool.closed is True


def test_streamable_http_rejects_untrusted_host_before_authentication() -> None:
    """DNS-rebinding protection rejects a hostile Host before token processing."""
    cfg = settings()
    pool = FakePool()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(cfg, pool_factory=pool_factory)
    app = mcp_server.build_mcp_http_app(server, cfg)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=_initialize_request(),
            headers={
                "Host": "attacker.example",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )
    assert response.status_code == 421
    assert "www-authenticate" not in response.headers
    assert pool.closed is True


def test_streamable_http_rejects_untrusted_origin_before_authentication() -> None:
    """A hostile browser Origin fails before OAuth or MCP request handling."""
    cfg = replace(settings(), mcp_allowed_origins=["https://buyer.example"])
    pool = FakePool()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(cfg, pool_factory=pool_factory)
    app = mcp_server.build_mcp_http_app(server, cfg)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=_initialize_request(),
            headers={
                "Origin": "https://attacker.example",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )
    assert response.status_code == 403
    assert "www-authenticate" not in response.headers
    assert pool.closed is True


def test_build_mcp_server_uses_loaded_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = settings()
    monkeypatch.setattr(mcp_server, "load_settings", lambda: cfg)
    server = mcp_server.build_mcp_server()
    assert server is not None
