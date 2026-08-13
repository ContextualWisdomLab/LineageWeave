"""Tests for lineageweave.post_chat.

parse_chat_response's tests need no live provider. The real-provider test
uses two synthetic linked posts where the question can only be answered
correctly by combining BOTH sources -- proving citation actually tracks
which source(s) contributed, not just that the model produced prose.
"""

from __future__ import annotations

import os

import pytest

from lineageweave.post_chat import (
    ChatSourceDocument,
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
    parse_chat_response,
)


def test_null_chat_client_is_unavailable_not_empty_answer() -> None:
    client = NullPostChatClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.answer("any question", [])

_SOURCES = [
    ChatSourceDocument("post-1", "Bid workshop", "We submitted the initial transformer bid on March 3."),
    ChatSourceDocument("post-2", "Bid revision", "The client asked for a revised quote on March 10; we sent it March 12."),
]


def test_parses_a_well_formed_json_object() -> None:
    content = '{"answer_text": "The bid was submitted then revised.", "cited_source_numbers": [1, 2]}'
    answer = parse_chat_response(content, _SOURCES)
    assert answer is not None
    assert answer.answer_text == "The bid was submitted then revised."
    assert answer.cited_post_ids == ("post-1", "post-2")


def test_out_of_range_citation_numbers_are_dropped_not_fatal() -> None:
    content = '{"answer_text": "Some answer.", "cited_source_numbers": [1, 99, 0, -1]}'
    answer = parse_chat_response(content, _SOURCES)
    assert answer is not None
    assert answer.cited_post_ids == ("post-1",)


def test_missing_answer_text_returns_none() -> None:
    content = '{"cited_source_numbers": [1]}'
    assert parse_chat_response(content, _SOURCES) is None


def test_empty_answer_text_returns_none() -> None:
    content = '{"answer_text": "   ", "cited_source_numbers": []}'
    assert parse_chat_response(content, _SOURCES) is None


def test_invalid_json_returns_none() -> None:
    assert parse_chat_response("not json", _SOURCES) is None


def test_no_citations_is_a_valid_answer() -> None:
    content = '{"answer_text": "The sources do not say.", "cited_source_numbers": []}'
    answer = parse_chat_response(content, _SOURCES)
    assert answer is not None
    assert answer.cited_post_ids == ()


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_answers_and_cites_both_linked_posts() -> None:
    """A question that genuinely requires combining two linked posts --
    "what happened between these events" is exactly this shape (the
    product brief's own framing of the in-popup chat).
    """
    client = ContextualOrchestratorPostChatClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )

    answer = client.answer(
        "What happened with the bid between the workshop and now?", _SOURCES
    )

    assert answer.answer_text.strip() != ""
    assert set(answer.cited_post_ids) == {"post-1", "post-2"}


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_does_not_cite_an_irrelevant_source() -> None:
    """A question answerable from only ONE of two sources should not cite
    the other -- proving citation tracks real relevance, not "cite
    everything provided."
    """
    client = ContextualOrchestratorPostChatClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    sources = [
        ChatSourceDocument("post-a", "Bid submitted", "We submitted the transformer bid on March 3."),
        ChatSourceDocument("post-b", "Unrelated: office move", "The Denver office is relocating to a new building in June."),
    ]

    answer = client.answer("When was the transformer bid submitted?", sources)

    assert "post-a" in answer.cited_post_ids
    assert "post-b" not in answer.cited_post_ids
