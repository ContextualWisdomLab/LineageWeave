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


def test_global_ask_query_terms_preserve_multilingual_words_and_compound_codes() -> None:
    assert retrieval.global_ask_query_terms(
        "客户 项目 顧客 プロジェクト dự-án P41-4182-202405-0015"
    ) == (
        "客户",
        "项目",
        "顧客",
        "プロジェクト",
        "dự-án",
        "p41-4182-202405-0015",
    )


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


def test_public_external_claim_facts_never_exports_people_private_or_raw_project_evidence() -> None:
    project = (
        "project: Apollo | evidence: Alice shared bearer-token=secret "
        "| ontology_iri: https://example.test/ontology#Project "
        "| extraction_method: llm | confidence: 0.90 "
        "[provenance=post_project_mention]"
    )
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

    assert facts == ("project: Apollo", fully_public_graph)
    assert "Alice" not in " ".join(facts)
    assert "secret" not in " ".join(facts)
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


class _LabelConnection:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows
        self.arguments = None
        self.query = None

    async def fetch(self, query: str, *arguments):
        self.query = query
        self.arguments = arguments
        return self.rows


@pytest.mark.anyio
async def test_semantic_candidate_post_ids_is_bounded_deduplicated_and_indexable(
    monkeypatch,
) -> None:
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
    query = connection.query.casefold()
    assert "post_project_mention" in query
    assert "post_summary_role" in query
    assert "post_person_mention" in query
    assert "post_organization_mention" in query
    assert "organization_name_resolution" in query
    assert "resolution.verification_status_code = 'verify_corroborated'" in query
    assert "resolution.raw_organization_name ilike" in query
    assert "resolution.resolved_organization_name ilike" in query
    assert "person_affiliation" in query
    assert "post_team_mention" in query
    assert "knowledge_graph_edge_evidence" in query

    # Expression concatenation defeats the per-column pg_trgm indexes and
    # turns every semantic table into a sequential expression scan.
    assert "concat_ws" not in query
    for predicate in (
        "mention.project_name ilike",
        "mention.evidence_text ilike",
        "mention.ontology_iri ilike",
        "role.actor_name ilike",
        "role.responsibility ilike",
        "role.affiliated_organization_name ilike",
        "person.person_name ilike",
        "person.last_known_job_title ilike",
        "mention.mention_context ilike",
        "entity.entity_name ilike",
        "team.team_name ilike",
        "team.affiliated_organization_name ilike",
    ):
        assert predicate in query

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


def test_verified_organization_label_fact_keeps_raw_and_canonical_separate() -> None:
    assert (
        retrieval.verified_organization_label_fact("DC", "Demo Corp")
        == "verified organization label: DC → Demo Corp"
    )
    assert retrieval.VERIFIED_ORGANIZATION_LABEL_NEXT_ACTION == (
        "Corroborated organization labels are current. Open a cited post to read Event Lineage."
    )


@pytest.mark.anyio
async def test_verified_organization_label_facts_disclose_corroborated_pairs_only() -> None:
    connection = _LabelConnection(
        [
            {
                "post_id": "11111111-1111-1111-1111-111111111111",
                "raw_organization_name": "DC",
                "resolved_organization_name": "Demo Corp",
            },
            {
                "post_id": "11111111-1111-1111-1111-111111111111",
                "raw_organization_name": "DC",
                "resolved_organization_name": "Demo Corp",
            },
            {
                "post_id": "22222222-2222-2222-2222-222222222222",
                "raw_organization_name": "AGP",
                "resolved_organization_name": "Aurora Grid Power",
            },
        ]
    )

    facts = await retrieval.verified_organization_label_facts(
        connection,
        "Which DC posts mention Demo Corp?",
        [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ],
    )

    assert facts == {
        "11111111-1111-1111-1111-111111111111": (
            "verified organization label: DC → Demo Corp",
        ),
        "22222222-2222-2222-2222-222222222222": (
            "verified organization label: AGP → Aurora Grid Power",
        ),
    }
    query = connection.query.casefold()
    assert "matched_organization_label" in query
    assert "organization_name_resolution" in query
    assert "resolution.verification_status_code = 'verify_corroborated'" in query
    assert "verify_pending" not in query
    assert "verify_uncorroborated" not in query
    assert "resolution.raw_organization_name ilike" in query
    assert "resolution.resolved_organization_name ilike" in query
    assert "post_organization_mention" in query
    assert "person_affiliation" in query
    assert "concat_ws" not in query
    assert connection.arguments[0] == ["dc", "mention", "demo", "corp"]
    assert connection.arguments[1] == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]


@pytest.mark.anyio
async def test_verified_organization_label_facts_skip_empty_question_or_posts() -> None:
    connection = _LabelConnection([])
    assert await retrieval.verified_organization_label_facts(connection, "DC", []) == {}
    assert await retrieval.verified_organization_label_facts(
        connection,
        "",
        ["11111111-1111-1111-1111-111111111111"],
    ) == {}
    assert connection.query is None
