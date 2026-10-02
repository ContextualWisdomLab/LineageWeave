"""Regression coverage for UTF-8 exact-version translation cache admission."""

from __future__ import annotations

import hashlib
import json

from backend.app.translation_ledger import _decode_cached_screen


def _sha256(value: str) -> str:
    """Return the PostgreSQL-compatible UTF-8 digest used by cache admission."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_utf8_bytes_cache_hit_with_non_ascii_identity_and_key_is_admitted() -> None:
    """A valid UTF-8 bytes payload must not miss solely because metadata is non-ASCII."""
    product_key = "리니지위브"
    screen_key = "고객-마스터"
    translation_key = "제목"
    translated_text = "A"
    raw_payload = json.dumps(
        {
            "product_key": product_key,
            "screen_key": screen_key,
            "resource_version": 7,
            "locale": "ko",
            "translations": {translation_key: translated_text},
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    result = _decode_cached_screen(
        raw_payload,
        product_key=product_key,
        screen_key=screen_key,
        resource_version=7,
        locale="ko",
        expected_text_digests={translation_key: _sha256(translated_text)},
        expected_text_octets={translation_key: len(translated_text.encode("utf-8"))},
    )

    assert result is not None
    assert result.translations == {translation_key: translated_text}
