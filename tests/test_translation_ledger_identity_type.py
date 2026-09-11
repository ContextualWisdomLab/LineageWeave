"""Domain-type admission for UI translation aggregate identities."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.app.translation_ledger import build_translation_cache_key, read_translation_screen


class NoAcquirePool:
    """Fail if malformed aggregate identity reaches PostgreSQL I/O."""

    def acquire(self) -> object:
        """Reject any attempted pool acquisition for an invalid identity."""
        raise AssertionError("malformed translation identity must fail before PostgreSQL I/O")


@pytest.mark.parametrize(
    ("product_key", "screen_key", "field_name"),
    (
        (None, "customer-master", "product_key"),
        (17, "customer-master", "product_key"),
        ("lineageweave", None, "screen_key"),
        ("lineageweave", 17, "screen_key"),
    ),
)
def test_translation_identity_rejects_non_string_segments_before_io(
    product_key: Any,
    screen_key: Any,
    field_name: str,
) -> None:
    """Malformed transport values become controlled domain errors before adapters run."""
    with pytest.raises(ValueError, match=field_name):
        build_translation_cache_key(product_key, screen_key, 17, "en")

    with pytest.raises(ValueError, match=field_name):
        asyncio.run(
            read_translation_screen(
                NoAcquirePool(),  # type: ignore[arg-type]
                None,
                product_key=product_key,
                screen_key=screen_key,
                locale="en",
                resource_version=17,
            )
        )


@pytest.mark.parametrize(
    ("product_key", "screen_key", "field_name"),
    (
        ("lineage\x00weave", "customer-master", "product_key"),
        ("lineage\ud800weave", "customer-master", "product_key"),
        ("lineageweave", "customer\x00-master", "screen_key"),
        ("lineageweave", "customer\ud800-master", "screen_key"),
    ),
)
def test_translation_identity_rejects_values_postgres_text_cannot_represent_before_io(
    product_key: str,
    screen_key: str,
    field_name: str,
) -> None:
    """Cache and database identity admit only values representable as PostgreSQL UTF-8 text."""
    with pytest.raises(ValueError, match=field_name):
        build_translation_cache_key(product_key, screen_key, 17, "en")

    with pytest.raises(ValueError, match=field_name):
        asyncio.run(
            read_translation_screen(
                NoAcquirePool(),  # type: ignore[arg-type]
                None,
                product_key=product_key,
                screen_key=screen_key,
                locale="en",
                resource_version=17,
            )
        )
