"""Current-contract MCP surface and deployment-policy tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from mcp.client import Client
from mcp.server.auth.provider import AccessToken
from starlette.testclient import TestClient

from backend.app.config import load_settings

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_quota_has_no_library_default(monkeypatch) -> None:
    """Generic backend settings never invent deployment capacity."""
    monkeypatch.delenv("MCP_RATE_LIMIT_REQUESTS", raising=False)
    monkeypatch.delenv("MCP_RATE_LIMIT_WINDOW_SECONDS", raising=False)
    settings = load_settings()
    assert settings.mcp_rate_limit_requests is None
    assert settings.mcp_rate_limit_window_seconds is None


def test_mcp_server_requires_measured_quota_and_exact_origins(monkeypatch) -> None:
    """The dedicated resource server fails closed on missing policy or wildcard Origin."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    configured = load_settings()
    assert {
        tool.name
        for tool in mcp_server.build_mcp_server(configured)._tool_manager.list_tools()
    } == {
        "submit_global_ask",
        "read_global_ask_job",
    }
    with pytest.raises(ValueError, match="measured capacity"):
        mcp_server.build_mcp_server(replace(configured, mcp_rate_limit_requests=None))
    with pytest.raises(ValueError, match="MCP_AUDIENCE"):
        mcp_server.build_mcp_server(replace(configured, mcp_audience=""))
    with pytest.raises(ValueError, match="exact HTTP"):
        mcp_server.build_mcp_http_app(
            mcp_server.build_mcp_server(configured),
            replace(configured, mcp_allowed_origins=["*"]),
        )


@pytest.mark.anyio
async def test_mcp_verifier_uses_exact_resource_audience(monkeypatch) -> None:
    """MCP authentication asks the shared decoder for the MCP audience."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_auth

    settings = load_settings()
    observed = []

    def decode(token, candidate_settings, *, audience):
        observed.append((token, candidate_settings, audience))
        return {
            "sub": "subject-1",
            "azp": "client-1",
            "exp": 2_000_000_000,
            "scope": "lineageweave:ask",
            "aud": audience,
        }

    monkeypatch.setattr(mcp_auth, "decode_access_token", decode)
    verified = await mcp_auth.KeyverseMcpTokenVerifier(settings).verify_token("token")
    assert verified is not None
    assert verified.resource == settings.mcp_audience
    assert observed == [("token", settings, settings.mcp_audience)]


@pytest.mark.anyio
async def test_mcp_verifier_rejects_invalid_or_unbound_claims(monkeypatch) -> None:
    """Decoder failures and missing client identity remain unauthenticated."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from fastapi import HTTPException

    from backend.app import mcp_auth

    settings = load_settings()
    monkeypatch.setattr(
        mcp_auth,
        "decode_access_token",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(HTTPException(401)),
    )
    assert await mcp_auth.KeyverseMcpTokenVerifier(settings).verify_token("bad") is None
    assert (
        await mcp_auth.KeyverseMcpTokenVerifier(
            replace(settings, mcp_audience="")
        ).verify_token("bad")
        is None
    )
    monkeypatch.setattr(
        mcp_auth, "decode_access_token", lambda *_args, **_kwargs: {"sub": "subject"}
    )
    assert await mcp_auth.KeyverseMcpTokenVerifier(settings).verify_token("bad") is None
    assert mcp_auth._scopes_from_claim(["one", 2, "two"]) == ["one", "two"]
    assert mcp_auth._scopes_from_claim(None) == []


@pytest.mark.parametrize(
    "name", ["MCP_RATE_LIMIT_REQUESTS", "MCP_RATE_LIMIT_WINDOW_SECONDS"]
)
def test_mcp_quota_inputs_must_be_positive_integers(monkeypatch, name) -> None:
    """Malformed deployment policy is rejected during configuration."""
    monkeypatch.setenv(name, "0")
    with pytest.raises(ValueError, match="positive"):
        load_settings()


