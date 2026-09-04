"""Timeout contracts for the optional exact-version translation cache."""

from __future__ import annotations

import asyncio
import hashlib

from backend.app.translation_ledger import (
    TranslationScreen,
    _read_exact_cache,
    _write_exact_cache,
)


class _HangingCache:
    """Valkey-shaped cache that never returns without cancellation."""

    async def get(self, _key: str) -> str:
        """Wait forever so the read model must impose its own cache deadline."""
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Wait forever so cache population cannot pin the buyer request."""
        assert ex > 0
        await asyncio.Event().wait()


def _screen() -> TranslationScreen:
    """Build one valid immutable projection for cache-write timeout coverage."""
    return TranslationScreen(
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=7,
        locale="en",
        cache_key="ui-translation:lineageweave:customer-master:v7:en",
        translations={"title": "Customer master"},
    )


def test_hung_cache_read_converges_to_miss_within_request_budget() -> None:
    """A non-authoritative Valkey read cannot prevent PostgreSQL fallback forever."""
    expected_digest = hashlib.sha256(b"Customer master").hexdigest()
    result = asyncio.run(
        asyncio.wait_for(
            _read_exact_cache(
                _HangingCache(),
                "ui-translation:lineageweave:customer-master:v7:en",
                product_key="lineageweave",
                screen_key="customer-master",
                resource_version=7,
                locale="en",
                expected_text_digests={"title": expected_digest},
            ),
            timeout=0.1,
        )
    )
    assert result is None


def test_hung_cache_write_does_not_hold_request_open() -> None:
    """Optional cache population must return even when Valkey never answers."""
    asyncio.run(
        asyncio.wait_for(
            _write_exact_cache(_HangingCache(), _screen()),
            timeout=0.1,
        )
    )
