"""Edge-case coverage for the versioned UI translation read model."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest
from redis.exceptions import RedisError

from backend.app.translation_ledger import (
    TranslationCoverageError,
    TranslationResourceNotFound,
    build_translation_cache_key,
    read_translation_screen,
    validate_ui_locale,
)


class FakeConnection:
    """Return deterministic asyncpg-shaped rows while recording query inputs."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[object, ...]] = []
        self.is_acquired = False

    async def fetch(self, *args: object) -> list[dict[str, object]]:
        """Record one SQL call and return the configured rows."""
        self.calls.append(args)
        return self.rows


class FakeAcquire:
    """Async context manager matching ``asyncpg.Pool.acquire`` usage."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        """Return the configured connection and expose its lease state."""
        self.connection.is_acquired = True
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        """Release the fake lease without suppressing exceptions."""
        self.connection.is_acquired = False
        return None


class FakePool:
    """Minimal pool adapter for read-model tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.connection = FakeConnection(rows)
        self.acquire_count = 0

    def acquire(self) -> FakeAcquire:
        """Return a tracked acquisition context."""
        self.acquire_count += 1
        return FakeAcquire(self.connection)


class FakeCache:
    """Valkey-compatible fake with optional read/write failures."""

    def __init__(self, payload: str | bytes | None = None, *, fail_get: bool = False, fail_set: bool = False) -> None:
        self.payload = payload
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str, int]] = []

    async def get(self, key: str) -> str | bytes | None:
        """Return a configured payload or simulate Valkey unavailability."""
        self.get_calls.append(key)
        if self.fail_get:
            raise RedisError("cache read unavailable")
        return self.payload

    async def set(self, key: str, value: str, *, ex: int) -> None:
        """Record a write or simulate Valkey unavailability."""
        if self.fail_set:
            raise RedisError("cache write unavailable")
        self.set_calls.append((key, value, ex))


class LeaseCheckingCache(FakeCache):
    """Reject cache reads that pin a PostgreSQL connection across Valkey I/O."""

    def __init__(self, pool: FakePool, payload: str | bytes | None) -> None:
        super().__init__(payload)
        self.pool = pool

    async def get(self, key: str) -> str | bytes | None:
        """Require the database lease to be released before external cache I/O."""
        assert not self.pool.connection.is_acquired, "Valkey read must not hold a PostgreSQL pool lease"
        return await super().get(key)


def _text_sha256(value: str | None) -> str | None:
    """Mirror PostgreSQL SHA-256 evidence for fake asyncpg rows."""
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _rows(*, body: str | None = "No customers", version: int = 7) -> list[dict[str, object]]:
    """Build asyncpg-shaped rows for one two-key screen resource."""
    title = "Customer master"
    return [
        {
            "resource_version": version,
            "translation_key": "body",
            "translated_text": body,
            "translated_text_sha256": _text_sha256(body),
        },
        {
            "resource_version": version,
            "translation_key": "title",
            "translated_text": title,
            "translated_text_sha256": _text_sha256(title),
        },
    ]


def test_locale_and_cache_identity_validation_rejects_ambiguous_inputs() -> None:
    """Unsupported locales and ambiguous identity segments fail before I/O."""
    with pytest.raises(ValueError, match="unsupported UI locale"):
        validate_ui_locale("pt")
    with pytest.raises(ValueError, match="product_key"):
        build_translation_cache_key("lineage:weave", "customer-master", 1, "en")
    with pytest.raises(ValueError, match="screen_key"):
        build_translation_cache_key("lineageweave", " ", 1, "en")
    for version in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="positive integer"):
            build_translation_cache_key("lineageweave", "customer-master", version, "en")  # type: ignore[arg-type]


def test_explicit_immutable_version_cache_hit_requires_authoritative_keyset() -> None:
    """A cache hit avoids text-row work only after PostgreSQL confirms the published key set."""
    payload = json.dumps(
        {
            "product_key": "lineageweave",
            "screen_key": "customer-master",
            "resource_version": 7,
            "locale": "en",
            "translations": {"title": "Customer master", "body": "No customers"},
        }
    )
    pool = FakePool(_rows())
    cache = FakeCache(payload)

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

    assert result.resource_version == 7
    assert result.translations["title"] == "Customer master"
    assert pool.acquire_count == 1
    assert len(pool.connection.calls) == 1


