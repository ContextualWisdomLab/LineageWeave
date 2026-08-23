from __future__ import annotations

import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pytest

from lineageweave.source_artifacts import SourceArtifactError, read_mhtml_html


def _mhtml_bytes(html: str) -> bytes:
    message = MIMEMultipart("related")
    message.attach(MIMEText(html, "html", "utf-8"))
    return message.as_bytes()


def test_read_mhtml_html_verifies_digest_and_returns_html_part(tmp_path: Path) -> None:
    payload = _mhtml_bytes("<html><body>synthetic source</body></html>")
    (tmp_path / "message.mhtml").write_bytes(payload)

    body = read_mhtml_html(
        tmp_path,
        "message.mhtml",
        hashlib.sha256(payload).hexdigest(),
    )

    assert body == "<html><body>synthetic source</body></html>"


@pytest.mark.parametrize(
    ("source_path", "expected_sha256", "message"),
    [
        ("../message.mhtml", "0" * 64, "outside the artifact root"),
        ("message.mhtml", "not-a-sha256", "64 hexadecimal"),
        ("message.mhtml", "0" * 64, "does not match"),
    ],
)
def test_read_mhtml_html_fails_closed_for_unproven_artifacts(
    tmp_path: Path,
    source_path: str,
    expected_sha256: str,
    message: str,
) -> None:
    payload = _mhtml_bytes("<p>synthetic</p>")
    (tmp_path / "message.mhtml").write_bytes(payload)

    with pytest.raises(SourceArtifactError, match=message):
        read_mhtml_html(tmp_path, source_path, expected_sha256)


def test_read_mhtml_html_rejects_non_related_or_html_free_messages(tmp_path: Path) -> None:
    message = MIMEText("plain source", "plain", "utf-8").as_bytes()
    (tmp_path / "message.mhtml").write_bytes(message)

    with pytest.raises(SourceArtifactError, match="multipart/related"):
        read_mhtml_html(tmp_path, "message.mhtml", hashlib.sha256(message).hexdigest())
