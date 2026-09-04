"""Regression coverage for exact translation-cache version identity types."""

from __future__ import annotations

import asyncio
import hashlib
import json

from backend.app.translation_ledger import read_translation_screen


class _Connection:
    """Return one complete published screen while recording database reads."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, *_args: object) -> list[dict[str, object]]:
        """Return rows shaped for both digest admission and authoritative projection."""
        self.calls += 1
        return [
            {
                "resource_version": 7,
                "translation_key": "title",
                "translated_text": "Customer master",
                "translated_text_sha256": hashlib.sha256(b"Customer master").hexdigest(),
            }
        ]


class _Acquire:
    """Expose one asyncpg-compatible acquisition context."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _Connection:
        """Return the configured fake connection."""
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        """Release without suppressing exceptions."""
        return None


class _Pool:
    """Count PostgreSQL acquisitions made by one translation read."""

    def __init__(self) -> None:
        self.connection = _Connection()
        self.acquire_count = 0

    def acquire(self) -> _Acquire:
        """Return a tracked acquisition context."""
        self.acquire_count += 1
        return _Acquire(self.connection)


class _Cache:
    """Return one exact-key cache payload and accept refresh writes."""

    def __init__(self, resource_version: int | float) -> None:
        self.payload = json.dumps(
            {
                "product_key": "lineageweave",
                "screen_key": "customer-master",
                "resource_version": resource_version,
                "locale": "en",
                "translations": {"title": "Customer master"},
            }
        )

    async def get(self, _key: str) -> str:
        """Return the configured payload."""
        return self.payload

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Accept an authoritative cache refresh."""
        assert ex == 300


def _read(resource_version: int | float) -> tuple[int, str]:
    """Read version 7 and return acquisition count plus translated title."""
    pool = _Pool()
    result = asyncio.run(
        read_translation_screen(
            pool,  # type: ignore[arg-type]
            _Cache(resource_version),
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
            resource_version=7,
        )
    )
    return pool.acquire_count, result.translations["title"]


def test_integer_cache_version_remains_an_exact_hit() -> None:
    """Canonical JSON integer identity keeps the one-acquisition cache path."""
    acquisitions, title = _read(7)

    assert acquisitions == 1
    assert title == "Customer master"


def test_float_cache_version_is_noncanonical_and_falls_back_to_postgres() -> None:
    """JSON 7.0 must not impersonate PostgreSQL BIGINT identity 7 through Python equality."""
    acquisitions, title = _read(7.0)

    assert acquisitions == 1
    assert title == "Customer master"
