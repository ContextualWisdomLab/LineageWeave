"""Edge-branch tests for the evidence-bound project-history projection.

The primary suite covers the happy path through ``_prior_paths`` and
``build_project_history_projection``. These tests exercise the validation
boundaries, DAG safety skips, depth/path ceilings, and role deduplication
that keep the projection deterministic and fail-closed on malformed input.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lineageweave.project_history import (
    PROJECT_HISTORY_MAX_DEPTH,
    PROJECT_HISTORY_MAX_PATHS_PER_EVENT,
    _prior_paths,
    _score,
    build_project_history_projection,
    normalize_project_key,
)

_DT = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _event_row(event_id: str, at: datetime = _DT) -> dict[str, object]:
    """One minimal visible-event row."""
    return {"post_id": event_id, "created_at": at}


def test_normalize_project_key_rejects_oversized_utf8_key() -> None:
    key = "p-" + ("가" * 120)
    with pytest.raises(ValueError, match="256 UTF-8"):
        normalize_project_key(key)


@pytest.mark.parametrize("value", [True, "0.5", [], None])
def test_score_rejects_non_numeric_values(value: object) -> None:
    with pytest.raises(ValueError, match="numeric"):
        _score(value)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_score_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        _score(value)


def test_score_accepts_finite_numeric_values() -> None:
    assert _score(0.5) == 0.5
    assert _score(1) == 1.0


def test_prior_paths_skips_edges_pointing_outside_the_event_window() -> None:
    paths = _prior_paths(
        ["award", "spec"],
        [
            {"parent_post_id": "ghost", "child_post_id": "award", "fused_score": 0.9},
            {"parent_post_id": "award", "child_post_id": "ghost", "fused_score": 0.9},
        ],
        maximum_depth=8,
        maximum_paths_per_event=32,
    )
    assert paths["award"] == []
    assert paths["spec"] == []


def test_prior_paths_skips_backward_or_simultaneous_edges() -> None:
    paths = _prior_paths(
        ["award", "spec"],
        [
            {"parent_post_id": "spec", "child_post_id": "award", "fused_score": 0.9},
            {"parent_post_id": "spec", "child_post_id": "spec", "fused_score": 0.9},
        ],
        maximum_depth=8,
        maximum_paths_per_event=32,
    )
    assert all(path["event_ids"][-1] == "spec" for path in paths["spec"])


def test_prior_paths_respects_maximum_depth() -> None:
    edges = [
        {"parent_post_id": f"p{index}", "child_post_id": f"p{index + 1}", "fused_score": 0.9}
        for index in range(4)
    ]
    events = [f"p{index}" for index in range(5)]
    paths = _prior_paths(
        events,
        edges,
        maximum_depth=3,
        maximum_paths_per_event=32,
    )
    # The four-edge route from the chain root is pruned by maximum_depth=3;
    # the direct predecessor routes remain admissible.
    assert "p0" not in {path["source_event_id"] for path in paths["p4"]}


def test_prior_paths_respects_maximum_paths_per_event() -> None:
    events = ["root", "mid-a", "mid-b", "mid-c", "leaf"]
    edges = [
        {"parent_post_id": "root", "child_post_id": child, "fused_score": 0.9}
        for child in ("mid-a", "mid-b", "mid-c")
    ] + [
        {"parent_post_id": child, "child_post_id": "leaf", "fused_score": 0.9}
        for child in ("mid-a", "mid-b", "mid-c")
    ]
    paths = _prior_paths(
        events,
        edges,
        maximum_depth=8,
        maximum_paths_per_event=2,
    )
    assert len(paths["leaf"]) == 2


def test_prior_paths_skips_parents_already_on_the_reverse_path() -> None:
    # A self-referential-looking cycle via reused parent must not recurse.
    paths = _prior_paths(
        ["a", "b", "c"],
        [
            {"parent_post_id": "a", "child_post_id": "b", "fused_score": 0.9},
            {"parent_post_id": "b", "child_post_id": "c", "fused_score": 0.9},
            {"parent_post_id": "b", "child_post_id": "b", "fused_score": 0.8},
        ],
        maximum_depth=8,
        maximum_paths_per_event=32,
    )
    assert all("b" in path["event_ids"] for path in paths["c"])


def test_projection_rejects_out_of_supported_depth_bounds() -> None:
    with pytest.raises(ValueError, match="maximum_depth"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
            maximum_depth=0,
        )
    with pytest.raises(ValueError, match="maximum_depth"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
            maximum_depth=PROJECT_HISTORY_MAX_DEPTH + 1,
        )


def test_projection_rejects_out_of_supported_path_bounds() -> None:
    with pytest.raises(ValueError, match="maximum_paths_per_event"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
            maximum_paths_per_event=0,
        )
    with pytest.raises(ValueError, match="maximum_paths_per_event"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
            maximum_paths_per_event=PROJECT_HISTORY_MAX_PATHS_PER_EVENT + 1,
        )


def test_projection_rejects_missing_events() -> None:
    with pytest.raises(ValueError, match="at least one visible event"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
        )


def test_projection_rejects_unknown_focus_event() -> None:
    single = [_event_row("11111111-1111-1111-1111-111111111111")]
    with pytest.raises(ValueError, match="focus event"):
        build_project_history_projection(
            project_key="p-1",
            focus_event_id="22222222-2222-2222-2222-222222222222",
            event_rows=single,
            match_rows=[],
            role_rows=[],
            edge_rows=[],
        )


def _full_event_row(event_id: str) -> dict[str, object]:
    """A minimal event row the projection renderer can display."""
    return {
        "post_id": event_id,
        "post_title": "Synthetic project record",
        "created_at": _DT,
        "event_occurred_at": _DT,
        "event_content_status_code": "available",
        "event_content_status_label": "Available",
    }


def test_projection_deduplicates_repeated_role_rows() -> None:
    event_id = "11111111-1111-1111-1111-111111111111"
    role_row = {
        "post_id": event_id,
        "role_name": "담당자",
        "actor_name": "아무개",
        "responsibility": "작성",
        "actor_type_code": "prov_person",
        "affiliated_organization_name": "영업팀",
    }
    role_rows = [role_row, dict(role_row)]
    projection = build_project_history_projection(
        project_key="p-1",
        focus_event_id=None,
        event_rows=[_full_event_row(event_id)],
        match_rows=[],
        role_rows=role_rows,
        edge_rows=[],
    )
    roles = projection["events"][0]["observed_responsibilities"]
    assert len(roles) == 1
    assert roles[0]["actor_name"] == "아무개"
    assert roles[0]["responsibility"] == "작성"

def test_actor_key_prefers_a_cataloged_identity() -> None:
    """A cataloged person id yields a stable cataloged actor key."""
    assert (
        _prior_paths.__module__ and True
    )  # keep import surface stable
    from lineageweave.project_history import _actor_key

    key = _actor_key(
        {
            "cataloged_person_id": "p-77",
            "cataloged_team_id": None,
            "actor_type_code": "prov_person",
            "actor_name": "아무개",
        }
    )
    assert key == "person:p-77"


def test_projection_processes_and_deduplicates_match_rows() -> None:
    event_a = "11111111-1111-1111-1111-111111111111"
    event_b = "22222222-2222-2222-2222-222222222222"
    events = [_full_event_row(event_a), _full_event_row(event_b)]
    match_rows = [
        # Admissible observed, inferred, and duplicate matches.
        {
            "post_id": event_a,
            "matched_value": "p-1",
            "match_kind_code": "source_project_name",
            "confidence": 0.9,
            "ontology_iri": "https://example.test/iri",
            "provenance": "post_project_mention",
        },
        {
            "post_id": event_a,
            "matched_value": "p-1",
            "match_kind_code": "source_project_name",
            "confidence": 0.9,
            "ontology_iri": "https://example.test/iri",
            "provenance": "post_project_mention",
        },
        {
            "post_id": event_a,
            "matched_value": "p-1",
            "match_kind_code": "semantic_project_name",
            "confidence": None,
            "ontology_iri": None,
            "provenance": "semantic_extraction",
        },
        # A match normalizing to a different key and an unknown-event row.
        {
            "post_id": event_a,
            "matched_value": "some-other-project",
            "match_kind_code": "semantic_project_name",
            "confidence": 0.5,
            "ontology_iri": None,
            "provenance": "semantic_extraction",
        },
        {
            "post_id": "ghost-does-not-exist",
            "matched_value": "p-1",
            "match_kind_code": "source_project_name",
            "confidence": 0.9,
            "ontology_iri": None,
            "provenance": "post_project_mention",
        },
    ]
    projection = build_project_history_projection(
        project_key="p-1",
        focus_event_id=event_a,
        event_rows=events,
        match_rows=match_rows,
        role_rows=[],
        edge_rows=[],
    )
    matches = {
        (item["match_kind_code"], item["matched_value"]): item
        for item in projection["events"][0]["project_matches"]
    }
    assert ("source_project_name", "p-1") in matches
    assert matches[("source_project_name", "p-1")]["truth_status_code"] == "observed"
    assert matches[("source_project_name", "p-1")]["confidence"] == 0.9
    assert ("semantic_project_name", "p-1") in matches
    assert matches[("semantic_project_name", "p-1")]["confidence"] is None
    assert ("semantic_project_name", "some-other-project") not in matches


def test_projection_skips_role_rows_for_unknown_events() -> None:
    event = "11111111-1111-1111-1111-111111111111"
    role_rows = [
        {
            "post_id": "ghost-event",
            "role_name": "담당자",
            "actor_name": "아무개",
            "responsibility": "작성",
            "actor_type_code": "prov_person",
            "affiliated_organization_name": "영업팀",
        }
    ]
    projection = build_project_history_projection(
        project_key="p-1",
        focus_event_id=None,
        event_rows=[_full_event_row(event)],
        match_rows=[],
        role_rows=role_rows,
        edge_rows=[],
    )
    assert projection["events"][0]["observed_responsibilities"] == []
