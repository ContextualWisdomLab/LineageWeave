from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from backend.app.post_chat_ingestion import gather_global_chat_sources
from lineageweave.ask_time_axis import TIME_AXIS_CREATED, TIME_AXIS_EVENT


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


def test_global_sources_apply_process_scope_before_sql_limit() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, {"corp-demo"}, {"process-demo"}
        )
    )

    source_query, source_args = calls[-1]
    assert "process_unit_id::text = any($2::text[])" in source_query
    assert source_args[:2] == (["corp-demo"], ["process-demo"])


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
        (query, args) for query, args in calls if "array_position($3::uuid[], post_id)" in query
    )
    assert "to_tsvector('simple'" in candidate_query
    assert candidate_args[0] == "mention"
    assert "array_position($3::uuid[], post_id)" in source_query
    assert source_args[3] == 8
    # Live bug (2026-08-19): a title match must outrank a body/source-field
    # match regardless of discovery order -- "uam-post" matched in the
    # title (higher weight) but was appended to candidate_rows after
    # "newest-post" (a body match); the final candidate_ids array passed
    # as $2 must still rank uam-post first.
    assert list(source_args[2]) == ["uam-post", "newest-post"]
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


def test_global_sources_keep_unicode_search_terms_for_localized_buyers() -> None:
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
        async def fetch(self, query: str, *args):
            if "matched_in" in query:
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
            if "matched_in" in query:
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
    candidate_calls = [(query, args) for query, args in calls if "matched_in" in query]
    assert all("event_clock" in query for query, _args in candidate_calls)
    assert all(
        args[1:] == (date(2026, 8, 21), date(2026, 8, 21))
        for _query, args in candidate_calls
    )


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
