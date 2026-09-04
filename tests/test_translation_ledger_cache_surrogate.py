"""Regression coverage for malformed Unicode in the translation cache boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json

from backend.app.translation_ledger import read_translation_screen


class _Connection:
    """Return one predetermined asyncpg-shaped result set."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    async def fetch(self, *_args: object) -> list[dict[str, object]]:
        """Return the configured rows for one repository query."""
        return self.rows


class _Acquire:
    """Expose one fake connection through the async pool context contract."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _Connection:
        """Acquire the configured fake connection."""
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        """Release the fake connection without suppressing exceptions."""
        return None


class _SequencedPool:
    """Return one projection carrying integrity evidence and authoritative copy."""

    def __init__(self) -> None:
        title = "Customer master"
        body = "No customers"
        self._connections = iter(
            (
                _Connection(
                    [
                        {
                            "resource_version": 7,
                            "translation_key": "body",
                            "translated_text_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                        },
                        {
                            "resource_version": 7,
                            "translation_key": "title",
                            "translated_text_sha256": hashlib.sha256(title.encode("utf-8")).hexdigest(),
                        },
                    ]
                ),
                _Connection(
                    [
                        {
                            "resource_version": 7,
                            "translation_key": "body",
                            "translated_text": body,
                        },
                        {
                            "resource_version": 7,
                            "translation_key": "title",
                            "translated_text": title,
                        },
                    ]
                ),
            )
        )
        self.acquire_count = 0

    def acquire(self) -> _Acquire:
        """Acquire the next query-specific fake connection."""
        self.acquire_count += 1
        return _Acquire(next(self._connections))


class _SurrogateCache:
    """Return valid JSON whose title contains an unpaired Unicode surrogate."""

    async def get(self, _key: str) -> str:
        """Return a structurally valid but non-UTF-8-encodable cache payload."""
        return json.dumps(
            {
                "product_key": "lineageweave",
                "screen_key": "customer-master",
                "resource_version": 7,
                "locale": "en",
                "translations": {"title": "\ud800", "body": "No customers"},
            }
        )

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Accept fallback cache population after PostgreSQL wins authority."""
        assert ex == 300


def test_unpaired_surrogate_cache_copy_falls_back_to_postgres() -> None:
    """Malformed cache Unicode cannot make an authoritative translation unavailable."""
    pool = _SequencedPool()

    result = asyncio.run(
        read_translation_screen(
            pool,  # type: ignore[arg-type]
            _SurrogateCache(),
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
            resource_version=7,
        )
    )

    assert result.translations == {"body": "No customers", "title": "Customer master"}
    assert pool.acquire_count == 2
