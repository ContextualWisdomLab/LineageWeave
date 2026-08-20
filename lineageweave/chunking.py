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
  boundaries ``div``, ``p``, ``li``, ``tr`` -- a table row, not each
  cell, since cells sharing a row are one unit; see ``_TABLE_CELL_TAGS``).
  Relevant once a source
  document is HTML/MHTML rather than plain text (e.g. a raw ingested
  email). Each block's inline ``style`` attribute is
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
from html import unescape
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
        "ul",
        "ol",
        "oi",
        "tr",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "w:p",
        "w:tbl",
        "w:tr",
    }
)

# A table row is the block unit, not each cell -- a cell pushed as its own
# block (the previous behavior for "td"/"w:tc") loses which cells shared a
# row: `<tr><td>1</td><td>Acme Corp</td></tr>` flattened into two
# independent one-line chunks "1" and "Acme Corp" is indistinguishable from
# two unrelated one-line paragraphs, and a real 5-column x 13-row table
# read this way degrades into an unrecoverable flat list (live bug,
# 2026-08-19). Cells append inline into the open row's buffer instead,
# delimited by " | ", so "1 | Acme Corp | ..." keeps each row's columns
# readable and attributable as one unit.
_TABLE_ROW_TAGS = frozenset({"tr", "w:tr"})
_TABLE_CELL_TAGS = frozenset({"td", "th", "w:tc"})
_LIST_CONTAINER_TAGS = frozenset({"ul", "ol", "oi"})

_LIST_ITEM_START = re.compile(
    r"^(?:[-*•·]\s+|[*†‡](?=\S)|(?:\d{1,3}|[A-Za-z가-힣])[.)]\s+|[①-⑳]\s+)"
)
_FOOTNOTE_START = re.compile(r"^[*†‡]+(?=\S)")


