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


def _request(*, origin: str | None = None, headers: dict[str, str] | None = None) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        raw_headers.append((b"origin", origin.encode()))
    for name, value in (headers or {}).items():
        raw_headers.append((name.lower().encode(), value.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/mcp",
            "raw_path": b"/mcp",
            "query_string": b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 1234),
            "server": ("lineage.example", 443),
        }
    )


def _meta() -> dict:
    return {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "test-client", "version": "1.0.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }


def _message(method: str, *, request_id: int = 1, **params) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {**params, "_meta": _meta()},
    }


class FakeValkey:
    def __init__(self, counts: list[int] | None = None) -> None:
        self.counts = list(counts or [1])
        self.calls: list[tuple[str, int, str]] = []

    async def eval(self, script: str, key_count: int, key: str) -> int:
        self.calls.append((script, key_count, key))
        return self.counts.pop(0)


def test_mcp_settings_validate_resource_and_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "https://lineage.example/mcp")
    monkeypatch.setenv(
        "LINEAGEWEAVE_MCP_ALLOWED_ORIGINS", "https://codex.example, https://admin.example"
    )
    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "17")
    settings = mcp.load_mcp_settings()
    assert settings.resource_uri == "https://lineage.example/mcp"
    assert settings.allowed_origins == frozenset({"https://codex.example", "https://admin.example"})
    assert settings.requests_per_minute == 17

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "file:///etc/passwd")
    with pytest.raises(ValueError, match="absolute http"):
        mcp.load_mcp_settings()

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "http://lineage.example/mcp")
    with pytest.raises(ValueError, match="HTTPS"):
        mcp.load_mcp_settings()

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "http://localhost:18421/mcp")
    assert mcp.load_mcp_settings().resource_uri == "http://localhost:18421/mcp"

    monkeypatch.setenv("LINEAGEWEAVE_MCP_RESOURCE_URI", "https://lineage.example/mcp")
    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "0")
    with pytest.raises(ValueError, match="between 1 and 600"):
        mcp.load_mcp_settings()

    monkeypatch.setenv("LINEAGEWEAVE_MCP_REQUESTS_PER_MINUTE", "not-a-number")
    with pytest.raises(ValueError, match="must be an integer"):
        mcp.load_mcp_settings()


def test_transport_target_checks_origin_and_host() -> None:
    settings = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset({"https://codex.example"}),
        requests_per_minute=30,
    )
    mcp._validate_transport_target(_request(), settings)
    mcp._validate_transport_target(
        _request(origin="https://codex.example", headers={"Host": "lineage.example"}), settings
    )
    with pytest.raises(Exception) as origin_error:
        mcp._validate_transport_target(_request(origin="https://evil.example"), settings)
    assert getattr(origin_error.value, "status_code", None) == 403
    with pytest.raises(Exception) as host_error:
        mcp._validate_transport_target(_request(headers={"Host": "evil.example"}), settings)
    assert getattr(host_error.value, "status_code", None) == 400


def test_resource_metadata_url_uses_canonical_resource_not_request_host() -> None:
    settings = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/public/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    assert (
        mcp._resource_metadata_url(settings)
        == "https://lineage.example/.well-known/oauth-protected-resource/public/mcp"
    )


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


