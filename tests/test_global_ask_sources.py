from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from uuid import UUID

from backend.app.post_chat_ingestion import gather_global_chat_sources
from lineageweave.tepp_client import TeppClient


def test_global_sources_apply_visibility_before_normalization() -> None:
    rows = [
        {
            "post_id": "public-post",
            "post_title": "Public evidence",
            "post_body": "<p>public body</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
        },
        {
            "post_id": "private-affiliated",
            "post_title": "Affiliated evidence",
            "post_body": "<p>affiliated body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-demo",
        },
        {
            "post_id": "private-hidden",
            "post_title": "Hidden evidence",
            "post_body": "<p>hidden body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-other",
        },
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public"
            or row["corporate_entity_id"] == "corp-demo",
            {"corp-demo"},
        )
    )

    assert [source.post_id for source in sources] == ["public-post", "private-affiliated"]
    assert sources[0].post_body == "public body"
    assert sources[1].post_body == "affiliated body"


def test_global_sources_apply_reader_eligibility_before_limit() -> None:
    calls: list[str] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append(query)
            if "matched_in" in query:
                return [{"post_id": "draft-post", "matched_in": "title"}]
            if "array_position($2::uuid[], post_id)" in query:
                return []
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, question="draft", limit=1
        )
    )

    source_query = next(query for query in calls if "array_position($2::uuid[], post_id)" in query)
    candidate_query = next(query for query in calls if "matched_in" in query)
    assert "authorized_source_post" in candidate_query
    assert "source_draft_code" in candidate_query
    assert "source_deleted_flag" in candidate_query
    assert "source_draft_code" in source_query
    assert "source_deleted_flag" in source_query


def test_global_sources_normalize_authorized_uuid_values_for_text_array() -> None:
    received = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "matched_in" in query:
                received.extend(args[1])
            return []

    entity_id = UUID("00000000-0000-0000-0000-000000000001")
    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, [entity_id], question="evidence"
        )
    )

    assert received == [str(entity_id)]


def test_global_sources_use_tepp_temporal_context_without_claiming_causality() -> None:
    now = datetime(2026, 8, 23, tzinfo=UTC)
    rows = [
        {
            "post_id": post_id,
            "post_title": post_id,
            "post_body": "synthetic body",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "author_account_id": f"actor-{index}",
            "created_at": now.replace(day=20 + index),
            "updated_at": now.replace(day=20 + index),
            "semantic_event_time": now.replace(day=20 + index).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "semantic_event_available_at": now.replace(day=20 + index),
        }
        for index, post_id in enumerate(("prior-post", "anchor-post"))
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "array_position($2::uuid[], post_id)" in query:
                return rows
            return []

    client = TeppClient(
        temporal_transport=lambda _payload: {
            "contract_version": 1,
            "claim_boundary": "association_not_causal",
            "timeline_events": [
                {
                    "event_id": "semantic-event:prior-post",
                    "source_post_id": "prior-post",
                    "event_type_code": "semantic_event",
                    "event_label": "Persisted semantic event",
                    "event_time": "2026-08-20T00:00:00Z",
                    "project_reference": None,
                    "actor_references": ["actor-0"],
                    "sequence_ordinal": 0,
                    "is_subject": False,
                },
                {
                    "event_id": "semantic-event:anchor-post",
                    "source_post_id": "anchor-post",
                    "event_type_code": "semantic_event",
                    "event_label": "Persisted semantic event",
                    "event_time": "2026-08-21T00:00:00Z",
                    "project_reference": None,
                    "actor_references": ["actor-1"],
                    "sequence_ordinal": 1,
                    "is_subject": True,
                },
            ],
            "temporal_relations": [
                {
                    "from_event_id": "semantic-event:prior-post",
                    "to_event_id": "semantic-event:anchor-post",
                    "relation_code": "before",
                }
            ],
            "transition_gap_candidates": [
                {
                    "from_event_id": "semantic-event:prior-post",
                    "to_event_id": "semantic-event:anchor-post",
                    "evidence_status_code": "candidate_not_causal",
                }
            ],
            "source_post_ids": ["prior-post", "anchor-post"],
        }
    )
    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            anchor_post_id="anchor-post",
            tepp_client=client,
        )
    )

    assert [source.post_id for source in sources] == ["anchor-post", "prior-post"]
    assert "association_not_causal" in sources[1].evidence_facts[-1]