def normalize_semantic_text(text: str) -> str:
    """Remove visual hanging-indent breaks without changing source content."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized: list[str] = []
    for line in lines:
        stripped = line.replace("\xa0", " ").strip()
        if not stripped:
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue
        if normalized and normalized[-1] != "" and not _LIST_ITEM_START.match(stripped):
            normalized[-1] = f"{normalized[-1]} {stripped}"
        else:
            normalized.append(stripped)
    return "\n".join(normalized).strip()


def _source_indent_width(text: str) -> int:
    """Measure leading source whitespace separately from semantic text."""
    first_line = next((line for line in text.replace("\r", "\n").split("\n") if line.strip()), "")
    leading = re.match(r"^[ \t]+", first_line)
    if leading is None:
        return 0
    return sum(4 if character == "\t" else 1 for character in leading.group(0))


def _length_to_indent_units(value: str) -> int:
    """Convert common CSS/XML lengths to a comparable eight-pixel unit."""
    match = re.fullmatch(r"\s*([+-]?(?:\d+\.?\d*|\.\d+))\s*(px|pt|em|rem|in|cm|mm|%)?\s*", value, re.I)
    if match is None:
        return 0
    amount = float(match.group(1))
    if amount <= 0:
        return 0
    scale = {
        "px": 1.0,
        "pt": 96 / 72,
        "em": 16.0,
        "rem": 16.0,
        "in": 96.0,
        "cm": 96 / 2.54,
        "mm": 96 / 25.4,
        "%": 16 / 100,
    }.get((match.group(2) or "px").lower(), 1.0)
    return max(0, round(amount * scale / 8))


def _shorthand_left_value(raw: str) -> str:
    """Pick the left-side length out of a CSS 1-4 value box shorthand
    (``margin``/``padding``), per the CSS box-model value-count rule:
    1 value = all sides, 2 = vertical/horizontal, 3 = top/horizontal/bottom,
    4 = top/right/bottom/left.
    """
    parts = raw.split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) >= 4:
        return parts[3]
    return parts[1]


def _declared_indent_width(tag: str, attrs: list[tuple[str, str | None]]) -> int:
    """Read HTML CSS and WordprocessingML paragraph indentation declarations."""
    width = 4 if tag in {"blockquote", "ul", "ol", "oi"} else 0
    style = next((value or "" for name, value in attrs if name == "style"), "")
    for match in re.finditer(
        r"(?:^|;)\s*(?:margin-left|padding-left|padding-inline-start|text-indent)\s*:\s*([^;]+)",
        style,
        re.I,
    ):
        width += _length_to_indent_units(match.group(1))
    # A real editor (Word paste, Outlook compose) declares indentation with
    # the box-model shorthand ("margin: 0cm 0cm 0cm 56px") far more often
    # than the longhand "margin-left" the pattern above alone recognizes --
    # every nested <li> in a real body used only the shorthand, so its
    # indentation silently read as 0 and every nesting level collapsed flat
    # (live bug, 2026-08-19).
    for match in re.finditer(r"(?:^|;)\s*(?:margin|padding)\s*:\s*([^;]+)", style, re.I):
        width += _length_to_indent_units(_shorthand_left_value(match.group(1)))
    for name, value in attrs:
        if name in {"w:left", "w:start", "w:firstline"} and value:
            try:
                width += max(0, round(int(value) / 120))
            except ValueError:
                continue
    return width


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
        indent_width: source indentation in semantic units, retained as
            structural metadata while presentation whitespace is removed from
            ``text``.
    """

    text: str
    unit_type: str
    index: int
    label: str = ""
    image_data: bytes | None = field(default=None, compare=True)
    style: str | None = None
    indent_width: int = 0


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
    paragraphs = [normalize_semantic_text(p) for p in re.split(r"\n\s*\n", text) if p.strip()]
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
    sentences = [normalize_semantic_text(s) for s in _SENTENCE_BOUNDARY.split(text.strip()) if s.strip()]
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
        self._stack: list[tuple[str, list[str], str | None, int]] = []
        self._unscoped_buffer: list[str] = []
        self._active_superscripts: list[tuple[int, list[str]]] = []
        self._numeric_superscript_buffers: set[int] = set()
        # Each entry is ("text", str, tag_name, style) or
        # ("image", (mime_type, bytes), "", None) -- a single sequence in
        # true document order, so an image's index among its siblings
        # reflects where it actually sat.
        self._finished: list[tuple[str, object, str, str | None, int]] = []

    def _declared_stack_width(self) -> int:
        """Combine list depth with explicit width without double counting."""
        list_depth = sum(entry[0] in _LIST_CONTAINER_TAGS for entry in self._stack)
        explicit_width = sum(
            max(0, entry[3] - 4) if entry[0] in _LIST_CONTAINER_TAGS else entry[3]
            for entry in self._stack
        )
        return max(explicit_width, list_depth * 4)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant text state when an HTML start tag is encountered."""
        if tag == "img":
            src = next((value for name, value in attrs if name == "src" and value), None)
            if src:
                decoded = _decode_data_uri_image(src)
                if decoded is not None:
                    self._finished.append(("image", decoded, "", None, 0))
            return
        if tag == "sup":
            if self._stack:
                self._active_superscripts.append((id(self._stack[-1][1]), []))
            return
        if tag in {"br", "w:br"} and self._stack:
            self._stack[-1][1].append("\n")
            return
        if tag == "w:ind" and self._stack:
            tag_name, buffer, style, indent_width = self._stack[-1]
            self._stack[-1] = (
                tag_name,
                buffer,
                style,
                indent_width + _declared_indent_width(tag, attrs),
            )
            return
        if tag in _LIST_CONTAINER_TAGS:
            # Emit a parent list item before entering its nested list. Closing
            # tags otherwise make the child appear before the parent in the
            # finished list, which destroys the source order buyers use to
            # read a hierarchy.
            if self._stack and self._stack[-1][0] == "li" and self._stack[-1][1]:
                tag_name, buffer, style, indent_width = self._stack[-1]
                self._stack[-1] = (tag_name, [], style, indent_width)
                self._finish_block(
                    tag_name,
                    buffer,
                    style,
                    self._declared_stack_width(),
                )
            style = next((value for name, value in attrs if name == "style" and value), None)
            self._stack.append((tag, [], style, _declared_indent_width(tag, attrs)))
            return
        if tag in _TABLE_CELL_TAGS:
            if self._stack and self._stack[-1][0] in _TABLE_ROW_TAGS and self._stack[-1][1]:
                self._stack[-1][1].append(" | ")
            return
        # A rich-text editor commonly wraps a table cell in a nested <p> or
        # <div>. Keep that content in the open row; otherwise the nested block
        # closes first and destroys the row/column boundary.
        if any(entry[0] in _TABLE_ROW_TAGS for entry in self._stack):
            return
        if tag in _DOM_BLOCK_TAGS:
            style = next((value for name, value in attrs if name == "style" and value), None)
            self._stack.append((tag, [], style, _declared_indent_width(tag, attrs)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle self-closing block tags without losing XML indentation state."""
        self.handle_starttag(tag, attrs)
        if tag in _DOM_BLOCK_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        """Close the relevant text state when an HTML end tag is encountered."""
        if tag == "sup":
            if self._active_superscripts:
                buffer_id, content = self._active_superscripts.pop()
                if re.fullmatch(r"\s*\d{1,3}\s*", "".join(content)):
                    self._numeric_superscript_buffers.add(buffer_id)
            return
        if tag in _DOM_BLOCK_TAGS and self._stack and self._stack[-1][0] == tag:
            declared_width = self._declared_stack_width()
            tag_name, buffer, style, _ = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width)

    def _finish_block(
        self, tag_name: str, buffer: list[str], style: str | None, declared_width: int
    ) -> None:
        """Emit one block buffer, including a block closed only at EOF."""
        raw_text = "".join(buffer)
        superscript_marker = id(buffer) in self._numeric_superscript_buffers
        for raw_unit, source_indent in _split_dom_units(raw_text):
            text = normalize_semantic_text(raw_unit)
            if text:
                indent_width = declared_width + source_indent
                label = (
                    "footnote"
                    if superscript_marker or _FOOTNOTE_START.match(text)
                    else tag_name
                )
                self._finished.append(
                    ("text", text, label, style, indent_width)
                )
        self._numeric_superscript_buffers.discard(id(buffer))

    def handle_data(self, data: str) -> None:
        """Collect character data from the current HTML text region."""
        text = data
        for _ in range(3):
            decoded = unescape(text)
            if decoded == text:
                break
            text = decoded
        if self._active_superscripts:
            self._active_superscripts[-1][1].append(text)
        had_nbsp = "\xa0" in text
        text = text.replace("\xa0", " ")
        if self._stack and (text.strip() or had_nbsp):
            self._stack[-1][1].append(text)
        elif text.strip() or had_nbsp:
            self._unscoped_buffer.append(text)

    def finished(self) -> list[tuple[str, object, str, str | None, int]]:
        """Return the normalized records collected from the HTML fragment."""
        while self._stack:
            declared_width = self._declared_stack_width()
            tag_name, buffer, style, _ = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width)
        if not self._finished:
            fallback = normalize_semantic_text("".join(self._unscoped_buffer))
            if fallback:
                return [("text", fallback, "", None, _source_indent_width(fallback))]
        return self._finished


