"""Query-budget contract for immutable exact-version translation reads."""

from __future__ import annotations

import asyncio
import hashlib
import json

from backend.app.translation_ledger import read_translation_screen


class _Connection:
    """Return one published exact-version projection while recording fetches."""

    def __init__(self) -> None:
        self.fetch_count = 0
        self.queries: list[str] = []

    async def fetch(self, *args: object) -> list[dict[str, object]]:
        """Return digest-only rows or the complete authoritative projection by query shape."""
        self.fetch_count += 1
        query = str(args[0])
        self.queries.append(query)
        if "translated_text_sha256" in query:
            return [
                {
                    "translation_key": "body",
                    "translated_text_sha256": hashlib.sha256(b"No customers").hexdigest(),
                },
                {
                    "translation_key": "title",
                    "translated_text_sha256": hashlib.sha256(b"Customer master").hexdigest(),
                },
            ]
        return [
            {
                "resource_version": 7,
                "translation_key": "body",
                "translated_text": "No customers",
            },
            {
                "resource_version": 7,
                "translation_key": "title",
                "translated_text": "Customer master",
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
    """Represent an exact-version Valkey miss before PostgreSQL work begins."""

    def __init__(self, pool: _Pool) -> None:
        self.pool = pool
        self.set_count = 0

    async def get(self, _key: str) -> None:
        """Require a cache miss to avoid a preliminary PostgreSQL digest query."""
        assert self.pool.acquire_count == 0
        assert self.pool.active_leases == 0
        return None

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Record repopulation after the authoritative projection is resolved."""
        assert ex == 300
        assert self.pool.active_leases == 0
        self.set_count += 1


class _PresentCache:
    """Return a valid candidate payload before PostgreSQL digest admission."""

    def __init__(self, pool: _Pool) -> None:
        self.pool = pool
        self.set_count = 0

    async def get(self, _key: str) -> str:
        """Return candidate copy without acquiring PostgreSQL first."""
        assert self.pool.acquire_count == 0
        assert self.pool.active_leases == 0
        return json.dumps(
            {
                "product_key": "lineageweave",
                "screen_key": "customer-master",
                "resource_version": 7,
                "locale": "en",
                "translations": {
                    "body": "No customers",
                    "title": "Customer master",
                },
            }
        )

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Record unexpected cache repopulation."""
        assert ex == 300
        self.set_count += 1


def test_exact_version_cache_miss_uses_one_full_postgres_projection() -> None:
    """An immutable exact-version miss skips a redundant digest-only PostgreSQL query."""
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
    assert "translated_text_sha256" not in pool.connection.queries[0]
    assert cache.set_count == 1


def test_exact_version_cache_hit_transfers_only_postgres_digest_evidence() -> None:
    """A valid cache hit avoids transferring the full localized PostgreSQL projection."""
    pool = _Pool()
    cache = _PresentCache(pool)

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
    assert "translated_text_sha256" in pool.connection.queries[0]
    assert "translation_text.translated_text," not in pool.connection.queries[0]
    assert cache.set_count == 0
