from __future__ import annotations

import ssl
from pathlib import Path

from lineageweave import http_client
from lineageweave.post_chat import CANONICAL_CHAT_QUESTION, normalize_chat_question


def test_http_client_declares_tls_1_2_floor_in_owned_transport_boundary() -> None:
    """The owned HTTPS boundary must not rely on interpreter/OpenSSL defaults."""

    source = (
        Path(__file__).resolve().parents[1] / "lineageweave" / "http_client.py"
    ).read_text(encoding="utf-8")

    assert "_SSL_CONTEXT.minimum_version = ssl.TLSVersion.TLSv1_2" in source
    assert http_client._SSL_CONTEXT.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_chat_question_trailing_strip_avoids_end_anchored_regex_backtracking() -> None:
    """User punctuation normalization must use the linear string boundary."""

    source = (
        Path(__file__).resolve().parents[1] / "lineageweave" / "post_chat.py"
    ).read_text(encoding="utf-8")

    assert "_TRAILING_PUNCT = re.compile" not in source
    assert '.rstrip("?.!")' in source
    canonical = normalize_chat_question(CANONICAL_CHAT_QUESTION)
    assert normalize_chat_question("What happened" + "?" * 10_000) == canonical
    assert normalize_chat_question("When was the bid sent" + "!" * 10_000) == (
        "when was the bid sent"
    )