def _split_dom_units(raw_text: str) -> list[tuple[str, int]]:
    """Split forced visual lines at authored list starts, not arbitrary wraps."""
    units: list[tuple[str, int]] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            raw_unit = "\n".join(current)
            if raw_unit.strip():
                units.append((raw_unit, _source_indent_width(raw_unit)))
            current.clear()

    for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line.strip():
            flush()
            continue
        if current and _LIST_ITEM_START.match(line.strip()):
            flush()
        current.append(line.rstrip())
    flush()
    return units


_MARKDOWN_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def _markdown_cells(line: str) -> list[str] | None:
    """Return Markdown table cells, or ``None`` for a non-table line."""
    if "|" not in line:
        return None
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith("\\|"):
        value = value[:-1]
    cells = [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", value)]
    return cells if len(cells) >= 2 and all(cells) else None


def _markdown_table_entries(text: str) -> list[tuple[str, str]]:
    """Extract table rows while retaining non-table prose around the table."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    entries: list[tuple[str, str]] = []
    pending: list[str] = []
    found_table = False

    def flush_pending() -> None:
        if pending:
            value = normalize_semantic_text("\n".join(pending))
            if value:
                entries.append(("", value))
            pending.clear()

    index = 0
    while index < len(lines):
        header = _markdown_cells(lines[index])
        separator = _markdown_cells(lines[index + 1]) if index + 1 < len(lines) else None
        if header is None or separator is None or not all(
            _MARKDOWN_SEPARATOR_CELL.fullmatch(cell) for cell in separator
        ):
            pending.append(lines[index])
            index += 1
            continue

        found_table = True
        flush_pending()
        entries.append(("markdown_tr", " | ".join(header)))
        index += 2
        while index < len(lines) and lines[index].strip():
            cells = _markdown_cells(lines[index])
            if cells is None:
                break
            entries.append(("markdown_tr", " | ".join(cells)))
            index += 1

    flush_pending()
    return entries if found_table else []


def chunk_by_dom(html: str) -> list[Chunk]:
    """Split HTML/MHTML content at sectioning/flow block-element boundaries,
    plus one ``"image"`` chunk per embedded base64 ``<img>``, all in a
    single document-order sequence.

    Nested block tags do not create nested chunks (the innermost block a
    piece of text sits in owns it) -- a ``<div><p>...</p></div>`` yields
    one chunk labeled ``p``, not one for the ``div`` and a duplicate for
    the ``p``. An ``"image"`` chunk's ``text`` starts empty (OCR/caption)
    text is filled in separately by a vision client -- see
    ``lineageweave.image_content``); its ``index`` among the full sequence
    is what lets the image be placed back where it actually was relative
    to the surrounding text chunks.
    """
    if "<" not in html:
        markdown_entries = _markdown_table_entries(html)
        if markdown_entries:
            return [
                Chunk(
                    text=text,
                    unit_type="plain_text",
                    index=index,
                    label=label,
                )
                for index, (label, text) in enumerate(markdown_entries)
            ]

    parser = _BlockTextExtractor()
    parser.feed(html)
    entries = parser.finished()
    chunks: list[Chunk] = []
    for index, (kind, value, tag_name, style, indent_width) in enumerate(entries):
        if kind == "text":
            chunks.append(
                Chunk(
                    text=value,
                    unit_type="plain_text" if not tag_name else "dom",
                    index=index,
                    label=tag_name,
                    style=style,
                    indent_width=indent_width,
                )
            )
        else:
            mime_type, image_bytes = value
            chunks.append(
                Chunk(
                    text="",
                    unit_type="image",
                    index=index,
                    label=mime_type,
                    image_data=image_bytes,
                )
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
