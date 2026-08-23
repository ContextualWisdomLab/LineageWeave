from __future__ import annotations

import hashlib

import pytest

from backend.app.mcp_rate_limit import (
    McpRateLimitExceeded,
    McpRateLimiterUnavailable,
    ValkeyMcpRateLimiter,
)


class FakeValkey:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.call = None

    async def eval(self, *args):
        self.call = args
        if self.error:
            raise self.error
        return self.result

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_limiter_uses_opaque_account_key_and_atomic_window() -> None:
    client = FakeValkey([1, 60])
    limiter = ValkeyMcpRateLimiter(client, request_limit=2, window_seconds=60)
    await limiter.consume("customer-account")
    assert client.call[1] == 1
    assert client.call[2] == (
        "lineageweave:mcp-rate-limit:v1:"
        + hashlib.sha256(b"customer-account").hexdigest()
    )
    assert "customer-account" not in client.call[2]
    assert client.call[3] == 60


@pytest.mark.asyncio
async def test_limiter_returns_bounded_retry_after() -> None:
    limiter = ValkeyMcpRateLimiter(FakeValkey([3, 900]), request_limit=2, window_seconds=60)
    with pytest.raises(McpRateLimitExceeded) as caught:
        await limiter.consume("account")
    assert caught.value.retry_after_seconds == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [None, [1], [0, 60], [1, -1]])
async def test_limiter_fails_closed_for_unavailable_or_invalid_state(result) -> None:
    limiter = ValkeyMcpRateLimiter(FakeValkey(result), request_limit=2, window_seconds=60)
    with pytest.raises(McpRateLimiterUnavailable):
        await limiter.consume("account")