def test_global_sources_use_post_recorded_boundary_without_semantic_event_time() -> None:
    called = False
    received = None

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "array_position($2::uuid[], post_id)" in query:
                return [
                    {
                        "post_id": post_id,
                        "post_title": post_id,
                        "post_body": "synthetic body",
                        "visibility_code": "public",
                        "corporate_entity_id": None,
                        "author_account_id": "synthetic-actor",
                        "created_at": datetime(2026, 8, 20 + index, tzinfo=UTC),
                        "updated_at": datetime(2026, 8, 20 + index, tzinfo=UTC),
                        "semantic_event_time": None,
                        "semantic_event_available_at": None,
                    }
                    for index, post_id in enumerate(("prior-post", "anchor-post"))
                ]
            return []

    def temporal_transport(_payload):
        nonlocal called, received
        called = True
        received = _payload
        raise OSError("synthetic unavailable transport")

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            anchor_post_id="anchor-post",
            tepp_client=TeppClient(temporal_transport=temporal_transport),
        )
    )

    assert len(sources) == 2
    assert called is True
    assert [event["event_type_code"] for event in received["events"]] == [
        "post_recorded",
        "post_recorded",
    ]
    assert all(event["event_time"] == event["available_time"] for event in received["events"])
    assert all("TEPP temporal context" not in fact for source in sources for fact in source.evidence_facts)


def test_global_sources_prioritize_question_terms_and_bound_long_bodies() -> None:
    rows = [
        {
            "post_id": "newest-post",
            "post_title": "Unrelated evidence",
            "post_body": "ordinary body",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "matched_in": "body",
        },
        {
            "post_id": "uam-post",
            "post_title": "UAM deployment evidence",
            "post_body": "x" * 7000,
            "visibility_code": "public",
            "corporate_entity_id": None,
            "matched_in": "title",
        },
    ]
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="Which posts mention UAM?",
            limit=8,
        )
    )

    candidate_query, candidate_args = calls[0]
    source_query, source_args = next(
        (query, args) for query, args in calls if "array_position($2::uuid[], post_id)" in query
    )
    assert "to_tsvector('simple'" in candidate_query
    assert candidate_args[0] == "mention"
    assert "array_position($2::uuid[], post_id)" in source_query
    assert source_args[2] == 8
    # Live bug (2026-08-19): a title match must outrank a body/source-field
    # match regardless of discovery order -- "uam-post" matched in the
    # title (higher weight) but was appended to candidate_rows after
    # "newest-post" (a body match); the final candidate_ids array passed
    # as $2 must still rank uam-post first.
    assert list(source_args[1]) == ["uam-post", "newest-post"]
    assert sources[1].post_body.startswith("x" * 4000)
    assert "Source body truncated for Global Ask" in sources[1].post_body


def test_global_sources_carry_source_and_semantic_evidence() -> None:
    rows = [
        {
            "post_id": "semantic-post",
            "post_title": "Operational note",
            "post_body": "No project name in this body.",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "source_project_code": "PROJECT-HINT",
            "source_record_key": "SYNTHETIC-KEY-001",
            "matched_in": "source_field",
        }
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "from source_post" in query:
                return rows
            if "from post_project_mention" in query:
                return [
                    {
                        "post_id": "semantic-post",
                        "fact": "project: semantic project | ontology_iri: urn:test",
                    }
                ]
            return []

    sources = __import__("asyncio").run(
        gather_global_chat_sources(
            FakeConnection(), lambda row: True, question="PROJECT-HINT", limit=1
        )
    )

    assert len(sources) == 1
    assert any(
        "source project code=PROJECT-HINT" in fact for fact in sources[0].evidence_facts
    )
    assert sources[0].evidence_facts[-1].startswith("project: semantic project")


def test_global_sources_keep_hyphenated_source_codes_atomic() -> None:
    """Live bug (2026-08-19): a hyphenated ERP-style job code such as
    ``P41-4182-202405-0015`` used to be shredded into generic numeric
    fragments (``P41``, ``4182``, ``202405``, ``0015``) by the search-term
    tokenizer, so unrelated posts sharing only a short fragment (e.g. a
    ``202405``-dated post from a different project) outranked or crowded
    out the actual code match. The tokenizer must keep a hyphen-joined
    code as one atomic search term.
    """
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="P41-4182-202405-0015",
            limit=4,
        )
    )

    candidate_terms = [args[0] for query, args in calls if "matched_in" in query]
    assert candidate_terms == ["p41-4182-202405-0015"]


def test_global_sources_keep_unicode_search_terms_for_localized_readers() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="无人机 ドローン dự-án",
            limit=4,
        )
    )

    candidate_terms = [args[0] for query, args in calls if "matched_in" in query]
    assert candidate_terms == ["无人机", "ドローン", "dự-án"]


def test_global_sources_drop_generic_korean_predecessor_words() -> None:
    calls = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append(query)
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="앞쪽에 있는 유관 이벤트를 찾아줘",
            anchor_post_id="00000000-0000-0000-0000-000000000002",
        )
    )

    assert not any("matched_in" in query for query in calls)


