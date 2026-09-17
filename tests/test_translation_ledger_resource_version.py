"""Resource-version value-object bounds for the UI translation ledger."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.translation_ledger import build_translation_cache_key, read_translation_screen


_POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807


class NoAcquirePool:
    """Fail if invalid resource-version admission reaches PostgreSQL I/O."""

    def acquire(self) -> object:
        """Reject any attempted pool acquisition for an invalid version."""
        raise AssertionError("oversized resource_version must fail before PostgreSQL I/O")


def test_resource_version_rejects_values_outside_postgresql_bigint() -> None:
    """Cache/read identities cannot name versions PostgreSQL cannot persist."""
    assert build_translation_cache_key(
        "lineageweave",
        "customer-master",
        _POSTGRES_BIGINT_MAX,
        "en",
    ).endswith(f":v{_POSTGRES_BIGINT_MAX}:en")

    oversized = _POSTGRES_BIGINT_MAX + 1
    with pytest.raises(ValueError, match="PostgreSQL bigint"):
        build_translation_cache_key("lineageweave", "customer-master", oversized, "en")

    with pytest.raises(ValueError, match="PostgreSQL bigint"):
        asyncio.run(
            read_translation_screen(
                NoAcquirePool(),  # type: ignore[arg-type]
                None,
                product_key="lineageweave",
                screen_key="customer-master",
                locale="en",
                resource_version=oversized,
            )
        )
