"""Dynamic-evaluation provenance projections owned by LineageWeave.

The module projects immutable item-generation, rater-observation, adjudication,
calibration, anchor-promotion, and supersession references without creating any
provider configuration, score, psychometric parameter, or adjudication decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from enum import StrEnum
from typing import Any

DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID = "lineageweave_dynamic_evaluation_lineage/v1"
MAX_LINEAGE_REFERENCE_LENGTH = 256
MAX_LINEAGE_ITEMS = 10_000
MAX_LINEAGE_REFERENCES = 256
_ITEM_TOKEN = object()
_RUN_TOKEN = object()

_PROHIBITED_AUTHORITY_FIELDS = frozenset(
    {
        "provider_api_key",
        "provider_key",
        "provider_endpoint",
        "model_endpoint",
        "model_id",
        "score",
        "latent_trait",
        "pass_fail",
        "certification",
        "employment_decision",
        "adjudication_decision",
    }
)
_ITEM_FIELDS = frozenset(
    {
        "item_snapshot_ref",
        "blueprint_revision_ref",
        "source_contract_ref",
        "source_contract_sha256",
        "generation_invocation_ref",
        "rater_invocation_refs",
        "adjudication_case_ref",
        "adjudication_resolution_ref",
        "calibration_artifact_refs",
        "anchor_promotion_decision_ref",
        "supersedes_item_snapshot_ref",
    }
)
_RUN_FIELDS = frozenset(
    {
        "contract_id",
        "run_snapshot_ref",
        "blueprint_revision_ref",
        "items",
        "anchor_item_snapshot_refs",
        "comparability_status",
        "linking_evidence_ref",
    }
)


class RunComparabilityStatus(StrEnum):
    """Comparability claim available for one exact dynamic-evaluation run."""

    UNAVAILABLE = "unavailable"
    WITHIN_RUN_ONLY = "within_run_only"
    LINKED = "linked"


class DynamicEvaluationLineageError(ValueError):
    """Stable fail-closed error for dynamic-evaluation lineage violations."""

    def __init__(self, code: str, message: str) -> None:
        """Retain a bounded machine-readable rejection code."""
        self.code = code
        super().__init__(message)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DynamicEvaluationLineageError(
            "invalid_object", f"{field_name} must be an object"
        )
    if any(type(key) is not str for key in value):
        raise DynamicEvaluationLineageError(
            "invalid_object_key", f"{field_name} keys must be strings"
        )
    return value


def _reject_unknown_fields(
    payload: Mapping[str, Any], allowed: frozenset[str], field_name: str
) -> None:
    unknown = set(payload) - allowed
    if unknown.intersection(_PROHIBITED_AUTHORITY_FIELDS):
        raise DynamicEvaluationLineageError(
            "authority_leakage",
            f"{field_name} must not contain provider, scoring, or adjudication authority",
        )
    if unknown:
        raise DynamicEvaluationLineageError(
            "unknown_field",
            f"{field_name} contains unsupported fields: {sorted(unknown)}",
        )


def _reference(value: Any, field_name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    if (
        not value
        or len(value) > MAX_LINEAGE_REFERENCE_LENGTH
        or value != value.strip()
        or value.startswith("\ufeff")
        or value.endswith("\ufeff")
        or any(
            ord(character) < 32
            or 127 <= ord(character) <= 159
            or 0xD800 <= ord(character) <= 0xDFFF
            for character in value
        )
    ):
        raise DynamicEvaluationLineageError(
            "invalid_reference", f"{field_name} must be an exact bounded opaque reference"
        )
    return value


def _optional_reference(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _reference(value, field_name)


def _reference_tuple(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list")
    if (not allow_empty and not value) or len(value) > MAX_LINEAGE_REFERENCES:
        lower = 0 if allow_empty else 1
        raise DynamicEvaluationLineageError(
            "invalid_reference_count",
            f"{field_name} must contain {lower}..{MAX_LINEAGE_REFERENCES} references",
        )
    normalized = tuple(
        _reference(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(normalized)) != len(normalized):
        raise DynamicEvaluationLineageError(
            "duplicate_reference", f"{field_name} must not contain duplicates"
        )
    return normalized


def _sha256(value: Any, field_name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise DynamicEvaluationLineageError(
            "invalid_sha256",
            f"{field_name} must be a complete lowercase SHA-256 digest",
        )
    return value


def _comparability_status(value: Any) -> RunComparabilityStatus:
    if type(value) is RunComparabilityStatus:
        return value
    if type(value) is not str:
        raise TypeError(
            "comparability_status must be a RunComparabilityStatus or exact string"
        )
    try:
        return RunComparabilityStatus(value)
    except ValueError as exc:
        raise DynamicEvaluationLineageError(
            "invalid_comparability_status", "unsupported run comparability status"
        ) from exc


@dataclass(frozen=True, slots=True)
class DynamicEvaluationItemLineage:
    """Provenance projection for one immutable dynamic item snapshot."""

    item_snapshot_ref: str
    blueprint_revision_ref: str
    source_contract_ref: str
    source_contract_sha256: str
    generation_invocation_ref: str | None
    rater_invocation_refs: tuple[str, ...]
    adjudication_case_ref: str | None
    adjudication_resolution_ref: str | None
    calibration_artifact_refs: tuple[str, ...]
    anchor_promotion_decision_ref: str | None
    supersedes_item_snapshot_ref: str | None
    _admission_token: InitVar[object | None] = None

    def __post_init__(self, _admission_token: object | None) -> None:
        """Prevent direct construction that bypasses the lineage builder."""
        if _admission_token is not _ITEM_TOKEN:
            raise ValueError(
                "DynamicEvaluationItemLineage must be created by "
                "build_dynamic_evaluation_item_lineage"
            )

    def to_mapping(self) -> dict[str, Any]:
        """Return the source-text-free projection payload."""
        return {
            "item_snapshot_ref": self.item_snapshot_ref,
            "blueprint_revision_ref": self.blueprint_revision_ref,
            "source_contract_ref": self.source_contract_ref,
            "source_contract_sha256": self.source_contract_sha256,
            "generation_invocation_ref": self.generation_invocation_ref,
            "rater_invocation_refs": list(self.rater_invocation_refs),
            "adjudication_case_ref": self.adjudication_case_ref,
            "adjudication_resolution_ref": self.adjudication_resolution_ref,
            "calibration_artifact_refs": list(self.calibration_artifact_refs),
            "anchor_promotion_decision_ref": self.anchor_promotion_decision_ref,
            "supersedes_item_snapshot_ref": self.supersedes_item_snapshot_ref,
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "DynamicEvaluationItemLineage":
        """Translate an untrusted item-lineage projection through the ACL."""
        payload = _mapping(value, "item lineage")
        _reject_unknown_fields(payload, _ITEM_FIELDS, "item lineage")
        missing = _ITEM_FIELDS - set(payload)
        if missing:
            raise DynamicEvaluationLineageError(
                "missing_field", f"item lineage is missing fields: {sorted(missing)}"
            )
        return build_dynamic_evaluation_item_lineage(
            item_snapshot_ref=payload["item_snapshot_ref"],
            blueprint_revision_ref=payload["blueprint_revision_ref"],
            source_contract_ref=payload["source_contract_ref"],
            source_contract_sha256=payload["source_contract_sha256"],
            generation_invocation_ref=payload["generation_invocation_ref"],
            rater_invocation_refs=payload["rater_invocation_refs"],
            adjudication_case_ref=payload["adjudication_case_ref"],
            adjudication_resolution_ref=payload["adjudication_resolution_ref"],
            calibration_artifact_refs=payload["calibration_artifact_refs"],
            anchor_promotion_decision_ref=payload["anchor_promotion_decision_ref"],
            supersedes_item_snapshot_ref=payload["supersedes_item_snapshot_ref"],
        )


def build_dynamic_evaluation_item_lineage(
    *,
    item_snapshot_ref: str,
    blueprint_revision_ref: str,
    source_contract_ref: str,
    source_contract_sha256: str,
    generation_invocation_ref: str | None,
    rater_invocation_refs: tuple[str, ...] | list[str],
    adjudication_case_ref: str | None,
    adjudication_resolution_ref: str | None,
    calibration_artifact_refs: tuple[str, ...] | list[str],
    anchor_promotion_decision_ref: str | None,
    supersedes_item_snapshot_ref: str | None,
) -> DynamicEvaluationItemLineage:
    """Build one lineage projection without transferring foreign authority."""
    normalized_item_ref = _reference(item_snapshot_ref, "item_snapshot_ref")
    normalized_case_ref = _optional_reference(
        adjudication_case_ref, "adjudication_case_ref"
    )
    normalized_resolution_ref = _optional_reference(
        adjudication_resolution_ref, "adjudication_resolution_ref"
    )
    if normalized_resolution_ref is not None and normalized_case_ref is None:
        raise DynamicEvaluationLineageError(
            "resolution_requires_case",
            "an adjudication resolution must reference its separate case",
        )
    if normalized_resolution_ref is not None and normalized_resolution_ref == normalized_case_ref:
        raise DynamicEvaluationLineageError(
            "adjudication_reference_collision",
            "adjudication case and resolution must retain distinct identities",
        )

    normalized_supersedes_ref = _optional_reference(
        supersedes_item_snapshot_ref, "supersedes_item_snapshot_ref"
    )
    if normalized_supersedes_ref == normalized_item_ref:
        raise DynamicEvaluationLineageError(
            "self_supersession", "an item snapshot cannot supersede itself"
        )

    return DynamicEvaluationItemLineage(
        item_snapshot_ref=normalized_item_ref,
        blueprint_revision_ref=_reference(
            blueprint_revision_ref, "blueprint_revision_ref"
        ),
        source_contract_ref=_reference(source_contract_ref, "source_contract_ref"),
        source_contract_sha256=_sha256(
            source_contract_sha256, "source_contract_sha256"
        ),
        generation_invocation_ref=_optional_reference(
            generation_invocation_ref, "generation_invocation_ref"
        ),
        rater_invocation_refs=_reference_tuple(
            rater_invocation_refs, "rater_invocation_refs", allow_empty=True
        ),
        adjudication_case_ref=normalized_case_ref,
        adjudication_resolution_ref=normalized_resolution_ref,
        calibration_artifact_refs=_reference_tuple(
            calibration_artifact_refs,
            "calibration_artifact_refs",
            allow_empty=True,
        ),
        anchor_promotion_decision_ref=_optional_reference(
            anchor_promotion_decision_ref, "anchor_promotion_decision_ref"
        ),
        supersedes_item_snapshot_ref=normalized_supersedes_ref,
        _admission_token=_ITEM_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class DynamicEvaluationRunLineage:
    """Immutable LineageWeave projection for one resolved evaluation run."""

    run_snapshot_ref: str
    blueprint_revision_ref: str
    items: tuple[DynamicEvaluationItemLineage, ...]
    anchor_item_snapshot_refs: tuple[str, ...]
    comparability_status: RunComparabilityStatus
    linking_evidence_ref: str | None
    contract_id: str = DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID
    _admission_token: InitVar[object | None] = None

    def __post_init__(self, _admission_token: object | None) -> None:
        """Prevent direct construction outside the run-lineage builder."""
        if _admission_token is not _RUN_TOKEN:
            raise ValueError(
                "DynamicEvaluationRunLineage must be created by "
                "build_dynamic_evaluation_run_lineage"
            )

    def to_mapping(self) -> dict[str, Any]:
        """Return the versioned source-text-free run projection."""
        return {
            "contract_id": self.contract_id,
            "run_snapshot_ref": self.run_snapshot_ref,
            "blueprint_revision_ref": self.blueprint_revision_ref,
            "items": [item.to_mapping() for item in self.items],
            "anchor_item_snapshot_refs": list(self.anchor_item_snapshot_refs),
            "comparability_status": self.comparability_status.value,
            "linking_evidence_ref": self.linking_evidence_ref,
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "DynamicEvaluationRunLineage":
        """Translate an untrusted run-lineage projection through the ACL."""
        payload = _mapping(value, "run lineage")
        _reject_unknown_fields(payload, _RUN_FIELDS, "run lineage")
        missing = _RUN_FIELDS - set(payload)
        if missing:
            raise DynamicEvaluationLineageError(
                "missing_field", f"run lineage is missing fields: {sorted(missing)}"
            )
        if payload["contract_id"] != DYNAMIC_EVALUATION_LINEAGE_CONTRACT_ID:
            raise DynamicEvaluationLineageError(
                "contract_incompatible", "unsupported dynamic evaluation lineage contract"
            )
        raw_items = payload["items"]
        if not isinstance(raw_items, (tuple, list)):
            raise TypeError("items must be a tuple or list")
        if len(raw_items) > MAX_LINEAGE_ITEMS:
            raise DynamicEvaluationLineageError(
                "item_set_budget_exceeded",
                f"run lineage may contain at most {MAX_LINEAGE_ITEMS} items",
            )
        return build_dynamic_evaluation_run_lineage(
            run_snapshot_ref=payload["run_snapshot_ref"],
            blueprint_revision_ref=payload["blueprint_revision_ref"],
            items=tuple(
                DynamicEvaluationItemLineage.from_mapping(item) for item in raw_items
            ),
            anchor_item_snapshot_refs=payload["anchor_item_snapshot_refs"],
            comparability_status=payload["comparability_status"],
            linking_evidence_ref=payload["linking_evidence_ref"],
        )


def build_dynamic_evaluation_run_lineage(
    *,
    run_snapshot_ref: str,
    blueprint_revision_ref: str,
    items: tuple[DynamicEvaluationItemLineage, ...] | list[DynamicEvaluationItemLineage],
    anchor_item_snapshot_refs: tuple[str, ...] | list[str],
    comparability_status: RunComparabilityStatus | str,
    linking_evidence_ref: str | None = None,
) -> DynamicEvaluationRunLineage:
    """Build a run projection that may explicitly contain zero fixed anchors."""
    if not isinstance(items, (tuple, list)) or not items:
        raise DynamicEvaluationLineageError(
            "invalid_item_set", "run lineage must contain at least one item"
        )
    if len(items) > MAX_LINEAGE_ITEMS:
        raise DynamicEvaluationLineageError(
            "item_set_budget_exceeded",
            f"run lineage may contain at most {MAX_LINEAGE_ITEMS} items",
        )
    normalized_items = tuple(items)
    if any(type(item) is not DynamicEvaluationItemLineage for item in normalized_items):
        raise TypeError("items must contain exact DynamicEvaluationItemLineage values")

    normalized_blueprint_ref = _reference(
        blueprint_revision_ref, "blueprint_revision_ref"
    )
    if any(
        item.blueprint_revision_ref != normalized_blueprint_ref
        for item in normalized_items
    ):
        raise DynamicEvaluationLineageError(
            "item_blueprint_mismatch",
            "every item projection must use the run blueprint revision",
        )
    item_refs = tuple(item.item_snapshot_ref for item in normalized_items)
    if len(set(item_refs)) != len(item_refs):
        raise DynamicEvaluationLineageError(
            "duplicate_item_snapshot", "run lineage item snapshots must be unique"
        )

    normalized_anchor_refs = _reference_tuple(
        anchor_item_snapshot_refs,
        "anchor_item_snapshot_refs",
        allow_empty=True,
    )
    unknown_anchors = set(normalized_anchor_refs) - set(item_refs)
    if unknown_anchors:
        raise DynamicEvaluationLineageError(
            "unknown_anchor_item", "every anchor must identify an item in this run"
        )
    item_by_ref = {item.item_snapshot_ref: item for item in normalized_items}
    for anchor_ref in normalized_anchor_refs:
        anchor = item_by_ref[anchor_ref]
        if (
            anchor.anchor_promotion_decision_ref is None
            or not anchor.calibration_artifact_refs
        ):
            raise DynamicEvaluationLineageError(
                "anchor_requires_promotion_evidence",
                "an anchor requires separate promotion and calibration evidence",
            )

    normalized_status = _comparability_status(comparability_status)
    normalized_linking_ref = _optional_reference(
        linking_evidence_ref, "linking_evidence_ref"
    )
    if normalized_status is RunComparabilityStatus.LINKED:
        if not normalized_anchor_refs:
            raise DynamicEvaluationLineageError(
                "linked_run_requires_anchor",
                "cross-version linking requires at least one promoted anchor",
            )
        if normalized_linking_ref is None:
            raise DynamicEvaluationLineageError(
                "linked_run_requires_evidence",
                "linked comparability requires immutable linking evidence",
            )
    elif normalized_linking_ref is not None:
        raise DynamicEvaluationLineageError(
            "unexpected_linking_evidence",
            "unavailable and within-run-only projections cannot claim linking evidence",
        )

    return DynamicEvaluationRunLineage(
        run_snapshot_ref=_reference(run_snapshot_ref, "run_snapshot_ref"),
        blueprint_revision_ref=normalized_blueprint_ref,
        items=normalized_items,
        anchor_item_snapshot_refs=normalized_anchor_refs,
        comparability_status=normalized_status,
        linking_evidence_ref=normalized_linking_ref,
        _admission_token=_RUN_TOKEN,
    )