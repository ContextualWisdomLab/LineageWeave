"""Base64-embedded image content: real OCR and object recognition/tagging
via a pluggable vision-capable client, with the image's position among its
sibling DOM units preserved so the original document layout is
reconstructable -- an extracted caption is useless for review if nobody
can tell which paragraph it illustrated.

Grounded in:

- **OCR** (text recognition): Li et al. (2023) -- TrOCR, a transformer
  encoder-decoder trained end-to-end for text recognition, the current
  standard architecture family modern OCR (including vision-capable LLMs)
  descends from.
- **Object recognition / captioning / tagging**: Radford et al. (2021) --
  CLIP, contrastive language-image pretraining. CLIP-style joint
  text-image embedding is the basis most current zero-shot image tagging
  and captioning builds on, including the vision-capable chat models this
  module calls.

Same pluggable-client, never-fake-a-missing-channel discipline as
:mod:`lineageweave.embedding_client` and
:mod:`lineageweave.adjudication_client`: :class:`NullImageContentClient`
makes the channel unavailable, never returns a placeholder description.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from .http_client import post_json

_DATA_URI_IMG = re.compile(
    r'<img\b[^>]*\bsrc\s*=\s*["\']data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)["\']',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EmbeddedImage:
    """One base64 image found in DOM content.

    Attributes:
        position: this image's order of appearance in the source document
            (0-based) -- the anchor that lets extracted content be placed
            back where the picture actually was.
        mime_type: e.g. ``"image/png"``.
        data: the decoded raw image bytes.
    """

    position: int
    mime_type: str
    data: bytes


def extract_base64_images(html: str) -> list[EmbeddedImage]:
    """Find every ``<img src="data:...;base64,...">`` in document order.

    Malformed base64 in a matched tag is skipped rather than raising --
    one corrupt embedded image must not fail extraction of the rest of the
    document.
    """
    images: list[EmbeddedImage] = []
    for match in _DATA_URI_IMG.finditer(html):
        mime_type = match.group(1)
        raw_b64 = re.sub(r"\s+", "", match.group(2))
        try:
            data = base64.b64decode(raw_b64, validate=True)
        except (binascii.Error, ValueError):
            continue
        images.append(EmbeddedImage(position=len(images), mime_type=mime_type, data=data))
    return images


@dataclass(frozen=True)
class ImageDescription:
    """Real content extracted from one image.

    Attributes:
        extracted_text: OCR result -- every piece of legible text found in
            the image, empty string if none.
        caption: one-sentence description of what the image shows.
        tags: short tags for the main objects/subjects, for independent
            keyword search separate from the free-text caption.
    """

    extracted_text: str
    caption: str
    tags: tuple[str, ...]


class ImageContentClient(Protocol):
    """Turns image bytes into searchable text content."""

    available: bool

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription: ...


class NullImageContentClient:
    """No vision provider configured -- the image channel is skipped."""

    available = False

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:  # pragma: no cover
        raise RuntimeError("NullImageContentClient has no image channel; check .available first")


_RESPONSE_FORMAT = (
    "Examine this image. Reply with EXACTLY three lines, no extra commentary:\n"
    "TEXT: <all legible text in the image, verbatim, or NONE if there is none>\n"
    "CAPTION: <one sentence describing what the image shows>\n"
    "TAGS: <comma-separated short tags for the main objects/subjects>"
)
_TEXT_LINE = re.compile(r"TEXT:\s*(.*)")
_CAPTION_LINE = re.compile(r"CAPTION:\s*(.*)")
_TAGS_LINE = re.compile(r"TAGS:\s*(.*)")


def _parse_description(content: str) -> ImageDescription:
    text_match = _TEXT_LINE.search(content)
    caption_match = _CAPTION_LINE.search(content)
    tags_match = _TAGS_LINE.search(content)

    extracted_text = text_match.group(1).strip() if text_match else ""
    if extracted_text.upper() == "NONE":
        extracted_text = ""
    caption = caption_match.group(1).strip() if caption_match else ""
    tags_raw = tags_match.group(1).strip() if tags_match else ""
    tags = tuple(tag.strip() for tag in tags_raw.split(",") if tag.strip())
    return ImageDescription(extracted_text=extracted_text, caption=caption, tags=tags)


class OpenAiCompatibleVisionClient:
    """Calls an OpenAI-compatible vision-capable chat model for OCR and
    object recognition/tagging in one round trip.
    """

    available = True

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 60.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"unsupported vision client URL scheme: {parsed.scheme or 'missing'}"
            )
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        body = post_json(
            f"{self._base_url}/chat/completions",
            {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _RESPONSE_FORMAT},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.0,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = body["choices"][0]["message"]["content"]
        return _parse_description(content)
