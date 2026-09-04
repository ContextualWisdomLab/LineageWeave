"""Transport-type regressions for dynamic-evaluation criterion references."""

from __future__ import annotations

from typing import Any

import pytest

from lineageweave.evaluation_lineage import build_dynamic_evaluation_item_lineage


_DIGEST = "a" * 64


def _build_item(criterion_refs: Any):
    return build_dynamic_evaluation_item_lineage(
        item_snapshot_ref="evaluation_item_snapshot_transport",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        source_contract_ref="synthetic_source_contract/v1",
        source_contract_sha256=_DIGEST,
        generation_invocation_ref=None,
        rater_invocation_refs=(),
        adjudication_case_ref=None,
        adjudication_resolution_ref=None,
        calibration_artifact_refs=(),
        anchor_promotion_decision_ref=None,
        supersedes_item_snapshot_ref=None,
        criterion_refs=criterion_refs,
    )


@pytest.mark.parametrize("malformed_refs", [None, "", 0, False, {}])
def test_falsy_non_collection_criterion_refs_fail_closed(malformed_refs: Any) -> None:
    """Do not let transport falsiness silently turn malformed criteria into unbound items."""
    with pytest.raises(TypeError, match="criterion_refs must be a tuple or list"):
        _build_item(malformed_refs)


def test_empty_reference_collection_remains_a_valid_unbound_item() -> None:
    item = _build_item([])

    assert item.criterion_bound is False
    assert item.criterion_refs == ()
