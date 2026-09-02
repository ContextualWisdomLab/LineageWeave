"""Fail-closed boundaries for dynamic evaluation lineage projections."""

from __future__ import annotations

from typing import Any

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

_DIGEST = "a" * 64


def _item(**overrides: Any) -> DynamicEvaluationItemLineage:
    payload: dict[str, Any] = {
        "item_snapshot_ref": "evaluation_item_snapshot_alpha",
        "blueprint_revision_ref": "evaluation_blueprint_revision_1",
        "source_contract_ref": "synthetic_source_contract/v1",
        "source_contract_sha256": _DIGEST,
        "generation_invocation_ref": "generation_invocation_1",
        "rater_invocation_refs": ("rater_invocation_1",),
        "adjudication_case_ref": None,
        "adjudication_resolution_ref": None,
        "calibration_artifact_refs": (),
        "anchor_promotion_decision_ref": None,
        "supersedes_item_snapshot_ref": None,
    }
    payload.update(overrides)
    return build_dynamic_evaluation_item_lineage(**payload)


def _run_payload() -> dict[str, Any]:
    return {
        "contract_id": DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
        "run_snapshot_ref": "evaluation_run_snapshot_1",
        "blueprint_revision_ref": "evaluation_blueprint_revision_1",
        "items": [_item().to_mapping()],
        "anchor_item_snapshot_refs": [],
        "comparability_status": "unavailable",
        "linking_evidence_ref": None,
    }


def test_item_mapping_round_trip_and_mapping_failures() -> None:
    item = DynamicEvaluationItemLineage.from_mapping(_item().to_mapping())
    assert item.item_snapshot_ref == "evaluation_item_snapshot_alpha"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationItemLineage.from_mapping([])
    assert caught.value.code == "invalid_object"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationItemLineage.from_mapping({1: "bad-key"})
    assert caught.value.code == "invalid_object_key"

    payload = _item().to_mapping()
    payload["unknown"] = "value"
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationItemLineage.from_mapping(payload)
    assert caught.value.code == "unknown_field"

    payload = _item().to_mapping()
    del payload["generation_invocation_ref"]
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationItemLineage.from_mapping(payload)
    assert caught.value.code == "missing_field"


def test_item_authority_fields_are_rejected() -> None:
    payload = _item().to_mapping()
    payload["adjudication_decision"] = "approved"
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationItemLineage.from_mapping(payload)
    assert caught.value.code == "authority_leakage"


def test_adjudication_case_and_resolution_keep_distinct_identities() -> None:
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        _item(
            adjudication_case_ref="adjudication_record_1",
            adjudication_resolution_ref="adjudication_record_1",
        )
    assert caught.value.code == "adjudication_reference_collision"


@pytest.mark.parametrize(
    "invalid",
    (
        "",
        " item_ref",
        "item_ref ",
        "\ufeffitem_ref",
        "item_ref\ufeff",
        "item\u200bref",
        "item\u202eref",
        "line\nbreak",
        "\ud800",
        "x" * 257,
    ),
)
def test_references_are_exact_bounded_and_free_of_format_controls(invalid: str) -> None:
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        _item(item_snapshot_ref=invalid)
    assert caught.value.code == "invalid_reference"

    with pytest.raises(TypeError, match="item_snapshot_ref must be a string"):
        _item(item_snapshot_ref=object())


def test_reference_collections_and_digest_are_typed_bounded_and_unique() -> None:
    for refs, expected in (
        ("rater_invocation_1", TypeError),
        (["rater_invocation_1"] * 257, DynamicEvaluationLineageError),
        (["rater_invocation_1", "rater_invocation_1"], DynamicEvaluationLineageError),
    ):
        with pytest.raises(expected):
            _item(rater_invocation_refs=refs)

    with pytest.raises(TypeError, match="source_contract_sha256 must be a string"):
        _item(source_contract_sha256=object())
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        _item(source_contract_sha256="A" * 64)
    assert caught.value.code == "invalid_sha256"


def test_run_mapping_round_trip_and_transport_failures() -> None:
    run = DynamicEvaluationRunLineage.from_mapping(_run_payload())
    assert run.to_mapping()["comparability_status"] == "unavailable"

    payload = _run_payload()
    del payload["linking_evidence_ref"]
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationRunLineage.from_mapping(payload)
    assert caught.value.code == "missing_field"

    payload = _run_payload()
    payload["contract_id"] = "wrong/v1"
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationRunLineage.from_mapping(payload)
    assert caught.value.code == "contract_incompatible"

    payload = _run_payload()
    payload["items"] = "not-an-array"
    with pytest.raises(TypeError, match="items must be a tuple or list"):
        DynamicEvaluationRunLineage.from_mapping(payload)


def test_comparability_and_run_resource_boundaries() -> None:
    item = _item()
    for status in (object(), "unknown"):
        with pytest.raises((TypeError, DynamicEvaluationLineageError)):
            build_dynamic_evaluation_run_lineage(
                run_snapshot_ref="evaluation_run_snapshot_1",
                blueprint_revision_ref="evaluation_blueprint_revision_1",
                items=(item,),
                anchor_item_snapshot_refs=(),
                comparability_status=status,
            )

    for items in ((), [], "not-an-item-array"):
        with pytest.raises(DynamicEvaluationLineageError) as caught:
            build_dynamic_evaluation_run_lineage(
                run_snapshot_ref="evaluation_run_snapshot_empty",
                blueprint_revision_ref="evaluation_blueprint_revision_1",
                items=items,
                anchor_item_snapshot_refs=(),
                comparability_status=RunComparabilityStatus.UNAVAILABLE,
            )
        assert caught.value.code == "invalid_item_set"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_large",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=[item] * 10_001,
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "item_set_budget_exceeded"

    with pytest.raises(TypeError, match="exact DynamicEvaluationItemLineage"):
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_wrong_type",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(item, object()),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )

    foreign = _item(blueprint_revision_ref="evaluation_blueprint_revision_2")
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_foreign",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(item, foreign),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "item_blueprint_mismatch"


def test_linking_evidence_is_admitted_only_with_promoted_anchors() -> None:
    anchor = _item(
        calibration_artifact_refs=("calibration_artifact_1",),
        anchor_promotion_decision_ref="anchor_promotion_decision_1",
    )
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_no_link_evidence",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(anchor,),
            anchor_item_snapshot_refs=(anchor.item_snapshot_ref,),
            comparability_status=RunComparabilityStatus.LINKED,
        )
    assert caught.value.code == "linked_run_requires_evidence"

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_unlinked_evidence",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(anchor,),
            anchor_item_snapshot_refs=(anchor.item_snapshot_ref,),
            comparability_status=RunComparabilityStatus.WITHIN_RUN_ONLY,
            linking_evidence_ref="linking_evidence_1",
        )
    assert caught.value.code == "unexpected_linking_evidence"


def test_run_rejects_cycles_in_item_supersession_lineage() -> None:
    first = _item(
        item_snapshot_ref="evaluation_item_snapshot_alpha",
        supersedes_item_snapshot_ref="evaluation_item_snapshot_beta",
    )
    second = _item(
        item_snapshot_ref="evaluation_item_snapshot_beta",
        supersedes_item_snapshot_ref="evaluation_item_snapshot_alpha",
    )

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="evaluation_run_snapshot_supersession_cycle",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            items=(first, second),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "supersession_cycle"
