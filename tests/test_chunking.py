from __future__ import annotations

from lineageweave.chunking import (
    ConversationTurn,
    _length_to_indent_units,
    _shorthand_left_value,
    chunk_by_conversation_turn,
    chunk_by_dom,
    chunk_by_source_body,
    chunk_by_paragraph,
    chunk_by_sentence,
    normalize_semantic_text,
)


def test_chunk_by_paragraph_splits_on_blank_lines() -> None:
    """Blank lines delimit ordered paragraph chunks."""
    text = "First paragraph about budgets.\n\nSecond paragraph about logistics.\n\nThird."
    chunks = chunk_by_paragraph(text)

    assert [c.text for c in chunks] == [
        "First paragraph about budgets.",
        "Second paragraph about logistics.",
        "Third.",
    ]
    assert all(c.unit_type == "paragraph" for c in chunks)
    assert [c.index for c in chunks] == [0, 1, 2]


def test_chunk_by_paragraph_ignores_extra_blank_lines_and_whitespace() -> None:
    """Extra blank lines and outer whitespace do not create chunks."""
    text = "  A.  \n\n\n\n  B.  "
    chunks = chunk_by_paragraph(text)
    assert [c.text for c in chunks] == ["A.", "B."]


def test_chunk_by_paragraph_empty_text_yields_no_chunks() -> None:
    """Empty paragraph input produces no semantic units."""
    assert chunk_by_paragraph("") == []
    assert chunk_by_paragraph("   \n\n  ") == []


def test_chunk_by_sentence_splits_on_sentence_boundaries() -> None:
    """Sentence punctuation followed by a new sentence creates a boundary."""
    text = "This is one sentence. This is another! Is this a third?"
    chunks = chunk_by_sentence(text)

    assert [c.text for c in chunks] == [
        "This is one sentence.",
        "This is another!",
        "Is this a third?",
    ]
    assert all(c.unit_type == "sentence" for c in chunks)


def test_chunk_by_sentence_empty_text_yields_no_chunks() -> None:
    """Whitespace alone has no sentence-level semantic unit."""
    assert chunk_by_sentence(" \n ") == []


def test_indent_helpers_cover_invalid_lengths_and_css_shorthand_shapes() -> None:
    """Invalid and non-positive lengths stay flat; shorthand picks the left side."""
    assert _length_to_indent_units("auto") == 0
    assert _length_to_indent_units("-8px") == 0
    assert _shorthand_left_value("") == ""
    assert _shorthand_left_value("8px") == "8px"
    assert _shorthand_left_value("8px 16px") == "16px"


def test_chunk_by_dom_splits_on_block_element_boundaries() -> None:
    """Sibling DOM blocks remain separate semantic units."""
    html = (
        "<article><p>First block of text.</p><p>Second block of text.</p></article>"
        "<aside>Unrelated sidebar content.</aside>"
    )
    chunks = chunk_by_dom(html)

    texts = [c.text for c in chunks]
    assert "First block of text." in texts
    assert "Second block of text." in texts
    assert "Unrelated sidebar content." in texts
    assert all(c.unit_type == "dom" for c in chunks)


def test_chunk_by_dom_nested_blocks_do_not_duplicate_text() -> None:
    """The innermost block owns text without duplicating its ancestor."""
    html = "<div><p>Nested paragraph text.</p></div>"
    chunks = chunk_by_dom(html)

    # The innermost block owns the text; there is exactly one chunk, not
    # one for the div and a duplicate for the p inside it.
    assert len(chunks) == 1
    assert chunks[0].text == "Nested paragraph text."
    assert chunks[0].label == "p"


def test_chunk_by_dom_flushes_parent_text_before_nested_block() -> None:
    """Direct parent text remains before a later child block."""
    chunks = chunk_by_dom("<div>Parent text<p>Child text</p></div>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("div", "Parent text"),
        ("p", "Child text"),
    ]


def test_chunk_by_dom_groups_table_cells_by_row_instead_of_flattening() -> None:
    """Live bug (2026-08-19): each <td> used to push its own independent
    chunk with no row grouping, so a real table (headers + N data rows)
    degraded into a flat, unattributable list of cell fragments -- e.g. a
    5-column x 13-row table read back as 65 disconnected one-word lines
    with no way to tell which cells shared a row.
    """
    html = (
        "<table>"
        "<tr><td>No.</td><td>Company</td><td>Result</td></tr>"
        "<tr><td>1</td><td>Acme Corp</td><td>Declined</td></tr>"
        "<tr><td>2</td><td>Globex Corp</td><td>Interested</td></tr>"
        "</table>"
    )
    chunks = chunk_by_dom(html)

    texts = [c.text for c in chunks]
    assert texts == [
        "No. | Company | Result",
        "1 | Acme Corp | Declined",
        "2 | Globex Corp | Interested",
    ]
    assert all(c.label == "tr" for c in chunks)


