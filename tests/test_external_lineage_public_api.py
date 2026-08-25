"""Public import-surface tests for external lineage consumers."""

from __future__ import annotations

from lineageweave import external_lineage


def test_external_lineage_module_exports_the_versioned_contract() -> None:
    assert external_lineage.CONTRACT_VERSION == "1.0.0"
    assert callable(external_lineage.parse_lineage_analysis_request)
    assert callable(external_lineage.analyze_external_lineage)
    assert callable(external_lineage.request_digest)
    assert callable(external_lineage.result_digest)
    assert external_lineage.LineageContractError.__name__ == (
        "LineageContractError"
    )
