from __future__ import annotations

import pytest

from lineageweave.chunking import (
    ConversationTurn,
    chunk_by_conversation_turn,
    chunk_by_dom,
    chunk_by_paragraph,
    chunk_by_sentence,
    chunk_by_source_body,
    normalize_script_text,
    normalize_semantic_text,
)


def test_chunk_by_paragraph_splits_on_blank_lines() -> None:
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
    text = "  A.  \n\n\n\n  B.  "
    chunks = chunk_by_paragraph(text)
    assert [c.text for c in chunks] == ["A.", "B."]


def test_chunk_by_paragraph_empty_text_yields_no_chunks() -> None:
    assert chunk_by_paragraph("") == []
    assert chunk_by_paragraph("   \n\n  ") == []


def test_chunk_by_sentence_splits_on_sentence_boundaries() -> None:
    text = "This is one sentence. This is another! Is this a third?"
    chunks = chunk_by_sentence(text)

    assert [c.text for c in chunks] == [
        "This is one sentence.",
        "This is another!",
        "Is this a third?",
    ]
    assert all(c.unit_type == "sentence" for c in chunks)


def test_chunk_by_dom_splits_on_block_element_boundaries() -> None:
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
    html = "<div><p>Nested paragraph text.</p></div>"
    chunks = chunk_by_dom(html)

    # The innermost block owns the text; there is exactly one chunk, not
    # one for the div and a duplicate for the p inside it.
    assert len(chunks) == 1
    assert chunks[0].text == "Nested paragraph text."
    assert chunks[0].label == "p"


def test_chunk_by_dom_keeps_mathml_as_a_formula_boundary() -> None:
    chunks = chunk_by_dom(
        "<p>Before.</p><math><mi>x</mi><mo>+</mo><mn>1</mn></math><p>After.</p>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Before."),
        ("math", "x+1"),
        ("p", "After."),
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
    chunks = chunk_by_dom(
        "<table><tr><td><p>No.</p></td><td><div>Company</div></td></tr></table>"
    )
    assert [(chunk.label, chunk.text) for chunk in chunks] == [("tr", "No. | Company")]


def test_chunk_by_dom_preserves_empty_table_cells() -> None:
    chunks = chunk_by_dom(
        "<table><tr><td></td><td>Synthetic item</td><td></td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "| Synthetic item |")
    ]


def test_chunk_by_dom_preserves_self_closing_empty_table_cells() -> None:
    html_chunks = chunk_by_dom(
        "<table><tr><td>Left</td><td/><td>Right</td></tr></table>"
    )
    word_chunks = chunk_by_dom(
        "<w:tbl><w:tr><w:tc>Left</w:tc><w:tc/><w:tc>Right</w:tc></w:tr></w:tbl>"
    )

    assert [(chunk.label, chunk.text) for chunk in html_chunks] == [
        ("tr", "Left |  | Right")
    ]
    assert [(chunk.label, chunk.text) for chunk in word_chunks] == [
        ("w:tr", "Left |  | Right")
    ]


def test_chunk_by_dom_scopes_cell_positions_to_nested_table_rows() -> None:
    chunks = chunk_by_dom(
        "<table><tr><td>Outer left"
        "<table><tr><td>Inner left</td><td>Inner right</td></tr></table>"
        "</td><td>Outer right</td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "Inner left | Inner right"),
        ("tr", "Outer left | Outer right"),
    ]


def test_chunk_by_dom_implicitly_closes_sibling_rows_at_the_same_table_depth() -> None:
    chunks = chunk_by_dom(
        "<table><tr><td>First left</td><td>First right</td>"
        "<tr><td>Second left</td><td>Second right</td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "First left | First right"),
        ("tr", "Second left | Second right"),
    ]


def test_chunk_by_dom_closes_an_unclosed_row_at_the_table_boundary() -> None:
    """A malformed final row still emits before its table closes."""

    chunks = chunk_by_dom(
        "<table><tr><td>Only left</td><td>Only right</td></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "Only left | Only right")
    ]


def test_chunk_by_dom_closes_sibling_rows_past_an_unclosed_cell_block() -> None:
    """Malformed inline cell markup cannot displace its owning row."""

    chunks = chunk_by_dom(
        "<table><tr><td><div>First left</td><td>First right</td>"
        "<tr><td>Second left</td><td>Second right</td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "First left | First right"),
        ("tr", "Second left | Second right"),
    ]


def test_chunk_by_dom_does_not_infer_a_footnote_from_a_bare_marker() -> None:
    chunks = chunk_by_dom("<p>Body text</p><p>*Synthetic list item</p>")
    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body text"),
        ("p", "*Synthetic list item"),
    ]


