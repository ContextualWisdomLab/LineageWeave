"""Browser admission regressions for the authenticated MCP endpoint."""

from __future__ import annotations

from dataclasses import dataclass

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
        frontend_origins=[],
        orchestrator_base_url="",
        orchestrator_api_key="",
        vision_model="",
        valkey_url="redis://example",
        searxng_base_url="",
        tepp_transport_url="",
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


def _app():
    """Build the real MCP ASGI surface without a reachable database."""
    cfg = _settings()
    pool = _Pool()

    async def pool_factory(_database_url: str):
        return pool

    server = mcp_server.build_mcp_server(cfg, pool_factory=pool_factory)
    return mcp_server.build_mcp_http_app(server, cfg), pool


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
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].casefold()
    assert "mcp-protocol-version" in response.headers["access-control-allow-headers"].casefold()
    assert "www-authenticate" not in response.headers
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
            assert "www-authenticate" not in response.headers
    assert pool.closed is True


def test_no_origin_non_browser_post_keeps_oauth_challenge() -> None:
    """Non-browser clients may omit Origin and still reach the OAuth boundary."""
    app, pool = _app()
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
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
            headers={"MCP-Protocol-Version": "2025-11-25"},
        )
    assert response.status_code == 401
    assert "resource_metadata" in response.headers["www-authenticate"]
    assert pool.closed is True
