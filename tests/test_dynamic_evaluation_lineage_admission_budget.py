"""Admission-budget regressions for dynamic evaluation lineage payloads."""

from __future__ import annotations

import pytest

from lineageweave.evaluation_lineage import (
    DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID,
    MAX_LINEAGE_ITEMS,
    DynamicEvaluationLineageError,
    DynamicEvaluationRunLineage,
)


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
