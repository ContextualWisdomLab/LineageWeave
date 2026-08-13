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
budget or is silently ignored by a text-only model -- neither of which
this repo's real posts can afford, since the source content genuinely
mixes rich-text formatting and inline images (SAP CRM VOC/consultation
records commonly do).

Grounded in the same VIPS (Cai, Yu, Wen, & Ma, 2003) and
TrOCR/CLIP (see ``image_content.py``) literature :mod:`lineageweave.chunking`
and :mod:`lineageweave.image_content` already cite -- this module adds no
new claim of its own, it only combines the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .chunking import Chunk, chunk_by_dom
from .image_content import ImageContentClient, ImageDescription, NullImageContentClient


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
class NormalizedPostContent:
    """The result of normalizing one post body.

    Attributes:
        text: clean, HTML-tag-free text, safe for an LLM prompt or an
            embedding call. Plain-text input passes through unchanged.
            Each embedded image is replaced with a bracketed placeholder
            at its original position (``[image: <caption>]`` when a
            vision client described it, ``[image: content unavailable]``
            when none was configured or the call failed) -- an image is
            never silently dropped and its raw base64 never appears in
            this string.
        formatting_hints: block-level formatting cues (tag, inline style)
            in document order, addressable by ``chunk_index`` -- empty
            for plain-text input.
        image_descriptions: every embedded image's real OCR text,
            caption, and tags, in document order -- empty when the input
            had no images or no vision client was available.
    """

    text: str
    formatting_hints: tuple[FormattingHint, ...] = field(default_factory=tuple)
    image_descriptions: tuple[ImageDescription, ...] = field(default_factory=tuple)


def _looks_like_html(body: str) -> bool:
    """A block-tag opening angle bracket is a strong enough signal --
    real plain-text business records essentially never contain one."""
    return "<" in body and ">" in body


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
        return NormalizedPostContent(text=body)

    chunks: list[Chunk] = chunk_by_dom(body)
    text_parts: list[str] = []
    formatting_hints: list[FormattingHint] = []
    image_descriptions: list[ImageDescription] = []

    for chunk in chunks:
        if chunk.unit_type == "dom":
            text_parts.append(chunk.text)
            if chunk.style is not None:
                formatting_hints.append(
                    FormattingHint(chunk_index=chunk.index, tag=chunk.label, style=chunk.style)
                )
        elif chunk.unit_type == "image":
            if vision_client.available and chunk.image_data is not None:
                try:
                    description = vision_client.describe(chunk.image_data, chunk.label)
                except Exception:  # noqa: BLE001 - a provider failure must not drop the whole post.
                    text_parts.append("[image: content unavailable]")
                else:
                    image_descriptions.append(description)
                    caption = description.caption or "no caption available"
                    text_parts.append(f"[image: {caption}]")
            else:
                text_parts.append("[image: content unavailable]")

    return NormalizedPostContent(
        text="\n\n".join(part for part in text_parts if part),
        formatting_hints=tuple(formatting_hints),
        image_descriptions=tuple(image_descriptions),
    )
