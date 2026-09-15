"""Criterion-first provenance contracts for dynamic evaluation lineage."""

from __future__ import annotations

from typing import Any

import pytest

from lineageweave.evaluation_criteria import (
    EvaluationCriterionLineageError,
    build_evaluation_criterion_set_lineage,
)
from lineageweave.evaluation_lineage import (
    DynamicEvaluationLineageError,
    RunComparabilityStatus,
    build_dynamic_evaluation_item_lineage,
    build_dynamic_evaluation_run_lineage,
)


def _criterion(seed: str) -> dict[str, object]:
    """Return one source-text-free but substantively identified criterion."""
    return {
        "criterion_ref": seed,
        "criterion_revision_ref": f"{seed}_revision_1",
        "definition_ref": f"{seed}_definition",
        "definition_sha256": "1" * 64,
        "admissible_evidence_rule_ref": f"{seed}_evidence_rule",
        "admissible_evidence_rule_sha256": "2" * 64,
        "exclusion_rule_ref": f"{seed}_exclusion_rule",
        "exclusion_rule_sha256": "3" * 64,
        "response_semantics_ref": f"{seed}_response_semantics",
        "response_semantics_sha256": "4" * 64,
        "abstention_rule_ref": f"{seed}_abstention_rule",
        "abstention_rule_sha256": "5" * 64,
        "not_observable_rule_ref": f"{seed}_not_observable_rule",
        "not_observable_rule_sha256": "6" * 64,
        "category_definition_refs": (
            f"{seed}_not_supported_definition",
            f"{seed}_supported_definition",
        ),
        "category_definition_sha256s": ("7" * 64, "8" * 64),
    }


def _criterion_set():
    """Build one complete immutable criterion-set lineage snapshot."""
    return build_evaluation_criterion_set_lineage(
        criterion_set_snapshot_ref="criterion_set_snapshot_1",
        criterion_set_sha256="a" * 64,
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        rubric_revision_ref="rubric_revision_1",
        intended_use_ref="intended_use_1",
        construct_ref="construct_1",
        population_scope_ref="population_scope_1",
        language_scope_ref="language_scope_1",
        domain_scope_ref="domain_scope_1",
        criteria=(
            _criterion("criterion_evidence_support"),
            _criterion("criterion_safety"),
        ),
    )


def _item(**overrides: Any):
    """Build one valid criterion-bound item-lineage projection."""
    payload: dict[str, Any] = {
        "item_snapshot_ref": "item_snapshot_1",
        "blueprint_revision_ref": "evaluation_blueprint_revision_1",
        "criterion_set_snapshot_ref": "criterion_set_snapshot_1",
        "criterion_set_sha256": "a" * 64,
        "rubric_revision_ref": "rubric_revision_1",
        "criterion_refs": (
            "criterion_evidence_support",
            "criterion_safety",
        ),
        "source_contract_ref": "fast_mlsirm_dynamic_evaluation_item_v1",
        "source_contract_sha256": "b" * 64,
        "generation_invocation_ref": "generation_invocation_1",
        "rater_invocation_refs": ("rater_invocation_1", "rater_invocation_2"),
        "adjudication_case_ref": "adjudication_case_1",
        "adjudication_resolution_ref": "adjudication_resolution_1",
        "calibration_artifact_refs": (),
        "anchor_promotion_decision_ref": None,
        "supersedes_item_snapshot_ref": None,
    }
    payload.update(overrides)
    return build_dynamic_evaluation_item_lineage(**payload)


def test_run_requires_complete_nonempty_criterion_meaning_before_items() -> None:
    """A dynamic run cannot be represented from criterion identifiers alone."""
    criterion_set = _criterion_set()
    run = build_dynamic_evaluation_run_lineage(
        run_snapshot_ref="run_snapshot_1",
        blueprint_revision_ref="evaluation_blueprint_revision_1",
        criterion_set=criterion_set,
        items=(_item(),),
        anchor_item_snapshot_refs=(),
        comparability_status=RunComparabilityStatus.WITHIN_RUN_ONLY,
    )
    assert run.criterion_set.criterion_refs == (
        "criterion_evidence_support",
        "criterion_safety",
    )
    assert run.to_mapping()["criterion_set"]["criteria"][0][
        "admissible_evidence_rule_ref"
    ] == "criterion_evidence_support_evidence_rule"


def test_criterion_set_rejects_missing_meaning_and_zero_criteria() -> None:
    """Definitions, evidence rules, response semantics, and categories are mandatory."""
    with pytest.raises(EvaluationCriterionLineageError) as caught:
        build_evaluation_criterion_set_lineage(
            criterion_set_snapshot_ref="criterion_set_snapshot_1",
            criterion_set_sha256="a" * 64,
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            rubric_revision_ref="rubric_revision_1",
            intended_use_ref="intended_use_1",
            construct_ref="construct_1",
            population_scope_ref="population_scope_1",
            language_scope_ref="language_scope_1",
            domain_scope_ref="domain_scope_1",
            criteria=(),
        )
    assert caught.value.code == "invalid_criterion_set"

    incomplete = _criterion("criterion_safety")
    del incomplete["response_semantics_ref"]
    with pytest.raises(EvaluationCriterionLineageError) as caught:
        build_evaluation_criterion_set_lineage(
            criterion_set_snapshot_ref="criterion_set_snapshot_1",
            criterion_set_sha256="a" * 64,
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            rubric_revision_ref="rubric_revision_1",
            intended_use_ref="intended_use_1",
            construct_ref="construct_1",
            population_scope_ref="population_scope_1",
            language_scope_ref="language_scope_1",
            domain_scope_ref="domain_scope_1",
            criteria=(incomplete,),
        )
    assert caught.value.code == "missing_field"


def test_item_and_run_reject_criterion_set_or_rubric_substitution() -> None:
    """Items, adjudication, and later artifacts stay on the administered criteria."""
    criterion_set = _criterion_set()
    for changed_item in (
        _item(criterion_set_snapshot_ref="criterion_set_snapshot_2"),
        _item(criterion_set_sha256="c" * 64),
        _item(rubric_revision_ref="rubric_revision_2"),
        _item(criterion_refs=("criterion_invented",)),
    ):
        with pytest.raises(DynamicEvaluationLineageError) as caught:
            build_dynamic_evaluation_run_lineage(
                run_snapshot_ref="run_snapshot_1",
                blueprint_revision_ref="evaluation_blueprint_revision_1",
                criterion_set=criterion_set,
                items=(changed_item,),
                anchor_item_snapshot_refs=(),
                comparability_status=RunComparabilityStatus.UNAVAILABLE,
            )
        assert caught.value.code in {
            "item_criterion_set_mismatch",
            "item_rubric_mismatch",
            "unknown_item_criterion",
            "criterion_coverage_mismatch",
        }


def test_run_requires_all_bound_criteria_to_be_operationalized() -> None:
    """A run cannot silently omit a declared evaluation criterion."""
    with pytest.raises(DynamicEvaluationLineageError) as caught:
        build_dynamic_evaluation_run_lineage(
            run_snapshot_ref="run_snapshot_1",
            blueprint_revision_ref="evaluation_blueprint_revision_1",
            criterion_set=_criterion_set(),
            items=(_item(criterion_refs=("criterion_evidence_support",)),),
            anchor_item_snapshot_refs=(),
            comparability_status=RunComparabilityStatus.UNAVAILABLE,
        )
    assert caught.value.code == "criterion_coverage_mismatch"