def test_local_keycloak_and_mcp_service_share_exact_fixed_audience() -> None:
    """The demo token mapper cannot drift from the local resource identifier."""
    realm = json.loads((ROOT / "docker/keycloak/realm-export.json").read_text())
    client = realm["clients"][0]
    mapper = next(
        item
        for item in client["protocolMappers"]
        if item["name"] == "lineageweave-mcp-audience"
    )
    audience = mapper["config"]["included.custom.audience"]
    compose = (ROOT / "docker-compose.yml").read_text()
    assert audience == "http://localhost:18001/mcp"
    assert f"MCP_RESOURCE_URL: {audience}" in compose
    assert f"MCP_AUDIENCE: {audience}" in compose
    assert '"18001:8001"' in compose


class FakePool:
    """Record MCP lifespan closure without opening PostgreSQL."""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        """Record pool closure."""
        self.closed = True


class FakeLimiter:
    """Record each authenticated tool quota consumption."""

    def __init__(self, error=None) -> None:
        self.accounts = []
        self.closed = False
        self.error = error

    async def consume(self, account_id: str) -> None:
        """Record one consumed account unit."""
        self.accounts.append(account_id)
        if self.error:
            raise self.error

    async def close(self) -> None:
        """Record limiter closure."""
        self.closed = True


@pytest.mark.anyio
async def test_mcp_lifespan_closes_pool_when_limiter_close_fails(monkeypatch) -> None:
    """A limiter shutdown defect cannot leak the database pool."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    class BrokenCloseLimiter(FakeLimiter):
        async def close(self) -> None:
            raise RuntimeError("limiter close failed")

    pool = FakePool()
    server = mcp_server.build_mcp_server(
        load_settings(),
        pool_factory=lambda _url: _return(pool),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda *_args: BrokenCloseLimiter(),
    )
    with pytest.raises(RuntimeError, match="limiter close failed"):
        async with Client(server):
            pass
    assert pool.closed


@pytest.mark.anyio
async def test_mcp_tools_delegate_to_current_service_once(monkeypatch) -> None:
    """Both tools share account resolution, quota, and durable service calls."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server
    from backend.app.auth import CurrentAccount

    settings = load_settings()
    pool = FakePool()
    limiter = FakeLimiter()
    account = CurrentAccount(
        "account-1",
        "subject-1",
        "Analyst",
        None,
        frozenset({"entity-1"}),
        frozenset({"unit-1"}),
        frozenset({"post_read"}),
    )

    async def resolve(candidate_pool, claims, candidate_settings):
        assert (candidate_pool, claims["sub"], candidate_settings) == (
            pool,
            "subject-1",
            settings,
        )
        return account

    submitted = []

    async def submit(**kwargs):
        submitted.append(kwargs)
        return {
            "ask_job_id": "00000000-0000-0000-0000-000000000123",
            "job_status_code": "queued",
        }

    async def read(**kwargs):
        assert kwargs["account"] is account
        return {"ask_job_id": str(kwargs["ask_job_id"]), "job_status_code": "running"}

    monkeypatch.setattr(mcp_server, "submit_global_ask_service", submit)
    monkeypatch.setattr(mcp_server, "read_global_ask_job_service", read)
    token = AccessToken(
        token="token",
        client_id="client-1",
        scopes=[],
        subject="subject-1",
        resource=settings.mcp_audience,
        claims={"sub": "subject-1"},
    )
    server = mcp_server.build_mcp_server(
        settings,
        pool_factory=lambda _url: _return(pool),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda _client, _requests, _window: limiter,
        account_resolver=resolve,
        access_token_provider=lambda: token,
    )
    async with Client(server) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {
            "submit_global_ask",
            "read_global_ask_job",
        }
        queued = await client.call_tool(
            "submit_global_ask",
            {
                "question": "What changed?",
                "verify_external": True,
                "knowledge_cutoff": "2026-08-25T00:00:00Z",
            },
        )
        assert queued.is_error is False
        running = await client.call_tool(
            "read_global_ask_job",
            {"ask_job_id": "00000000-0000-0000-0000-000000000123"},
        )
        assert running.is_error is False
        invalid = await client.call_tool(
            "read_global_ask_job", {"ask_job_id": "not-a-uuid"}
        )
        assert invalid.is_error is True
    assert submitted[0]["account"] is account
    assert submitted[0]["verify_external"] is True
    assert limiter.accounts == ["account-1", "account-1", "account-1"]
    assert pool.closed and limiter.closed


