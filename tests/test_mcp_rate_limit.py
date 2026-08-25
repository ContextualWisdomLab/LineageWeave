"""Shared MCP quota regressions."""

from __future__ import annotations

import hashlib

import pytest

from backend.app.mcp_rate_limit import (
    McpRateLimiterUnavailable,
    McpRateLimitExceeded,
    ValkeyMcpRateLimiter,
    build_mcp_rate_limiter,
)


class FakeValkey:
    """Return a configured Lua result without a real Valkey server."""

    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.call = None
        self.closed = False

    async def eval(self, *args):
        """Record and answer one script invocation."""
        self.call = args
        if self.error:
            raise self.error
        return self.result

    async def aclose(self) -> None:
        """Record closure."""
        self.closed = True


@pytest.mark.anyio
async def test_limiter_uses_opaque_account_key_and_atomic_window() -> None:
    client = FakeValkey([1, 60])
    limiter = ValkeyMcpRateLimiter(client, request_limit=2, window_seconds=60)
    await limiter.consume("customer-account")
    assert client.call[1:] == (
        1,
        "lineageweave:mcp-rate-limit:v1:"
        + hashlib.sha256(b"customer-account").hexdigest(),
        60,
    )


@pytest.mark.anyio
async def test_limiter_returns_bounded_retry_after_and_closes() -> None:
    client = FakeValkey([3, 900])
    limiter = ValkeyMcpRateLimiter(client, request_limit=2, window_seconds=60)
    with pytest.raises(McpRateLimitExceeded) as caught:
        await limiter.consume("account")
    assert caught.value.retry_after_seconds == 60
    await limiter.close()
    assert client.closed


@pytest.mark.anyio
@pytest.mark.parametrize("result", [None, [1], [0, 60], [1, -1]])
async def test_limiter_fails_closed_for_invalid_state(result) -> None:
    limiter = ValkeyMcpRateLimiter(
        FakeValkey(result), request_limit=2, window_seconds=60
    )
    with pytest.raises(McpRateLimiterUnavailable):
        await limiter.consume("account")


@pytest.mark.anyio
async def test_limiter_fails_closed_for_valkey_error() -> None:
    limiter = ValkeyMcpRateLimiter(
        FakeValkey(error=RuntimeError("offline")), request_limit=2, window_seconds=60
    )
    with pytest.raises(McpRateLimiterUnavailable):
        await limiter.consume("account")


def test_builder_uses_shared_valkey_factory(monkeypatch) -> None:
    """The production builder wires the configured shared Valkey URL."""
    client = FakeValkey([1, 60])
    monkeypatch.setattr(
        "backend.app.mcp_rate_limit.create_valkey_client",
        lambda url: client if url == "redis://shared" else None,
    )
    limiter = build_mcp_rate_limiter("redis://shared", 2, 60)
    assert limiter._client is client
