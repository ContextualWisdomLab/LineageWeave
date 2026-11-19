"""Preserve mixed suffix normalization, aliases, and empty-question rejection."""

import pytest

from lineageweave.post_chat import normalize_chat_question


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What happened ? !", "what happened between these events"),
        ("Who's involved ? !", "who is involved"),
        ("What's the next commitment ? !", "what is the next commitment"),
        ("When was the bid sent ? !", "when was the bid sent"),
        ("? !", ""),
        ("\t?\n!\u2003.\u00a0", ""),
        ("", ""),
        ("\u2003\t\n", ""),
        ("A ? B ! C", "a ? b ! c"),
        ("한글\u2003질문 ?\u00a0!", "한글 질문"),
        ("Keep: ;", "keep: ;"),
        ("Question" + "? ! . " * 10000, "question"),
        ("What happened?", "what happened between these events"),
        ("What happened between these events", "what happened between these events"),
    ],
)
def test_mixed_suffix_matches_retained_key_contract(question, expected):
    """Strip only normalized suffix spaces/punctuation and retain canonical keys."""
    actual = normalize_chat_question(question)
    assert actual == expected
    assert normalize_chat_question(actual) == actual
