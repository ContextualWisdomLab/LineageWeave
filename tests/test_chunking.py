from __future__ import annotations

from lineageweave.chunking import (
    ConversationTurn,
    chunk_by_conversation_turn,
    chunk_by_dom,
    chunk_by_paragraph,
    chunk_by_sentence,
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


def test_chunk_by_dom_keeps_indentation_as_metadata_not_embedding_text() -> None:
    html = "<p>&nbsp;&nbsp;Level one</p><p>&nbsp;&nbsp;&nbsp;&nbsp;Level two</p>"
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["Level one", "Level two"]
    assert [chunk.indent_width for chunk in chunks] == [2, 4]


def test_chunk_by_dom_reads_html_and_word_indentation_declarations() -> None:
    html = (
        '<p style="margin-left: 32px">HTML</p>'
        '<w:p><w:pPr><w:ind w:left="480"/></w:pPr>'
        "<w:r><w:t>Word</w:t></w:r></w:p>"
    )
    chunks = chunk_by_dom(html)

    assert [chunk.text for chunk in chunks] == ["HTML", "Word"]
    assert [chunk.indent_width for chunk in chunks] == [4, 4]


def test_chunk_by_dom_joins_visual_continuation_lines_but_keeps_list_items() -> None:
    html = (
        "<p>1. 배경<br>"
        "    1) 기존 대차는 이전이 필요함<br>"
        "        콘크리트 양생까지 공장 운영 불가하여 이전 불가<br>"
        "    2) 신규 대차 제작으로 결정</p>"
    )

    chunks = chunk_by_dom(html)

    assert chunks[0].text == (
        "1. 배경\n"
        "1) 기존 대차는 이전이 필요함 콘크리트 양생까지 공장 운영 불가하여 이전 불가\n"
        "2) 신규 대차 제작으로 결정"
    )


def test_chunk_by_dom_empty_html_yields_no_chunks() -> None:
    assert chunk_by_dom("<div></div>") == []
    assert chunk_by_dom("") == []


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
