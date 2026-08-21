"""Project history projections preserve authority, chronology, and gaps."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.project_history_api import ProjectHistoryProjection
from lineageweave.project_history import (
    _prior_paths,
    _normalized_matches,
    _score,
    build_project_history_projection,
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


def event(post_id: str, title: str, day: int, **extra: object) -> dict[str, object]:
    """Return one already-authorized source row."""

    return {
        "post_id": post_id,
        "post_title": title,
        "created_at": datetime(2026, 1, day, 9, tzinfo=timezone.utc),
        "voc_type_code": "vom",
        "source_stage_code": None,
        "source_detail_state_code": None,
        **extra,
    }


def match(post_id: str, kind: str = "source_project_code", value: str = "P-100") -> dict[str, object]:
    """Return one matching explicit or semantic project fact."""

    return {
        "post_id": post_id,
        "match_kind_code": kind,
        "matched_value": value,
        "confidence": None if kind.startswith("source_") else 0.91,
        "ontology_iri": None if kind.startswith("source_") else "https://w3id.org/lineageweave#Project",
        "provenance": kind,
    }


def role(post_id: str, name: str, person_id: str | None) -> dict[str, object]:
    """Return one observed R&R row."""

    return {
        "post_id": post_id,
        "actor_name": name,
        "responsibility": "Own the event",
        "actor_type_code": "prov_person",
        "affiliated_organization_name": "Demo Corp",
        "cataloged_person_id": person_id,
        "cataloged_team_id": None,
        "cataloged_corporate_entity_id": None,
    }


def test_normalization_and_display_classification_are_deterministic() -> None:
    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert classify_project_event(
        title="Specification revision requested",
        source_stage_code=None,
        source_detail_state_code=None,
        voc_type_code="vom",
        is_focus=False,
    ) == "specification_changed"
    assert classify_project_event(
        title="Account note",
        source_stage_code=None,
        source_detail_state_code=None,
        voc_type_code="voc",
        is_focus=False,
    ) == "source_recorded"
    assert classify_project_event(
        title="Account note",
        source_stage_code=None,
        source_detail_state_code=None,
        voc_type_code="voc",
        is_focus=True,
    ) == "voc_received"
    with pytest.raises(ValueError, match="empty"):
        normalize_project_key("  ")


def test_responsibility_transition_does_not_invent_assignment_facts() -> None:
    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code([], ["person:b"]) == "assignment_gap"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"


def test_projection_deduplicates_matches_and_explains_visible_prior_paths() -> None:
    events = [
        event("voc", "VOC received", 4, voc_type_code="voc"),
        event("award", "Contract awarded", 1),
        event("spec", "Specification revision requested", 2),
        event("delivery", "Delivery confirmed", 3),
        event("spec", "Duplicate transport row", 2),
    ]
    matches = [
        match("award"),
        match("award", "semantic_project_key"),
        match("spec"),
        match("delivery", "semantic_project_name", "Ｐ－１００"),
        match("voc"),
        match("voc"),
    ]
    roles = [
        role("award", "Ada", "person-a"),
        role("spec", "Ada", "person-a"),
        role("delivery", "Priya", "person-b"),
    ]
    edges = [
        {"parent_post_id": "award", "child_post_id": "spec", "fused_score": 0.91},
        {"parent_post_id": "spec", "child_post_id": "delivery", "fused_score": 0.82},
        {"parent_post_id": "delivery", "child_post_id": "voc", "fused_score": 0.73},
        {"parent_post_id": "voc", "child_post_id": "award", "fused_score": 0.99},
        {"parent_post_id": "hidden", "child_post_id": "voc", "fused_score": 1.0},
    ]

    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id="voc",
        event_rows=events,
        match_rows=matches,
        role_rows=roles,
        edge_rows=edges,
    )
    validated = ProjectHistoryProjection.model_validate(projection)

    assert validated.focus_event_id == "voc"
    assert validated.time_basis_code == "document_time"
    assert normalize_project_key(validated.project_name) == "p-100"

    assert [item["event_id"] for item in projection["events"]] == [
        "award",
        "spec",
        "delivery",
        "voc",
    ]
    assert projection["event_count"] == 4
    assert projection["distinct_observed_actor_count"] == 2
    assert [item["responsibility_transition_code"] for item in projection["events"]] == [
        None,
        "continuous",
        "handoff",
        "assignment_gap",
    ]
    assert len(projection["events"][0]["project_matches"]) == 2
    assert len(projection["events"][3]["project_matches"]) == 1

    voc_paths = projection["events"][3]["related_prior_paths"]
    assert [path["source_event_id"] for path in voc_paths] == ["delivery", "spec", "award"]
    assert voc_paths[-1]["event_ids"] == ["award", "spec", "delivery", "voc"]
    assert voc_paths[-1]["minimum_fused_score"] == pytest.approx(0.73)
    assert all(path["truth_status_code"] == "inferred" for path in voc_paths)
    assert all("hidden" not in path["event_ids"] for path in voc_paths)


def test_projection_rejects_invisible_focus_and_out_of_bound_options() -> None:
    rows = [event("award", "Contract awarded", 1)]
    with pytest.raises(ValueError, match="focus"):
        build_project_history_projection(
            project_key="P-100",
            focus_event_id="hidden",
            event_rows=rows,
            match_rows=[match("award")],
            role_rows=[],
            edge_rows=[],
        )
    with pytest.raises(ValueError, match="maximum_depth"):
        build_project_history_projection(
            project_key="P-100",
            focus_event_id="award",
            event_rows=rows,
            match_rows=[match("award")],
            role_rows=[],
            edge_rows=[],
            maximum_depth=0,
        )


def test_projection_rejects_oversized_keys_and_invalid_scores() -> None:
    """Identity and numeric trust boundaries fail before producing evidence."""

    with pytest.raises(ValueError, match="exceeds"):
        normalize_project_key("x" * 257)
    with pytest.raises(ValueError, match="numeric"):
        _score(True)
    with pytest.raises(ValueError, match="finite"):
        _score(float("inf"))
    assert not _normalized_matches(None, "p-100")


def test_projection_handles_dag_depth_path_and_unbound_child_edges() -> None:
    """Bounded path traversal remains deterministic at depth and path limits."""

    bounded = _prior_paths(
        ["a", "b", "c"],
        [
            {"parent_post_id": "a", "child_post_id": "b", "fused_score": 0.9},
            {"parent_post_id": "a", "child_post_id": "c", "fused_score": 0.8},
            {"parent_post_id": "b", "child_post_id": "c", "fused_score": 0.7},
            {"parent_post_id": "unknown", "child_post_id": "c", "fused_score": 1.0},
        ],
        maximum_depth=1,
        maximum_paths_per_event=1,
    )
    assert len(bounded["c"]) == 1
    depth_limited = _prior_paths(
        ["a", "b", "c"],
        [{"parent_post_id": "a", "child_post_id": "b", "fused_score": 0.9}],
        maximum_depth=1,
        maximum_paths_per_event=32,
    )
    assert depth_limited["b"]

    diamond = _prior_paths(
        ["a", "b", "c"],
        [
            {"parent_post_id": "a", "child_post_id": "b", "fused_score": 0.9},
            {"parent_post_id": "a", "child_post_id": "c", "fused_score": 0.8},
            {"parent_post_id": "b", "child_post_id": "c", "fused_score": 0.7},
        ],
        maximum_depth=8,
        maximum_paths_per_event=32,
    )
    assert [path["source_event_id"] for path in diamond["c"]] == ["a", "b"]


def test_projection_discards_unbound_matches_and_roles() -> None:
    """Rows outside the visible event set or exact identity never leak in."""

    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=None,
        event_rows=[event("visible", "Account note", 1)],
        match_rows=[
            {**match("hidden"), "identity_key": "P-100"},
            {**match("visible"), "identity_key": "P-200"},
            {**match("visible"), "identity_key": "x" * 257},
        ],
        role_rows=[
            {
                **role("hidden", "Hidden", None),
                "cataloged_team_id": "team-1",
            },
            {
                **role("visible", "Team", None),
                "cataloged_team_id": "team-1",
            },
            role("visible", "Text", None),
        ],
        edge_rows=[],
    )
    assert projection["focus_event_id"] == "visible"
    assert projection["events"][0]["project_matches"] == []
    actor_keys = {
        item["actor_key"] for item in projection["events"][0]["observed_responsibilities"]
    }
    assert "team:team-1" in actor_keys
    assert any(key.startswith("text:") for key in actor_keys)

    with pytest.raises(ValueError, match="maximum_paths"):
        build_project_history_projection(
            project_key="P-100",
            focus_event_id="visible",
            event_rows=[event("visible", "Account note", 1)],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
            maximum_paths_per_event=0,
        )
    with pytest.raises(ValueError, match="at least one"):
        build_project_history_projection(
            project_key="P-100",
            focus_event_id=None,
            event_rows=[],
            match_rows=[],
            role_rows=[],
            edge_rows=[],
        )