def test_explicit_cache_read_releases_postgres_pool_lease_before_valkey_io() -> None:
    """Slow cache I/O cannot pin scarce PostgreSQL pool capacity."""
    payload = json.dumps(
        {
            "product_key": "lineageweave",
            "screen_key": "customer-master",
            "resource_version": 7,
            "locale": "en",
            "translations": {"title": "Customer master", "body": "No customers"},
        }
    )
    pool = FakePool(_rows())
    cache = LeaseCheckingCache(pool, payload)

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

    assert result.translations["body"] == "No customers"
    assert pool.acquire_count == 1


def test_malformed_or_mismatched_cache_falls_back_to_postgres() -> None:
    """Cache corruption never becomes product copy authority."""
    for payload in (
        b"{not-json",
        json.dumps(
            {
                "product_key": "other-product",
                "screen_key": "customer-master",
                "resource_version": 7,
                "locale": "en",
                "translations": {"title": "wrong"},
            }
        ),
    ):
        pool = FakePool(_rows())
        cache = FakeCache(payload)
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
        assert result.translations["body"] == "No customers"
        assert pool.acquire_count == 1
        assert len(pool.connection.calls) == 1


def test_incomplete_exact_cache_falls_back_to_authoritative_postgres() -> None:
    """A correct cache identity cannot hide a missing published screen key."""
    payload = json.dumps(
        {
            "product_key": "lineageweave",
            "screen_key": "customer-master",
            "resource_version": 7,
            "locale": "en",
            "translations": {"title": "Customer master"},
        }
    )
    pool = FakePool(_rows())
    cache = FakeCache(payload)

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
    assert len(pool.connection.calls) == 1


def test_complete_but_poisoned_exact_cache_falls_back_to_authoritative_postgres() -> None:
    """Matching cache identity and key coverage cannot make altered copy authoritative."""
    payload = json.dumps(
        {
            "product_key": "lineageweave",
            "screen_key": "customer-master",
            "resource_version": 7,
            "locale": "en",
            "translations": {"title": "Tampered customer master", "body": "No customers"},
        }
    )
    pool = FakePool(_rows())
    cache = FakeCache(payload)

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
    assert len(pool.connection.calls) == 1


def test_cache_read_or_write_failure_does_not_replace_postgres_authority() -> None:
    """Valkey failure degrades to a PostgreSQL read rather than a user-visible failure."""
    for cache in (FakeCache(fail_get=True), FakeCache(fail_set=True)):
        pool = FakePool(_rows())
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
        assert result.resource_version == 7
        assert pool.acquire_count == 1


def test_latest_read_resolves_postgres_before_cache() -> None:
    """Latest is not a mutable cache alias and therefore never performs an unversioned cache read."""
    pool = FakePool(_rows(version=8))
    cache = FakeCache(payload=b"stale")
    result = asyncio.run(
        read_translation_screen(
            pool,  # type: ignore[arg-type]
            cache,
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
        )
    )

    assert result.resource_version == 8
    assert cache.get_calls == []
    assert cache.set_calls[0][0].endswith(":v8:en")


def test_missing_resource_and_incomplete_locale_fail_closed() -> None:
    """Missing resource or requested-locale copy cannot silently fall back."""
    with pytest.raises(TranslationResourceNotFound):
        asyncio.run(
            read_translation_screen(
                FakePool([]),  # type: ignore[arg-type]
                None,
                product_key="lineageweave",
                screen_key="customer-master",
                locale="en",
            )
        )

    with pytest.raises(TranslationCoverageError, match="body"):
        asyncio.run(
            read_translation_screen(
                FakePool(_rows(body=None)),  # type: ignore[arg-type]
                None,
                product_key="lineageweave",
                screen_key="customer-master",
                locale="en",
            )
        )


def test_complete_postgres_read_writes_exact_version_cache_receipt() -> None:
    """A successful authoritative read writes only the resolved immutable cache identity."""
    pool = FakePool(_rows(version=11))
    cache = FakeCache()
    result = asyncio.run(
        read_translation_screen(
            pool,  # type: ignore[arg-type]
            cache,
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
        )
    )

    assert result.cache_key == "ui-translation:lineageweave:customer-master:v11:en"
    assert result.translations == {"body": "No customers", "title": "Customer master"}
    assert len(cache.set_calls) == 1
    key, payload, ttl = cache.set_calls[0]
    assert key == result.cache_key
    assert ttl == 300
    assert json.loads(payload)["resource_version"] == 11