def test_chunk_by_dom_keeps_nested_table_cell_blocks_in_their_row() -> None:
    """Nested cell blocks retain their table-row grouping."""
    chunks = chunk_by_dom(
        "<table><tr><td><p>No.</p></td><td><div>Company</div></td></tr></table>"
    )
    assert [(chunk.label, chunk.text) for chunk in chunks] == [("tr", "No. | Company")]


def test_chunk_by_dom_keeps_cell_lists_inside_their_table_row() -> None:
    """A list inside a cell stays readable and grouped with its row."""
    chunks = chunk_by_dom(
        "<table><tr><td>Items:<ul><li>A</li><li>B</li></ul></td>"
        "<td>Owner</td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "Items: A B | Owner")
    ]

    leading_list = chunk_by_dom(
        "<table><tr><td><ul><li>A</li><li>B</li></ul></td>"
        "<td>Owner</td></tr></table>"
    )
    assert [chunk.text for chunk in leading_list] == ["A B | Owner"]


def test_chunk_by_dom_labels_markerless_footnotes() -> None:
    """A leading footnote marker assigns the footnote label."""
    chunks = chunk_by_dom("<p>Body text</p><p>*Tier 2: follow-up note</p>")
    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body text"),
        ("footnote", "*Tier 2: follow-up note"),
    ]


def test_chunk_by_dom_labels_numeric_superscript_footnotes() -> None:
    """A leading numeric superscript assigns the footnote label."""
    chunks = chunk_by_dom("<p><sup>1</sup> Source note attached to the record.</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "1 Source note attached to the record."),
    ]


def test_chunk_by_dom_labels_numeric_superscript_after_body_text() -> None:
    """A numeric superscript anywhere in a paragraph marks its evidence role."""
    chunks = chunk_by_dom("<p>Body claim<sup>1</sup> source note.</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "Body claim1 source note."),
    ]


def test_chunk_by_dom_does_not_treat_non_numeric_superscript_as_footnote() -> None:
    """A formula superscript remains ordinary prose."""
    chunks = chunk_by_dom("<p>Formula x<sup>n</sup> remains prose.</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Formula xn remains prose."),
    ]


def test_chunk_by_dom_preserves_nested_list_order_and_depth() -> None:
    """Nested list items retain source order and increasing depth."""
    chunks = chunk_by_dom(
        "<ol><li>Parent item<ul><li>Child item</li></ul></li></ol>"
    )

    assert [chunk.text for chunk in chunks] == ["Parent item", "Child item"]
    assert [chunk.indent_width for chunk in chunks] == [4, 8]


def test_chunk_by_dom_accepts_exporter_oi_list_container() -> None:
    """The exporter-specific oi tag behaves as an ordered-list container."""
    chunks = chunk_by_dom("<oi><li>First item</li><li>Second item</li></oi>")

    assert [chunk.text for chunk in chunks] == ["First item", "Second item"]
    assert [chunk.indent_width for chunk in chunks] == [4, 4]


def test_chunk_by_dom_keeps_markdown_table_rows_as_searchable_units() -> None:
    """Markdown rows become independently searchable row units."""
    chunks = chunk_by_dom(
        "| Project | Status |\n| :--- | ---: |\n| Alpha | Ready |"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("markdown_tr", "Project | Status"),
        ("markdown_tr", "Alpha | Ready"),
    ]


def test_chunk_by_dom_keeps_prose_around_markdown_table_rows() -> None:
    """Prose surrounding a Markdown table stays in document order."""
    chunks = chunk_by_dom(
        "Intro.\n\n| Project | Status |\n| --- | --- |\n| Alpha | Ready |\n\nNext action."
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("", "Intro."),
        ("markdown_tr", "Project | Status"),
        ("markdown_tr", "Alpha | Ready"),
        ("", "Next action."),
    ]


def test_chunk_by_dom_accepts_markdown_tables_without_outer_pipes() -> None:
    """Outer pipes are optional while columns remain row-scoped evidence."""
    chunks = chunk_by_dom("Project | Status\n--- | ---\nAlpha | Ready")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("markdown_tr", "Project | Status"),
        ("markdown_tr", "Alpha | Ready"),
    ]


