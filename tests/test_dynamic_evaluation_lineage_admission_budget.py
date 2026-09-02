"""Admission-budget regressions for dynamic evaluation lineage payloads."""

from __future__ import annotations

import pytest

import lineageweave.evaluation_lineage as evaluation_lineage
from lineageweave.evaluation_lineage import (
    DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
    MAX_LINEAGE_ITEMS,
    DynamicEvaluationLineageError,
    DynamicEvaluationRunLineage,
    build_dynamic_evaluation_item_lineage,
)

_DIGEST = "a" * 64


def test_run_mapping_rejects_oversized_item_array_before_item_decoding() -> None:
    """Reject hostile item counts before spending work on individual item payloads."""
    payload = {
        "contract_id": DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
        "run_snapshot_ref": "evaluation_run_snapshot_oversized",
        "blueprint_revision_ref": "evaluation_blueprint_revision_1",
        "items": [object()] * (MAX_LINEAGE_ITEMS + 1),
        "anchor_item_snapshot_refs": [],
        "comparability_status": "unavailable",
        "linking_evidence_ref": None,
    }

    with pytest.raises(DynamicEvaluationLineageError) as caught:
        DynamicEvaluationRunLineage.from_mapping(payload)

    assert caught.value.code == "item_set_budget_exceeded"


def test_long_acyclic_supersession_chain_uses_linear_set_work(monkeypatch) -> None:
    """Bound graph-walk work without relying on runner-specific wall-clock speed."""
    item_count = 512
    items = tuple(
        build_dynamic_evaluation_item_lineage(
            item_snapshot_ref=f"evaluation_item_snapshot_{index}",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            source_contract_ref="fast_mlsirm_dynamic_evaluation_item/v1",
            source_contract_sha256=_DIGEST,
            generation_invocation_ref=None,
            rater_invocation_refs=(),
            adjudication_case_ref=None,
            adjudication_resolution_ref=None,
            calibration_artifact_refs=(),
            anchor_promotion_decision_ref=None,
            supersedes_item_snapshot_ref=(
                "external_prior_snapshot"
                if index == 0
                else f"evaluation_item_snapshot_{index - 1}"
            ),
        )
        for index in range(item_count)
    )

    class CountingSet(set):
        operations = 0

        def __contains__(self, value: object) -> bool:
            type(self).operations += 1
            return super().__contains__(value)

        def add(self, value: object) -> None:
            type(self).operations += 1
            super().add(value)

        def update(self, *others: object) -> None:
            for other in others:
                values = tuple(other)
                type(self).operations += len(values)
                super().update(values)

    monkeypatch.setattr(evaluation_lineage, "set", CountingSet, raising=False)
    evaluation_lineage._validate_supersession_graph(items)

    assert CountingSet.operations <= item_count * 6