def test_request_envelope_requires_current_protocol_and_capabilities() -> None:
    params, meta = mcp._request_envelope(_message("tools/list"))
    assert params["_meta"] is meta
    assert meta["io.modelcontextprotocol/protocolVersion"] == "2026-07-28"

    missing = _message("tools/list")
    del missing["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"]
    with pytest.raises(ValueError, match="clientCapabilities"):
        mcp._request_envelope(missing)

    old = _message("tools/list")
    old["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2025-06-18"
    with pytest.raises(RuntimeError):
        mcp._request_envelope(old)


def test_transport_headers_follow_final_error_precedence() -> None:
    message = _message("tools/call", name="global_ask", arguments={"question": "Q"})
    valid = _request(
        headers={
            "MCP-Protocol-Version": "2026-07-28",
            "Mcp-Method": "tools/call",
            "Mcp-Name": "global_ask",
        }
    )
    assert mcp._validate_transport_headers(valid, message) is None

    mismatch = _request(
        headers={
            "MCP-Protocol-Version": "2025-06-18",
            "Mcp-Method": "tools/call",
            "Mcp-Name": "global_ask",
        }
    )
    response = mcp._validate_transport_headers(mismatch, message)
    assert response.status_code == 400
    assert b'"code":-32020' in response.body

    old_message = _message("tools/call", name="global_ask", arguments={"question": "Q"})
    old_message["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "2025-06-18"
    old_header = _request(
        headers={
            "MCP-Protocol-Version": "2025-06-18",
            "Mcp-Method": "tools/call",
            "Mcp-Name": "global_ask",
        }
    )
    response = mcp._validate_transport_headers(old_header, old_message)
    assert response.status_code == 400
    assert b'"code":-32022' in response.body
    assert b'"supported":["2026-07-28"]' in response.body
    assert b'"requested":"2025-06-18"' in response.body


def test_discover_and_tool_catalog_are_stateless_current_protocol() -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    discover, discover_status = asyncio.run(
        mcp._dispatch_message(
            _message("server/discover"), object(), FakeValkey(), _account(), runtime
        )
    )
    assert discover_status == 200
    assert discover["result"]["supportedVersions"] == ["2026-07-28"]
    assert discover["result"]["resultType"] == "complete"
    assert discover["result"]["ttlMs"] == 0
    assert discover["result"]["cacheScope"] == "private"
    assert discover["result"]["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "lineageweave"

    tools, tools_status = asyncio.run(
        mcp._dispatch_message(_message("tools/list"), object(), FakeValkey(), _account(), runtime)
    )
    assert tools_status == 200
    tool = tools["result"]["tools"][0]
    assert tool["name"] == "global_ask"
    assert tool["annotations"]["readOnlyHint"] is True
    assert tool["annotations"]["openWorldHint"] is False
    assert tool["outputSchema"] == mcp._GLOBAL_ASK_OUTPUT_SCHEMA
    assert tools["result"]["ttlMs"] == 0
    assert tools["result"]["cacheScope"] == "private"


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

    async def no_limit(client, account_id, limit):
        assert account_id == "account-1"
        assert limit == 30

    monkeypatch.setattr(mcp, "_global_ask", fake_ask)
    monkeypatch.setattr(mcp, "_check_rate_limit", no_limit)
    response, http_status = asyncio.run(
        mcp._dispatch_message(
            _message(
                "tools/call",
                request_id=7,
                name="global_ask",
                arguments={"question": "What changed?"},
            ),
            object(),
            FakeValkey(),
            _account(),
            runtime,
        )
    )
    assert http_status == 200
    result = response["result"]
    assert result["structuredContent"] == expected
    assert json.loads(result["content"][0]["text"]) == expected
    assert result["isError"] is False
    assert result["resultType"] == "complete"


def test_tool_validation_execution_failure_and_unknown_method_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    unknown_tool, unknown_status = asyncio.run(
        mcp._dispatch_message(
            _message("tools/call", name="write_everything", arguments={}),
            object(),
            FakeValkey(),
            _account(),
            runtime,
        )
    )
    assert unknown_status == 200
    assert unknown_tool["error"]["code"] == -32602

    async def no_limit(client, account_id, limit):
        return None

    async def unavailable(pool, account, question):
        raise RuntimeError("orchestrator unavailable")

    monkeypatch.setattr(mcp, "_check_rate_limit", no_limit)
    monkeypatch.setattr(mcp, "_global_ask", unavailable)
    failed, failed_status = asyncio.run(
        mcp._dispatch_message(
            _message(
                "tools/call",
                name="global_ask",
                arguments={"question": "Question"},
            ),
            object(),
            FakeValkey(),
            _account(),
            runtime,
        )
    )
    assert failed_status == 200
    assert "error" not in failed
    assert failed["result"]["isError"] is True
    assert failed["result"]["content"][0]["text"] == "orchestrator unavailable"

    missing, missing_status = asyncio.run(
        mcp._dispatch_message(
            _message("resources/list"), object(), FakeValkey(), _account(), runtime
        )
    )
    assert missing_status == 404
    assert missing["error"]["code"] == -32601


def test_rate_limit_uses_valkey_and_rejects_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp.time, "time", lambda: 600.0)
    allowed = FakeValkey([2])
    asyncio.run(mcp._check_rate_limit(allowed, "account", 2))
    assert allowed.calls[0][1] == 1
    assert allowed.calls[0][2] == "mcp:rate:account:10"

    denied = FakeValkey([3])
    with pytest.raises(Exception) as error:
        asyncio.run(mcp._check_rate_limit(denied, "account", 2))
    assert getattr(error.value, "status_code", None) == 429


def test_invalid_jsonrpc_and_notification_behavior() -> None:
    runtime = mcp.McpRuntimeSettings(
        resource_uri="https://lineage.example/mcp",
        allowed_origins=frozenset(),
        requests_per_minute=30,
    )
    invalid, invalid_status = asyncio.run(
        mcp._dispatch_message({"id": 1}, object(), FakeValkey(), _account(), runtime)
    )
    assert invalid_status == 200
    assert invalid["error"]["code"] == -32600

    notification = _message("notifications/custom")
    notification.pop("id")
    response, response_status = asyncio.run(
        mcp._dispatch_message(notification, object(), FakeValkey(), _account(), runtime)
    )
    assert response is None
    assert response_status == 202
