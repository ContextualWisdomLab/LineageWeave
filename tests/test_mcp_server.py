from __future__ import annotations

import asyncio
import base64
import json

import pytest
from starlette.requests import Request

import backend.app.mcp_server as mcp
from backend.app.auth import CurrentAccount


def _segment(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unsigned_token(header: dict) -> str:
    return f"{_segment(header)}.{_segment({'sub': 'subject'})}.signature"


def _account() -> CurrentAccount:
    return CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Demo Analyst",
        preferred_locale="ko-KR",
        corporate_entity_ids=frozenset({"corp-demo"}),
        permission_codes=frozenset({"post_read"}),
    )


def _request(origin: str | None = None) -> Request:
    headers = [] if origin is None else [(b"origin", origin.encode())]
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/mcp",
            "raw_path": b"/mcp",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": ("lineage.example", 443),
        }
    )


def test_mcp_settings_validate_resource_and_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "https://lineage.example/mcp")
    monkeypatch.setenv("LINEAGEWEAVE_MCP_ALLOWED_ORIGINS", "https://codex.example, https://admin.example")
    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "17")
    settings = mcp.load_mcp_settings()
    assert settings.resource_uri == "https://lineage.example/mcp"
    assert settings.allowed_origins == frozenset({"https://codex.example", "https://admin.example"})
    assert settings.requests_per_minute == 17

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "file:///etc/passwd")
    with pytest.raises(ValueError, match="absolute http"):
        mcp.load_mcp_settings()

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "https://lineage.example/mcp")
    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "0")
    with pytest.raises(ValueError, match="between 1 and 600"):
        mcp.load_mcp_settings()

    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "not-a-number")
    with pytest.raises(ValueError, match="must be an integer"):
        mcp.load_mcp_settings()


def test_origin_is_fail_closed_only_when_browser_origin_is_present() -> None:
    settings = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset({"https://codex.example"}),
        requests_per_minute=30,
    )
    mcp._validate_origin(_request(), settings)
    mcp._validate_origin(_request("https://codex.example"), settings)
    with pytest.raises(Exception) as error:
        mcp._validate_origin(_request("https://evil.example"), settings)
    assert getattr(error.value, "status_code", None) == 403


def test_signing_key_requires_nonempty_exact_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp.RSAAlgorithm, "from_jwk", lambda value: ("key", value))
    jwks = {
        "keys": [
            {"kid": "first", "kty": "RSA", "alg": "RS256", "n": "x", "e": "AQAB"},
            {"kid": "wanted", "kty": "RSA", "alg": "RS256", "n": "y", "e": "AQAB"},
        ]
    }
    key = mcp._mcp_signing_key(jwks, _unsigned_token({"alg": "RS256", "kid": "wanted"}))
    assert key[0] == "key"
    assert '"kid": "wanted"' in key[1]

    with pytest.raises(Exception) as missing:
        mcp._mcp_signing_key(jwks, _unsigned_token({"alg": "RS256"}))
    assert getattr(missing.value, "status_code", None) == 401

    with pytest.raises(Exception) as unknown:
        mcp._mcp_signing_key(jwks, _unsigned_token({"alg": "RS256", "kid": "unknown"}))
    assert getattr(unknown.value, "status_code", None) == 401


def test_access_token_decode_binds_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(mcp, "_mcp_jwks", lambda settings: {"keys": []})
    monkeypatch.setattr(mcp, "_mcp_signing_key", lambda jwks, token: "signing-key")

    def fake_decode(token, **kwargs):
        captured.update(kwargs)
        return {"sub": "subject-1"}

    monkeypatch.setattr(mcp.jwt, "decode", fake_decode)
    shared = type(
        "SettingsStub",
        (),
        {"oidc_issuer": "https://id.example", "oidc_clock_skew_seconds": 5},
    )()
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    claims = mcp._decode_mcp_access_token("token", shared, runtime)
    assert claims["sub"] == "subject-1"
    assert captured["issuer"] == "https://id.example"
    assert captured["audience"] == "https://lineage.example/mcp"
    assert captured["algorithms"] == ["RS256"]


def test_access_token_requires_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp, "_mcp_jwks", lambda settings: {"keys": []})
    monkeypatch.setattr(mcp, "_mcp_signing_key", lambda jwks, token: "signing-key")
    monkeypatch.setattr(mcp.jwt, "decode", lambda *args, **kwargs: {})
    shared = type(
        "SettingsStub",
        (),
        {"oidc_issuer": "https://id.example", "oidc_clock_skew_seconds": 5},
    )()
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    with pytest.raises(Exception) as error:
        mcp._decode_mcp_access_token("token", shared, runtime)
    assert getattr(error.value, "status_code", None) == 401


