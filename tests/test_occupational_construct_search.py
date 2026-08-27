"""Authorized occupational construct catalog search (ADR 0256)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from backend.app.occupational_construct_search import (
    CONSTRUCT_IRI_PREFIX,
    CANDIDATE_ROW_LIMIT,
    OccupationalConstructSearchError,
    like_contains_pattern,
    normalize_construct_search_cursor,
    normalize_construct_search_family,
    normalize_construct_search_limit,
    normalize_construct_search_query,
    search_page_to_payload,
    search_visible_occupational_constructs,
)

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
HIDDEN_POST_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CONSTRUCT_ID = "99999999-9999-9999-9999-999999999999"
CONSTRUCT_IRI = f"{CONSTRUCT_IRI_PREFIX}1.A.1.a.1"
LATER_IRI = f"{CONSTRUCT_IRI_PREFIX}1.A.1.b.2"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)


class RecordingConnection:
    """Record parameterized search SQL without a database."""

    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.calls.append((" ".join(query.split()), args))
        return self.rows


def _row(
    *,
    construct_id: str = CONSTRUCT_ID,
    construct_iri: str = CONSTRUCT_IRI,
    family: str = "cognitive_ability",
    label: str = "Oral Comprehension",
    post_id: str = POST_ID,
    title: str = "Synthetic briefing",
    visibility: str = "visibility_public",
    evidence: str = "reviewed the written procedure",
    truth: str = "truth_inferred",
    available_at: datetime = T0,
) -> dict[str, object]:
    return {
        "construct_id": construct_id,
        "construct_iri": construct_iri,
        "construct_family_code": family,
        "preferred_label": label,
        "version_label": "31.0",
        "post_id": post_id,
        "post_title": title,
        "visibility_code": visibility,
        "corporate_entity_id": None,
        "process_unit_id": None,
        "evidence_text": evidence,
        "truth_status_code": truth,
        "available_at": available_at,
    }


def _public(row: object) -> bool:
    mapping = row if isinstance(row, dict) else {}
    return mapping.get("visibility_code") == "visibility_public"


def test_like_pattern_escapes_metacharacters() -> None:
    assert like_contains_pattern("100%") == r"%100\%%"
    assert like_contains_pattern("a_b") == r"%a\_b%"
    assert like_contains_pattern(r"path\name") == r"%path\\name%"


def test_query_family_cursor_and_limit_fail_closed() -> None:
    with pytest.raises(OccupationalConstructSearchError, match="two or more"):
        normalize_construct_search_query(" a ")
    with pytest.raises(OccupationalConstructSearchError, match="Shorten"):
        normalize_construct_search_query("x" * 81)
    with pytest.raises(OccupationalConstructSearchError, match="cognitive ability"):
        normalize_construct_search_family("affective_reaction")
    with pytest.raises(OccupationalConstructSearchError, match="catalog IRI"):
        normalize_construct_search_cursor("after:secret")
    with pytest.raises(OccupationalConstructSearchError, match="1 and 50"):
        normalize_construct_search_limit(0)
    assert normalize_construct_search_family("") is None
    assert normalize_construct_search_cursor(CONSTRUCT_IRI) == CONSTRUCT_IRI


def test_visible_substring_hit_opens_supporting_post() -> None:
    conn = RecordingConnection([_row()])
    page = asyncio.run(
        search_visible_occupational_constructs(
            conn, query="  Oral  ", can_see_post=_public
        )
    )
    assert len(page.hits) == 1
    hit = page.hits[0]
    assert hit.preferred_label == "Oral Comprehension"
    assert hit.supporting_post_id == POST_ID
    assert hit.evidence_text == "reviewed the written procedure"
    assert "score" not in search_page_to_payload(page)
    sql, args = conn.calls[0]
    assert "ilike $1 escape E" in sql
    assert "post_occupational_construct_assertion" in sql
    assert args[0] == like_contains_pattern("Oral")
    assert args[4] == CANDIDATE_ROW_LIMIT


def test_hidden_post_does_not_create_a_catalog_hit() -> None:
    conn = RecordingConnection(
        [_row(post_id=HIDDEN_POST_ID, visibility="visibility_private")]
    )
    page = asyncio.run(
        search_visible_occupational_constructs(
            conn, query="Oral", can_see_post=_public
        )
    )
    assert page.hits == ()
    assert page.next_cursor is None


def test_truth_conflict_and_withdrawn_status_omit_the_construct() -> None:
    conflict = RecordingConnection(
        [
            _row(truth="truth_inferred"),
            _row(truth="truth_observed", post_id=HIDDEN_POST_ID),
            _row(post_id="cccccccc-cccc-cccc-cccc-ccccccccccc1", truth="truth_proposed"),
        ]
    )
    page = asyncio.run(
        search_visible_occupational_constructs(
            conflict, query="Oral", can_see_post=_public
        )
    )
    assert page.hits == ()

    withdrawn = RecordingConnection([_row(truth="truth_rejected")])
    omitted = asyncio.run(
        search_visible_occupational_constructs(
            withdrawn, query="Oral", can_see_post=_public
        )
    )
    assert omitted.hits == ()


def test_keyset_cursor_and_family_filter_are_parameterized() -> None:
    conn = RecordingConnection(
        [_row(construct_iri=LATER_IRI, family="work_style", label="Adaptability")]
    )
    page = asyncio.run(
        search_visible_occupational_constructs(
            conn,
            query="Adapt",
            family_code="work_style",
            cursor=CONSTRUCT_IRI,
            knowledge_cutoff=T0,
            can_see_post=_public,
        )
    )
    sql, args = conn.calls[0]
    assert args[1] == "work_style"
    assert args[2] == CONSTRUCT_IRI
    assert args[3] == T0
    assert "construct.construct_iri > $3" in sql
    assert page.hits[0].construct_family_code == "work_style"


def test_payload_omits_internal_extraction_and_hidden_counts() -> None:
    page = asyncio.run(
        search_visible_occupational_constructs(
            RecordingConnection([_row()]),
            query="Oral",
            can_see_post=_public,
        )
    )
    payload = search_page_to_payload(page)
    hit = payload["hits"][0]
    assert set(hit) == {
        "construct_id",
        "construct_iri",
        "construct_family_code",
        "preferred_label",
        "vocabulary_version",
        "supporting_post_id",
        "supporting_post_title",
        "evidence_text",
        "truth_status_code",
    }
    assert "extraction_method" not in hit
    assert "omitted_count" not in payload
    assert payload["next_cursor"] is None
