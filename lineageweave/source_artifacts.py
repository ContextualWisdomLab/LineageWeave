"""Resolve an explicitly mapped MHTML artifact into its HTML source body."""

from __future__ import annotations

import hashlib
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path


class SourceArtifactError(ValueError):
    """Raised when an artifact cannot be proven to be the mapped source body."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _artifact_path(root: Path, source_path: str) -> Path:
    """Resolve a source path and reject traversal or symlink escape."""
    if not source_path.strip():
        raise SourceArtifactError("source artifact path is empty")
    root_path = root.expanduser().resolve()
    candidate = Path(source_path).expanduser()
    if not candidate.is_absolute():
        candidate = root_path / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise SourceArtifactError("source artifact path is missing or outside the artifact root") from exc
    if not resolved.is_file():
        raise SourceArtifactError("source artifact is not a regular file")
    return resolved


def read_mhtml_html(root: Path, source_path: str, expected_sha256: str) -> str:
    """Read the first leaf HTML part from a hash-verified RFC 2557 artifact."""
    digest = expected_sha256.strip().lower()
    if not _SHA256.fullmatch(digest):
        raise SourceArtifactError("source artifact SHA-256 must be 64 hexadecimal characters")
    artifact = _artifact_path(root, source_path)
    payload = artifact.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise SourceArtifactError("source artifact SHA-256 does not match the source row")

    message = BytesParser(policy=policy.default).parsebytes(payload)
    if not message.is_multipart() or message.get_content_subtype().casefold() != "related":
        raise SourceArtifactError("source artifact is not a multipart/related MHTML message")
    for part in message.walk():
        if part.is_multipart() or part.get_content_type().casefold() != "text/html":
            continue
        body = part.get_content()
        if isinstance(body, bytes):
            charset = part.get_content_charset() or "utf-8"
            body = body.decode(charset, errors="strict")
        if isinstance(body, str) and body.strip():
            return body
    raise SourceArtifactError("source artifact contains no non-empty text/html root part")
