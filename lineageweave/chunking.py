"""Semantic-unit chunking for the embedding channel.

Embedding a whole flattened document as one vector buries a short relevant
passage under everything else in the same document -- the embedding
averages over content that has nothing to do with the query. Splitting
into meaning-identifiable units first, embedding each unit, and comparing
at the unit level (see :func:`chunked_max_similarity` in
:mod:`lineageweave.embedding_client`) keeps a genuinely relevant unit's
signal from being diluted by everything around it.

Four unit types, each grounded in a boundary concept that already has a
name in the literature or a relevant standard rather than an arbitrary
character-count split:

- **paragraph**: subtopic-passage boundaries (Hearst, 1997 -- TextTiling).
  A cheap paragraph-break splitter here approximates TextTiling's
  block-comparison boundary detection without the full lexical-cohesion
  scoring machinery; see the module docstring note on the upgrade path.
- **sentence**: the finer-grained unit inside a paragraph, for short-form
  content (titles, single-sentence records) where a paragraph split alone
  would still leave the whole record as one unit.
- **dom**: sectioning-content element boundaries (WHATWG HTML Living
  Standard / W3C HTML5 -- ``article``, ``section``, ``nav``, ``aside``,
  ``header``, ``footer``, headings ``h1``-``h6``, and flow-content block
  boundaries ``div``, ``p``, ``li``, ``td``). Relevant once a source
  document is HTML/MHTML rather than plain text (e.g. a raw ingested
  email or SAP ALV export). Each block's inline ``style`` attribute is
  captured on the resulting :class:`Chunk` as separate metadata, never
  concatenated into the embedded text -- raw markup diluting an
  embedding's signal is exactly the failure mode chunking exists to
  avoid, and a formatting cue (color, alignment, size) is real
  structural signal worth keeping, not noise to discard (VIPS; Cai,
  Yu, Wen, & Ma, 2003).
- **conversation_turn**: sender/receiver boundaries (RFC 5322 email
  structure -- ``From``/``To`` headers delimit one party's turn from the
  next). Reuses the same "one message, one party" shape ThreadWeave's JWZ
  threading already models (see ``reconstruct.py``), just applied within a
  single record's body instead of across records.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

# WHATWG HTML Living Standard / W3C HTML5 sectioning-content and common
# flow-content block elements -- boundaries a DOM-unit chunker should
# split on rather than treating the whole document as one text blob.
# h1-h6 included: a heading's tag name is itself a formatting/importance
# cue (VIPS, Cai, Yu, Wen, & Ma, 2003 -- font/size/tag signals distinguish a
# document's structural blocks), not just a text-boundary marker.
_DOM_BLOCK_TAGS = frozenset(
    {
        "article",
        "section",
        "nav",
        "aside",
        "header",
        "footer",
        "div",
        "p",
        "li",
        "td",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }
)


@dataclass(frozen=True)
class Chunk:
    """One semantic unit ready to be embedded independently.

    Attributes:
        text: the unit's text content (empty for an ``"image"`` chunk
            until a vision client fills in OCR/caption text separately --
            see ``lineageweave.image_content``).
        unit_type: which chunker produced this (``"paragraph"``,
            ``"sentence"``, ``"dom"``, ``"image"``, or
            ``"conversation_turn"``).
        index: position among this document's chunks (0-based) -- for an
            ``"image"`` chunk produced by :func:`chunk_by_dom`, this is
            the image's position among ALL sibling chunks (text and
            image together, true document order), which is what makes the
            image's original location in the document reconstructable.
        label: optional unit-specific context (a DOM tag name, a
            sender/receiver identifier, or an image MIME type) -- not
            embedded, useful for attributing which chunk matched in a
            result.
        image_data: raw decoded image bytes, only set for ``"image"``
            chunks.
        style: the block's raw inline ``style`` attribute (e.g.
            ``"color:red;text-align:center"``), only set for ``"dom"``
            chunks that had one. A formatting cue -- font color,
            alignment, size -- degrades an embedding or an LLM prompt if
            dumped into the text alongside the content (VIPS; Cai, Yu,
            Wen, & Ma, 2003), so it is kept here as separate,
            addressable metadata instead, never concatenated into
            ``text``. ``None`` when the element had no ``style``
            attribute, distinct from an empty string (which would mean
            "had the attribute, but it was blank").
    """

    text: str
    unit_type: str
    index: int
    label: str = ""
    image_data: bytes | None = field(default=None, compare=True)
    style: str | None = None


def chunk_by_paragraph(text: str) -> list[Chunk]:
    """Split on blank-line boundaries (Hearst, 1997 -- subtopic passages).

    ponytail: a real TextTiling implementation scores lexical cohesion in
    a sliding window and places boundaries at cohesion minima; this uses
    the much cheaper proxy of literal blank-line breaks, which is exactly
    right for content that already uses paragraph breaks as authored
    structure (most real documents) and only degrades for the harder case
    of paragraph-free prose. Upgrade to real TextTiling scoring if a real
    document set turns out to need it.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []
    return [Chunk(text=p, unit_type="paragraph", index=i) for i, p in enumerate(paragraphs)]


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9가-힣])")


