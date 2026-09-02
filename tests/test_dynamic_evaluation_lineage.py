"""Contracts for dynamic-evaluation provenance projections."""

from __future__ import annotations

import pytest

from lineageweave.evaluation_lineage import (
    DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
    DynamicEvaluationItemLineage,
    DynamicEvaluationLineageError,
    DynamicEvaluationRunLineage,
    RunComparabilityStatus,
    build_dynamic_evaluation_item_lineage,
    build_dynamic_evaluation_run_lineage,
)

_CONTRACT_DIGEST = "a" * 64


def _item(
    *,
    item_snapshot_ref: str = "evaluation_item_snapshot_alpha",
    adjudication_case_ref: str | None = None,
    adjudication_resolution_ref: str | None = None,
    calibration_artifact_refs: tuple[str, ...] = (),
    anchor_promotion_decision_ref: str | None = None,
    supersedes_item_snapshot_ref: str | None = None,
) -> DynamicEvaluationItemLineage:
    """Build one item lineage through the public admission boundary."""
    return build_dynamic_evaluation_item_lineage(
        item_snapshot_ref=item_snapshot_ref,
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        source_contract_ref="fast_mlsirm_dynamic_evaluation_item/v1",
        source_contract_sha256=_CONTRACT_DIGEST,
        generation_invocation_ref="generation_invocation_1",
        rater_invocation_refs=("rater_invocation_1", "rater_invocation_2"),
        adjudication_case_ref=adjudication_case_ref,
        adjudication_resolution_ref=adjudication_resolution_ref,
        calibration_artifact_refs=calibration_artifact_refs,
        anchor_promotion_decision_ref=anchor_promotion_decision_ref,
        supersedes_item_snapshot_ref=supersedes_item_snapshot_ref,
    )


def test_zero_anchor_run_is_representable_without_linking_claim() -> None:
    """A dynamic run may have no fixed anchors while exposing that comparability limit."""
    run = build_dynamic_evaluation_run_lineage(
        run_snapshot_ref="evaluation_run_snapshot_1",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        items=(_item(),),
        anchor_item_snapshot_refs=(),
        comparability_status=RunComparabilityStatus.UNAVAILABLE,
    )

    assert run.contract_id == DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID
    assert run.anchor_item_snapshot_refs == ()
    assert run.comparability_status is RunComparabilityStatus.UNAVAILABLE

    within_run = build_dynamic_evaluation_run_lineage(
        run_snapshot_ref="evaluation_run_snapshot_2",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        items=(_item(),),
        anchor_item_snapshot_refs=(),
        comparability_status=RunComparabilityStatus.WITHIN_RUN_ONLY,
    )
    assert within_run.comparability_status is RunComparabilityStatus.WITHIN_RUN_ONLY

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_3",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(_item(),),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.LINKED,
            linking_evidence_ref="linking_evidence_1",
        )
    assert caught.value.code == "linked_run_requires_anchor"


def test_adjudication_resolution_is_separate_from_source_observations() -> None:
    """A resolution references a case and never replaces immutable rater invocations."""
    item = _item(
        adjudication_case_ref="adjudication_case_1",
        adjudication_resolution_ref="adjudication_resolution_1",
    )
    assert item.rater_invocation_refs == (
        "rater_invocation_1",
        "rater_invocation_2",
    )
    assert item.adjudication_case_ref == "adjudication_case_1"
    assert item.adjudication_resolution_ref == "adjudication_resolution_1"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        _item(adjudication_resolution_ref="adjudication_resolution_1")
    assert caught.value.code == "resolution_requires_case"


def test_adjudication_alone_cannot_promote_an_anchor() -> None:
    """Anchor projection requires a separate promotion decision and calibration evidence."""
    adjudicated = _item(
        adjudication_case_ref="adjudication_case_1",
        adjudication_resolution_ref="adjudication_resolution_1",
    )
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_1",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(adjudicated,),
            anchor_item_snapshot_refs=(adjudicated.item_snapshot_ref,),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "anchor_requires_promotion_evidence"

    promoted = _item(
        adjudication_case_ref="adjudication_case_1",
        adjudication_resolution_ref="adjudication_resolution_1",
        calibration_artifact_refs=("calibration_artifact_1",),
        anchor_promotion_decision_ref="anchor_promotion_decision_1",
    )
    run = build_dynamic_evaluation_run_lineage(
        run_snapshot_ref="evaluation_run_snapshot_2",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        items=(promoted,),
        anchor_item_snapshot_refs=(promoted.item_snapshot_ref,),
        comparability_status=RunComparabilityStatus.LINKED,
        linking_evidence_ref="linking_evidence_1",
    )
    assert run.anchor_item_snapshot_refs == (promoted.item_snapshot_ref,)


