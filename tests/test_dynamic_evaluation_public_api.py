"""Public package export contract for dynamic evaluation lineage."""

from __future__ import annotations

import lineageweave


def test_public_package_exports_dynamic_evaluation_lineage_contract() -> None:
    """The reusable projection is discoverable from the package boundary."""
    assert (
        lineageweave.DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID
        == "lineageweave_dynamic_evaluation_lineage/v1"
    )
    assert lineageweave.DynamicEvaluationItemLineage.__module__.endswith(
        "evaluation_lineage"
    )
    assert lineageweave.DynamicEvaluationRunLineage.__module__.endswith(
        "evaluation_lineage"
    )
    assert callable(lineageweave.build_dynamic_evaluation_item_lineage)
    assert callable(lineageweave.build_dynamic_evaluation_run_lineage)
