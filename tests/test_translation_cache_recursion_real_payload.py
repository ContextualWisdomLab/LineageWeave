"""Real malformed-cache recursion evidence independent of synthetic fault injection."""

from __future__ import annotations

import hashlib
import json
import sys

from backend.app.translation_ledger import _decode_cached_screen


def test_real_over_nested_json_payload_is_a_cache_miss() -> None:
    """A real over-nested wire payload must remain a non-authoritative cache miss."""
    depth = max(10_000, sys.getrecursionlimit() * 10)
    raw_payload = "[" * depth + "0" + "]" * depth
    expected_digest = hashlib.sha256(b"Title").hexdigest()

    try:
        decoded = json.loads(raw_payload)
    except RecursionError:
        pass
    else:
        assert isinstance(decoded, list)

    assert _decode_cached_screen(
        raw_payload,
        product_key="lineageweave",
        screen_key="customer-master",
        resource_version=1,
        locale="en",
        expected_text_digests={"title": expected_digest},
    ) is None
