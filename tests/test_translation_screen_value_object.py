"""Value-object invariants for immutable published translation projections."""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.app.translation_ledger import TranslationScreen, read_translation_screen


class _Connection:
    """Return one complete two-key published screen projection."""

    async def fetch(self, *_args: object) -> list[dict[str, object]]:
        """Return asyncpg-shaped rows for the requested screen."""
        return [
            {"resource_version": 7, "translation_key": "body", "translated_text": "No customers"},
            {"resource_version": 7, "translation_key": "title", "translated_text": "Customer master"},
        ]


class _Acquire:
    """Minimal async pool-acquire context."""

    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _Connection:
        """Return the deterministic connection."""
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        """Release without suppressing exceptions."""
        return None


class _Pool:
    """Minimal asyncpg-shaped pool."""

    def __init__(self) -> None:
        self.connection = _Connection()

    def acquire(self) -> _Acquire:
        """Return one deterministic acquisition context."""
        return _Acquire(self.connection)


class _Cache:
    """Exact-version cache fixture for the cache-hit construction path."""

    def __init__(self) -> None:
        self.payload = json.dumps(
            {
                "product_key": "lineageweave",
                "screen_key": "customer-master",
                "resource_version": 7,
                "locale": "en",
                "translations": {"body": "No customers", "title": "Customer master"},
            }
        )

    async def get(self, _key: str) -> str:
        """Return a structurally complete exact-version payload."""
        return self.payload

    async def set(self, _key: str, _value: str, *, ex: int) -> None:
        """Accept cache population for protocol completeness."""
        assert ex > 0


def _assert_projection_is_read_only(translations: object) -> None:
    """Published screen copy cannot be mutated while retaining its immutable identity."""
    with pytest.raises(TypeError):
        translations["title"] = "tampered"  # type: ignore[index]


def test_translation_screen_constructor_detaches_mutable_source_mapping() -> None:
    """The value object owns a detached read-only copy, not the caller's mutable alias."""
    source = {"body": "No customers", "title": "Customer master"}
    result = TranslationScreen(
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=7,
        locale="en",
        cache_key="ui-translation:lineageweave:customer-master:v7:en",
        translations=source,
    )

    source["title"] = "tampered through caller alias"

    assert result.translations["title"] == "Customer master"
    _assert_projection_is_read_only(result.translations)


def test_translation_screen_postgres_projection_is_read_only() -> None:
    """The PostgreSQL construction path returns an immutable value projection."""
    result = asyncio.run(
        read_translation_screen(
            _Pool(),  # type: ignore[arg-type]
            None,
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
        )
    )

    _assert_projection_is_read_only(result.translations)
    assert result.translations["title"] == "Customer master"


def test_translation_screen_cache_hit_projection_is_read_only() -> None:
    """The exact-version cache-hit path preserves the same immutable value contract."""
    result = asyncio.run(
        read_translation_screen(
            _Pool(),  # type: ignore[arg-type]
            _Cache(),
            product_key="lineageweave",
            screen_key="customer-master",
            locale="en",
            resource_version=7,
        )
    )

    _assert_projection_is_read_only(result.translations)
    assert result.translations["title"] == "Customer master"