def test_global_sources_keep_lineage_expansion_within_requested_limit() -> None:
    matched_row = {
        "post_id": "anchor-post",
        "post_title": "Anchor evidence",
        "post_body": "anchor body",
        "visibility_code": "public",
        "corporate_entity_id": None,
        "matched_in": "title",
    }
    neighbor_ids = [f"neighbor-{index:02d}" for index in range(20)]
    source_call: tuple[str, tuple[object, ...]] | None = None

    class FakeConnection:
        async def fetch(self, query: str, *args):
            nonlocal source_call
            if "matched_in" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": post_id} for post_id in reversed(neighbor_ids)]
            if "array_position($2::uuid[], post_id)" in query:
                source_call = (query, args)
                rows = {
                    "anchor-post": matched_row,
                    **{
                        post_id: {
                            "post_id": post_id,
                            "post_title": post_id,
                            "post_body": "neighbor body",
                            "visibility_code": "public",
                            "corporate_entity_id": None,
                        }
                        for post_id in neighbor_ids
                    },
                }
                return [rows[post_id] for post_id in args[1]]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="Anchor evidence",
            limit=4,
        )
    )

    assert source_call is not None
    _query, source_args = source_call
    assert source_args[2] == 4
    assert list(source_args[1]) == [
        "anchor-post",
        "neighbor-00",
        "neighbor-01",
        "neighbor-02",
    ]
    assert [source.post_id for source in sources] == list(source_args[1])
    assert len(sources) == 4


def test_global_sources_return_no_evidence_for_zero_limit() -> None:
    class FakeConnection:
        async def fetch(self, _query: str, *_args):
            raise AssertionError("zero source budget must not query evidence")

    assert (
        asyncio.run(
            gather_global_chat_sources(
                FakeConnection(),
                lambda _row: True,
                question="anything",
                limit=0,
            )
        )
        == []
    )


def test_global_sources_expand_top_match_through_event_lineage() -> None:
    """Global Ask must speak to a connected timeline, not an isolated
    snapshot -- expand the single top-ranked keyword match through its
    direct `post_lineage_edge` neighbors (`lineageweave.reconstruct`'s
    output), mirroring the post-scoped chat flow's `find_linked_post_ids`.
    """
    matched_row = {
        "post_id": "event-2",
        "post_title": "Northridge Grid capacity review",
        "post_body": "capacity review body",
        "visibility_code": "public",
        "corporate_entity_id": None,
        "matched_in": "title",
    }
    lineage_row = {
        "post_id": "event-1",
        "post_title": "Northridge Grid kickoff",
        "post_body": "kickoff body",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }

    class FakeConnection:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def fetch(self, query: str, *args):
            self.queries.append(query)
            if "matched_in" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": "event-1"}]
            if "array_position($2::uuid[], post_id)" in query:
                return [matched_row, lineage_row]
            return []

    connection = FakeConnection()
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda row: True,
            question="Northridge Grid capacity",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["event-2", "event-1"]
    assert any(
        "commercial_context=no_sales_identifier_candidate" in fact
        for fact in sources[0].evidence_facts
    )
    assert any("source_lifecycle_vector=∅/∅/∅/∅" in fact for fact in sources[0].evidence_facts)
    assert any(
        "Event Lineage: reconstructed timeline neighbor of post_id=event-2" in fact
        for fact in sources[1].evidence_facts
    )
    source_query = next(query for query in connection.queries if "array_position($2::uuid[], post_id)" in query)
    for field_name in (
        "source_order_pool_code",
        "source_sales_order_code",
        "source_sales_order_item_number",
        "source_inspection_point_code",
        "source_stage_code",
        "source_deleted_flag",
    ):
        assert field_name in source_query


