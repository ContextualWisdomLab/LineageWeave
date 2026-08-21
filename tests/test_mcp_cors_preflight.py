"""Browser admission regressions for the authenticated MCP endpoint."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest
from starlette.testclient import TestClient

from backend.app import mcp_server
from backend.app.config import Settings


def _settings() -> Settings:
    """Return one exact browser Origin and Host admission policy."""
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
        mcp_allowed_origins=["https://buyer.example"],
    )


@dataclass
class _Pool:
    """Minimal lifespan pool for transport-only requests."""

    closed: bool = False

    async def close(self) -> None:
        self.closed = True


def _app(cfg: Settings | None = None):
    """Build the real MCP ASGI surface without a reachable database."""
    cfg = cfg or _settings()
    pool = _Pool()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(cfg, pool_factory=pool_factory)
    return mcp_server.build_mcp_http_app(server, cfg), pool


def _initialize_request() -> dict[str, object]:
    """Return one protocol-valid initialization body."""
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


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "ftp://buyer.example",
        "https://user@buyer.example",
        "https://buyer.example/path",
        "https://buyer.example?query=1",
        "https://buyer.example#fragment",
    ],
)
def test_unsafe_configured_browser_origin_prevents_startup(origin: str) -> None:
    """The operator cannot turn an exact-Origin contract into reflection/wildcard CORS."""
    cfg = replace(_settings(), mcp_allowed_origins=[origin])
    server = mcp_server.build_mcp_server(cfg)
    with pytest.raises(ValueError, match="MCP_ALLOWED_ORIGINS"):
        mcp_server.build_mcp_http_app(server, cfg)


def test_allowed_exact_origin_preflight_finishes_before_oauth() -> None:
    """A browser can preflight the authenticated MCP request contract."""
    app, pool = _app()
    with TestClient(app) as client:
        response = client.options(
            "/mcp",
            headers={
                "Origin": "https://buyer.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization, content-type, mcp-protocol-version, mcp-session-id"
                ),
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://buyer.example"
    assert "Origin" in response.headers["vary"]
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].casefold()
    assert "mcp-protocol-version" in response.headers["access-control-allow-headers"].casefold()
    assert "mcp-session-id" in response.headers["access-control-allow-headers"].casefold()
    assert "www-authenticate" not in response.headers
    assert pool.closed is True


def test_allowed_origin_post_reaches_oauth_with_cors_response_contract() -> None:
    """An allowed browser Origin can read the OAuth discovery challenge."""
    app, pool = _app()
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=_initialize_request(),
            headers={
                "Origin": "https://buyer.example",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "https://buyer.example"
    assert "Origin" in response.headers["vary"]
    exposed = response.headers["access-control-expose-headers"].casefold()
    assert "mcp-session-id" in exposed
    assert "mcp-protocol-version" in exposed
    assert "www-authenticate" in exposed
    assert "resource_metadata" in response.headers["www-authenticate"]
    assert pool.closed is True


def test_disallowed_origin_preflight_fails_closed_without_reflection() -> None:
    """Prefix, suffix, null, and unrelated Origins are never reflected."""
    app, pool = _app()
    with TestClient(app) as client:
        for origin in (
            "https://buyer.example.attacker.test",
            "https://prefix-buyer.example",
            "null",
            "https://attacker.example",
        ):
            response = client.options(
                "/mcp",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization, content-type",
                },
            )
            assert response.status_code == 403
            assert response.headers.get("access-control-allow-origin") != origin
            assert "Origin" in response.headers["vary"]
            assert "www-authenticate" not in response.headers
    assert pool.closed is True


def test_no_origin_non_browser_post_keeps_oauth_challenge() -> None:
    """Non-browser clients may omit Origin and still reach the OAuth boundary."""
    app, pool = _app()
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=_initialize_request(),
            headers={"MCP-Protocol-Version": "2025-11-25"},
        )
    assert response.status_code == 401
    assert "access-control-allow-origin" not in response.headers
    assert "resource_metadata" in response.headers["www-authenticate"]
    assert pool.closed is True


def test_allowed_origin_can_read_bounded_request_error_code() -> None:
    """Browser clients can act on a CORS-readable admission error."""
    cfg = replace(_settings(), mcp_max_request_bytes=8)
    app, _ = _app(cfg)

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            content=b"123456789",
            headers={
                "Origin": "https://buyer.example",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )

    assert response.status_code == 413
    assert response.json() == {"error_code": "mcp_request_too_large"}
    assert response.headers["access-control-allow-origin"] == "https://buyer.example"
    assert "Origin" in response.headers["vary"]
