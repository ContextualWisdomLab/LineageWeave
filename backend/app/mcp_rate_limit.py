"""Distributed, principal-scoped admission for expensive MCP Global Ask calls.

The limiter uses one atomic Valkey Lua script and the Valkey server clock. It
never falls back to process-local counters because doing so would let callers
bypass policy by switching replicas. Rate-limit failures are represented as
structured JSON-RPC errors at the MCP layer; the pinned MCP SDK does not yet
provide a stable supported hook for preserving an application HTTP 429 response
through Streamable HTTP.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Protocol

GLOBAL_ASK_RATE_LIMIT_ERROR_CODE = -32029
GLOBAL_ASK_RATE_LIMIT_UNAVAILABLE_ERROR_CODE = -32028
DEFAULT_RATE_LIMIT_KEY_PREFIX = "lineageweave:mcp:global_ask:principal"

_FIXED_WINDOW_SCRIPT = """
local maximum_requests = tonumber(ARGV[1])
local window_milliseconds = tonumber(ARGV[2])
local server_time = redis.call('TIME')
local now_milliseconds = tonumber(server_time[1]) * 1000 + math.floor(tonumber(server_time[2]) / 1000)
local bucket_number = math.floor(now_milliseconds / window_milliseconds)
local bucket_key = KEYS[1] .. ':' .. tostring(bucket_number)
local current_count = redis.call('INCR', bucket_key)
if current_count == 1 then
    redis.call('PEXPIRE', bucket_key, window_milliseconds + 1000)
end
local reset_milliseconds = (bucket_number + 1) * window_milliseconds
local retry_milliseconds = math.max(1, reset_milliseconds - now_milliseconds)
if current_count <= maximum_requests then
    return {1, 0}
end
return {0, retry_milliseconds}
""".strip()


class GlobalAskRateLimitUnavailable(RuntimeError):
    """The shared limiter could not make a trustworthy distributed decision."""


@dataclass(frozen=True)
class RateLimitDecision:
    """One bounded shared-window decision for an authenticated principal."""

    allowed: bool
    retry_after_seconds: int


class GlobalAskRateLimiter(Protocol):
    """Consume one authenticated Global Ask invocation allowance."""

    async def acquire(self, principal_id: str) -> RateLimitDecision:
        """Return a distributed decision for ``principal_id``."""

        raise NotImplementedError


class ValkeyGlobalAskRateLimiter:
    """Fixed-window Valkey limiter using one atomic server-time script."""

    def __init__(
        self,
        client: Any,
        *,
        maximum_requests: int,
        window_seconds: int,
        key_prefix: str = DEFAULT_RATE_LIMIT_KEY_PREFIX,
    ) -> None:
        if not 1 <= maximum_requests <= 10_000:
            raise ValueError("maximum_requests must be between 1 and 10000")
        if not 1 <= window_seconds <= 86_400:
            raise ValueError("window_seconds must be between 1 and 86400")
        if not key_prefix.strip():
            raise ValueError("key_prefix is required")
        self._client = client
        self._maximum_requests = maximum_requests
        self._window_seconds = window_seconds
        self._key_prefix = key_prefix.rstrip(":")

    def _principal_key(self, principal_id: str) -> str:
        """Return a stable opaque key without persisting the account UUID."""
        normalized = principal_id.strip()
        if not normalized:
            raise GlobalAskRateLimitUnavailable("authenticated principal id is empty")
        digest = hashlib.sha256(
            f"lineageweave-mcp-global-ask\x00{normalized}".encode("utf-8")
        ).hexdigest()
        return f"{self._key_prefix}:{digest}"

    async def acquire(self, principal_id: str) -> RateLimitDecision:
        """Atomically consume one fixed-window allowance or fail closed."""
        key = self._principal_key(principal_id)
        try:
            raw_result = await self._client.eval(
                _FIXED_WINDOW_SCRIPT,
                1,
                key,
                self._maximum_requests,
                self._window_seconds * 1000,
            )
        except (OSError, TimeoutError, TypeError, ValueError) as exc:
            raise GlobalAskRateLimitUnavailable(
                "distributed rate-limit backend is unavailable"
            ) from exc
        if (
            not isinstance(raw_result, (list, tuple))
            or len(raw_result) != 2
            or isinstance(raw_result[0], bool)
            or isinstance(raw_result[1], bool)
        ):
            raise GlobalAskRateLimitUnavailable(
                "distributed rate-limit backend returned an invalid decision"
            )
        try:
            allowed_number = int(raw_result[0])
            retry_milliseconds = int(raw_result[1])
        except (TypeError, ValueError) as exc:
            raise GlobalAskRateLimitUnavailable(
                "distributed rate-limit backend returned a non-numeric decision"
            ) from exc
        if allowed_number not in {0, 1} or retry_milliseconds < 0:
            raise GlobalAskRateLimitUnavailable(
                "distributed rate-limit backend returned an out-of-range decision"
            )
        if allowed_number == 1:
            if retry_milliseconds != 0:
                raise GlobalAskRateLimitUnavailable(
                    "distributed rate-limit backend returned conflicting allowance metadata"
                )
            return RateLimitDecision(allowed=True, retry_after_seconds=0)
        retry_after_seconds = max(
            1,
            min(
                self._window_seconds,
                math.ceil(retry_milliseconds / 1000),
            ),
        )
        return RateLimitDecision(
            allowed=False,
            retry_after_seconds=retry_after_seconds,
        )


__all__ = [
    "DEFAULT_RATE_LIMIT_KEY_PREFIX",
    "GLOBAL_ASK_RATE_LIMIT_ERROR_CODE",
    "GLOBAL_ASK_RATE_LIMIT_UNAVAILABLE_ERROR_CODE",
    "GlobalAskRateLimitUnavailable",
    "GlobalAskRateLimiter",
    "RateLimitDecision",
    "ValkeyGlobalAskRateLimiter",
]