def test_chunk_by_dom_labels_html_and_word_footnote_markup() -> None:
    html = (
        "<p>Body text</p>"
        '<ol class="footnotes"><li id="fn1"><p>HTML footnote body</p></li></ol>'
        '<p class="MsoFootnoteText"><a href="#_ftnref1"><sup>1</sup></a> Word footnote body</p>'
    )

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body text"),
        ("footnote", "HTML footnote body"),
        ("footnote", "¹ Word footnote body"),
    ]


def test_chunk_by_dom_does_not_label_body_footnote_citation_as_footnote() -> None:
    html = (
        '<p>Body cites <a href="#_ftn1" name="_ftnref1">[1]</a>.</p>'
        '<p><a href="#_ftnref1" name="_ftn1">[1]</a> Footnote definition.</p>'
    )

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body cites [1]."),
        ("footnote", "[1] Footnote definition."),
    ]


def test_chunk_by_dom_labels_ooxml_footnote_containers() -> None:
    chunks = chunk_by_dom(
        "<w:footnote w:id='1'><w:p>OOXML footnote body</w:p></w:footnote>"
        "<w:endnote w:id='2'><w:p>OOXML endnote body</w:p></w:endnote>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "OOXML footnote body"),
        ("footnote", "OOXML endnote body"),
    ]


def test_chunk_by_dom_word_table_rows_also_group_cells() -> None:
    html = "<w:tbl><w:tr><w:tc>1</w:tc><w:tc>Acme Corp</w:tc></w:tr></w:tbl>"
    chunks = chunk_by_dom(html)

    assert [c.text for c in chunks] == ["1 | Acme Corp"]
    assert chunks[0].label == "w:tr"


def test_chunk_by_dom_keeps_indentation_as_metadata_not_embedding_text() -> None:
    html = "<p>&nbsp;&nbsp;Level one</p><p>&nbsp;&nbsp;&nbsp;&nbsp;Level two</p>"
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["Level one", "Level two"]
    assert [chunk.indent_width for chunk in chunks] == [2, 4]
    assert [chunk.declared_indent_width for chunk in chunks] == [0, 0]


def test_chunk_by_dom_reads_html_and_word_indentation_declarations() -> None:
    html = (
        '<p style="margin-left: 32px">HTML</p>'
        '<w:p><w:pPr><w:ind w:left="480"/></w:pPr>'
        "<w:r><w:t>Word</w:t></w:r></w:p>"
    )
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["HTML", "Word"]
    assert [chunk.indent_width for chunk in chunks] == [4, 4]
    assert [chunk.declared_indent_width for chunk in chunks] == [4, 4]


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
    assert outer.indent_width < nested.indent_width
    assert outer.indent_width > 0


def test_chunk_by_dom_uses_list_container_depth_as_explicit_indentation() -> None:
    html = "<ol><li>Outer<ol><li>Nested</li></ol></li></ol>"

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("li", "Outer"), ("li", "Nested")]
    assert [chunk.indent_width for chunk in chunks] == [4, 8]


def test_chunk_by_source_body_splits_plain_lists_and_markdown_tables() -> None:
    body = """1. Background
    continuation stays with the first item.
2. Decision

| Field | Value |
| --- | --- |
| Volume | 12 m^3 |
"""

    chunks = chunk_by_source_body(body)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("", "1. Background continuation stays with the first item."),
        ("", "2. Decision"),
        ("tr", "Field | Value"),
        ("tr", "Volume | 12 m³"),
    ]


def test_chunk_by_source_body_normalizes_entity_encoded_quantity_scripts() -> None:
    chunks = chunk_by_source_body(
        "Reserve 12 m&#94;3, x&lt;sup&gt;2&lt;/sup&gt;, and H&lt;sub&gt;2&lt;/sub&gt;O."
    )

    assert [chunk.text for chunk in chunks] == ["Reserve 12 m³, x², and H₂O."]


def test_chunk_by_source_body_keeps_invalid_encoded_script_pairs_literal() -> None:
    bodies = (
        "Keep x&lt;sup&gt;2 unmatched.",
        "Keep x&lt;sup/&gt;2 self-closing.",
        "Keep x&lt;sup class=&quot;unit&quot;&gt;2&lt;/sup&gt; attributed.",
        "Keep x&lt;sup&gt;2&lt;/sub&gt; mismatched.",
    )

    assert [chunk_by_source_body(body)[0].text for body in bodies] == list(bodies)
    combined = " ".join(bodies)
    assert chunk_by_source_body(combined)[0].text == combined


