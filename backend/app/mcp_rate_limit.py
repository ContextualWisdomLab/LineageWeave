"""Valkey-backed quota for authenticated, provisioned MCP accounts."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.app.activity_stream import create_valkey_client

_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


class McpRateLimitExceeded(Exception):
    """The account exhausted its current shared window."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("MCP account rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


class McpRateLimiterUnavailable(Exception):
    """The shared limiter could not make an authoritative decision."""


class ValkeyMcpRateLimiter:
    """Consume one atomic fixed-window quota entry in shared Valkey."""

    def __init__(self, client: Any, *, request_limit: int, window_seconds: int) -> None:
        self._client = client
        self._request_limit = request_limit
        self._window_seconds = window_seconds

    async def consume(self, user_account_id: str) -> None:
        """Consume one provisioned account request or fail closed."""
        digest = hashlib.sha256(user_account_id.encode("utf-8")).hexdigest()
        key = f"lineageweave:mcp-rate-limit:v1:{digest}"
        try:
            result = await self._client.eval(_SCRIPT, 1, key, self._window_seconds)
            count, ttl = int(result[0]), int(result[1])
        except Exception as exc:
            raise McpRateLimiterUnavailable(
                "shared MCP rate limiter unavailable"
            ) from exc
        if count < 1 or ttl < 0:
            raise McpRateLimiterUnavailable(
                "shared MCP rate limiter returned invalid state"
            )
        if count > self._request_limit:
            raise McpRateLimitExceeded(max(1, min(ttl, self._window_seconds)))

    async def close(self) -> None:
        """Close the underlying Valkey client."""
        await self._client.aclose()


def build_mcp_rate_limiter(
    valkey_url: str, request_limit: int, window_seconds: int
) -> ValkeyMcpRateLimiter:
    """Build the limiter from validated deployment settings."""
    return ValkeyMcpRateLimiter(
        create_valkey_client(valkey_url),
        request_limit=request_limit,
        window_seconds=window_seconds,
    )
