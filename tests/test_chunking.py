from __future__ import annotations

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


def test_chunk_by_paragraph_empty_text_returns_no_chunks() -> None:
    assert chunk_by_paragraph("") == []
    assert chunk_by_paragraph("   \n\n  ") == []


def test_chunk_by_sentence_splits_on_sentence_boundaries() -> None:
    text = "First sentence here. Second sentence follows! Third one too?"
    chunks = chunk_by_sentence(text)

    assert [c.text for c in chunks] == [
        "First sentence here.",
        "Second sentence follows!",
        "Third one too?",
    ]
    assert all(c.unit_type == "sentence" for c in chunks)


def test_chunk_by_dom_splits_on_block_element_boundaries() -> None:
    html = "<article><p>First paragraph.</p><p>Second paragraph.</p></article>"
    chunks = chunk_by_dom(html)

    assert [c.text for c in chunks] == ["First paragraph.", "Second paragraph."]
    assert all(c.unit_type == "dom" for c in chunks)


def test_chunk_by_dom_nested_blocks_do_not_duplicate_text() -> None:
    html = "<div><p>Only the inner block owns this.</p></div>"
    chunks = chunk_by_dom(html)

    assert len(chunks) == 1
    assert chunks[0].text == "Only the inner block owns this."
    assert chunks[0].label == "p"


def test_chunk_by_dom_groups_table_cells_by_row_instead_of_flattening() -> None:
    html = (
        "<table>"
        "<tr><td>1</td><td>Acme Corp</td><td>Declined</td></tr>"
        "<tr><td>2</td><td>Globex Corp</td><td>Interested</td></tr>"
        "</table>"
    )
    chunks = chunk_by_dom(html)

    assert [c.text for c in chunks] == [
        "1 | Acme Corp | Declined",
        "2 | Globex Corp | Interested",
    ]
    assert all(c.label == "tr" for c in chunks)


def test_chunk_by_dom_keeps_nested_table_cell_blocks_in_their_row() -> None:
    chunks = chunk_by_dom(
        "<table><tr><td><p>No.</p></td><td><div>Company</div></td></tr></table>"
    )
    assert [(chunk.label, chunk.text) for chunk in chunks] == [("tr", "No. | Company")]


def test_chunk_by_dom_preserves_boundary_before_first_cell_after_row_text() -> None:
    """Malformed editor markup must not merge row text into the first cell."""
    chunks = chunk_by_dom(
        "<table><tr><p>caption</p><td>A</td><td>B</td></tr></table>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [("tr", "caption | A | B")]


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


def test_chunk_by_dom_labels_numbered_html_footnote_ids() -> None:
    """Common Markdown HTML footnote ids identify the definition block."""
    html = '<ol><li id="fn1"><a href="#fnref1">1</a> Definition.</li></ol>'

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "1 Definition."),
    ]


def test_chunk_by_dom_does_not_label_short_non_footnote_ids() -> None:
    """Short application ids must not be mistaken for numbered footnotes."""
    chunks = chunk_by_dom('<p id="en1">Engagement summary.</p>')

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Engagement summary."),
    ]


def test_chunk_by_dom_keeps_numbered_footnote_backlinks_in_body_paragraphs() -> None:
    html = (
        '<p>Body cites <a href="#fn1" id="fnref1">[1]</a>.</p>'
        '<p id="fn1">Definition.</p>'
    )

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body cites [1]."),
        ("footnote", "Definition."),
    ]


def test_chunk_by_dom_labels_colon_separated_footnote_ids() -> None:
    html = (
        '<p>Body cites <a href="#fn:1" id="fnref:1">[1]</a>.</p>'
        '<p><a href="#_ftnref1_body" name="_ftn1_body">[1]</a> Definition.</p>'
    )

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Body cites [1]."),
        ("footnote", "[1] Definition."),
    ]


def test_chunk_by_dom_labels_bare_word_footnote_backlinks() -> None:
    html = '<p><a href="#_ftnref" name="_ftn1_body">[1]</a> Definition.</p>'

    chunks = chunk_by_dom(html)

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "[1] Definition."),
    ]


def test_chunk_by_dom_preserves_empty_table_cells_as_columns() -> None:
    html = "<table><tr><td></td><td>Company</td><td></td><td>Result</td></tr></table>"

    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["|  | Company |  | Result"]


def test_chunk_by_dom_does_not_add_phantom_column_for_multiple_leading_empty_cells() -> None:
    html = "<table><tr><td></td><td></td><td>X</td></tr></table>"

    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["|  | X"]


def test_chunk_by_dom_skips_rows_with_only_empty_table_cells() -> None:
    html = "<table><tr><td></td><td></td></tr><tr><td>Value</td></tr></table>"

    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["Value"]


def test_chunk_by_dom_labels_ooxml_footnote_containers() -> None:
    chunks = chunk_by_dom(
        "<w:footnote w:id='1'><w:p>OOXML footnote body</w:p></w:footnote>"
        "<w:endnote w:id='2'><w:p>OOXML endnote body</w:p></w:endnote>"
    )

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("footnote", "OOXML footnote body"),
        ("footnote", "OOXML endnote body"),
    ]


def test_chunk_by_dom_preserves_explicit_metric_superscripts() -> None:
    """A metric exponent remains searchable mathematical evidence."""
    chunks = chunk_by_dom("<p>Volume: 5m<sup>3</sup>.</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Volume: 5m³.")
    ]


def test_chunk_by_dom_preserves_explicit_metric_subscripts() -> None:
    """A metric subscript is retained without changing ordinary footnotes."""
    chunks = chunk_by_dom("<p>Index m<sub>3</sub> is measured.</p>")

    assert [(chunk.label, chunk.text) for chunk in chunks] == [
        ("p", "Index m₃ is measured.")
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

    assert chunks[0].text == "Urgent: confirm by Friday."
    assert chunks[0].style == "color:red;text-align:center"


def test_chunk_by_dom_style_is_none_when_element_has_no_style_attribute() -> None:
    chunks = chunk_by_dom("<p>No style here.</p>")
    assert chunks[0].style is None


def test_chunk_by_dom_splits_on_heading_boundaries_and_labels_the_level() -> None:
    html = "<h1>Title</h1><h2>Subtitle</h2><p>Body.</p>"
    chunks = chunk_by_dom(html)

    assert [(c.label, c.text) for c in chunks] == [
        ("h1", "Title"),
        ("h2", "Subtitle"),
        ("h3", "Body.") if False else ("p", "Body."),
    ]


def test_chunk_by_dom_preserves_style_per_block_independently() -> None:
    html = '<p style="color:red">Red text.</p><p>Plain text.</p>'
    chunks = chunk_by_dom(html)

    assert [c.style for c in chunks] == ["color:red", "color:red"] if False else [c.style for c in chunks] == ["color:red", None]
