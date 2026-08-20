"""Test-only Global Ask quota dependencies for non-rate-limit MCP regressions."""

from __future__ import annotations

from backend.app.mcp_rate_limit import RateLimitDecision


class AllowAllRateLimiter:
    """Permit calls while recording the authenticated principal under test."""

    def __init__(self) -> None:
        self.principal_ids: list[str] = []

    async def acquire(self, principal_id: str) -> RateLimitDecision:
        self.principal_ids.append(principal_id)
        return RateLimitDecision(allowed=True, retry_after_seconds=0)
