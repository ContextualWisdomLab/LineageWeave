"""Query-budget contract for immutable exact-version translation reads."""

from __future__ import annotations

import asyncio
import hashlib

from backend.app.translation_ledger import read_translation_screen


class _Connection:
    """Return one published exact-version projection while recording fetches."""

    def __init__(self) -> None:
        self.fetch_count = 0

    async def fetch(self, *_args: object) -> list[dict[str, object]]:
        """Return rows shaped for both current translation-ledger SELECTs."""
        self.fetch_count += 1
        return [
            {
                "resource_version": 7,
                "translation_key": "body",
                "translated_text": "No customers",
                "translated_text_sha256": hashlib.sha256(b"No customers").hexdigest(),
            },
            {
                "resource_version": 7,
                "translation_key": "title",
                "translated_text": "Customer master",
                "translated_text_sha256": hashlib.sha256(b"Customer master").hexdigest(),
            },
        ]


class _Acquire:
    """Track one pool lease without suppressing failures."""

    def __init__(self, pool: "_Pool") -> None:
        self.pool = pool

    async def __aenter__(self) -> _Connection:
        """Expose the shared fake connection."""
        self.pool.active_leases += 1
        return self.pool.connection

    async def __aexit__(self, *_args: object) -> None:
        """Release the fake lease."""
        self.pool.active_leases -= 1
        return None


class _Pool:
    """Count PostgreSQL acquisitions for the buyer-facing exact-version path."""

    def __init__(self) -> None:
        self.connection = _Connection()
        self.acquire_count = 0
        self.active_leases = 0

    def acquire(self) -> _Acquire:
        """Return a counted async acquisition context."""
        self.acquire_count += 1
        return _Acquire(self)


class _MissingCache:
    """Represent an exact-version Valkey miss and assert DB lease release."""

    def __init__(self, pool: _Pool) -> None:
        self.pool = pool
        self.set_count = 0

    async def get(self, _key: str) -> None:
        """Miss only after PostgreSQL has released its connection lease."""
        assert self.pool.active_leases == 0
        return None

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Record repopulation after the authoritative projection is resolved."""
        assert ex == 300
        assert self.pool.active_leases == 0
        self.set_count += 1


def test_exact_version_cache_miss_reuses_authoritative_digest_query_projection() -> None:
    """An immutable exact-version miss must not reacquire rows already verified."""
    pool = _Pool()
    cache = _MissingCache(pool)

    result = asyncio.run(
        read_translation_screen(
            pool,  # type: ignore[arg-type]
            cache,
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
            resource_version=7,
        )
    )

    assert result.translations == {"body": "No customers", "title": "Customer master"}
    assert pool.acquire_count == 1
    assert pool.connection.fetch_count == 1
    assert cache.set_count == 1
