"""Valkey-backed quota for authenticated, provisioned MCP accounts."""

from __future__ import annotations

import hashlib
import os
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
        digest = hashlib.sha256(user_account_id.encode("utf-8")).hexdigest()
        key = f"lineageweave:mcp-rate-limit:v1:{digest}"
        try:
            result = await self._client.eval(_SCRIPT, 1, key, self._window_seconds)
            count, ttl = int(result[0]), int(result[1])
        except Exception as exc:
            raise McpRateLimiterUnavailable("shared MCP rate limiter unavailable") from exc
        if count < 1 or ttl < 0:
            raise McpRateLimiterUnavailable("shared MCP rate limiter returned invalid state")
        if count > self._request_limit:
            raise McpRateLimitExceeded(max(1, min(ttl, self._window_seconds)))

    async def close(self) -> None:
        await self._client.aclose()


def build_mcp_rate_limiter(valkey_url: str) -> ValkeyMcpRateLimiter:
    """Build the limiter from bounded runtime settings and the existing client."""
    request_limit = _bounded_env("MCP_RATE_LIMIT_REQUESTS", default=30, minimum=1, maximum=10_000)
    window_seconds = _bounded_env("MCP_RATE_LIMIT_WINDOW_SECONDS", default=60, minimum=1, maximum=3_600)
    return ValkeyMcpRateLimiter(
        create_valkey_client(valkey_url),
        request_limit=request_limit,
        window_seconds=window_seconds,
    )


def _bounded_env(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value