def test_chunk_by_dom_keeps_non_table_text_after_a_markdown_table() -> None:
    """A malformed next row ends the table and remains ordinary prose."""
    chunks = chunk_by_dom(
        "Project | Status\n--- | ---\nAlpha | Ready\nNext action without cells"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("markdown_tr", "Project | Status"),
        ("markdown_tr", "Alpha | Ready"),
        ("", "Next action without cells"),
    ]


def test_chunk_by_dom_word_table_rows_also_group_cells() -> None:
    """WordprocessingML table cells group by their source row."""
    html = "<w:tbl><w:tr><w:tc>1</w:tc><w:tc>Acme Corp</w:tc></w:tr></w:tbl>"
    chunks = chunk_by_dom(html)

    assert [c.text for c in chunks] == ["1 | Acme Corp"]
    assert chunks[0].label == "w:tr"


def test_chunk_by_dom_keeps_indentation_as_metadata_not_embedding_text() -> None:
    """Non-breaking-space indentation stays metadata, not semantic text."""
    html = "<p>&nbsp;&nbsp;Level one</p><p>&nbsp;&nbsp;&nbsp;&nbsp;Level two</p>"
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["Level one", "Level two"]
    assert [chunk.indent_width for chunk in chunks] == [2, 4]


def test_chunk_by_dom_reads_html_and_word_indentation_declarations() -> None:
    """HTML and Word indentation declarations map to comparable units."""
    html = (
        '<p style="margin-left: 32px">HTML</p>'
        '<w:p><w:pPr><w:ind w:left="480"/></w:pPr>'
        "<w:r><w:t>Word</w:t></w:r></w:p>"
    )
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["HTML", "Word"]
    assert [chunk.indent_width for chunk in chunks] == [4, 4]


def test_chunk_by_dom_ignores_invalid_word_indentation() -> None:
    """Malformed Word indentation metadata cannot create a false hierarchy."""
    chunks = chunk_by_dom(
        '<w:p><w:pPr><w:ind w:left="invalid"/></w:pPr><w:t>Word</w:t></w:p>'
    )

    assert [(chunk.text, chunk.indent_width) for chunk in chunks] == [("Word", 0)]


def test_chunk_by_dom_reads_the_css_margin_shorthand_not_just_margin_left() -> None:
    """Live bug (2026-08-19): a real editor (Word paste, Outlook compose)
    declares indentation with the box-model shorthand
    ("margin: 0cm 0cm 0cm 56px") far more often than the "margin-left"
    longhand -- every nested <li> in a real body used only the shorthand,
    so indentation silently read as 0 and every nesting level flattened.
    """
    html = (
        '<ul><li style="margin: 0cm 0cm 0cm 56px">Outer item</li></ul>'
        '<ul><li style="margin: 0cm 0cm 0cm 80px">Nested item</li></ul>'
    )
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["Outer item", "Nested item"]
    outer, nested = chunks
    assert [outer.indent_width, nested.indent_width] == [7, 10]
    assert outer.indent_width < nested.indent_width
    assert outer.indent_width > 0


def test_chunk_by_dom_uses_list_container_depth_as_explicit_indentation() -> None:
    """Nested list-container depth contributes explicit indentation."""
    html = "<ol><li>Outer<ol><li>Nested</li></ol></li></ol>"

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("li", "Outer"), ("li", "Nested")]
    assert [chunk.indent_width for chunk in chunks] == [4, 8]


def test_chunk_by_source_body_splits_plain_lists_and_markdown_tables() -> None:
    """Plain authored lists and tables split into semantic source units."""
    body = """1. Background
    continuation stays with the first item.
2. Decision

| Field | Value |
| --- | --- |
| Owner | Buyer |
"""

    chunks = chunk_by_source_body(body)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("", "1. Background continuation stays with the first item."),
        ("", "2. Decision"),
        ("tr", "Field | Value"),
        ("tr", "Owner | Buyer"),
    ]


def test_chunk_by_source_body_keeps_a_single_pipe_row_as_plain_text() -> None:
    """One pipe-delimited row alone is not enough evidence of a table."""
    chunks = chunk_by_source_body("Only | one row")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("", "Only | one row")]


