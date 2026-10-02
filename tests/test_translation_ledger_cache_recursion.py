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
        expected_text_octets={"title": len(b"Title")},
    ) is None


def test_oversized_cache_payload_is_rejected_before_json_decode(monkeypatch) -> None:
    """Authoritative text size must bound decoder work for an untrusted cache value."""
    def unexpected_decoder(*_args, **_kwargs):
        raise AssertionError("oversized cache payload reached the JSON decoder")

    monkeypatch.setattr(translation_ledger.json, "loads", unexpected_decoder)

    assert _decode_cached_screen(
        b"{" + b" " * 10_000,
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=1,
        locale="en",
        expected_text_digests={"title": hashlib.sha256(b"T").hexdigest()},
        expected_text_octets={"title": 1},
    ) is None
