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
  boundaries ``div``, ``p``, ``li``, ``ol``, ``ul``, ``tr`` -- a table row, not each
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
        "ol",
        "ul",
        "li",
        "math",
        "footnote",
        "endnote",
        "w:footnote",
        "w:endnote",
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
_TABLE_TAGS = frozenset({"table", "w:tbl"})

_LIST_ITEM_START = re.compile(
    r"^(?:[-*•·]\s+|[*†‡](?=\S)|(?:\d{1,3}|[A-Za-z가-힣])[.)]\s+|[①-⑳]\s+)"
)


def _is_footnote_block(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
    """Recognize semantic footnote markup emitted by HTML and Word exports."""
    if tag.casefold().rsplit(":", 1)[-1] in {"footnote", "endnote"}:
        return True
    values = " ".join(
        value or ""
        for name, value in attrs
        if name.casefold() in {"class", "id", "role", "data-role"}
    ).casefold()
    return "footnote" in values or "endnote" in values


def _is_footnote_reference(attrs: list[tuple[str, str | None]]) -> bool:
    """Recognize a Word footnote-definition backlink, not its body citation."""
    values = {
        name.casefold(): (value or "").casefold()
        for name, value in attrs
        if name.casefold() in {"href", "id", "name"}
    }
    href = values.get("href", "")
    anchor_values = (values.get("id", ""), values.get("name", ""))
    return "ftnref" in href and any(
        "ftn" in value and "ftnref" not in value for value in anchor_values
    )


# Unicode Super/Subscript blocks (The Unicode Consortium, 2024, §22.4) plus the
# Latin-1 superscript digits. Quantity display uses these so embeddings keep
# "m³" distinct from "m3" without retaining HTML in the semantic text (ADR 0165).
_SUPERSCRIPT = {
    "0": "\u2070",
    "1": "\u00b9",
    "2": "\u00b2",
    "3": "\u00b3",
    "4": "\u2074",
    "5": "\u2075",
    "6": "\u2076",
    "7": "\u2077",
    "8": "\u2078",
    "9": "\u2079",
    "+": "\u207a",
    "-": "\u207b",
    "=": "\u207c",
    "(": "\u207d",
    ")": "\u207e",
    "n": "\u207f",
    "N": "\u207f",
    "i": "\u2071",
    "I": "\u2071",
}
_SUBSCRIPT = {
    "0": "\u2080",
    "1": "\u2081",
    "2": "\u2082",
    "3": "\u2083",
    "4": "\u2084",
    "5": "\u2085",
    "6": "\u2086",
    "7": "\u2087",
    "8": "\u2088",
    "9": "\u2089",
    "+": "\u208a",
    "-": "\u208b",
    "=": "\u208c",
    "(": "\u208d",
    ")": "\u208e",
    "a": "\u2090",
    "e": "\u2091",
    "h": "\u2095",
    "i": "\u1d62",
    "k": "\u2096",
    "l": "\u2097",
    "m": "\u2098",
    "n": "\u2099",
    "o": "\u2092",
    "p": "\u209a",
    "s": "\u209b",
    "t": "\u209c",
    "x": "\u2093",
}
_SUPERSCRIPT_VALUES = frozenset(_SUPERSCRIPT.values())
_SUBSCRIPT_VALUES = frozenset(_SUBSCRIPT.values())
_INLINE_SCRIPT_TAGS = frozenset({"sup", "sub"})
_HTML_SUP = re.compile(r"<sup\b[^>]*>(.*?)</sup>", re.IGNORECASE | re.DOTALL)
_HTML_SUB = re.compile(r"<sub\b[^>]*>(.*?)</sub>", re.IGNORECASE | re.DOTALL)
_INNER_TAG = re.compile(r"<[^>]+>")
# Quantity caret after a unit/digit, not a leading footnote marker such as `^1`.
_CARET_EXPONENT = re.compile(
    r"(?<=[A-Za-z0-9µμ°ΩÅåÅ)])\^(?:\{([+\-]?\d{1,3}|[nNiI])\}|([+\-]?\d{1,3}|[nNiI]))"
)
_ENCODED_CARET = re.compile(r"&(?:amp;)*(?:#0*94|#x0*5e);", re.IGNORECASE)
_ENCODED_LT = r"&(?:amp;)*(?:lt|#0*60|#x0*3c);"
_ENCODED_GT = r"&(?:amp;)*(?:gt|#0*62|#x0*3e);"
_ENCODED_SCRIPT_TOKEN = (
    rf"{_ENCODED_LT}\s*/?\s*(?:sup|sub)(?=\s|/|{_ENCODED_GT})"
)
_ENCODED_SCRIPT_PAIR = re.compile(
    rf"{_ENCODED_LT}(?P<kind>sup|sub){_ENCODED_GT}"
    rf"(?P<inner>(?:(?!{_ENCODED_SCRIPT_TOKEN}).)*?)"
    rf"{_ENCODED_LT}/(?P=kind){_ENCODED_GT}",
    re.IGNORECASE | re.DOTALL,
)


def apply_unicode_script(text: str, kind: str) -> str:
    """Map a short exponent/index run to Unicode, or keep a caret/underscore."""
    table = _SUPERSCRIPT if kind == "sup" else _SUBSCRIPT
    values = _SUPERSCRIPT_VALUES if kind == "sup" else _SUBSCRIPT_VALUES
    compact = text.strip()
    if not compact:
        return text
    if all(ch in table or ch in values or ch.isspace() for ch in compact):
        return "".join(table.get(ch, ch) for ch in text)
    prefix = "^" if kind == "sup" else "_"
    leading_len = len(text) - len(text.lstrip())
    trailing_len = len(text) - len(text.rstrip())
    leading = text[:leading_len]
    trailing = text[len(text) - trailing_len :] if trailing_len else ""
    return f"{leading}{prefix}{compact}{trailing}"


def _decode_html_entities(text: str) -> str:
    for _ in range(3):
        decoded = unescape(text)
        if decoded == text:
            break
        text = decoded
    return text


def _decode_script_entities(text: str) -> str:
    decoded_pairs = _ENCODED_SCRIPT_PAIR.sub(
        lambda match: (
            f"<{match.group('kind').lower()}>{match.group('inner')}"
            f"</{match.group('kind').lower()}>"
        ),
        text,
    )
    return _ENCODED_CARET.sub(
        lambda match: _decode_html_entities(match.group(0)), decoded_pairs
    )


def _replace_html_script(match: re.Match[str], kind: str) -> str:
    inner = _decode_html_entities(match.group(1))
    return apply_unicode_script(_INNER_TAG.sub("", inner), kind)


def normalize_script_text(text: str) -> str:
    """Turn HTML/caret quantity scripts into Unicode without treating comparisons as tags."""
    replaced = _CARET_EXPONENT.sub(
        lambda match: apply_unicode_script(match.group(1) or match.group(2), "sup"),
        _decode_script_entities(text),
    )
    replaced = _HTML_SUP.sub(lambda match: _replace_html_script(match, "sup"), replaced)
    replaced = _HTML_SUB.sub(lambda match: _replace_html_script(match, "sub"), replaced)
    return replaced


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
    return normalize_script_text("\n".join(normalized).strip())


def _source_indent_width(text: str) -> int:
    """Measure leading source whitespace separately from semantic text."""
    first_line = next((line for line in text.replace("\r", "\n").split("\n") if line.strip()), "")
    leading = re.match(r"^[ \t]+", first_line)
    if leading is None:
        return 0
    return sum(4 if character == "\t" else 1 for character in leading.group(0))


def _length_to_indent_units(value: str) -> int:
    """Convert common CSS/XML lengths to a comparable eight-pixel unit."""
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+\.?\d*|\.\d+))\s*(px|pt|em|rem|in|cm|mm|%)?\s*",
        value,
        re.IGNORECASE,
    )
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
    width = 4 if tag in {"blockquote", "ul", "ol"} else 0
    style = next((value or "" for name, value in attrs if name == "style"), "")
    for match in re.finditer(
        r"(?:^|;)\s*(?:margin-left|padding-left|padding-inline-start|text-indent)\s*:\s*([^;]+)",
        style,
        re.IGNORECASE,
    ):
        width += _length_to_indent_units(match.group(1))
    # A real editor (Word paste, Outlook compose) declares indentation with
    # the box-model shorthand ("margin: 0cm 0cm 0cm 56px") far more often
    # than the longhand "margin-left" the pattern above alone recognizes --
    # every nested <li> in a real body used only the shorthand, so its
    # indentation silently read as 0 and every nesting level collapsed flat
    # (live bug, 2026-08-19).
    for match in re.finditer(
        r"(?:^|;)\s*(?:margin|padding)\s*:\s*([^;]+)", style, re.IGNORECASE
    ):
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
        declared_indent_width: indentation declared by HTML/CSS/OOXML or a
            nested list container. Source-only leading spaces are excluded so
            callers can distinguish authored structure from visual alignment.
        source_evidence_reference: optional opaque caller-owned reference for
            an explicitly parsed source unit. LineageWeave stores but never
            interprets this value.
    """

    text: str
    unit_type: str
    index: int
    label: str = ""
    image_data: bytes | None = field(default=None, compare=True)
    style: str | None = None
    indent_width: int = 0
    declared_indent_width: int = 0
    source_evidence_reference: str | None = None


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
        self._stack: list[tuple[str, list[str], str | None, int, bool]] = []
        self._unscoped_buffer: list[str] = []
        self._script_stack: list[str] = []
        self._table_cell_counts: list[int] = []
        self._table_depth = 0
        self._table_row_depths: list[int] = []
        # Each entry is ("text", str, tag_name, style) or
        # ("image", (mime_type, bytes), "", None) -- a single sequence in
        # true document order, so an image's index among its siblings
        # reflects where it actually sat.
        self._finished: list[tuple[str, object, str, str | None, int, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant text state when an HTML start tag is encountered."""
        if tag in _TABLE_TAGS:
            self._table_depth += 1
        if tag in _INLINE_SCRIPT_TAGS:
            self._script_stack.append(tag)
            return
        if tag == "img":
            src = next((value for name, value in attrs if name == "src" and value), None)
            if src:
                decoded = _decode_data_uri_image(src)
                if decoded is not None:
                    self._finished.append(("image", decoded, "", None, 0, 0))
            return
        if tag in {"br", "w:br"} and self._stack:
            self._stack[-1][1].append("\n")
            return
        if tag == "w:ind" and self._stack:
            tag_name, buffer, style, indent_width, is_footnote = self._stack[-1]
            self._stack[-1] = (
                tag_name,
                buffer,
                style,
                indent_width + _declared_indent_width(tag, attrs),
                is_footnote,
            )
            return
        if tag == "a" and self._stack and _is_footnote_reference(attrs):
            tag_name, buffer, style, indent_width, _ = self._stack[-1]
            self._stack[-1] = (tag_name, buffer, style, indent_width, True)
            return
        if tag in _TABLE_CELL_TAGS:
            self._script_stack.clear()
            if self._stack and self._stack[-1][0] in _TABLE_ROW_TAGS:
                if self._table_cell_counts[-1]:
                    self._stack[-1][1].append(" | ")
                self._table_cell_counts[-1] += 1
            return
        if (
            tag in _TABLE_ROW_TAGS
            and self._table_row_depths
            and self._table_row_depths[-1] == self._table_depth
        ):
            declared_width = sum(entry[3] for entry in self._stack)
            tag_name, buffer, style, _, is_footnote = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width, is_footnote)
        # A rich-text editor commonly wraps a table cell in a nested <p> or
        # <div>. Keep that content in the open row; otherwise the nested block
        # closes first and destroys the row/column boundary.
        if (
            tag not in _TABLE_ROW_TAGS
            and any(entry[0] in _TABLE_ROW_TAGS for entry in self._stack)
        ):
            return
        if tag in _DOM_BLOCK_TAGS:
            if tag not in _TABLE_ROW_TAGS and self._stack and self._stack[-1][1]:
                tag_name, buffer, style, _, is_footnote = self._stack[-1]
                declared_width = sum(entry[3] for entry in self._stack)
                self._finish_block(tag_name, buffer, style, declared_width, is_footnote)
                buffer.clear()
            style = next((value for name, value in attrs if name == "style" and value), None)
            is_footnote = _is_footnote_block(tag, attrs) or any(
                entry[4] for entry in self._stack
            )
            self._stack.append(
                (tag, [], style, _declared_indent_width(tag, attrs), is_footnote)
            )
            if tag in _TABLE_ROW_TAGS:
                self._table_cell_counts.append(0)
                self._table_row_depths.append(self._table_depth)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle self-closing block tags without losing XML indentation state."""
        self.handle_starttag(tag, attrs)
        if tag in _DOM_BLOCK_TAGS or tag in _INLINE_SCRIPT_TAGS or tag in _TABLE_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        """Close the relevant text state when an HTML end tag is encountered."""
        if (
            tag in _TABLE_TAGS
            and self._table_row_depths
            and self._table_row_depths[-1] == self._table_depth
        ):
            declared_width = sum(entry[3] for entry in self._stack)
            tag_name, buffer, style, _, is_footnote = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width, is_footnote)
        if tag in _INLINE_SCRIPT_TAGS:
            if tag in self._script_stack:
                while self._script_stack:
                    closed = self._script_stack.pop()
                    if closed == tag:
                        break
            return
        if tag in _TABLE_CELL_TAGS:
            self._script_stack.clear()
            return
        if tag in _DOM_BLOCK_TAGS and self._stack and self._stack[-1][0] == tag:
            declared_width = sum(entry[3] for entry in self._stack)
            tag_name, buffer, style, _, is_footnote = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width, is_footnote)
        if tag in _TABLE_TAGS:
            self._table_depth = max(0, self._table_depth - 1)

    def _finish_block(
        self,
        tag_name: str,
        buffer: list[str],
        style: str | None,
        declared_width: int,
        is_footnote: bool = False,
    ) -> None:
        """Emit one block buffer, including a block closed only at EOF."""
        # An unclosed <sup>/<sub> never reaches handle_endtag, so nothing else
        # pops it off _script_stack. Every block boundary (a sibling block
        # opening, this block's own endtag, or EOF) routes through here, so
        # clearing here stops a dangling script tag from bleeding into later,
        # unrelated blocks -- mirroring how a browser would not let inline
        # formatting survive a block-level boundary.
        self._script_stack.clear()
        raw_text = "".join(buffer)
        if tag_name in _TABLE_ROW_TAGS:
            self._table_cell_counts.pop()
            self._table_row_depths.pop()
        for raw_unit, source_indent in _split_dom_units(raw_text):
            text = normalize_semantic_text(raw_unit)
            if text:
                indent_width = declared_width + source_indent
                label = "footnote" if is_footnote else tag_name
                self._finished.append(
                    (
                        "text",
                        text,
                        label,
                        style,
                        indent_width,
                        declared_width,
                    )
                )

    def handle_data(self, data: str) -> None:
        """Collect character data from the current HTML text region."""
        text = data
        for _ in range(3):
            decoded = unescape(text)
            if decoded == text:
                break
            text = decoded
        had_nbsp = "\xa0" in text
        text = text.replace("\xa0", " ")
        if self._script_stack:
            text = apply_unicode_script(text, self._script_stack[-1])
        if self._stack and (text.strip() or had_nbsp):
            self._stack[-1][1].append(text)
        elif text.strip() or had_nbsp:
            self._unscoped_buffer.append(text)

    def finished(self) -> list[tuple[str, object, str, str | None, int, int]]:
        """Return the normalized records collected from the HTML fragment."""
        while self._stack:
            declared_width = sum(entry[3] for entry in self._stack)
            tag_name, buffer, style, _, is_footnote = self._stack.pop()
            self._finish_block(tag_name, buffer, style, declared_width, is_footnote)
        if not self._finished:
            fallback = normalize_semantic_text("".join(self._unscoped_buffer))
            if fallback:
                return [
                    ("text", fallback, "", None, _source_indent_width(fallback), 0)
                ]
        return self._finished


def _split_dom_units(raw_text: str) -> list[tuple[str, int]]:
    """Split forced visual lines at authored list starts, not arbitrary wraps."""
    units: list[tuple[str, int]] = []
    current: list[str] = []

    def flush() -> None:
        """Join the buffered lines into one DOM unit and clear the buffer."""
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


_MARKDOWN_TABLE_SEPARATOR = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


def _markdown_table_cells(line: str) -> list[str]:
    """Return cells while removing only optional outer pipe delimiters."""
    cells = line.strip().split("|")
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return cells


def _is_markdown_table_row(line: str) -> bool:
    """Recognize a pipe row only when it has at least two cells."""
    cells = _markdown_table_cells(line)
    return len(cells) >= 2 and any(cell.strip() for cell in cells)


def _is_empty_markdown_table_row(line: str, column_count: int) -> bool:
    """Recognize an all-empty row only inside an established table."""
    cells = _markdown_table_cells(line)
    return len(cells) == column_count and not any(cell.strip() for cell in cells)


def _render_markdown_table_row(line: str) -> str:
    """Keep Markdown table columns as searchable row evidence."""
    return " | ".join(cell.strip() for cell in _markdown_table_cells(line))


def _split_plain_text_units(text: str) -> list[tuple[str, int, str]]:
    """Split markup-free source into paragraphs, list items, and table rows."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    units: list[tuple[str, int, str]] = []
    current: list[str] = []

    def flush() -> None:
        """Normalize the buffered lines into one plain-text unit and clear the buffer."""
        if current:
            raw_unit = "\n".join(current)
            normalized = normalize_semantic_text(raw_unit)
            if normalized:
                units.append((normalized, _source_indent_width(raw_unit), ""))
            current.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            flush()
            index += 1
            continue
        if _is_markdown_table_row(line):
            rows: list[str] = []
            column_count = len(_markdown_table_cells(line))
            while index < len(lines):
                candidate = lines[index]
                established = (
                    len(rows) >= 2
                    and bool(_MARKDOWN_TABLE_SEPARATOR.match(rows[1]))
                    and len(_markdown_table_cells(rows[1])) == column_count
                )
                if not _is_markdown_table_row(candidate) and not (
                    established
                    and _is_empty_markdown_table_row(candidate, column_count)
                ):
                    break
                rows.append(candidate)
                index += 1
            data_rows = [row for row in rows if not _MARKDOWN_TABLE_SEPARATOR.match(row)]
            if len(data_rows) >= 2:
                flush()
                units.extend(
                    (
                        normalize_semantic_text(_render_markdown_table_row(row)),
                        _source_indent_width(row),
                        "tr",
                    )
                    for row in data_rows
                )
                continue
            current.extend(rows)
            continue
        if current and _LIST_ITEM_START.match(line.strip()):
            flush()
        current.append(line.rstrip())
        index += 1
    flush()
    return units


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
    parser = _BlockTextExtractor()
    parser.feed(html)
    entries = parser.finished()
    chunks: list[Chunk] = []
    for index, (
        kind,
        value,
        tag_name,
        style,
        indent_width,
        declared_indent_width,
    ) in enumerate(entries):
        if kind == "text":
            chunks.append(
                Chunk(
                    text=value,
                    unit_type="plain_text" if not tag_name else "dom",
                    index=index,
                    label=tag_name,
                    style=style,
                    indent_width=indent_width,
                    declared_indent_width=declared_indent_width,
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


def chunk_by_source_body(body: str) -> list[Chunk]:
    """Chunk either a DOM body or markup-free authored semantic units."""
    dom_chunks = chunk_by_dom(body)
    if re.search(r"<[A-Za-z][^>]*>", body):
        return dom_chunks
    return [
        Chunk(
            text=text,
            unit_type="plain_text",
            index=index,
            label=label,
            indent_width=indent_width,
            declared_indent_width=0,
        )
        for index, (text, indent_width, label) in enumerate(_split_plain_text_units(body))
    ]


@dataclass(frozen=True)
class ConversationTurn:
    """One party's turn in a conversation-shaped document (RFC 5322 From/To)."""

    sender: str
    text: str
    source_evidence_reference: str | None = None


def chunk_by_conversation_turn(turns: list[ConversationTurn]) -> list[Chunk]:
    """One chunk per non-empty sender turn, labeled with who sent it.

    Empty turns are filtered out before indexing, not after -- so
    ``Chunk.index`` is always a contiguous 0-based position among the
    chunks actually returned, never the filtered-out original turn index.
    """
    non_empty_turns = [turn for turn in turns if turn.text.strip()]
    return [
        Chunk(
            text=turn.text,
            unit_type="conversation_turn",
            index=i,
            label=turn.sender,
            source_evidence_reference=turn.source_evidence_reference,
        )
        for i, turn in enumerate(non_empty_turns)
    ]