def test_chunk_by_source_body_delegates_html_to_dom_chunking() -> None:
    """HTML input retains its DOM label instead of entering the plain-text splitter."""
    chunks = chunk_by_source_body("<p>HTML evidence</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("p", "HTML evidence")]


def test_chunk_by_dom_joins_visual_continuation_lines_but_keeps_list_items() -> None:
    """Visual wraps join while authored list starts retain boundaries."""
    html = (
        '<p>1. 배경<br style="line-height: 1.5;" />'
        "    1) 기존 대차는 이전이 필요함<br>"
        "        콘크리트 양생까지 공장 운영 불가하여 이전 불가<br>"
        "    2) 신규 대차 제작으로 결정</p>"
    )

    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == [
        "1. 배경",
        "1) 기존 대차는 이전이 필요함 콘크리트 양생까지 공장 운영 불가하여 이전 불가",
        "2) 신규 대차 제작으로 결정",
    ]
    assert [chunk.indent_width for chunk in chunks] == [0, 4, 4]


def test_normalize_semantic_text_removes_visual_hanging_indent_breaks() -> None:
    """Hanging-indent line wraps normalize without flattening list items."""
    text = (
        "1. 배경\n\n"
        "    1) 기존 대차는 이전이 필요함\n"
        "        콘크리트 양생까지 공장 운영 불가하여 이전 불가\n"
        "    2) 신규 대차 제작"
    )

    assert normalize_semantic_text(text) == (
        "1. 배경\n\n"
        "1) 기존 대차는 이전이 필요함 콘크리트 양생까지 공장 운영 불가하여 이전 불가\n"
        "2) 신규 대차 제작"
    )


def test_normalize_semantic_text_preserves_blank_paragraph_boundaries() -> None:
    """Blank lines continue to separate authored paragraphs."""
    assert normalize_semantic_text("첫 문단\n\n둘째 문단") == "첫 문단\n\n둘째 문단"


def test_normalize_semantic_text_does_not_embed_visual_indentation_markers() -> None:
    """Presentation-only non-breaking spaces do not enter semantic text."""
    assert normalize_semantic_text("\xa0\xa0계속되는 문장\n\xa0\xa0\xa0\xa0다음 줄") == (
        "계속되는 문장 다음 줄"
    )


def test_chunk_by_dom_does_not_infer_marker_depth_without_source_whitespace() -> None:
    """Marker shape alone cannot invent indentation depth."""
    chunks = chunk_by_dom("<p>1. Root<br>1) Child<br>- Detail</p>")

    assert [chunk.text for chunk in chunks] == ["1. Root", "1) Child", "- Detail"]
    assert [chunk.indent_width for chunk in chunks] == [0, 0, 0]


def test_chunk_by_dom_empty_html_yields_no_chunks() -> None:
    """Empty block, self-closing block, and empty input yield no chunks."""
    assert chunk_by_dom("<div></div>") == []
    assert chunk_by_dom("<p/>") == []
    assert chunk_by_dom("") == []


def test_chunk_by_dom_keeps_unscoped_superscript_as_plain_text() -> None:
    """Orphan formatting remains plain text while empty markup adds nothing."""
    chunks = chunk_by_dom("<sup>1</sup></sup><span/><p> </p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("", "1")]


def test_chunk_by_dom_decodes_deeply_escaped_entities_with_a_bounded_loop() -> None:
    """Nested HTML entity escapes decode without an unbounded parser loop."""
    assert [chunk.text for chunk in chunk_by_dom("<p>&amp;amp;amp;amp;</p>")] == ["&"]


def test_chunk_by_dom_falls_back_for_inline_only_markup() -> None:
    """Inline-only markup falls back to one plain-text unit."""
    chunks = chunk_by_dom("<span>First inline block.</span><span>Second inline block.</span>")

    assert len(chunks) == 1
    assert chunks[0].unit_type == "plain_text"
    assert chunks[0].text == "First inline block.Second inline block."


def test_chunk_by_dom_flushes_unclosed_block_at_end_of_document() -> None:
    """EOF flushes content from an unclosed source block."""
    chunks = chunk_by_dom("<div><span>Unclosed source fragment.")

    assert len(chunks) == 1
    assert chunks[0].unit_type == "dom"
    assert chunks[0].text == "Unclosed source fragment."


def test_chunk_by_dom_interleaves_images_with_text_in_document_order() -> None:
    """Embedded images retain their exact position between text blocks."""
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    html = (
        f"<p>Before the picture.</p>"
        f'<img src="data:image/png;base64,{tiny_png_b64}">'
        f"<p>After the picture.</p>"
    )
    chunks = chunk_by_dom(html)

    assert [c.unit_type for c in chunks] == ["dom", "image", "dom"]
    assert [c.index for c in chunks] == [0, 1, 2]
    assert chunks[0].text == "Before the picture."
    assert chunks[1].label == "image/png"
    assert chunks[1].image_data is not None
    assert chunks[2].text == "After the picture."


def test_chunk_by_dom_labels_text_chunks_with_their_tag_name() -> None:
    """DOM text chunks expose their source tag as the unit label."""
    html = "<article><p>A paragraph.</p></article><aside>Sidebar.</aside>"
    chunks = chunk_by_dom(html)

    labels = {c.text: c.label for c in chunks}
    assert labels["A paragraph."] == "p"
    assert labels["Sidebar."] == "aside"


def test_chunk_by_dom_skips_malformed_image_data() -> None:
    """Malformed base64 cannot create an image chunk."""
    html = '<p>Text.</p><img src="data:image/png;base64,not-valid!!!">'
    chunks = chunk_by_dom(html)
    assert [c.unit_type for c in chunks] == ["dom"]


def test_chunk_by_dom_skips_images_without_embedded_base64_data() -> None:
    """Missing, external, and non-base64 image sources are not embedded images."""
    html = '<img><img src="https://images.example/item.png"><img src="data:image/png,abc">'
    assert chunk_by_dom(html) == []


def test_chunk_by_conversation_turn_labels_each_chunk_with_its_sender() -> None:
    """Conversation units retain their sender labels and order."""
    turns = [
        ConversationTurn(sender="alice@example.com", text="Can we move the meeting?"),
        ConversationTurn(sender="bob@example.com", text="Sure, how about Thursday?"),
    ]
    chunks = chunk_by_conversation_turn(turns)

    assert [c.label for c in chunks] == ["alice@example.com", "bob@example.com"]
    assert [c.text for c in chunks] == ["Can we move the meeting?", "Sure, how about Thursday?"]
    assert all(c.unit_type == "conversation_turn" for c in chunks)


def test_chunk_by_conversation_turn_skips_empty_turns() -> None:
    """Empty turns are removed before contiguous chunk indexing."""
    turns = [
        ConversationTurn(sender="alice@example.com", text="Hello."),
        ConversationTurn(sender="bob@example.com", text="   "),
    ]
    chunks = chunk_by_conversation_turn(turns)
    assert len(chunks) == 1
    assert chunks[0].label == "alice@example.com"


def test_chunk_by_conversation_turn_index_is_contiguous_after_filtering() -> None:
    """A regression test for a real bug: an empty turn in the MIDDLE of
    the conversation must not leave a gap in the surviving chunks'
    `index` values (e.g. [0, 2] instead of [0, 1]) -- `Chunk.index` is a
    position among the chunks actually returned, not the original turn
    list's position.
    """
    turns = [
        ConversationTurn(sender="alice@example.com", text="First."),
        ConversationTurn(sender="bob@example.com", text="   "),
        ConversationTurn(sender="carol@example.com", text="Third."),
    ]
    chunks = chunk_by_conversation_turn(turns)
    assert [c.index for c in chunks] == [0, 1]
    assert [c.label for c in chunks] == ["alice@example.com", "carol@example.com"]


def test_chunk_by_dom_captures_style_as_separate_metadata_not_embedded_text() -> None:
    """The formatting cue must be addressable on the Chunk, and must NOT
    leak into `.text` -- an embedding/LLM call on `.text` should never
    see the literal style string.
    """
    html = '<p style="color:red;text-align:center">Urgent: confirm by Friday.</p>'
    chunks = chunk_by_dom(html)

    assert len(chunks) == 1
    assert chunks[0].text == "Urgent: confirm by Friday."
    assert chunks[0].style == "color:red;text-align:center"
    assert "style" not in chunks[0].text
    assert "color:red" not in chunks[0].text


def test_chunk_by_dom_style_is_none_when_element_has_no_style_attribute() -> None:
    """A missing style attribute remains distinct from an empty style value."""
    chunks = chunk_by_dom("<p>Plain paragraph.</p>")
    assert chunks[0].style is None


def test_chunk_by_dom_splits_on_heading_boundaries_and_labels_the_level() -> None:
    """Heading boundaries preserve their source level label."""
    html = "<h2>Quarterly Review</h2><p>Body text follows.</p>"
    chunks = chunk_by_dom(html)

    assert [c.label for c in chunks] == ["h2", "p"]
    assert [c.text for c in chunks] == ["Quarterly Review", "Body text follows."]


def test_chunk_by_dom_preserves_style_per_block_independently() -> None:
    """Two sibling blocks with different formatting must not bleed their
    style onto each other."""
    html = '<li style="color:blue">Bullet one</li><li>Bullet two</li>'
    chunks = chunk_by_dom(html)

    assert chunks[0].style == "color:blue"
    assert chunks[1].style is None
