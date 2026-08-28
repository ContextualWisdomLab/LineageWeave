"""RED contracts for the customer-facing project-history timeline."""

from __future__ import annotations

import pytest

from lineageweave.project_history import (
    _prior_paths,
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


def test_project_identity_is_exact_but_unicode_compatible() -> None:
    """Compatibility forms may normalize; fuzzy project binding may not."""
    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert normalize_project_key("P-100-A") != normalize_project_key("P-100")
    with pytest.raises(ValueError):
        normalize_project_key("   ")


def test_event_display_classification_uses_only_controlled_evidence() -> None:
    """Free text cannot manufacture a lifecycle event classification."""
    assert (
        classify_project_event(
            title="Contract awarded",
            source_stage_code=None,
            source_detail_state_code=None,
            voc_type_code=None,
            is_focus=False,
        )
        == "source_recorded"
    )
    for is_focus in (False, True):
        assert (
            classify_project_event(
                title="Field complaint received",
                source_stage_code=None,
                source_detail_state_code=None,
                voc_type_code="voc",
                is_focus=is_focus,
            )
            == "voc_received"
        )


def test_responsibility_transition_describes_document_evidence_only() -> None:
    """Missing adjacent evidence is a visible evidence gap, not an HR fact."""
    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"


def test_prior_paths_keep_the_first_deterministic_shortest_route_per_predecessor() -> None:
    """A tied route reports one stable path for a prior event rather than duplicate history."""
    paths = _prior_paths(
        ["award", "spec-a", "spec-b", "delivery"],
        [
            {
                "parent_post_id": "award",
                "child_post_id": "spec-a",
                "fused_score": 0.9,
                "temporal_observed": True,
                "allen_relations": ["before"],
                "artifact_digest_sha256": "a" * 64,
            },
            {"parent_post_id": "award", "child_post_id": "spec-b", "fused_score": 0.8},
            {"parent_post_id": "spec-a", "child_post_id": "delivery", "fused_score": 0.7},
            {"parent_post_id": "spec-b", "child_post_id": "delivery", "fused_score": 0.6},
        ],
        maximum_depth=8,
        maximum_paths_per_event=32,
    )

    award_paths = [path for path in paths["delivery"] if path["source_event_id"] == "award"]
    assert [path["event_ids"] for path in award_paths] == [["award", "spec-a", "delivery"]]
    assert award_paths[0]["edges"][0]["temporal_evidence"] == {
        "truth_status_code": "observed",
        "interval_relations": ["before"],
        "artifact_digest_sha256": "a" * 64,
    }
    assert award_paths[0]["edges"][1]["temporal_evidence"] is None
