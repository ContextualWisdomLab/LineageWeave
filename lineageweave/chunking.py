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
  ``header``, ``footer``, and flow-content block boundaries ``div``,
  ``p``, ``li``, ``td``). Relevant once a source document is HTML/MHTML
  rather than plain text (e.g. a raw ingested email or SAP ALV export).
- **conversation_turn**: sender/receiver boundaries (RFC 5322 email
  structure -- ``From``/``To`` headers delimit one party's turn from the
  next). Reuses the same "one message, one party" shape ThreadWeave's JWZ
  threading already models (see ``reconstruct.py``), just applied within a
  single record's body instead of across records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

# WHATWG HTML Living Standard / W3C HTML5 sectioning-content and common
# flow-content block elements -- boundaries a DOM-unit chunker should
# split on rather than treating the whole document as one text blob.
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
    }
)


@dataclass(frozen=True)
class Chunk:
    """One semantic unit ready to be embedded independently.

    Attributes:
        text: the unit's text content.
        unit_type: which chunker produced this (``"paragraph"``,
            ``"sentence"``, ``"dom"``, or ``"conversation_turn"``).
        index: position among this document's chunks (0-based).
        label: optional unit-specific context (a DOM tag name, or a
            sender/receiver identifier) -- not embedded, useful for
            attributing which chunk matched in a result.
    """

    text: str
    unit_type: str
    index: int
    label: str = ""


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


class _BlockTextExtractor(HTMLParser):
    """Attributes each piece of text to its innermost enclosing block tag.

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
        self._stack: list[list[str]] = []
        self._finished_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DOM_BLOCK_TAGS:
            self._stack.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag in _DOM_BLOCK_TAGS and self._stack:
            buffer = self._stack.pop()
            text = " ".join(buffer).strip()
            if text:
                self._finished_blocks.append(text)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text and self._stack:
            self._stack[-1].append(text)

    def blocks(self) -> list[str]:
        return self._finished_blocks


def chunk_by_dom(html: str) -> list[Chunk]:
    """Split HTML/MHTML content at sectioning/flow block-element boundaries.

    Nested block tags do not create nested chunks (the outermost block a
    piece of text sits in owns it) -- a ``<div><p>...</p></div>`` yields
    one chunk for the ``div``, not one for the ``div`` and a duplicate for
    the ``p``.
    """
    parser = _BlockTextExtractor()
    parser.feed(html)
    blocks = parser.blocks()
    if not blocks:
        return []
    return [Chunk(text=b, unit_type="dom", index=i) for i, b in enumerate(blocks)]


@dataclass(frozen=True)
class ConversationTurn:
    """One party's turn in a conversation-shaped document (RFC 5322 From/To)."""

    sender: str
    text: str


def chunk_by_conversation_turn(turns: list[ConversationTurn]) -> list[Chunk]:
    """One chunk per sender turn, labeled with who sent it."""
    return [
        Chunk(text=turn.text, unit_type="conversation_turn", index=i, label=turn.sender)
        for i, turn in enumerate(turns)
        if turn.text.strip()
    ]