def test_chunk_by_source_body_keeps_encoded_non_script_markup_inert() -> None:
    body = (
        "Keep &lt;b&gt;bold&lt;/b&gt;, &lt;sup-note&gt;2&lt;/sup-note&gt;, "
        "and &lt;script&gt;alert(1)&lt;/script&gt; literal."
    )

    chunks = chunk_by_source_body(body)

    assert [(chunk.unit_type, chunk.text) for chunk in chunks] == [("plain_text", body)]


def test_chunk_by_source_body_preserves_empty_markdown_table_cells() -> None:
    chunks = chunk_by_source_body(
        "| Key | Value | State |\n"
        "| --- | --- | --- |\n"
        "| A | | Open |"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "Key | Value | State"),
        ("tr", "A |  | Open"),
    ]


def test_chunk_by_source_body_keeps_contextual_all_empty_markdown_rows() -> None:
    chunks = chunk_by_source_body(
        "| Key | Value | State |\n"
        "| --- | --- | --- |\n"
        "| | | |"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("tr", "Key | Value | State"),
        ("tr", "|  |"),
    ]


def test_chunk_by_source_body_does_not_promote_a_standalone_empty_pipe_line() -> None:
    chunks = chunk_by_source_body("| | |")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("", "| | |")]


def test_chunk_by_dom_joins_visual_continuation_lines_but_keeps_list_items() -> None:
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
    assert normalize_semantic_text("첫 문단\n\n둘째 문단") == "첫 문단\n\n둘째 문단"


def test_normalize_semantic_text_does_not_embed_visual_indentation_markers() -> None:
    assert normalize_semantic_text("\xa0\xa0계속되는 문장\n\xa0\xa0\xa0\xa0다음 줄") == (
        "계속되는 문장 다음 줄"
    )


def test_chunk_by_dom_does_not_infer_marker_depth_without_source_whitespace() -> None:
    chunks = chunk_by_dom("<p>1. Root<br>1) Child<br>- Detail</p>")

    assert [chunk.text for chunk in chunks] == ["1. Root", "1) Child", "- Detail"]
    assert [chunk.indent_width for chunk in chunks] == [0, 0, 0]


def test_chunk_by_dom_empty_html_yields_no_chunks() -> None:
    assert chunk_by_dom("<div></div>") == []
    assert chunk_by_dom("") == []


def test_chunk_by_dom_falls_back_for_inline_only_markup() -> None:
    chunks = chunk_by_dom("<span>First inline block.</span><span>Second inline block.</span>")

    assert len(chunks) == 1
    assert chunks[0].unit_type == "plain_text"
    assert chunks[0].text == "First inline block.Second inline block."


def test_chunk_by_dom_flushes_unclosed_block_at_end_of_document() -> None:
    chunks = chunk_by_dom("<div><span>Unclosed source fragment.")

    assert len(chunks) == 1
    assert chunks[0].unit_type == "dom"
    assert chunks[0].text == "Unclosed source fragment."


def test_chunk_by_dom_interleaves_images_with_text_in_document_order() -> None:
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
    html = "<article><p>A paragraph.</p></article><aside>Sidebar.</aside>"
    chunks = chunk_by_dom(html)

    labels = {c.text: c.label for c in chunks}
    assert labels["A paragraph."] == "p"
    assert labels["Sidebar."] == "aside"


def test_chunk_by_dom_skips_malformed_image_data() -> None:
    html = '<p>Text.</p><img src="data:image/png;base64,not-valid!!!">'
    chunks = chunk_by_dom(html)
    assert [c.unit_type for c in chunks] == ["dom"]


def test_chunk_by_conversation_turn_labels_each_chunk_with_its_sender() -> None:
    turns = [
        ConversationTurn(sender="alice@example.com", text="Can we move the meeting?"),
        ConversationTurn(sender="bob@example.com", text="Sure, how about Thursday?"),
    ]
    chunks = chunk_by_conversation_turn(turns)

    assert [c.label for c in chunks] == ["alice@example.com", "bob@example.com"]
    assert [c.text for c in chunks] == ["Can we move the meeting?", "Sure, how about Thursday?"]
    assert all(c.unit_type == "conversation_turn" for c in chunks)


def test_chunk_by_conversation_turn_skips_empty_turns() -> None:
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
    chunks = chunk_by_dom("<p>Plain paragraph.</p>")
    assert chunks[0].style is None


def test_chunk_by_dom_splits_on_heading_boundaries_and_labels_the_level() -> None:
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