def test_http_boundary_rejects_host_before_oauth(monkeypatch) -> None:
    """A hostile Host receives no OAuth challenge and invokes no tool."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    settings = replace(load_settings(), mcp_allowed_hosts=["testserver"])
    pool = FakePool()
    limiter = FakeLimiter()
    server = mcp_server.build_mcp_server(
        settings,
        pool_factory=lambda _url: _return(pool),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda *_args: limiter,
    )
    app = mcp_server.build_mcp_http_app(server, settings)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Host": "attacker.example", "MCP-Protocol-Version": "2025-11-25"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
    assert response.status_code == 421
    assert "www-authenticate" not in response.headers
    assert pool.closed and limiter.closed


def test_http_boundary_rejects_origin_and_challenges_trusted_host(monkeypatch) -> None:
    """Origin rejection precedes OAuth while a trusted no-Origin client is challenged."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    settings = replace(
        load_settings(),
        mcp_allowed_hosts=["testserver"],
        mcp_allowed_origins=["https://trusted.example"],
    )
    pool = FakePool()
    limiter = FakeLimiter()
    server = mcp_server.build_mcp_server(
        settings,
        pool_factory=lambda _url: _return(pool),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda *_args: limiter,
    )
    app = mcp_server.build_mcp_http_app(server, settings)
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    with TestClient(app) as client:
        rejected = client.post(
            "/mcp", headers={"Origin": "https://attacker.example"}, json=payload
        )
        challenged = client.post("/mcp", json=payload)
    assert rejected.status_code == 403
    assert rejected.headers["vary"] == "Origin"
    assert challenged.status_code == 401


def test_exhausted_http_tool_emits_retry_after(monkeypatch) -> None:
    """The complete Streamable HTTP path returns the measured quota delay."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server
    from backend.app.auth import CurrentAccount
    from backend.app.mcp_rate_limit import McpRateLimitExceeded

    settings = replace(load_settings(), mcp_allowed_hosts=["testserver"])
    token = AccessToken(
        token="token",
        client_id="client",
        scopes=["lineageweave:ask"],
        subject="subject-1",
        resource=settings.mcp_audience,
        claims={"sub": "subject-1"},
    )

    class TokenVerifier:
        async def verify_token(self, _token):
            return token

    account = CurrentAccount(
        "account-1",
        "subject-1",
        "Analyst",
        None,
        frozenset(),
        frozenset(),
        frozenset({"post_read"}),
    )

    async def resolve(*_args):
        return account

    server = mcp_server.build_mcp_server(
        settings,
        pool_factory=lambda _url: _return(FakePool()),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda *_args: FakeLimiter(McpRateLimitExceeded(7)),
        token_verifier=TokenVerifier(),
        account_resolver=resolve,
        access_token_provider=lambda: token,
    )
    headers = {
        "Authorization": "Bearer token",
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(mcp_server.build_mcp_http_app(server, settings)) as client:
        initialized = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        headers.update(
            {
                "Mcp-Session-Id": initialized.headers["mcp-session-id"],
                "MCP-Protocol-Version": "2025-11-25",
            }
        )
        client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        exhausted = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "submit_global_ask",
                    "arguments": {"question": "question"},
                },
            },
        )

    assert exhausted.headers["retry-after"] == "7"
    assert '"code":-31929' in exhausted.text


@pytest.mark.anyio
async def test_retry_after_wrapper_replaces_existing_header(monkeypatch) -> None:
    """Quota exhaustion exposes only the bounded current retry interval."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    async def downstream(scope, _receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"retry-after", b"999")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": (
                    b'event: message\r\ndata: {"jsonrpc":"2.0","id":2,'
                    b'"error":{"code":-31929,"message":"quota","data":'
                    b'{"retry_after_seconds":7}}}\r\n\r\n'
                ),
            }
        )

    sent = []
    scope = {"type": "http", "method": "POST"}

    async def send(message):
        """Capture one wrapped ASGI response message."""
        sent.append(message)

    await mcp_server.McpRetryAfterHeaderApp(downstream)(
        scope, lambda: _return({"type": "http.disconnect"}), send
    )
    assert (b"retry-after", b"7") in sent[0]["headers"]
    assert (b"retry-after", b"999") not in sent[0]["headers"]