def test_global_sources_do_not_leak_lineage_anchor_id_when_anchor_is_invisible() -> None:
    """If ABAC hides the top match itself, an expanded neighbor must not
    cite that hidden post's id as its lineage anchor.
    """
    matched_row = {
        "post_id": "hidden-anchor",
        "post_title": "Private kickoff",
        "post_body": "private body",
        "visibility_code": "private",
        "corporate_entity_id": "corp-other",
        "matched_in": "title",
    }
    lineage_row = {
        "post_id": "visible-neighbor",
        "post_title": "Public follow-up",
        "post_body": "public body",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "matched_in" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": "visible-neighbor"}]
            if "array_position($2::uuid[], post_id)" in query:
                return [matched_row, lineage_row]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public",
            question="kickoff",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["visible-neighbor"]
    assert any(
        "commercial_context=no_sales_identifier_candidate" in fact
        for fact in sources[0].evidence_facts
    )


def test_global_sources_use_selected_post_to_find_prior_semantic_event() -> None:
    anchor = {
        "post_id": "event-2",
        "post_title": "Current event",
        "post_body": "current body",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }
    prior = {**anchor, "post_id": "event-1", "post_title": "Prior event"}

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "anchor_events" in query:
                assert args[0] == "event-2"
                assert "post.source_company_code = anchor.source_company_code" in query
                assert "0.85 * (post.source_sales_order_code is not null" in query
                return [{"post_id": "event-1", "relevance": 0.5}]
            if "matched_in" in query:
                return []
            if "post_lineage_edge" in query:
                return []
            if "array_position($2::uuid[], post_id)" in query:
                assert args[1][:2] == ["event-2", "event-1"]
                return [anchor, prior]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="what happened before?",
            anchor_post_id="event-2",
        )
    )

    assert [source.post_id for source in sources] == ["event-2", "event-1"]


def test_global_sources_discover_ontology_declared_kg_sibling_and_fetch_candidates_only() -> None:
    anchor = {
        "post_id": "event-2",
        "post_title": "Current event",
        "post_body": "current body",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }
    sibling = {**anchor, "post_id": "event-1", "post_title": "Prior graph event"}
    source_query = ""

    class FakeConnection:
        async def fetch(self, query: str, *args):
            nonlocal source_query
            if "with anchor_nodes as" in query:
                return [
                    {
                        "post_id": "event-1",
                        "edge_type_code": "edge_mention",
                        "edge_weight": 1.0,
                    },
                    {
                        "post_id": "ignored-post",
                        "edge_type_code": "not_in_ontology",
                        "edge_weight": 1.0,
                    },
                ]
            if "anchor_events" in query or "matched_in" in query or "post_lineage_edge" in query:
                return []
            if "array_position($2::uuid[], post_id)" in query:
                source_query = query
                assert args[1][:2] == ["event-2", "event-1"]
                assert "ignored-post" not in args[1]
                return [anchor, sibling]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            anchor_post_id="event-2",
        )
    )

    assert [source.post_id for source in sources] == ["event-2", "event-1"]
    assert "post_id = any($2::uuid[])" in source_query


def test_global_sources_keep_question_retrieval_with_selected_post() -> None:
    anchor = {
        "post_id": "event-2",
        "post_title": "Current event",
        "post_body": "current body",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }
    question_match = {
        **anchor,
        "post_id": "question-match",
        "post_title": "Northridge evidence",
        "matched_in": "title",
    }

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "matched_in" in query:
                assert args[0] == "northridge"
                return [question_match]
            if "anchor_events" in query or "post_lineage_edge" in query:
                return []
            if "array_position($2::uuid[], post_id)" in query:
                assert args[1][:2] == ["event-2", "question-match"]
                return [anchor, question_match]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="Northridge",
            anchor_post_id="event-2",
        )
    )

    assert [source.post_id for source in sources] == ["event-2", "question-match"]


def test_global_sources_resolve_relative_time_against_seoul_calendar_day(
    monkeypatch,
) -> None:
    """Live bug: the resolver's `today` and the SQL day-boundary cast must
    agree on the same calendar -- otherwise a question asked during
    KST 00:00-09:00 (still "yesterday" by a UTC clock) resolves "어제" one
    day off from the day `created_at::date` is compared against.
    """
    monkeypatch.setattr(
        "backend.app.post_chat_ingestion._seoul_today", lambda: date(2026, 8, 22)
    )
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, question="어제 있었던 일 알려줘", limit=4
        )
    )

    source_query, source_args = next(
        (query, args) for query, args in calls if "array_position($2::uuid[], post_id)" in query
    )
    # Both sides of the day-boundary comparison must read the same zone --
    # asserting the SQL cast pins that the created_at side is never left on
    # the connection's plain UTC/session default while `today` moves to KST.
    assert "at time zone 'Asia/Seoul'" in source_query
    assert source_args[3] == date(2026, 8, 21)
    assert source_args[4] == date(2026, 8, 21)


def test_global_sources_drop_particle_attached_temporal_words_from_search_terms() -> None:
    """Live bug: the temporal-stopword filter used exact match, so a Korean
    particle attached directly to a time word ("어제는") tokenized as one
    token and survived into keyword search, even though this is the
    ordinary way to phrase the question (not an edge case).
    """
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="어제는 무슨 일이 있었나요?",
            limit=4,
        )
    )

    candidate_terms = [args[0] for query, args in calls if "matched_in" in query]
    assert candidate_terms == ["무슨", "일이", "있었나요"]