def chunk_by_sentence(text: str) -> list[Chunk]:
    """Split on sentence boundaries -- the finer unit inside a paragraph.

    ponytail: a regex sentence splitter over-merges/under-merges on
    abbreviations, decimals, and quoted speech; a real NLP sentence
    segmenter (e.g. a Unicode-aware tokenizer) is the upgrade path if a
    real document set shows this matters. Good enough for short business
    records and paragraph-internal splitting.
    """
    sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(text.strip()) if s.strip()]
    if not sentences:
        return []
    return [Chunk(text=s, unit_type="sentence", index=i) for i, s in enumerate(sentences)]


def _decode_data_uri_image(src: str) -> tuple[str, bytes] | None:
    """Parse a ``data:image/<mime>;base64,<data>`` src attribute value."""
    if not src.lower().startswith("data:image/"):
        return None
    header, _, encoded = src.partition(",")
    if ";base64" not in header:
        return None
    mime_type = header[len("data:") : header.index(";")]
    try:
        return mime_type, base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
    except (binascii.Error, ValueError):
        return None


class _BlockTextExtractor(HTMLParser):
    """Attributes each piece of text to its innermost enclosing block tag,
    and records ``<img>`` data-URI occurrences in the same document-order
    sequence as the surrounding text blocks.

    A stack of buffers, one per currently-open block element: text is
    appended only to the top (innermost) buffer, so
    ``<article><p>A</p><p>B</p></article>`` yields two chunks ("A" and
    "B"), not one merged "A B" -- the more specific enclosing block wins.
    A block with no direct text of its own (only nested blocks, as in
    ``<div><p>text</p></div>``) contributes no chunk -- its child already
    owns that text, so it is never duplicated onto the ancestor.
    """

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[tuple[str, list[str], str | None]] = []
        # Each entry is ("text", str, tag_name, style) or
        # ("image", (mime_type, bytes), "", None) -- a single sequence in
        # true document order, so an image's index among its siblings
        # reflects where it actually sat.
        self._finished: list[tuple[str, object, str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            src = next((value for name, value in attrs if name == "src" and value), None)
            if src:
                decoded = _decode_data_uri_image(src)
                if decoded is not None:
                    self._finished.append(("image", decoded, "", None))
            return
        if tag in _DOM_BLOCK_TAGS:
            style = next((value for name, value in attrs if name == "style" and value), None)
            self._stack.append((tag, [], style))

    def handle_endtag(self, tag: str) -> None:
        if tag in _DOM_BLOCK_TAGS and self._stack:
            tag_name, buffer, style = self._stack.pop()
            text = " ".join(buffer).strip()
            if text:
                self._finished.append(("text", text, tag_name, style))

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text and self._stack:
            self._stack[-1][1].append(text)

    def finished(self) -> list[tuple[str, object, str, str | None]]:
        return self._finished


def chunk_by_dom(html: str) -> list[Chunk]:
    """Split HTML/MHTML content at sectioning/flow block-element boundaries,
    plus one ``"image"`` chunk per embedded base64 ``<img>``, all in a
    single document-order sequence.

    Nested block tags do not create nested chunks (the outermost block a
    piece of text sits in owns it) -- a ``<div><p>...</p></div>`` yields
    one chunk for the ``div``, not one for the ``div`` and a duplicate for
    the ``p``. An ``"image"`` chunk's ``text`` starts empty (OCR/caption
    text is filled in separately by a vision client -- see
    ``lineageweave.image_content``); its ``index`` among the full sequence
    is what lets the image be placed back where it actually was relative
    to the surrounding text chunks.
    """
    parser = _BlockTextExtractor()
    parser.feed(html)
    entries = parser.finished()
    chunks: list[Chunk] = []
    for index, (kind, value, tag_name, style) in enumerate(entries):
        if kind == "text":
            chunks.append(Chunk(text=value, unit_type="dom", index=index, label=tag_name, style=style))
        else:
            mime_type, image_bytes = value
            chunks.append(
                Chunk(text="", unit_type="image", index=index, label=mime_type, image_data=image_bytes)
            )
    return chunks


@dataclass(frozen=True)
class ConversationTurn:
    """One party's turn in a conversation-shaped document (RFC 5322 From/To)."""

    sender: str
    text: str


def chunk_by_conversation_turn(turns: list[ConversationTurn]) -> list[Chunk]:
    """One chunk per non-empty sender turn, labeled with who sent it.

    Empty turns are filtered out before indexing, not after -- so
    ``Chunk.index`` is always a contiguous 0-based position among the
    chunks actually returned, never the filtered-out original turn index.
    """
    non_empty_turns = [turn for turn in turns if turn.text.strip()]
    return [
        Chunk(text=turn.text, unit_type="conversation_turn", index=i, label=turn.sender)
        for i, turn in enumerate(non_empty_turns)
    ]
