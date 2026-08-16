"""Shared decode rules for embedded ``data:image`` payloads.

The product popup, :func:`lineageweave.image_content.extract_base64_images`,
and :func:`lineageweave.chunking.chunk_by_dom` must accept and reject the
same bytes. A regex that stops at the first ``>`` misses Outlook-style
``alt="Invoice > 1000"`` tags; an open MIME class
``image/[a-zA-Z0-9.+-]+`` treats ``image/svg+xml`` as a picture. Both
failures put the buyer back in front of a base64 wall or send scriptable
XML into the vision channel.

Raster-only MIME types plus magic-byte checks keep the three extractors
honest. Grounded in the WHATWG HTML parser (attribute values may contain
``>``) and the PNG signature (Boutell & Randers-Pehrson, 2003).
"""

from __future__ import annotations

import base64
import binascii
import re

RASTER_IMAGE_MIME_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
        "image/avif",
    }
)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_PREFIX = b"\xff\xd8\xff"


def looks_like_raster_image(mime_type: str, data: bytes) -> bool:
    """Return True when ``data`` matches the claimed raster MIME type.

    A payload labeled ``image/png`` that decodes to ``Hello`` is not a
    picture. The popup must not render it, and the vision client must not
    spend a call on it.
    """
    normalized = mime_type.lower()
    if normalized not in RASTER_IMAGE_MIME_TYPES or not data:
        return False
    if normalized == "image/png":
        return data.startswith(_PNG_SIGNATURE)
    if normalized in {"image/jpeg", "image/jpg"}:
        return data.startswith(_JPEG_PREFIX)
    if normalized == "image/gif":
        return data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    if normalized == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if normalized == "image/avif":
        return len(data) >= 12 and data[4:8] == b"ftyp" and (
            b"avif" in data[8:16] or b"avis" in data[8:16] or b"mif1" in data[8:16]
        )
    return False


def decode_data_uri_image(src: str) -> tuple[str, bytes] | None:
    """Parse a ``data:image/<raster>;base64,<data>`` ``src`` value.

    Returns ``None`` for remote URLs, SVG, unpadded or invalid base64,
    and bytes that do not match the claimed raster signature.
    """
    if not src.lower().startswith("data:image/"):
        return None
    header, separator, encoded = src.partition(",")
    if not separator or ";base64" not in header.lower():
        return None
    mime_type = header[len("data:") : header.index(";")].strip().lower()
    if mime_type not in RASTER_IMAGE_MIME_TYPES:
        return None
    raw_b64 = re.sub(r"\s+", "", encoded)
    try:
        data = base64.b64decode(raw_b64, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not looks_like_raster_image(mime_type, data):
        return None
    return mime_type, data


def source_offset(source: str, line: int, column: int) -> int:
    """Convert HTMLParser ``getpos()`` (1-based line, 0-based column) to a
    character offset in ``source``.
    """
    if line < 1:
        return 0
    lines = source.splitlines(keepends=True)
    if line > len(lines):
        return len(source)
    return sum(len(part) for part in lines[: line - 1]) + column
