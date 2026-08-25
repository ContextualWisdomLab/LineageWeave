from __future__ import annotations

import asyncio
import math
from datetime import date, datetime, timezone

from backend.app.post_chat_ingestion import (
    _fuse_global_candidate_ids,
    _ontology_lookup_codes_in_question,
    gather_global_chat_sources as _gather_global_chat_sources,
    prepare_global_question_embedding,
)
from lineageweave.ask_time_axis import TIME_AXIS_CREATED, TIME_AXIS_EVENT


class _EmbeddingClient:
    available = True
    resolved_model = "test-embedding"

    def embed(self, _text: str) -> list[float]:
        return [1.0, 0.0]


def test_prepare_global_question_embedding_rejects_blank_input_before_provider() -> None:
    """A blank question must fail closed without crossing the provider boundary."""

    class RejectCallsEmbedding:
        resolved_model = "synthetic-embedding"

        def embed(self, _text: str) -> list[float]:
            raise AssertionError("blank question must not call the embedding provider")

    assert (
        asyncio.run(
            prepare_global_question_embedding(" \t\n", RejectCallsEmbedding())
        )
        is None
    )


def test_nonfinite_embeddings_fail_closed_before_database_access() -> None:
    """Provider and precomputed vectors must remain finite."""

    class NonfiniteEmbedding:
        available = True
        resolved_model = "synthetic-embedding"

        def embed(self, _text: str) -> list[float]:
            return [math.nan, math.inf]

    class RejectDatabase:
        async def fetch(self, _query: str, *_args):
            raise AssertionError("nonfinite embeddings must not reach PostgreSQL")

    assert asyncio.run(
        prepare_global_question_embedding("question", NonfiniteEmbedding())
    ) is None
    assert asyncio.run(
        _gather_global_chat_sources(
            RejectDatabase(),
            lambda _row: True,
            question="question",
            question_embedding=([math.inf, 0.0], "synthetic-embedding", math.inf),
        )
    ) == []


def gather_global_chat_sources(*args, **kwargs):
    """Exercise Global Ask with an available deterministic semantic channel."""
    kwargs.setdefault("embedding_client", _EmbeddingClient())
    return _gather_global_chat_sources(*args, **kwargs)


def test_parameter_free_rrf_combines_embedding_and_evidence_rank_lists() -> None:
    """A post supported by both owned channels outranks one-channel hits."""

    assert _fuse_global_candidate_ids(
        ["embedding-only", "shared"], ["shared", "evidence-only"], 3
    )[0] == "shared"


def test_disabled_rankweave_keeps_embedding_order(monkeypatch) -> None:
    """The shared runtime switch disables Global Ask fusion as well."""
    monkeypatch.setenv("RANKWEAVE_DISABLED", "1")

    assert _fuse_global_candidate_ids(
        ["embedding-only", "shared"], ["shared", "evidence-only"], 3
    ) == ["embedding-only", "shared"]


def test_complete_canonical_ontology_iri_maps_to_its_lookup_code() -> None:
    """Ontology nomination uses the published full IRI, not substring guessing."""

    codes = _ontology_lookup_codes_in_question(
        "Explain https://contextualwisdomlab.github.io/LineageWeave/ontology#affiliatedWith"
    )

    assert codes == ["edge_affiliation"]
    assert _ontology_lookup_codes_in_question("affiliatedWith") == []


def test_evidence_only_term_nominates_its_authorized_source() -> None:
    """A persisted semantic hit works even when no body embedding nominates it."""

    source_row = {
        "post_id": "semantic-only",
        "post_title": "Neutral source title",
        "post_body": "Neutral source body",
        "visibility_code": "public",
        "corporate_entity_id": None,
        "process_unit_id": None,
        "created_at": datetime(2026, 8, 25, tzinfo=timezone.utc),
        "event_occurred_at": None,
    }

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "unit_similarity" in query:
                assert "authorized_evidence_candidates" in query
                assert query.index("authorized_evidence_candidates") < query.rindex("limit $8")
                assert args[8] == "exclusive responsibility"
                return [
                    {
                        "candidate_channel": "evidence",
                        "post_id": "semantic-only",
                        "channel_rank": 1,
                    }
                ]
            if "from post_lineage_edge" in query:
                return []
            if "array_position($3::uuid[], post_id)" in query:
                return [source_row]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public",
            question="exclusive responsibility",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["semantic-only"]


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
            question="public evidence",
        )
    )

    assert [source.post_id for source in sources] == ["public-post", "private-affiliated"]
    assert sources[0].post_body == "public body"
    assert sources[1].post_body == "affiliated body"