def test_lineage_rejects_provider_configuration_and_decision_payload_fields() -> None:
    """Lineage projection cannot absorb provider credentials, endpoints, scores, or decisions."""
    payload = {
        "contract_id": DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
        "run_snapshot_ref": "evaluation_run_snapshot_1",
        "blueprint_revision_ref": "evaluation_blueprint_revision_1",
        "items": [
            {
                "item_snapshot_ref": "evaluation_item_snapshot_alpha",
                "blueprint_revision_ref": "evaluation_blueprint_revision_1",
                "source_contract_ref": "fast_mlsirm_dynamic_evaluation_item/v1",
                "source_contract_sha256": _CONTRACT_DIGEST,
                "generation_invocation_ref": "generation_invocation_1",
                "rater_invocation_refs": ["rater_invocation_1"],
                "adjudication_case_ref": None,
                "adjudication_resolution_ref": None,
                "calibration_artifact_refs": [],
                "anchor_promotion_decision_ref": None,
                "supersedes_item_snapshot_ref": None,
            }
        ],
        "anchor_item_snapshot_refs": [],
        "comparability_status": "unavailable",
        "linking_evidence_ref": None,
        "provider_api_key": "secret",
    }
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationRunLineage.from_mapping(payload)
    assert caught.value.code == "authority_leakage"

    payload.pop("provider_api_key")
    payload["score"] = 1.0
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationRunLineage.from_mapping(payload)
    assert caught.value.code == "authority_leakage"


def test_run_freezes_unique_items_and_anchor_references() -> None:
    """Run lineage is an immutable projection over one unique blueprint-bound item set."""
    first = _item()
    second = _item(item_snapshot_ref="evaluation_item_snapshot_beta")
    source = [first, second]
    run = build_dynamic_evaluation_run_lineage(
        run_snapshot_ref="evaluation_run_snapshot_1",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        items=source,
        anchor_item_snapshot_refs=(),
        comparability_status=RunComparabilityStatus.WITHIN_RUN_ONLY,
    )
    source.pop()
    assert run.items == (first, second)

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_duplicate",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(first, first),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "duplicate_item_snapshot"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_unknown_anchor",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(first,),
            anchor_item_snapshot_refs=("evaluation_item_snapshot_missing",),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "unknown_anchor_item"


def test_supersession_cannot_point_to_self() -> None:
    """A lineage successor cannot claim to supersede its own item snapshot identity."""
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        _item(supersedes_item_snapshot_ref="evaluation_item_snapshot_alpha")
    assert caught.value.code == "self_supersession"


def test_direct_aggregate_construction_is_sealed() -> None:
    """Only builders may produce admitted item and run projections."""
    with pytest.raises(ValueError, match="build_dynamic_evaluation_item_lineage"):
        DynamicEvaluationItemLineage(  # type: ignore[call-arg]
            item_snapshot_ref="evaluation_item_snapshot_alpha",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            source_contract_ref="fast_mlsirm_dynamic_evaluation_item/v1",
            source_contract_sha256=_CONTRACT_DIGEST,
            generation_invocation_ref="generation_invocation_1",
            rater_invocation_refs=("rater_invocation_1",),
            adjudication_case_ref=None,
            adjudication_resolution_ref=None,
            calibration_artifact_refs=(),
            anchor_promotion_decision_ref=None,
            supersedes_item_snapshot_ref=None,
        )

    with pytest.raises(ValueError, match="build_dynamic_evaluation_run_lineage"):
        DynamicEvaluationRunLineage(  # type: ignore[call-arg]
            run_snapshot_ref="evaluation_run_snapshot_1",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(_item(),),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
            linking_evidence_ref=None,
        )
