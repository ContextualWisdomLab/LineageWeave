from __future__ import annotations

import ssl
from pathlib import Path

from lineageweave import http_client


def test_http_client_declares_tls_1_2_floor_in_owned_transport_boundary() -> None:
    """The owned HTTPS boundary must not rely on interpreter/OpenSSL defaults."""

    source = (
        Path(__file__).resolve().parents[1] / "lineageweave" / "http_client.py"
    ).read_text(encoding="utf-8")

    assert "_SSL_CONTEXT.minimum_version = ssl.TLSVersion.TLSv1_2" in source
    assert http_client._SSL_CONTEXT.minimum_version >= ssl.TLSVersion.TLSv1_2
