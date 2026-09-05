"""Malformed Valkey recursion must not outrank PostgreSQL translation authority."""

from __future__ import annotations

import hashlib
from backend.app import translation_ledger
from backend.app.translation_ledger import _decode_cached_screen


def test_deeply_nested_cache_json_is_an_authoritative_miss(monkeypatch) -> None:
    """Decoder recursion exhaustion must fall back instead of escaping cache admission."""
    expected_digest = hashlib.sha256(b"Title").hexdigest()

    def exhaust_decoder(*_args, **_kwargs):
        raise RecursionError("synthetic JSON nesting limit")

    monkeypatch.setattr(translation_ledger.json, "loads", exhaust_decoder)

    assert _decode_cached_screen(
        "{}",
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=1,
        locale="en",
        expected_text_digests={"title": expected_digest},
    ) is None
