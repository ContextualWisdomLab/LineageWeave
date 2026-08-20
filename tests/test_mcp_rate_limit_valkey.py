from __future__ import annotations

import os
import uuid

import pytest

from backend.app.activity_stream import create_valkey_client
from backend.app.mcp_rate_limit import ValkeyGlobalAskRateLimiter


@pytest.mark.asyncio
async def test_real_valkey_window_is_shared_bounded_and_principal_isolated() -> None:
    """Two limiter instances observe one counter while another principal stays isolated."""
    url = os.environ.get("LINEAGEWEAVE_TEST_VALKEY_URL")
    if not url:
        pytest.skip("LINEAGEWEAVE_TEST_VALKEY_URL is not configured")

    namespace = f"lineageweave:test:mcp:{uuid.uuid4().hex}"
    client_a = create_valkey_client(url)
    client_b = create_valkey_client(url)
    try:
        limiter_a = ValkeyGlobalAskRateLimiter(
            client_a,
            maximum_requests=2,
            window_seconds=30,
            key_prefix=namespace,
        )
        limiter_b = ValkeyGlobalAskRateLimiter(
            client_b,
            maximum_requests=2,
            window_seconds=30,
            key_prefix=namespace,
        )

        first = await limiter_a.acquire("principal-a")
        second = await limiter_b.acquire("principal-a")
        denied = await limiter_a.acquire("principal-a")
        isolated = await limiter_b.acquire("principal-b")

        assert first.allowed is True
        assert second.allowed is True
        assert denied.allowed is False
        assert 1 <= denied.retry_after_seconds <= 30
        assert isolated.allowed is True

        keys = [
            key.decode("utf-8") if isinstance(key, bytes) else str(key)
            async for key in client_a.scan_iter(match=f"{namespace}:*")
        ]
        assert len(keys) == 2
        assert all("principal-a" not in key and "principal-b" not in key for key in keys)
        assert all(await client_a.pttl(key) > 0 for key in keys)
    finally:
        keys = [key async for key in client_a.scan_iter(match=f"{namespace}:*")]
        if keys:
            await client_a.delete(*keys)
        await client_b.aclose()
        await client_a.aclose()
