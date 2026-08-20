from __future__ import annotations

from dataclasses import replace

import pytest
from mcp.client import Client
from mcp.server.auth.provider import AccessToken
from mcp.shared.exceptions import MCPError

from backend.app import mcp_rate_limit, mcp_server
from backend.app.auth import CurrentAccount
from backend.app.global_ask import GlobalAskAnswer
from backend.app.global_ask_media import GlobalAskContentBlock


ACCOUNT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class _FakeValkey:
    """Return one scripted atomic-window result and record opaque keying."""

    def __init__(self, result: object = (1, 0), error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    async def eval(self, *args: object) -> object:
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result


@pytest.mark.asyncio
async def test_valkey_limiter_uses_one_atomic_script_and_opaque_principal_key() -> None:
    client = _FakeValkey(result=(1, 0))
    limiter = mcp_rate_limit.ValkeyGlobalAskRateLimiter(
        client,
        maximum_requests=3,
        window_seconds=60,
    )

    decision = await limiter.acquire(ACCOUNT_ID)

    assert decision.allowed is True
    assert decision.retry_after_seconds == 0
    assert len(client.calls) == 1
    script, key_count, key, maximum_requests, window_milliseconds = client.calls[0]
    assert "INCR" in script
    assert "PEXPIRE" in script
    assert "PTTL" in script
    assert "TIME" not in script
    assert "KEYS[1] .." not in script
    assert key_count == 1
    assert ACCOUNT_ID not in str(key)
    assert str(key).startswith("lineageweave:mcp:global_ask:principal:")
    assert maximum_requests == 3
    assert window_milliseconds == 60_000


@pytest.mark.asyncio
async def test_valkey_limiter_returns_bounded_retry_and_fails_closed_on_malformed_result() -> None:
    denied = mcp_rate_limit.ValkeyGlobalAskRateLimiter(
        _FakeValkey(result=(0, 60_001)),
        maximum_requests=1,
        window_seconds=60,
    )
    decision = await denied.acquire(ACCOUNT_ID)
    assert decision.allowed is False
    assert decision.retry_after_seconds == 60

    malformed = mcp_rate_limit.ValkeyGlobalAskRateLimiter(
        _FakeValkey(result=(1,)),
        maximum_requests=1,
        window_seconds=60,
    )
    with pytest.raises(mcp_rate_limit.GlobalAskRateLimitUnavailable):
        await malformed.acquire(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_valkey_limiter_never_falls_back_to_process_local_state() -> None:
    limiter = mcp_rate_limit.ValkeyGlobalAskRateLimiter(
        _FakeValkey(error=OSError("valkey unavailable")),
        maximum_requests=5,
        window_seconds=60,
    )
    with pytest.raises(mcp_rate_limit.GlobalAskRateLimitUnavailable):
        await limiter.acquire(ACCOUNT_ID)


class _Pool:
    """Minimal MCP lifespan pool."""

    closed = False

    async def close(self) -> None:
        self.closed = True


class _Limiter:
    """Deterministic integration limiter."""

    def __init__(self, decision: mcp_rate_limit.RateLimitDecision | Exception) -> None:
        self.decision = decision
        self.principals: list[str] = []

    async def acquire(self, principal_id: str) -> mcp_rate_limit.RateLimitDecision:
        self.principals.append(principal_id)
        if isinstance(self.decision, Exception):
            raise self.decision
        return self.decision


def _settings():
    return replace(
        mcp_server.load_settings(),
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
        mcp_allowed_origins=[],
        mcp_global_ask_rate_limit=2,
        mcp_global_ask_rate_window_seconds=60,
        mcp_rate_limit_unavailable_retry_seconds=5,
    )


async def _server(limiter: _Limiter, *, permissions=frozenset({"post_read"})):
    pool = _Pool()

    async def pool_factory(_database_url: str):
        return pool

    account = CurrentAccount(
        user_account_id=ACCOUNT_ID,
        external_subject_id="subject",
        display_name="Analyst",
        corporate_entity_ids=frozenset(),
        permission_codes=permissions,
    )

    async def account_resolver(_pool, _subject: str):
        return account

    async def answerer(*_args, **_kwargs):
        return GlobalAskAnswer(
            answer_text="Grounded",
            anchor_post_id="post-1",
            cited_post_ids=("post-1",),
            cited_posts=({"post_id": "post-1", "post_title": "Evidence"},),
            source_post_ids=("post-1",),
            content_blocks=(GlobalAskContentBlock(type="text", text="Grounded"),),
        )

    token = AccessToken(
        token="token",
        client_id="codex",
        scopes=[],
        subject="subject",
        resource="https://lineage.example/mcp",
    )
    return mcp_server.build_mcp_server(
        _settings(),
        pool_factory=pool_factory,
        account_resolver=account_resolver,
        answerer=answerer,
        access_token_provider=lambda: token,
        rate_limiter=limiter,
    ), pool


@pytest.mark.asyncio
async def test_global_ask_consumes_quota_after_principal_and_permission_resolution() -> None:
    limiter = _Limiter(mcp_rate_limit.RateLimitDecision(allowed=True, retry_after_seconds=0))
    server, pool = await _server(limiter)

    async with Client(server) as client:
        result = await client.call_tool("global_ask", {"question": "What happened?"})

    assert result.is_error is False
    assert limiter.principals == [ACCOUNT_ID]
    assert pool.closed is True


@pytest.mark.asyncio
async def test_global_ask_rate_limit_error_has_bounded_protocol_retry_metadata() -> None:
    limiter = _Limiter(mcp_rate_limit.RateLimitDecision(allowed=False, retry_after_seconds=17))
    server, pool = await _server(limiter)

    async with Client(server) as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool("global_ask", {"question": "What happened?"})

    assert exc_info.value.error.code == mcp_rate_limit.GLOBAL_ASK_RATE_LIMIT_ERROR_CODE
    assert exc_info.value.error.data == {
        "error_code": "global_ask_rate_limited",
        "retry_after_seconds": 17,
        "retryable": True,
        "scope": "authenticated_principal",
    }
    assert limiter.principals == [ACCOUNT_ID]
    assert pool.closed is True


@pytest.mark.asyncio
async def test_rate_limit_backend_failure_is_explicit_and_unauthorized_principal_consumes_no_quota() -> None:
    unavailable = _Limiter(mcp_rate_limit.GlobalAskRateLimitUnavailable("offline"))
    server, _pool = await _server(unavailable)
    async with Client(server) as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool("global_ask", {"question": "What happened?"})
    assert (
        exc_info.value.error.code
        == mcp_rate_limit.GLOBAL_ASK_RATE_LIMIT_UNAVAILABLE_ERROR_CODE
    )
    assert exc_info.value.error.data["error_code"] == "global_ask_rate_limit_unavailable"
    assert exc_info.value.error.data["retry_after_seconds"] == 5

    forbidden = _Limiter(mcp_rate_limit.RateLimitDecision(allowed=True, retry_after_seconds=0))
    forbidden_server, _pool = await _server(forbidden, permissions=frozenset())
    async with Client(forbidden_server) as client:
        result = await client.call_tool("global_ask", {"question": "What happened?"})
    assert result.is_error is True
    assert "post_read" in result.content[0].text
    assert forbidden.principals == []
