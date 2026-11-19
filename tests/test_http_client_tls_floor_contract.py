from __future__ import annotations

import importlib.util
import ssl
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lineageweave import http_client
from lineageweave.post_chat import CANONICAL_CHAT_QUESTION, normalize_chat_question


def test_http_client_declares_tls_1_2_floor_in_owned_transport_boundary() -> None:
    """The owned HTTPS boundary must set its protocol floor before escape."""

    context = SimpleNamespace(minimum_version=ssl.TLSVersion.MINIMUM_SUPPORTED)
    with patch.object(
        http_client.ssl, "create_default_context", return_value=context
    ) as create_context:
        spec = importlib.util.spec_from_file_location(
            "lineageweave._tls_floor_contract_probe", http_client.__file__
        )
        assert spec is not None and spec.loader is not None
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        built_context = probe._SSL_CONTEXT

    create_context.assert_called_once_with(cafile=http_client.certifi.where())

    assert built_context is context
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert http_client._SSL_CONTEXT.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_chat_question_trailing_strip_avoids_end_anchored_regex_backtracking() -> None:
    """User punctuation normalization must use the linear string boundary."""

    source = (
        Path(__file__).resolve().parents[1] / "lineageweave" / "post_chat.py"
    ).read_text(encoding="utf-8")

    assert "_TRAILING_PUNCT = re.compile" not in source
    assert '.rstrip("?.! ")' in source
    canonical = normalize_chat_question(CANONICAL_CHAT_QUESTION)
    assert normalize_chat_question("What happened" + "?" * 10_000) == canonical
    assert normalize_chat_question("When was the bid sent" + "!" * 10_000) == (
        "when was the bid sent"
    )