def test_normalize_script_text_maps_quantity_exponents_and_leaves_comparisons() -> None:
    assert normalize_script_text("Tank volume is 12 m<sup>3</sup>.") == "Tank volume is 12 m³."
    assert normalize_script_text("Tank volume is 12 m^3.") == "Tank volume is 12 m³."
    assert normalize_script_text("Coolant is H<sub>2</sub>O.") == "Coolant is H₂O."
    assert normalize_script_text("x<sup> </sup>") == "x "
    assert normalize_script_text("qty < 50 and price > 10") == "qty < 50 and price > 10"
    assert normalize_script_text("^1 See the tank note.") == "^1 See the tank note."


def test_normalize_script_text_keeps_mixed_script_content_as_a_visible_fallback() -> None:
    assert normalize_script_text("x<sup>3a</sup>") == "x^3a"


def test_normalize_script_text_decodes_nested_inline_markup_before_stripping() -> None:
    assert normalize_script_text("x<sup>&lt;span&gt;2&lt;/span&gt;</sup>") == "x²"


def test_chunk_by_dom_keeps_html_quantity_scripts_as_unicode() -> None:
    chunks = chunk_by_dom("<p>Tank volume is 12 m<sup>3</sup> of H<sub>2</sub>O.</p>")

    assert [chunk.text for chunk in chunks] == ["Tank volume is 12 m³ of H₂O."]


def test_chunk_by_dom_normalizes_entity_encoded_quantity_scripts() -> None:
    chunks = chunk_by_dom(
        "<p>Reserve 12 m&#94;3 and x&lt;sup&gt;2&lt;/sup&gt; units.</p>"
    )

    assert [chunk.text for chunk in chunks] == ["Reserve 12 m³ and x² units."]


def test_chunk_by_dom_unclosed_sup_does_not_cross_table_cells() -> None:
    chunks = chunk_by_dom("<table><tr><td>m<sup>3</td><td>Acme Corp</td></tr></table>")

    assert [chunk.text for chunk in chunks] == ["m³ | Acme Corp"]


def test_chunk_by_dom_unclosed_sup_does_not_corrupt_later_paragraphs() -> None:
    """A malformed, never-closed <sup> must not leak its script context into
    every later block. HTMLParser (unlike a browser) does not implicitly
    close an unclosed inline tag at a block boundary, so a naive
    _script_stack would otherwise stay "open" for the rest of the document."""
    html = (
        "<p>Tank volume is 12 m<sup>3</p>"
        "<p>Unrelated paragraph mentions n2 and o2 plainly.</p>"
    )
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == [
        "Tank volume is 12 m³",
        "Unrelated paragraph mentions n2 and o2 plainly.",
    ]


def test_chunk_by_source_body_maps_plain_caret_quantities() -> None:
    chunks = chunk_by_source_body("Reserve 12 m^3 and 10^{-3} M stock.")

    assert chunks[0].text == "Reserve 12 m³ and 10⁻³ M stock."


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1px", 0),  # rounds below one eight-pixel unit
        ("16px", 2),
        ("1em", 2),
        ("0", 0),
        ("-4px", 0),
        ("10pt", 2),
        ("garbage", 0),
        ("", 0),
    ],
)
def test_length_to_indent_units_clamps_rounds_and_rejects(value: str, expected: int) -> None:
    from lineageweave.chunking import _length_to_indent_units

    assert _length_to_indent_units(value) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10px", "10px"),
        ("10px 20px", "20px"),
        ("10px 20px 30px", "20px"),
        ("10px 20px 30px 40px", "40px"),
        ("", ""),
    ],
)
def test_shorthand_left_value_picks_the_box_model_slot(raw: str, expected: str) -> None:
    from lineageweave.chunking import _shorthand_left_value

    assert _shorthand_left_value(raw) == expected


def test_chunk_by_sentence_returns_empty_for_no_sentences() -> None:
    from lineageweave.chunking import chunk_by_sentence

    assert chunk_by_sentence("   ") == []


def test_decode_data_uri_image_accepts_png_and_rejects_malformed() -> None:
    import base64

    from lineageweave.chunking import _decode_data_uri_image

    png = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
    mime, raw = _decode_data_uri_image(f"data:image/png;base64,{png}")
    assert mime == "image/png"
    assert raw == b"\x89PNG\r\n\x1a\n"

    assert _decode_data_uri_image("http://example.test/image.png") is None
    assert _decode_data_uri_image("data:image/png,notbase64") is None
    assert _decode_data_uri_image("data:image/png;base64,%%%bad") is None
