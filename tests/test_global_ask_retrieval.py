from __future__ import annotations

import pytest

from backend.app import global_ask_retrieval as retrieval


def test_global_ask_query_terms_are_bounded_deduplicated_and_stopword_filtered() -> None:
    terms = retrieval.global_ask_query_terms(
        "What is Apollo Apollo Acme project and which post is related?",
        maximum_terms=3,
    )
    assert terms == ("is", "apollo", "acme")
    assert retrieval.global_ask_query_terms("Apollo", maximum_terms=0) == ()


def test_graph_fact_evidence_post_ids_extracts_all_named_sources() -> None:
    fact = (
        'node_team "Apollo" --edge_team_affiliation--> node_organization "Acme" '
        "[evidence_post_id=11111111-1111-1111-1111-111111111111,"
        "22222222-2222-2222-2222-222222222222]"
    )
    assert retrieval.graph_fact_evidence_post_ids(fact) == frozenset(
        {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        }
    )
    assert retrieval.graph_fact_evidence_post_ids("no provenance") == frozenset()


def test_public_external_claim_facts_never_exports_people_private_or_partial_graph_evidence() -> None:
    project = "project: Apollo | evidence: Acme launch"
    actor = "actor: Alice | responsibility: sponsor"
    keyman = "Keyman mention: Alice"
    fully_public_graph = (
        'node_team "Apollo" --edge_team_affiliation--> node_organization "Acme" '
        "[evidence_post_id=11111111-1111-1111-1111-111111111111,"
        "22222222-2222-2222-2222-222222222222]"
    )
    partial_graph = (
        'node_team "Apollo" --edge_team_affiliation--> node_organization "PrivateCo" '
        "[evidence_post_id=11111111-1111-1111-1111-111111111111,"
        "33333333-3333-3333-3333-333333333333]"
    )
    public_ids = frozenset(
        {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        }
    )

    facts = retrieval.public_external_claim_facts(
        {"visibility_code": "public"},
        (project, actor, keyman),
        (fully_public_graph, partial_graph),
        public_ids,
    )

    assert facts == (project, fully_public_graph)
    assert retrieval.public_external_claim_facts(
        {"visibility_code": "private"},
        (project,),
        (fully_public_graph,),
        public_ids,
    ) == ()


class _FakeConnection:
    def __init__(self) -> None:
        self.arguments = None
        self.query = None

    async def fetch(self, query: str, *arguments):
        self.query = query
        self.arguments = arguments
        return [
            {"post_id": "11111111-1111-1111-1111-111111111111"},
            {"post_id": "11111111-1111-1111-1111-111111111111"},
            {"post_id": "22222222-2222-2222-2222-222222222222"},
        ]


@pytest.mark.anyio
async def test_semantic_candidate_post_ids_is_bounded_and_deduplicated(monkeypatch) -> None:
    monkeypatch.setattr(
        retrieval,
        "ontology_lookup_codes_for_question",
        lambda question: ("edge_team_affiliation",),
    )
    connection = _FakeConnection()

    candidates = await retrieval.semantic_candidate_post_ids(
        connection,
        "Apollo team Acme",
        maximum_candidates=7,
    )

    assert candidates == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]
    assert "post_project_mention" in connection.query
    assert "post_summary_role" in connection.query
    assert "post_person_mention" in connection.query
    assert "post_organization_mention" in connection.query
    assert "post_team_mention" in connection.query
    assert "knowledge_graph_edge_evidence" in connection.query
    assert connection.arguments[1] == ["edge_team_affiliation"]
    assert connection.arguments[2] == 7


@pytest.mark.anyio
async def test_semantic_candidate_post_ids_skips_empty_or_zero_budget(monkeypatch) -> None:
    connection = _FakeConnection()
    monkeypatch.setattr(
        retrieval,
        "ontology_lookup_codes_for_question",
        lambda question: (),
    )
    assert await retrieval.semantic_candidate_post_ids(connection, "", maximum_candidates=8) == []
    assert await retrieval.semantic_candidate_post_ids(connection, "Apollo", maximum_candidates=0) == []
    assert connection.query is None
