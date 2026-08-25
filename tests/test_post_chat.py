"""Tests for lineageweave.post_chat.

parse_chat_response's tests need no live provider. The real-provider test
uses two synthetic linked posts where the question can only be answered
correctly by combining BOTH sources -- proving citation actually tracks
which source(s) contributed, not just that the model produced prose.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from backend.app.post_chat_ingestion import (
    _graph_facts_for_posts,
    seeded_demo_chat,
    seeded_demo_commitment_chat,
    seeded_demo_exchanges,
    seeded_demo_involved_chat,
    seeded_fixture_chat,
    seeded_fixture_commitment_chat,
    seeded_fixture_exchanges,
    seeded_fixture_involved_chat,
)
from lineageweave.fixtures import ambiguous_commitment_post, fixture_thread_cast, sample_records
from lineageweave.post_chat import (
    CANONICAL_CHAT_QUESTION,
    CANONICAL_COMMITMENT_QUESTION,
    CANONICAL_INVOLVED_QUESTION,
    ChatSourceDocument,
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
    _render_sources_block,
    cited_post_evidence,
    cited_post_summaries,
    normalize_chat_question,
    parse_chat_response,
)


def test_normalize_chat_question_aliases_the_placeholder() -> None:
    canonical = normalize_chat_question(CANONICAL_CHAT_QUESTION)
    assert canonical == "what happened between these events"
    assert normalize_chat_question("  What happened?  ") == canonical
    assert normalize_chat_question("What happened between these events") == canonical
    assert normalize_chat_question("When was the bid sent?") == "when was the bid sent"


def test_normalize_chat_question_aliases_who_is_involved() -> None:
    involved = normalize_chat_question(CANONICAL_INVOLVED_QUESTION)
    assert involved == "who is involved"
    assert normalize_chat_question("Who's involved?") == involved
    assert normalize_chat_question("  who is involved here?  ") == involved


def test_normalize_chat_question_aliases_next_commitment() -> None:
    commitment = normalize_chat_question(CANONICAL_COMMITMENT_QUESTION)
    assert commitment == "what is the next commitment"
    assert normalize_chat_question("What's the next commitment?") == commitment
    assert normalize_chat_question("  what is the next commitment here?  ") == commitment


def test_every_sample_record_has_a_seeded_chat_answer() -> None:
    """Event Lineage click-through must have a stored Ask answer for
    every reconstruct fixture -- not a shared placeholder, not live LLM.
    """
    seen: set[str] = set()
    involved_seen: set[str] = set()
    commitment_seen: set[str] = set()
    for rec in sample_records():
        chat = seeded_fixture_chat(rec.label)
        assert chat is not None, rec.label
        assert chat.answer_text.strip()
        assert rec.label in chat.cited_titles
        assert chat.answer_text not in seen
        seen.add(chat.answer_text)
        involved = seeded_fixture_involved_chat(rec.label)
        assert involved is not None, rec.label
        assert involved.answer_text.strip()
        assert rec.label in involved.cited_titles
        assert involved.answer_text not in involved_seen
        involved_seen.add(involved.answer_text)
        cast = fixture_thread_cast(rec.label)
        if cast is not None and cast.person_names:
            for name in cast.person_names:
                assert name in involved.answer_text, rec.label
        else:
            assert "does not name a Keyman" in involved.answer_text
        questions = [question for question, _ in seeded_fixture_exchanges(rec.label)]
        assert questions == [
            CANONICAL_CHAT_QUESTION,
            CANONICAL_INVOLVED_QUESTION,
            CANONICAL_COMMITMENT_QUESTION,
        ]
        commitment = seeded_fixture_commitment_chat(rec.label)
        assert commitment is not None, rec.label
        assert commitment.answer_text.strip()
        assert rec.label in commitment.cited_titles
        assert commitment.answer_text not in commitment_seen
        commitment_seen.add(commitment.answer_text)
        if rec.label == "Unrelated: annual account review":
            assert "does not have an open commitment" in commitment.answer_text
        elif rec.secondary_key == "proj-beta":
            assert "Send Westfield Power the revised specification" in commitment.answer_text
            assert "2026-01-14" in commitment.answer_text
        elif rec.label == "Delivery schedule question raised":
            assert "Confirm the delivery window with logistics" in commitment.answer_text
            assert "2026-01-16" in commitment.answer_text
        else:
            assert "Send Northridge Grid the revised quote" in commitment.answer_text
            assert "2026-01-12" in commitment.answer_text
    calendar_title, _ = ambiguous_commitment_post()
    calendar = seeded_fixture_chat(calendar_title)
    assert calendar is not None
    assert "Riverbend" in calendar.answer_text
    calendar_involved = seeded_fixture_involved_chat(calendar_title)
    assert calendar_involved is not None
    assert "does not name a Keyman" in calendar_involved.answer_text
    calendar_commitment = seeded_fixture_commitment_chat(calendar_title)
    assert calendar_commitment is not None
    assert "Send Riverbend the revised delivery schedule" in calendar_commitment.answer_text
    assert "2026-01-09" in calendar_commitment.answer_text
    assert [question for question, _ in seeded_fixture_exchanges(calendar_title)] == [
        CANONICAL_CHAT_QUESTION,
        CANONICAL_INVOLVED_QUESTION,
        CANONICAL_COMMITMENT_QUESTION,
    ]
    assert seeded_fixture_chat("not a fixture title") is None
    assert seeded_fixture_involved_chat("not a fixture title") is None
    assert seeded_fixture_commitment_chat("not a fixture title") is None
    assert seeded_fixture_exchanges("not a fixture title") == []
    demo = seeded_demo_chat()
    assert "Northridge Grid" in demo.answer_text
    demo_involved = seeded_demo_involved_chat()
    assert "Ada West" in demo_involved.answer_text
    assert "Priya Nair" in demo_involved.answer_text
    demo_commitment = seeded_demo_commitment_chat()
    assert "Send Northridge Grid the revised quote" in demo_commitment.answer_text
    assert "2026-01-12" in demo_commitment.answer_text
    assert [question for question, _ in seeded_demo_exchanges()] == [
        CANONICAL_CHAT_QUESTION,
        CANONICAL_INVOLVED_QUESTION,
        CANONICAL_COMMITMENT_QUESTION,
    ]


def test_null_chat_client_is_unavailable_not_empty_answer() -> None:
    client = NullPostChatClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.answer("any question", [])

_SOURCES = [
    ChatSourceDocument("post-1", "Bid workshop", "We submitted the initial transformer bid on March 3."),
    ChatSourceDocument("post-2", "Bid revision", "The client asked for a revised quote on March 10; we sent it March 12."),
]


def test_cited_post_summaries_keep_citation_order_and_drop_unknown_ids() -> None:
    chips = cited_post_summaries(_SOURCES, ("post-2", "missing", "post-1"))
    assert chips == [
        {"post_id": "post-2", "post_title": "Bid revision"},
        {"post_id": "post-1", "post_title": "Bid workshop"},
    ]


def test_cited_post_evidence_hides_prompt_metadata_but_keeps_semantic_facts() -> None:
    source = ChatSourceDocument(
        "post-evidence",
        "Evidence post",
        "body",
        evidence_facts=(
            "project: Semantic project | evidence: Body evidence | ontology_iri: https://example.test/ontology#Project | extraction_method: contextual_orchestrator_semantic | confidence: 0.9 [provenance=post_project_mention]",
            "Keyman mention: Ada West | context: account lead [provenance=post_person_mention]",
            "time axis: event occurred at",
        ),
    )

    evidence = cited_post_evidence((source,), ("post-evidence", "missing"))

    assert evidence == [
        {
            "post_id": "post-evidence",
            "facts": [
                {"kind": "semantic_project", "text": "project: Semantic project | evidence: Body evidence"},
                {"kind": "semantic_keyman", "text": "Keyman mention: Ada West | context: account lead"},
                {"kind": "time_axis", "text": "time axis: event occurred at"},
            ],
        }
    ]


def test_chat_render_includes_persisted_graph_facts_with_source_evidence() -> None:
    source = ChatSourceDocument(
        "post-graph",
        "Graph-backed post",
        "A customer asked for a revised quote.",
        graph_facts=(
            'node_person "Ada West" --edge_affiliation--> '
            'node_corporate_entity "Demo Corp" [evidence_post_id=post-graph]',
        ),
        evidence_facts=("source project code=PROJECT-HINT [hint_only]",),
    )

    rendered = _render_sources_block([source])

    assert "Persisted Knowledge Graph facts" in rendered
    assert "Demo Corp" in rendered
    assert "evidence_post_id=post-graph" in rendered
    assert "Persisted source/semantic evidence" in rendered
    assert "PROJECT-HINT" in rendered


def test_graph_facts_are_hydrated_from_visible_evidence_posts(monkeypatch) -> None:
    class _Connection:
        async def fetch(self, _query, _visible_post_ids):
            return [
                {
                    "source_node_type_code": "node_person",
                    "source_node_id": "person-ada",
                    "target_node_type_code": "node_corporate_entity",
                    "target_node_id": "corp-demo",
                    "edge_type_code": "edge_affiliation",
                    "edge_weight": 1.0,
                    "evidence_post_ids": ["post-graph"],
                }
            ]

    async def fake_hydrate(_conn, _node_keys):
        return [
            {"node_type_code": "node_person", "node_id": "person-ada", "label": "Ada West"},
            {
                "node_type_code": "node_corporate_entity",
                "node_id": "corp-demo",
                "label": "Demo Corp",
            },
        ]

    monkeypatch.setattr("backend.app.post_chat_ingestion.hydrate_related_nodes", fake_hydrate)
    facts = asyncio.run(_graph_facts_for_posts(_Connection(), ["post-graph"]))

    assert facts == (
        'node_person "Ada West" --edge_affiliation '
        '(https://contextualwisdomlab.github.io/LineageWeave/ontology#affiliatedWith)--> '
        'node_corporate_entity "Demo Corp" [evidence_post_id=post-graph]',
    )


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


def test_contextual_orchestrator_chat_requests_plain_citations(monkeypatch) -> None:
    observed = {}

    def fake_post_json(url, payload, *, headers, timeout):
        observed["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": "근거 답변\nCITED SOURCES: 1"
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.post_chat.post_json", fake_post_json)
    answer = ContextualOrchestratorPostChatClient("https://orchestrator.test", "token").answer(
        "What happened?", _SOURCES
    )

    assert answer.answer_text == "근거 답변"
    assert observed["payload"]["reasoning_effort"] == "auto"
    assert observed["payload"]["mode"] == "auto"
    assert "CITED SOURCES" in observed["payload"]["messages"][0]["content"]
