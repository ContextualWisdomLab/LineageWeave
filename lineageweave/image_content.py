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
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlparse

from .embedded_image_payload import decode_data_uri_image, source_offset
from .http_client import post_json


@dataclass(frozen=True)
class EmbeddedImage:
    """One base64 image found in DOM content.

    Attributes:
        position: this image's character offset in the source HTML
            (0-based) -- NOT an image-only ordinal. An ordinal (0, 1, 2...)
            cannot distinguish "two images with a paragraph between them"
            from "two images back to back," so the original document
            layout could not be reconstructed from it. A character offset
            can: it is comparable against any text unit's own position
            (e.g. a DOM chunk's start offset) to recover relative order.
        mime_type: e.g. ``"image/png"``.
        data: the decoded raw image bytes.
    """

    position: int
    mime_type: str
    data: bytes


class _EmbeddedImageExtractor(HTMLParser):
    """Collect raster ``data:image`` ``<img>`` tags in document order.

    Uses the HTML parser so ``alt="Invoice > 1000"`` and unquoted
    attributes still find the picture. Comments, ``<style>``, and
    ``<script>`` are ignored -- the same contract as
    :func:`lineageweave.chunking.chunk_by_dom`.
    """

    def __init__(self, source: str) -> None:
        """Bind the original HTML so ``getpos()`` can become a character offset."""
        super().__init__()
        self._source = source
        self._skip_depth = 0
        self.images: list[EmbeddedImage] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record a raster ``<img>`` or enter a skipped ``style``/``script``."""
        if tag in {"style", "script"}:
            self._skip_depth += 1
        if self._skip_depth or tag != "img":
            return
        src = next((value for name, value in attrs if name == "src" and value), None)
        if not src:
            return
        decoded = decode_data_uri_image(src)
        if decoded is None:
            return
        mime_type, data = decoded
        line, column = self.getpos()
        self.images.append(
            EmbeddedImage(
                position=source_offset(self._source, line, column),
                mime_type=mime_type,
                data=data,
            )
        )

    def handle_endtag(self, tag: str) -> None:
        """Leave a skipped ``style`` or ``script`` region."""
        if tag in {"style", "script"} and self._skip_depth:
            self._skip_depth -= 1


def extract_base64_images(html: str) -> list[EmbeddedImage]:
    """Find every raster ``<img src="data:...;base64,...">`` in document order.

    Malformed base64, SVG, remote ``http(s)`` tags, and commented-out
    pictures are skipped rather than raising -- one corrupt embedded
    image must not fail extraction of the rest of the document.
    """
    parser = _EmbeddedImageExtractor(html)
    parser.feed(html)
    return parser.images


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

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        """Return OCR text, caption, and tags for one image.

        Implementations must raise if they cannot produce a description.
        Protocol stubs raise ``NotImplementedError`` so a no-op body is
        never treated as a successful empty result.
        """
        raise NotImplementedError


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
# TEXT may legitimately span multiple lines because OCR output is often
# multi-line. CAPTION and TAGS are explicitly single-line fields. Synthetic
# format-variation fixtures cover common provider drift such as bolded or
# reordered labels without allowing trailing commentary to contaminate the
# searchable caption or tag values.
_LABEL_LINE = re.compile(
    r"^\s*(?:[*_`>#\-]\s*)*(TEXT|CAPTION|TAGS)(?:\s*[*_`]+)?\s*:\s*"
    r"(?:(?:[*_`]+)(?=\s|$)\s*)?(.*)$",
    re.IGNORECASE,
)
_MARKDOWN_EMPHASIS_MARKERS = ("**", "__", "`", "*", "_")


class ImageDescriptionParseError(ValueError):
    """Neither TEXT nor CAPTION could be found in the vision provider's
    response -- raised instead of silently returning an empty
    ImageDescription, so a provider response genuinely unusable end to
    end is surfaced, not confused with "described nothing."
    """


def _strip_outer_markdown_emphasis(value: str) -> str:
    """Remove balanced outer Markdown emphasis without changing inner text."""
    cleaned = value.strip()
    changed = True
    while changed:
        changed = False
        for marker in _MARKDOWN_EMPHASIS_MARKERS:
            if (
                cleaned.startswith(marker)
                and cleaned.endswith(marker)
                and len(cleaned) > 2 * len(marker)
            ):
                cleaned = cleaned[len(marker) : -len(marker)].strip()
                changed = True
                break
    return cleaned


def _parse_description(content: str) -> ImageDescription:
    fields: dict[str, list[str]] = {"TEXT": [], "CAPTION": [], "TAGS": []}
    multiline_field: str | None = None
    for line in content.splitlines():
        match = _LABEL_LINE.match(line)
        if match:
            label = match.group(1).upper()
            remainder = _strip_outer_markdown_emphasis(match.group(2))
            if remainder:
                fields[label].append(remainder)
            multiline_field = "TEXT" if label == "TEXT" else None
            continue

        if re.match(r"^\s*[*_`>#\-\s]*[A-Za-z][A-Za-z0-9 _-]*\s*:", line):
            multiline_field = None
            continue
        if multiline_field == "TEXT" and line.strip():
            fields["TEXT"].append(_strip_outer_markdown_emphasis(line))

    if not fields["TEXT"] and not fields["CAPTION"]:
        raise ImageDescriptionParseError(
            f"vision response had neither TEXT nor CAPTION content: {content!r}"
        )

    extracted_text = "\n".join(fields["TEXT"]).strip()
    if extracted_text.upper() == "NONE":
        extracted_text = ""
    caption = "\n".join(fields["CAPTION"]).strip()
    tags_raw = " ".join(fields["TAGS"]).strip()
    tags = tuple(
        cleaned
        for tag in tags_raw.split(",")
        if (cleaned := _strip_outer_markdown_emphasis(tag))
    )
    return ImageDescription(extracted_text=extracted_text, caption=caption, tags=tags)


class OpenAiCompatibleVisionClient:
    """Calls an OpenAI-compatible vision-capable chat model for OCR and
    object recognition/tagging in one round trip.
    """

    available = True

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 60.0,
        allow_insecure_http: bool = False,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"unsupported vision client URL scheme: {parsed.scheme or 'missing'}"
            )
        if parsed.scheme == "http" and not allow_insecure_http:
            # A plain-HTTP endpoint sends the Bearer API key and every raw
            # image over the wire unencrypted. Secure-by-default: require
            # an explicit opt-in (local dev/tests only) rather than
            # allowing any remote http:// host silently.
            raise ValueError(
                "OpenAiCompatibleVisionClient requires https:// by default; "
                "pass allow_insecure_http=True for local-dev-only http:// endpoints"
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


def orchestrator_vision_client(base_url: str, api_key: str, model: str) -> ImageContentClient:
    """Build a vision client against the same orchestrator root other channels use.

    Other clients POST ``{base_url}/v1/chat/completions``;
    :class:`OpenAiCompatibleVisionClient` POSTs ``{base_url}/chat/completions``,
    so this appends ``/v1`` unless already present. An ``http://`` orchestrator
    (local docker) is allowed because the other channels already talk to the
    same URL. A construct-time error degrades to the unavailable null rather
    than crashing the request that asked for a description.
    """
    if not (base_url and api_key and model):
        return NullImageContentClient()
    parsed = urlparse(base_url)
    vision_base = base_url.rstrip("/")
    if not vision_base.endswith("/v1"):
        vision_base = f"{vision_base}/v1"
    try:
        return OpenAiCompatibleVisionClient(
            base_url=vision_base,
            api_key=api_key,
            model=model,
            allow_insecure_http=parsed.scheme == "http",
        )
    except ValueError:
        return NullImageContentClient()