def test_global_sources_apply_process_scope_before_sql_limit() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            {"corp-demo"},
            {"process-demo"},
            question="synthetic process evidence",
        )
    )

    source_query, source_args = calls[-1]
    assert "process_unit_id::text = any($2::text[])" in source_query
    assert source_args[:2] == (["corp-demo"], ["process-demo"])


def test_global_sources_use_semantic_rank_order_and_bound_long_bodies() -> None:
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
        (query, args) for query, args in calls if "array_position($3::uuid[], post_id)" in query
    )
    assert "unit_similarity" in candidate_query
    assert "websearch_to_tsquery('simple', $9)" in candidate_query
    assert "post_project_mention" in candidate_query
    assert "knowledge_graph_edge_evidence" in candidate_query
    assert "ilike" not in candidate_query.lower()
    assert candidate_args[0] == [1.0, 0.0]
    assert candidate_args[2] == "test-embedding"
    assert "array_position($3::uuid[], post_id)" in source_query
    assert "source_post.post_id = any($3::uuid[])" in source_query
    assert source_args[3] == 8
    # A test row without a channel marker is the legacy embedding-channel
    # fixture and retains its database rank order.
    assert list(source_args[2]) == ["newest-post", "uam-post"]
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


def test_global_sources_keep_graph_facts_with_their_evidence_source(monkeypatch) -> None:
    """Graph provenance cannot move from one visible post to another."""
    rows = [
        {
            "post_id": post_id,
            "post_title": f"Evidence {post_id}",
            "post_body": f"body {post_id}",
            "visibility_code": "public",
            "corporate_entity_id": None,
        }
        for post_id in ("post-a", "post-b")
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            return rows if "from source_post" in query else []

    async def fake_graph_facts(_conn, _visible_post_ids, _knowledge_cutoff=None):
        return {"post-b": ("fact evidenced by post-b",)}

    monkeypatch.setattr(
        "backend.app.post_chat_ingestion._graph_facts_for_posts", fake_graph_facts
    )

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, question="evidence", limit=2
        )
    )

    assert sources[0].post_id == "post-a"
    assert sources[0].graph_facts == ()
    assert sources[1].post_id == "post-b"
    assert sources[1].graph_facts == ("fact evidenced by post-b",)


def test_global_sources_embed_identifier_question_without_tokenizing() -> None:
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

    candidate_calls = [(query, args) for query, args in calls if "unit_similarity" in query]
    assert len(candidate_calls) == 1
    assert candidate_calls[0][1][0] == [1.0, 0.0]


def test_global_sources_embed_localized_question_once() -> None:
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

    candidate_calls = [(query, args) for query, args in calls if "unit_similarity" in query]
    assert len(candidate_calls) == 1


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
            if "unit_similarity" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": post_id} for post_id in reversed(neighbor_ids)]
            if "array_position($3::uuid[], post_id)" in query:
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
                return [rows[post_id] for post_id in args[2]]
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
    assert source_args[3] == 4
    assert list(source_args[2]) == [
        "anchor-post",
        "neighbor-00",
        "neighbor-01",
        "neighbor-02",
    ]
    assert [source.post_id for source in sources] == list(source_args[2])
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


def test_global_sources_fail_closed_when_embedding_is_unavailable() -> None:
    class UnavailableEmbedding:
        available = False
        resolved_model = None

        def embed(self, _text: str) -> list[float]:
            raise AssertionError("unavailable embedding must not be called")

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "authorized_evidence_candidates" in query:
                assert args[10] is False
            return []

    sources = asyncio.run(
        _gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="semantic question",
            embedding_client=UnavailableEmbedding(),
        )
    )

    assert sources == []


def test_global_sources_accept_valid_precomputed_embedding_without_provider() -> None:
    """A validated embedding envelope must not depend on provider availability."""

    class UnavailableEmbedding:
        available = False
        resolved_model = None

        def embed(self, _text: str) -> list[float]:
            raise AssertionError("precomputed embedding must not call the provider")

    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    sources = asyncio.run(
        _gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="semantic question",
            question_embedding=([1.0, 0.0], "synthetic-embedding", 1.0),
            embedding_client=UnavailableEmbedding(),
        )
    )

    assert sources == []
    candidate_calls = [(query, args) for query, args in calls if "unit_similarity" in query]
    assert len(candidate_calls) == 1
    assert candidate_calls[0][1][:3] == ([1.0, 0.0], 1.0, "synthetic-embedding")


def test_global_sources_disable_an_embedding_without_a_resolved_model() -> None:
    """An unbound vector cannot match persisted rows but evidence remains available."""

    class UnboundEmbedding:
        available = True
        resolved_model = None

        def embed(self, _text: str) -> list[float]:
            return [1.0, 0.0]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "authorized_evidence_candidates" in query:
                assert args[10] is False
            return []

    sources = asyncio.run(
        _gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="semantic question",
            embedding_client=UnboundEmbedding(),
        )
    )

    assert sources == []


