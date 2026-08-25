"""Current-contract MCP surface and deployment-policy tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.app.config import load_settings


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


@pytest.mark.parametrize(
    "name", ["MCP_RATE_LIMIT_REQUESTS", "MCP_RATE_LIMIT_WINDOW_SECONDS"]
)
def test_mcp_quota_inputs_must_be_positive_integers(monkeypatch, name) -> None:
    """Malformed deployment policy is rejected during configuration."""
    monkeypatch.setenv(name, "0")
    with pytest.raises(ValueError, match="positive"):
        load_settings()
