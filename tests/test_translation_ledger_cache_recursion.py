"""Malformed Valkey recursion must not outrank PostgreSQL translation authority."""

from __future__ import annotations

import hashlib
import sys

from backend.app.translation_ledger import _decode_cached_screen


def test_deeply_nested_cache_json_is_an_authoritative_miss() -> None:
    """Decoder recursion exhaustion must fall back instead of escaping cache admission."""
    depth = sys.getrecursionlimit() * 2
    raw_payload = "[" * depth + "0" + "]" * depth
    expected_digest = hashlib.sha256(b"Title").hexdigest()

    assert _decode_cached_screen(
        raw_payload,
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=1,
        locale="en",
        expected_text_digests={"title": expected_digest},
    ) is None