def test_global_sources_expand_top_match_through_event_lineage() -> None:
    """Global Ask must speak to a connected timeline, not an isolated
        snapshot -- expand the single top-ranked semantic match through its
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
        async def fetch(self, query: str, *args):
            if "unit_similarity" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": "event-1"}]
            if "array_position($3::uuid[], post_id)" in query:
                return [matched_row, lineage_row]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="Northridge Grid capacity",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["event-2", "event-1"]
    assert sources[0].evidence_facts == ()
    assert any(
        "Event Lineage: reconstructed timeline neighbor of post_id=event-2" in fact
        for fact in sources[1].evidence_facts
    )


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
            if "unit_similarity" in query:
                return [matched_row]
            if "post_lineage_edge" in query:
                return [{"other_id": "visible-neighbor"}]
            if "array_position($3::uuid[], post_id)" in query:
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
    assert sources[0].evidence_facts == ()


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
        (query, args) for query, args in calls if "array_position($3::uuid[], post_id)" in query
    )
    # Both sides of the day-boundary comparison must read the same zone --
    # asserting the SQL cast pins that the event-time side is never left on
    # the connection's plain UTC/session default while `today` moves to KST.
    assert "coalesce(event_occurred_at, created_at)" in source_query
    assert "at time zone 'Asia/Seoul'" in source_query
    assert source_args[4] == date(2026, 8, 21)
    assert source_args[5] == date(2026, 8, 21)
    candidate_calls = [(query, args) for query, args in calls if "unit_similarity" in query]
    assert all("event_clock" in query for query, _args in candidate_calls)
    assert all(
        args[5:7] == (date(2026, 8, 21), date(2026, 8, 21))
        for _query, args in candidate_calls
    )


def test_global_sources_keep_body_and_title_lexical_fallback_disabled() -> None:
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

    candidate_queries = [query for query, _args in calls if "unit_similarity" in query]
    assert len(candidate_queries) == 1
    assert "ilike" not in candidate_queries[0].lower()
    assert "source_post_search_text" not in candidate_queries[0]
    assert "websearch_to_tsquery('simple', $9)" in candidate_queries[0]


def test_global_sources_bind_relative_time_to_event_clock_not_ingest_cluster(
    monkeypatch,
) -> None:
    """Bulk-imported posts share one created_at. Ask '어제' must keep the
    post whose event fell yesterday and drop the one whose event fell
    last week, then name the event axis on the cited source.
    """
    monkeypatch.setattr(
        "backend.app.post_chat_ingestion._seoul_today", lambda: date(2026, 8, 22)
    )
    import_cluster = datetime(2026, 8, 22, 6, 0, tzinfo=timezone.utc)
    rows = [
        {
            "post_id": "yesterday-event",
            "post_title": "Synthetic follow-up that happened yesterday",
            "post_body": "<p>yesterday event body</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "created_at": import_cluster,
            "event_occurred_at": datetime(2026, 8, 21, 3, 0, tzinfo=timezone.utc),
            "matched_in": "title",
        },
        {
            "post_id": "last-week-event",
            "post_title": "Synthetic follow-up from last week",
            "post_body": "<p>last week event body</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "created_at": import_cluster,
            "event_occurred_at": datetime(2026, 8, 12, 3, 0, tzinfo=timezone.utc),
            "matched_in": "title",
        },
        {
            "post_id": "ingest-only",
            "post_title": "Synthetic ingest-only cluster row",
            "post_body": "<p>no event clock</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "created_at": import_cluster,
            "event_occurred_at": None,
            "matched_in": "title",
        },
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "from post_lineage_edge" in query:
                return []
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="어제 무슨 일이 있었나요?",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["yesterday-event"]
    assert TIME_AXIS_EVENT in sources[0].evidence_facts
    assert TIME_AXIS_CREATED not in sources[0].evidence_facts


def test_global_sources_name_created_at_fallback_when_event_clock_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.post_chat_ingestion._seoul_today", lambda: date(2026, 8, 22)
    )
    rows = [
        {
            "post_id": "ingest-yesterday",
            "post_title": "Synthetic ingest-clock post",
            "post_body": "<p>ingested yesterday</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "created_at": datetime(2026, 8, 21, 3, 0, tzinfo=timezone.utc),
            "event_occurred_at": None,
            "matched_in": "title",
        }
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "from post_lineage_edge" in query:
                return []
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda _row: True,
            question="어제 무슨 일이 있었나요?",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["ingest-yesterday"]
    assert TIME_AXIS_CREATED in sources[0].evidence_facts
