"""Regression contract for ambiguous duplicate-name Valkey JSON payloads."""

from __future__ import annotations

import hashlib

import pytest

from backend.app.translation_ledger import _decode_cached_screen


def _sha256(value: str) -> str:
    """Return the PostgreSQL-equivalent SHA-256 evidence for one UTF-8 value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    "payload",
    (
        (
            '{"product_key":"lineageweave","screen_key":"customer-master",'
            '"resource_version":7,"locale":"fr","locale":"en",'
            '"translations":{"body":"No customers","title":"Customer master"}}'
        ),
        (
            '{"product_key":"lineageweave","screen_key":"customer-master",'
            '"resource_version":7,"locale":"en",'
            '"translations":{"body":"No customers","title":"stale",'
            '"title":"Customer master"}}'
        ),
    ),
)
def test_duplicate_json_member_names_are_cache_misses(payload: str) -> None:
    """Noncanonical duplicate-name cache evidence must fall back to PostgreSQL."""
    expected_text_digests = {
        "body": _sha256("No customers"),
        "title": _sha256("Customer master"),
    }

    assert (
        _decode_cached_screen(
            payload,
            product_key="lineageweave",
            screen_key="customer-master",
            resource_version=7,
            locale="en",
            expected_text_digests=expected_text_digests,
        )
        is None
    )