def test_initialize_and_tool_catalog_are_current_protocol() -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    initialize = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
            object(),
            _account(),
            runtime,
        )
    )
    assert initialize["result"]["protocolVersion"] == "2025-06-18"
    assert initialize["result"]["capabilities"] == {"tools": {"listChanged": False}}

    tools = asyncio.run(
        mcp._dispatch_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            object(),
            _account(),
            runtime,
        )
    )
    tool = tools["result"]["tools"][0]
    assert tool["name"] == "global_ask"
    assert tool["annotations"]["readOnlyHint"] is True
    assert tool["annotations"]["openWorldHint"] is False
    assert tool["outputSchema"] == mcp._GLOBAL_ASK_OUTPUT_SCHEMA


def test_initialize_rejects_other_protocol_and_initialized_notification_is_silent() -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    rejected = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            },
            object(),
            _account(),
            runtime,
        )
    )
    assert rejected["error"]["code"] == -32602
    notification = asyncio.run(
        mcp._dispatch_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            object(),
            _account(),
            runtime,
        )
    )
    assert notification is None


def test_global_ask_tool_returns_structured_and_text_content(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    expected = {
        "answer_text": "Grounded answer",
        "cited_post_ids": ["post-1"],
        "cited_posts": [{"post_id": "post-1", "post_title": "Evidence"}],
        "cited_post_evidence": [{"post_id": "post-1", "facts": ["source record"]}],
        "source_post_ids": ["post-1"],
        "next_action": None,
    }

    async def fake_ask(pool, account, question):
        assert account.user_account_id == "account-1"
        assert question == "What changed?"
        return expected

    async def no_limit(account_id, limit):
        assert account_id == "account-1"
        assert limit == 30

    monkeypatch.setattr(mcp, "_global_ask", fake_ask)
    monkeypatch.setattr(mcp, "_check_rate_limit", no_limit)
    response = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "global_ask", "arguments": {"question": "What changed?"}},
            },
            object(),
            _account(),
            runtime,
        )
    )
    result = response["result"]
    assert result["structuredContent"] == expected
    assert json.loads(result["content"][0]["text"]) == expected
    assert result["isError"] is False


def test_tool_validation_and_execution_failure_are_distinct(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    unknown = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "write_everything", "arguments": {}},
            },
            object(),
            _account(),
            runtime,
        )
    )
    assert unknown["error"]["code"] == -32602

    invalid = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "global_ask", "arguments": {"question": "   ", "extra": 1}},
            },
            object(),
            _account(),
            runtime,
        )
    )
    assert invalid["error"]["code"] == -32602

    async def no_limit(account_id, limit):
        return None

    async def unavailable(pool, account, question):
        raise RuntimeError("orchestrator unavailable")

    monkeypatch.setattr(mcp, "_check_rate_limit", no_limit)
    monkeypatch.setattr(mcp, "_global_ask", unavailable)
    failed = asyncio.run(
        mcp._dispatch_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "global_ask", "arguments": {"question": "Question"}},
            },
            object(),
            _account(),
            runtime,
        )
    )
    assert "error" not in failed
    assert failed["result"]["isError"] is True
    assert failed["result"]["content"][0]["text"] == "orchestrator unavailable"


def test_rate_limit_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    mcp._RATE_WINDOWS.clear()
    times = iter([10.0, 10.1, 10.2])
    monkeypatch.setattr(mcp.time, "monotonic", lambda: next(times))
    asyncio.run(mcp._check_rate_limit("account", 2))
    asyncio.run(mcp._check_rate_limit("account", 2))
    with pytest.raises(Exception) as error:
        asyncio.run(mcp._check_rate_limit("account", 2))
    assert getattr(error.value, "status_code", None) == 429


def test_invalid_jsonrpc_and_unknown_method_return_protocol_errors() -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    invalid = asyncio.run(mcp._dispatch_message({"id": 1}, object(), _account(), runtime))
    assert invalid["error"]["code"] == -32600
    missing = asyncio.run(
        mcp._dispatch_message(
            {"jsonrpc": "2.0", "id": 2, "method": "resources/list"},
            object(),
            _account(),
            runtime,
        )
    )
    assert missing["error"]["code"] == -32601
