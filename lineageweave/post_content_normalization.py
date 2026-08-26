"""Normalizes a post's raw body -- which may be plain text or HTML/MHTML
with embedded base64 images -- into clean text safe to hand to an LLM
prompt or an embedding call, with formatting cues and image content kept
as structured metadata instead of either degrading the text or silently
dropping them.

This module is the missing wire between two already-built, already-tested
capabilities (:mod:`lineageweave.chunking`'s DOM-unit split and
:mod:`lineageweave.image_content`'s per-image OCR/captioning) and every
call site that currently reads ``source_post.post_body`` and hands it
straight to an LLM: raw HTML tags dilute an embedding or a prompt exactly
the way :mod:`lineageweave.chunking` was built to avoid, and a base64
``<img>`` payload sent as literal text either blows the prompt's token
budget or is silently ignored by a text-only model.

Grounded in the same VIPS (Cai, Yu, Wen, & Ma, 2003) and
TrOCR/CLIP (see ``image_content.py``) literature :mod:`lineageweave.chunking`
and :mod:`lineageweave.image_content` already cite -- this module adds no
new claim of its own, it only combines the two.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .chunking import Chunk, chunk_by_dom, normalize_semantic_text
from .image_content import (
    ImageContentClient,
    ImageDescription,
    ImageRegion,
    NullImageContentClient,
    crop_image_region,
)

# Real HTML tags only -- a VOC body like "qty < 50 and price > 10" is
# still plain text and must pass through unchanged. Listed tags match
# what chunk_by_dom already splits on, plus the inline/replaced tags
# that carry images or wrap rich-text fragments.
_HTML_OPEN_TAG = re.compile(
    r"<\s*/?\s*(?:article|section|nav|aside|header|footer|div|p|li|td|th|tr|"
    r"table|blockquote|h[1-6]|img|br|hr|ul|ol|span|strong|em|b|i|u|a|"
    r"sup|sub|"
    r"html|body|head|style|script|font|center|pre)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FormattingHint:
    """One block's structural formatting, kept separate from its text
    content -- see :attr:`Chunk.style` for why this is never concatenated
    into the normalized text.
    """

    chunk_index: int
    tag: str
    style: str | None


@dataclass(frozen=True)
class ImageContentResult:
    """One embedded image's document-order result, including failures."""

    chunk_index: int
    mime_type: str
    status_code: str
    description: ImageDescription | None = None
    regions: tuple[ImageRegionResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ImageRegionResult:
    """One visual subregion and its independently obtained description."""

    region_index: int
    region: ImageRegion
    status_code: str
    description: ImageDescription | None = None


@dataclass(frozen=True)
class NormalizedPostContent:
    """The result of normalizing one post body.

    Attributes:
        text: clean, HTML-tag-free text, safe for an LLM prompt or an
            embedding call. Plain-text input passes through unchanged.
            Each embedded image is replaced with a bracketed placeholder
            at its original position (``[image: <caption> | text: <ocr>]``
            when a vision client described it, ``[image: content unavailable]``
            when none was configured or the call failed) -- an image is
            never silently dropped and its raw base64 never appears in
            this string.
        formatting_hints: block-level formatting cues (tag, inline style)
            in document order, addressable by ``chunk_index`` -- empty
            for plain-text input.
        image_descriptions: every embedded image's real OCR text,
            caption, and tags, in document order -- empty when the input
            had no images or no vision client was available.
        image_results: every embedded image's outcome, including unavailable
            and failed outcomes, keyed by the original document-order index.
    """

    text: str
    formatting_hints: tuple[FormattingHint, ...] = field(default_factory=tuple)
    image_descriptions: tuple[ImageDescription, ...] = field(default_factory=tuple)
    image_results: tuple[ImageContentResult, ...] = field(default_factory=tuple)


def _looks_like_html(body: str) -> bool:
    """True only when a real HTML tag is present, not a comparison operator."""
    return _HTML_OPEN_TAG.search(body) is not None


def _image_placeholder(description: ImageDescription) -> str:
    """Caption plus OCR text -- both are what the vision call paid for."""
    caption = description.caption or "no caption available"
    ocr = description.extracted_text.strip()
    if ocr:
        return f"[image: {caption}]\n\n{ocr}\n"
    return f"[image: {caption}]"


def _merge_region_descriptions(descriptions: list[ImageDescription]) -> ImageDescription:
    """Keep all successful region evidence in the parent image unit."""
    extracted_text = "\n".join(item.extracted_text.strip() for item in descriptions if item.extracted_text.strip())
    captions = " ".join(item.caption.strip() for item in descriptions if item.caption.strip())
    tags = tuple(dict.fromkeys(tag for item in descriptions for tag in item.tags))
    return ImageDescription(extracted_text=extracted_text, caption=captions, tags=tags)


def _is_bounded_region(region: ImageRegion) -> bool:
    """Accept only finite, positive regions wholly inside the image."""
    if not isinstance(region, ImageRegion):
        return False
    values = (region.x, region.y, region.width, region.height)
    if not all(isinstance(value, (int, float)) for value in values):
        return False
    return (
        all(math.isfinite(value) for value in values)
        and 0.0 <= region.x <= 1.0
        and 0.0 <= region.y <= 1.0
        and 0.0 < region.width <= 1.0
        and 0.0 < region.height <= 1.0
        and region.x + region.width <= 1.0
        and region.y + region.height <= 1.0
    )


def _describe_image_region(
    region_index: int,
    image_bytes: bytes,
    mime_type: str,
    region: ImageRegion,
    vision_client: ImageContentClient,
) -> ImageRegionResult:
    """Describe one region without allowing one failed crop to cancel siblings."""
    try:
        cropped, cropped_mime = crop_image_region(image_bytes, mime_type, region)
        description = vision_client.describe(cropped, cropped_mime)
    except Exception:  # noqa: BLE001 - preserve the region-level failure evidence.
        return ImageRegionResult(region_index, region, "failed")
    return ImageRegionResult(region_index, region, "described", description)


def _describe_image_chunk(
    chunk: Chunk, vision_client: ImageContentClient
) -> tuple[ImageContentResult, ImageDescription | None, str]:
    """Analyze one image chunk and keep its evidence and failure state."""
    result = ImageContentResult(
        chunk_index=chunk.index,
        mime_type=chunk.label,
        status_code="unavailable",
    )
    if not vision_client.available or chunk.image_data is None:
        return result, None, "[image: content unavailable]"

    region_results: list[ImageRegionResult] = []
    try:
        locator = getattr(vision_client, "locate_regions", None)
        try:
            regions = locator(chunk.image_data, chunk.label) if callable(locator) else ()
        except Exception:  # noqa: BLE001 - locator failure falls back to whole-image evidence.
            regions = ()
        try:
            regions = tuple(
                region
                for region in (regions or ())
                if _is_bounded_region(region)
            )
        except Exception:  # noqa: BLE001 - malformed locator output falls back safely.
            regions = ()
        full_image_region = len(regions) == 1 and regions[0] == ImageRegion(0.0, 0.0, 1.0, 1.0)
        has_subregions = bool(regions) and not full_image_region
        if not regions or full_image_region:
            # Missing or full-image locator output is not a decomposed region.
            # Preserve parent-image evidence below without inventing coordinates.
            regions = ()
        # ponytail: serialize per-post VISION calls; nested image/region pools
        # overwhelmed the gateway and turned valid region evidence into failures.
        # Reintroduce bounded concurrency only after provider capacity is measured.
        if regions:
            region_results.extend(
                _describe_image_region(
                    region_index,
                    chunk.image_data,
                    chunk.label,
                    region,
                    vision_client,
                )
                for region_index, region in enumerate(regions)
            )
        successful_regions = [
            item.description for item in region_results if item.description is not None
        ]
        if has_subregions:
            # Keep valid salient panels instead of replacing them with a full-image
            # crop, then ask once more for the uncovered parent image so text outside
            # those panels remains searchable and its original location is preserved.
            try:
                description = vision_client.describe(chunk.image_data, chunk.label)
            except Exception:
                if not successful_regions:
                    raise
                description = _merge_region_descriptions(successful_regions)
        else:
            description = (
                _merge_region_descriptions(successful_regions)
                if successful_regions
                else vision_client.describe(chunk.image_data, chunk.label)
            )
    except Exception:  # noqa: BLE001 - a provider failure must not drop the whole post.
        return ImageContentResult(chunk.index, chunk.label, "failed"), None, "[image: content unavailable]"

    result = ImageContentResult(
        chunk_index=chunk.index,
        mime_type=chunk.label,
        status_code="described",
        description=description,
        regions=tuple(region_results),
    )
    return result, description, _image_placeholder(description)


def normalize_post_body(
    body: str, vision_client: ImageContentClient | None = None
) -> NormalizedPostContent:
    """Turn a raw ``post_body`` into text safe for an LLM/embedding call.

    Plain-text input (no HTML markup detected) passes through unchanged
    with no formatting hints or images -- this function never invents
    structure that was not there. `vision_client` defaults to
    :class:`~lineageweave.image_content.NullImageContentClient`
    (unavailable): an embedded image still gets a clearly-labeled
    "content unavailable" placeholder at its correct position rather
    than vanishing, so a caller can tell the difference between "no
    image was here" and "an image was here but could not be described."
    """
    if vision_client is None:
        vision_client = NullImageContentClient()

    if not _looks_like_html(body):
        return NormalizedPostContent(text=normalize_semantic_text(body))

    chunks: list[Chunk] = chunk_by_dom(body)
    text_parts: list[str] = []
    formatting_hints: list[FormattingHint] = []
    image_descriptions: list[ImageDescription] = []
    image_results: list[ImageContentResult] = []
    image_outcomes: dict[int, tuple[ImageContentResult, ImageDescription | None, str]] = {}
    image_chunks = [chunk for chunk in chunks if chunk.unit_type == "image"]
    if image_chunks and vision_client.available:
        for chunk in image_chunks:
            image_outcomes[chunk.index] = _describe_image_chunk(chunk, vision_client)

    for chunk in chunks:
        if chunk.unit_type == "dom":
            text_parts.append(chunk.text)
            if chunk.style is not None:
                formatting_hints.append(
                    FormattingHint(chunk_index=chunk.index, tag=chunk.label, style=chunk.style)
                )
        elif chunk.unit_type == "image":
            result, description, placeholder = image_outcomes.get(
                chunk.index,
                (
                    ImageContentResult(chunk.index, chunk.label, "unavailable"),
                    None,
                    "[image: content unavailable]",
                ),
            )
            if description is not None:
                image_descriptions.append(description)
            text_parts.append(placeholder)
            image_results.append(result)

    return NormalizedPostContent(
        text="\n\n".join(part for part in text_parts if part),
        formatting_hints=tuple(formatting_hints),
        image_descriptions=tuple(image_descriptions),
        image_results=tuple(image_results),
    )
