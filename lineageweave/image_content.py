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
import json
import math
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
from urllib.parse import urlparse

from PIL import Image

from .http_client import chat_completion_content, post_json

_DATA_URI_IMG = re.compile(
    r'<img\b[^>]*\bsrc\s*=\s*["\']data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)["\']',
    re.IGNORECASE,
)


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


@dataclass(frozen=True)
class ImageRegion:
    """A normalized visual region returned by the VISION locator."""

    x: float
    y: float
    width: float
    height: float


def crop_image_region(image_bytes: bytes, mime_type: str, region: ImageRegion) -> tuple[bytes, str]:
    """Normalize an image and crop one bounded region as opaque PNG."""
    from .vision_image import normalize_vision_image

    normalized, _ = normalize_vision_image(image_bytes, mime_type)
    with Image.open(BytesIO(normalized)) as source:
        left = max(0, min(source.width - 1, round(region.x * source.width)))
        top = max(0, min(source.height - 1, round(region.y * source.height)))
        right = max(left + 1, min(source.width, round((region.x + region.width) * source.width)))
        bottom = max(top + 1, min(source.height, round((region.y + region.height) * source.height)))
        output = BytesIO()
        source.crop((left, top, right, bottom)).save(output, format="PNG")
    return output.getvalue(), "image/png"


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
        images.append(EmbeddedImage(position=match.start(), mime_type=mime_type, data=data))
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
        """Describe the supplied image through the configured vision channel."""
        raise RuntimeError("NullImageContentClient has no image channel; check .available first")


_RESPONSE_FORMAT = (
    "Examine this image. Reply with EXACTLY three lines, no extra commentary:\n"
    "TEXT: <all legible text in the image, verbatim, or NONE if there is none. "
    "If the image contains a table, preserve its row/column structure: one row "
    "per line, with ' | ' between that row's cell values, in reading order -- "
    "never flatten a table into an unstructured word list.>\n"
    "CAPTION: <2-4 concise, evidence-grounded sentences describing the visible layout, "
    "objects, relationships, directions, measurements, and labels; do not guess "
    "anything that is not visible>\n"
    "TAGS: <comma-separated short tags for the main objects/subjects>"
)
_REGION_RESPONSE_FORMAT = (
    "Find distinct meaningful visual regions in this image for separate OCR and description. "
    "The returned regions must collectively cover the entire image, edge to edge -- "
    "do not stop at only the most visually striking parts and omit the rest; a "
    "plain-looking area (a table, a block of body text) still needs its own "
    "region if no existing region already covers it. "
    "Return JSON only in this exact shape: "
    '{"regions":[{"x":0.0,"y":0.0,"width":1.0,"height":1.0}]} . '
    "Coordinates are normalized to 0..1, omit decorative borders, and return at most 12 regions."
)
_VISION_SYSTEM_ROLE = (
    "You are the LineageWeave visual-evidence agent. Extract only evidence "
    "visible in the supplied image; never invent people, projects, or text."
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
    """Implement the _parse_description operation for this channel."""
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
        raise ImageDescriptionParseError("vision response had no usable TEXT or CAPTION content")

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
        model: str | None = None,
        *,
        timeout: float = 180.0,
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
        self._model = model.strip() if model else ""
        self._timeout = timeout

    def describe(self, image_bytes: bytes, mime_type: str) -> ImageDescription:
        """Describe the supplied image through the configured vision channel."""
        from .vision_image import normalize_vision_image

        image_bytes, mime_type = normalize_vision_image(image_bytes, mime_type)
        data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        payload = {
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_ROLE},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _RESPONSE_FORMAT},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "mode": "auto",
            "reasoning_effort": "auto",
            "max_tokens": 1024,
        }
        if self._model:
            payload["model"] = self._model
        body = post_json(
            f"{self._base_url}/chat/completions",
            payload,
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = chat_completion_content(body)
        return _parse_description(content)

    def locate_regions(self, image_bytes: bytes, mime_type: str) -> tuple[ImageRegion, ...]:
        """Locate meaningful visual panels through the same orchestrator VISION model."""
        from .vision_image import normalize_vision_image

        image_bytes, mime_type = normalize_vision_image(image_bytes, mime_type)
        data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        payload = {
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_ROLE},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _REGION_RESPONSE_FORMAT},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "mode": "auto",
            "reasoning_effort": "auto",
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        if self._model:
            payload["model"] = self._model
        body = post_json(
            f"{self._base_url}/chat/completions",
            payload,
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = chat_completion_content(body)
        fenced = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content, flags=re.IGNORECASE)
        document = json.loads(fenced)
        if not isinstance(document, dict):
            raise TypeError("vision region response had no regions list")
        regions = document.get("regions")
        if not isinstance(regions, list):
            single_region = tuple(document.get(name) for name in ("x", "y", "width", "height"))
            if all(
                isinstance(value, (int, float)) and math.isfinite(float(value))
                for value in single_region
            ):
                regions = [document]
            else:
                raise ValueError("vision region response had no regions list")
        accepted: list[ImageRegion] = []
        seen: set[tuple[int, int, int, int]] = set()
        for candidate in regions[:12]:
            if not isinstance(candidate, dict):
                continue
            values = tuple(candidate.get(name) for name in ("x", "y", "width", "height"))
            if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values):
                continue
            x, y, width, height = (float(value) for value in values)
            if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
                continue
            key = tuple(round(value * 1000) for value in (x, y, width, height))
            if key not in seen:
                accepted.append(ImageRegion(x, y, width, height))
                seen.add(key)
        return tuple(accepted)


def orchestrator_vision_client(
    base_url: str,
    api_key: str,
    model: str | None = None,
    *,
    timeout: float = 180.0,
) -> ImageContentClient:
    """Build a vision client against the same orchestrator root other channels use.

    Other clients POST ``{base_url}/v1/chat/completions``;
    :class:`OpenAiCompatibleVisionClient` POSTs ``{base_url}/chat/completions``,
    so this appends ``/v1`` unless already present. An ``http://`` orchestrator
    (local docker) is allowed because the other channels already talk to the
    same URL. The optional timeout lets a bounded caller share its admitted
    transport budget with synchronous Vision requests. A construct-time error
    degrades to the unavailable null rather than crashing the request that
    asked for a description.
    """
    if not (base_url and api_key):
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
            timeout=timeout,
            allow_insecure_http=parsed.scheme == "http",
        )
    except ValueError:
        return NullImageContentClient()
