"""Global Ask optional knowledge cutoff keeps retrieval evidence-honest (ADR 0135)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from lineageweave.post_chat import (
    FULLY_CUTOFF_GROUNDED,
    LIVE_ONLY,
    PARTIALLY_CUTOFF_GROUNDED,
    ChatSourceDocument,
    ask_grounding_status,
    ask_next_action,
    cited_post_citations,
    historical_body_limitations,
)
from backend.app.post_chat_ingestion import gather_global_chat_sources
from backend.app.main import global_ask_timeline
from backend.app.source_post_revision import parse_as_of_clock

_CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
_JANUARY = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
_FEBRUARY = datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc)


def _row(
    post_id: str,
    *,
    title: str,
    body: str,
    created_at: datetime,
    updated_at: datetime | None = None,
    matched_in: str = "title",
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "post_title": title,
        "post_body": body,
        "visibility_code": "public",
        "corporate_entity_id": None,
        "matched_in": matched_in,
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "source_project_code": "PHOENIX-LIVE",
    }


class _CutoffConnection:
    def __init__(
        self,
        rows: list[dict[str, object]],
        revisions: list[dict[str, object]],
        semantic_rows: list[dict[str, object]] | None = None,
        lineage_edges: list[tuple[str, str]] | None = None,
    ) -> None:
        self.rows = rows
        self.revisions = revisions
        self.semantic_rows = semantic_rows or []
        self.lineage_edges = lineage_edges or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args):
        self.calls.append((query, args))
        if "matched_in" in query:
            term = str(args[0]).casefold()
            cutoff = args[2] if len(args) > 2 else None
            matches = []
            if cutoff is not None:
                covering: dict[str, dict[str, object]] = {}
                for revision in self.revisions:
                    if revision["written_at"] <= cutoff and (
                        revision.get("superseded_at") is None
                        or revision["superseded_at"] > cutoff
                    ):
                        covering[str(revision["post_id"])] = revision
                by_id = {str(row["post_id"]): row for row in self.rows}
                for post_id, revision in covering.items():
                    row = by_id.get(post_id)
                    if row is None or row["created_at"] > cutoff:
                        continue
                    haystack = f"{revision['post_title']} {revision['post_body']}".casefold()
                    if term in haystack:
                        matches.append(
                            {
                                "post_id": post_id,
                                "matched_in": (
                                    "title"
                                    if term in str(revision["post_title"]).casefold()
                                    else "body"
                                ),
                            }
                        )
                return matches
            for row in self.rows:
                haystack = f"{row['post_title']} {row['post_body']}".casefold()
                if term in haystack:
                    matches.append(row)
            return matches
        if "from source_post_revision" in query:
            cutoff = args[1]
            wanted = {str(post_id) for post_id in args[0]}
            return [
                revision
                for revision in self.revisions
                if str(revision["post_id"]) in wanted
                and revision["written_at"] <= cutoff
                and (
                    revision.get("superseded_at") is None
                    or revision["superseded_at"] > cutoff
                )
            ]
        if "from post_project_mention" in query or "from post_summary_role" in query:
            return self.semantic_rows
        if "post_lineage_edge" in query:
            anchor = str(args[0])
            cutoff = args[1] if len(args) > 1 else None
            others = []
            for parent_id, child_id in self.lineage_edges:
                other = (
                    child_id
                    if parent_id == anchor
                    else parent_id
                    if child_id == anchor
                    else None
                )
                if other is None:
                    continue
                row = next((item for item in self.rows if str(item["post_id"]) == other), None)
                if row is None:
                    continue
                if cutoff is not None and row["created_at"] > cutoff:
                    continue
                others.append({"other_id": other})
            return others
        if "array_position($2::uuid[], post_id)" in query:
            cutoff = args[3] if len(args) > 3 else None
            by_id = {str(row["post_id"]): row for row in self.rows}
            selected = []
            for post_id in args[1]:
                row = by_id.get(str(post_id))
                if row is None:
                    continue
                if cutoff is not None and row["created_at"] > cutoff:
                    continue
                selected.append(row)
            return selected[: args[2]]
        return []


def test_cutoff_uses_retained_revision_not_live_body() -> None:
    rows = [
        _row(
            "phoenix-post",
            title="Phoenix live rewrite",
            body="Live delivery window slipped to March.",
            created_at=_JANUARY,
            updated_at=_FEBRUARY,
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-january",
            "post_id": "phoenix-post",
            "post_title": "Phoenix January note",
            "post_body": "Phoenix kickoff completed in January.",
            "written_at": _JANUARY,
            "superseded_at": _FEBRUARY,
        }
    ]
    sources = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(rows, revisions),
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert [source.post_id for source in sources] == ["phoenix-post"]
    assert sources[0].post_title == "Phoenix January note"
    assert "January" in sources[0].post_body
    assert "March" not in sources[0].post_body
    assert sources[0].source_revision_id == "rev-january"
    assert sources[0].live_after_cutoff is True
    assert sources[0].historical_body_unavailable is False
    assert sources[0].knowledge_cutoff == _CUTOFF.isoformat()
    assert sources[0].evidence_facts == ()


def test_cutoff_excludes_posts_created_after_the_clock() -> None:
    rows = [
        _row(
            "late-post",
            title="Phoenix February note",
            body="Phoenix later status.",
            created_at=_FEBRUARY,
        )
    ]
    connection = _CutoffConnection(rows, [])
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert sources == []
    candidate_query, candidate_args = connection.calls[0]
    assert "source_post_revision" in candidate_query
    assert "created_at <= $3" in candidate_query
    assert candidate_args[2] == _CUTOFF
    source_query = next(query for query, _args in connection.calls if "array_position" in query)
    assert "created_at <= $4" in source_query


def test_cutoff_does_not_leak_current_semantic_facts() -> None:
    rows = [
        _row(
            "semantic-post",
            title="Operational note",
            body="No project name in this body.",
            created_at=_JANUARY,
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-ops",
            "post_id": "semantic-post",
            "post_title": "Operational note",
            "post_body": "No project name in this body.",
            "written_at": _JANUARY,
            "superseded_at": None,
        }
    ]
    connection = _CutoffConnection(
        rows,
        revisions,
        semantic_rows=[
            {
                "post_id": "semantic-post",
                "fact": "project: later invented project | ontology_iri: urn:test",
            }
        ],
    )
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: True,
            question="Operational",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert sources[0].evidence_facts == ()
    assert all("post_project_mention" not in query for query, _args in connection.calls)
    assert all("PHOENIX-LIVE" not in fact for fact in sources[0].evidence_facts)


def test_missing_historical_body_is_explicit_and_never_live() -> None:
    rows = [
        _row(
            "anchor-post",
            title="Phoenix January note",
            body="Phoenix kickoff completed in January.",
            created_at=_JANUARY,
        ),
        _row(
            "body-lost",
            title="Phoenix live only",
            body="This live rewrite must not become the cutoff body.",
            created_at=_JANUARY,
            updated_at=_FEBRUARY,
        ),
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-anchor",
            "post_id": "anchor-post",
            "post_title": "Phoenix January note",
            "post_body": "Phoenix kickoff completed in January.",
            "written_at": _JANUARY,
            "superseded_at": None,
        }
    ]
    sources = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(
                rows,
                revisions,
                lineage_edges=[("anchor-post", "body-lost")],
            ),
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
            limit=4,
        )
    )
    by_id = {source.post_id: source for source in sources}
    assert "body-lost" in by_id
    assert by_id["body-lost"].historical_body_unavailable is True
    assert by_id["body-lost"].post_body == ""
    assert "live rewrite" not in by_id["body-lost"].post_body
    assert historical_body_limitations(sources) == [
        {"post_id": "body-lost", "limitation_code": "historical_body_unavailable"}
    ]
    assert ask_grounding_status(sources, _CUTOFF) == PARTIALLY_CUTOFF_GROUNDED
    assert [event["post_id"] for event in global_ask_timeline(sources)] == [
        "anchor-post",
        "body-lost",
    ]


def test_naive_updated_at_is_compared_as_utc_at_cutoff() -> None:
    rows = [
        _row(
            "naive-clock-post",
            title="Phoenix live rewrite",
            body="Live rewrite",
            created_at=_JANUARY,
            updated_at=_FEBRUARY.replace(tzinfo=None),
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-naive-clock",
            "post_id": "naive-clock-post",
            "post_title": "Phoenix January note",
            "post_body": "January body",
            "written_at": _JANUARY,
            "superseded_at": _FEBRUARY,
        }
    ]
    sources = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(rows, revisions),
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert sources[0].live_after_cutoff is True


def test_two_cutoffs_select_revision_specific_citations() -> None:
    rows = [
        _row(
            "phoenix-post",
            title="Phoenix live rewrite",
            body="March window",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=_FEBRUARY,
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-early",
            "post_id": "phoenix-post",
            "post_title": "Phoenix kickoff",
            "post_body": "Kickoff body",
            "written_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "superseded_at": _JANUARY,
        },
        {
            "source_post_revision_id": "rev-mid",
            "post_id": "phoenix-post",
            "post_title": "Phoenix follow-up",
            "post_body": "Follow-up body",
            "written_at": _JANUARY,
            "superseded_at": _FEBRUARY,
        },
    ]
    first = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(rows, revisions),
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
    )
    second = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(rows, revisions),
            lambda _row: True,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert first[0].source_revision_id == "rev-early"
    assert first[0].post_title == "Phoenix kickoff"
    assert second[0].source_revision_id == "rev-mid"
    assert second[0].post_title == "Phoenix follow-up"
    citations = cited_post_citations(second, ["phoenix-post"])
    assert citations[0]["source_revision_id"] == "rev-mid"
    assert citations[0]["knowledge_cutoff"] == _CUTOFF.isoformat()


def test_live_query_without_cutoff_stays_backward_compatible() -> None:
    rows = [
        _row(
            "phoenix-post",
            title="Phoenix live rewrite",
            body="Live delivery window slipped to March.",
            created_at=_JANUARY,
            updated_at=_FEBRUARY,
        )
    ]
    connection = _CutoffConnection(
        rows,
        [],
        semantic_rows=[
            {"post_id": "phoenix-post", "fact": "project: live project | ontology_iri: urn:test"}
        ],
    )
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: True,
            question="Phoenix",
        )
    )
    assert sources[0].post_body.startswith("Live delivery")
    assert sources[0].knowledge_cutoff is None
    assert ask_grounding_status(sources, None) == LIVE_ONLY
    assert "created_at <= $2" not in connection.calls[0][0]
    assert "source_post_revision" not in connection.calls[0][0]


def test_live_rewrite_text_does_not_select_historical_post() -> None:
    rows = [
        _row(
            "phoenix-post",
            title="Phoenix classified patent",
            body="Classified patent window slipped to March.",
            created_at=_JANUARY,
            updated_at=_FEBRUARY,
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-january",
            "post_id": "phoenix-post",
            "post_title": "Phoenix kickoff",
            "post_body": "Phoenix kickoff completed in January.",
            "written_at": _JANUARY,
            "superseded_at": _FEBRUARY,
        }
    ]
    sources = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(rows, revisions),
            lambda _row: True,
            question="classified patent",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert sources == []


def test_unauthorized_historical_revisions_remain_unauthorized() -> None:
    rows = [
        _row(
            "hidden-post",
            title="Phoenix January note",
            body="Phoenix kickoff completed in January.",
            created_at=_JANUARY,
        )
    ]
    revisions = [
        {
            "source_post_revision_id": "rev-hidden",
            "post_id": "hidden-post",
            "post_title": "Phoenix January note",
            "post_body": "Phoenix kickoff completed in January.",
            "written_at": _JANUARY,
            "superseded_at": None,
        }
    ]
    connection = _CutoffConnection(rows, revisions)
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: False,
            question="Phoenix",
            knowledge_cutoff=_CUTOFF,
        )
    )
    assert sources == []
    covering_fetches = [
        args
        for query, args in connection.calls
        if "from source_post_revision" in query and "matched_in" not in query
    ]
    assert covering_fetches == []

def test_parse_cutoff_rejects_unparseable_clocks() -> None:
    try:
        parse_as_of_clock("not-a-clock")
    except ValueError:
        return
    raise AssertionError("unparseable knowledge_cutoff must fail closed")


def test_ask_next_action_never_calls_live_only_an_as_of_answer() -> None:
    live = ChatSourceDocument("post-1", "Live", "body")
    assert ask_grounding_status([live], None) == LIVE_ONLY
    assert "as-of" not in ask_next_action(LIVE_ONLY, has_sources=True).lower()
    assert "cutoff" not in ask_next_action(LIVE_ONLY, has_sources=True).lower()
    unavailable = ChatSourceDocument(
        "post-1",
        "Lost",
        "",
        historical_body_unavailable=True,
        knowledge_cutoff=_CUTOFF.isoformat(),
    )
    assert ask_grounding_status([unavailable], _CUTOFF) == PARTIALLY_CUTOFF_GROUNDED
    retained = ChatSourceDocument(
        "post-1",
        "Kept",
        "January body",
        knowledge_cutoff=_CUTOFF.isoformat(),
    )
    assert ask_grounding_status([retained], _CUTOFF) == FULLY_CUTOFF_GROUNDED


def test_ask_next_action_names_when_no_historical_body_was_retained() -> None:
    assert "no historical source bodies" in ask_next_action(
        PARTIALLY_CUTOFF_GROUNDED,
        has_sources=True,
        has_retained_bodies=False,
    ).lower()
