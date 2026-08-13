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

    # The outermost block owns the text; there is exactly one chunk, not
    # one for the div and a duplicate for the p inside it.
    assert len(chunks) == 1
    assert chunks[0].text == "Nested paragraph text."


def test_chunk_by_dom_empty_html_yields_no_chunks() -> None:
    assert chunk_by_dom("<div></div>") == []
    assert chunk_by_dom("") == []


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