@pytest.mark.anyio
async def test_retry_after_wrapper_does_not_buffer_get_streams(monkeypatch) -> None:
    """GET streams commit response headers without waiting for a body event."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    sent = []

    async def downstream(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        assert sent == [{"type": "http.response.start", "status": 200, "headers": []}]

    async def send(message):
        sent.append(message)

    await mcp_server.McpRetryAfterHeaderApp(downstream)(
        {"type": "http", "method": "GET"},
        lambda: _return({"type": "http.disconnect"}),
        send,
    )


@pytest.mark.anyio
async def test_retry_after_wrapper_preserves_non_quota_header(monkeypatch) -> None:
    """A non-quota POST keeps the downstream Retry-After contract unchanged."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server

    async def downstream(_scope, _receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"retry-after", b"11")],
            }
        )
        await send({"type": "http.response.body", "body": b"unavailable"})

    sent = []

    async def send(message):
        sent.append(message)

    await mcp_server.McpRetryAfterHeaderApp(downstream)(
        {"type": "http", "method": "POST"},
        lambda: _return({"type": "http.disconnect"}),
        send,
    )
    assert (b"retry-after", b"11") in sent[0]["headers"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mode", ["missing_token", "permission", "exceeded", "unavailable"]
)
async def test_tool_auth_and_quota_fail_closed(monkeypatch, mode) -> None:
    """Unauthenticated, unauthorized, exhausted, and unavailable calls never submit."""
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")
    from backend.app import mcp_server
    from backend.app.auth import CurrentAccount
    from backend.app.mcp_rate_limit import (
        McpRateLimiterUnavailable,
        McpRateLimitExceeded,
    )

    settings = load_settings()
    pool = FakePool()
    error = {
        "exceeded": McpRateLimitExceeded(7),
        "unavailable": McpRateLimiterUnavailable(),
    }.get(mode)
    limiter = FakeLimiter(error)
    permissions = frozenset() if mode == "permission" else frozenset({"post_read"})
    account = CurrentAccount(
        "account-1",
        "subject-1",
        "Analyst",
        None,
        frozenset({"entity-1"}),
        frozenset({"unit-1"}),
        permissions,
    )

    async def resolve(*_args):
        return account

    token = (
        None
        if mode == "missing_token"
        else AccessToken(
            token="token",
            client_id="client",
            scopes=[],
            subject="subject-1",
            resource=settings.mcp_audience,
            claims={"sub": "subject-1"},
        )
    )
    server = mcp_server.build_mcp_server(
        settings,
        pool_factory=lambda _url: _return(pool),
        valkey_factory=lambda _url: object(),
        limiter_factory=lambda *_args: limiter,
        account_resolver=resolve,
        access_token_provider=lambda: token,
    )
    async with Client(server) as client:
        if mode in {"exceeded", "unavailable"}:
            from mcp.shared.exceptions import MCPError

            with pytest.raises(MCPError):
                await client.call_tool("submit_global_ask", {"question": "question"})
        else:
            result = await client.call_tool(
                "submit_global_ask", {"question": "question"}
            )
            assert result.is_error is True


def test_production_limiter_factory_uses_validated_values(monkeypatch) -> None:
    """The server's default limiter factory forwards measured inputs unchanged."""
    from backend.app import mcp_server

    client = object()
    limiter = mcp_server._build_limiter(client, 3, 17)
    assert limiter._client is client
    assert limiter._request_limit == 3
    assert limiter._window_seconds == 17


async def _return(value):
    """Return a value from an awaitable factory."""
    return value
