"""Product-owned substantive criterion lineage for dynamic evaluations.

LineageWeave owns the product meaning and evidence provenance of evaluation
criteria. This module retains source-text-free references and exact digests for
criterion definitions, evidence admission and exclusion rules, response and
missingness semantics, and every admissible response category. It does not call
providers, score observations, adjudicate cases, or calibrate items.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import InitVar, dataclass
from typing import Any

MAX_CRITERION_REFERENCE_LENGTH = 256
MAX_EVALUATION_CRITERIA = 128
MAX_CRITERION_CATEGORIES = 64
_CRITERION_TOKEN = object()
_SET_TOKEN = object()

_CRITERION_FIELDS = frozenset(
    {
        "criterion_ref",
        "criterion_revision_ref",
        "definition_ref",
        "definition_sha256",
        "admissible_evidence_rule_ref",
        "admissible_evidence_rule_sha256",
        "exclusion_rule_ref",
        "exclusion_rule_sha256",
        "response_semantics_ref",
        "response_semantics_sha256",
        "abstention_rule_ref",
        "abstention_rule_sha256",
        "not_observable_rule_ref",
        "not_observable_rule_sha256",
        "category_refs",
        "category_definition_refs",
        "category_definition_sha256s",
    }
)
_SET_FIELDS = frozenset(
    {
        "criterion_set_snapshot_ref",
        "criterion_set_sha256",
        "blueprint_revision_ref",
        "rubric_revision_ref",
        "intended_use_ref",
        "construct_ref",
        "population_scope_ref",
        "language_scope_ref",
        "domain_scope_ref",
        "criteria",
    }
)


class EvaluationCriterionLineageError(ValueError):
    """Stable fail-closed error for substantive criterion lineage violations."""

    def __init__(self, code: str, message: str) -> None:
        """Retain a machine-readable rejection code without source content."""
        self.code = code
        super().__init__(message)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    """Require one string-keyed mapping."""
    if not isinstance(value, Mapping):
        raise EvaluationCriterionLineageError(
            "invalid_object", f"{field_name} must be an object"
        )
    if any(type(key) is not str for key in value):
        raise EvaluationCriterionLineageError(
            "invalid_object_key", f"{field_name} keys must be strings"
        )
    return value


def _reject_unknown_fields(
    payload: Mapping[str, Any], allowed: frozenset[str], field_name: str
) -> None:
    """Reject fields outside the source-text-free criterion contract."""
    unknown = set(payload) - allowed
    if unknown:
        raise EvaluationCriterionLineageError(
            "unknown_field",
            f"{field_name} contains unsupported fields: {sorted(unknown)}",
        )


def _reference(value: Any, field_name: str) -> str:
    """Validate one exact bounded opaque reference without normalization."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    if (
        not value
        or len(value) > MAX_CRITERION_REFERENCE_LENGTH
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
        raise EvaluationCriterionLineageError(
            "invalid_reference", f"{field_name} must be an exact bounded reference"
        )
    return value


def _sha256(value: Any, field_name: str) -> str:
    """Validate one complete lowercase SHA-256 digest."""
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise EvaluationCriterionLineageError(
            "invalid_sha256",
            f"{field_name} must be 64 lowercase hexadecimal characters",
        )
    return value


def _reference_tuple(
    value: Any,
    field_name: str,
    *,
    minimum: int,
    maximum: int,
) -> tuple[str, ...]:
    """Copy and validate a bounded unique ordered reference collection."""
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list")
    if not minimum <= len(value) <= maximum:
        raise EvaluationCriterionLineageError(
            "invalid_reference_count",
            f"{field_name} must contain {minimum}..{maximum} references",
        )
    normalized = tuple(
        _reference(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(normalized)) != len(normalized):
        raise EvaluationCriterionLineageError(
            "duplicate_reference", f"{field_name} must not contain duplicates"
        )
    return normalized


def _digest_tuple(
    value: Any,
    field_name: str,
    *,
    minimum: int,
    maximum: int,
) -> tuple[str, ...]:
    """Copy and validate a bounded ordered digest collection."""
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list")
    if not minimum <= len(value) <= maximum:
        raise EvaluationCriterionLineageError(
            "invalid_digest_count",
            f"{field_name} must contain {minimum}..{maximum} digests",
        )
    return tuple(
        _sha256(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )


@dataclass(frozen=True, slots=True)
class EvaluationCriterionLineage:
    """Immutable substantive meaning and category contract for one criterion."""

    criterion_ref: str
    criterion_revision_ref: str
    definition_ref: str
    definition_sha256: str
    admissible_evidence_rule_ref: str
    admissible_evidence_rule_sha256: str
    exclusion_rule_ref: str
    exclusion_rule_sha256: str
    response_semantics_ref: str
    response_semantics_sha256: str
    abstention_rule_ref: str
    abstention_rule_sha256: str
    not_observable_rule_ref: str
    not_observable_rule_sha256: str
    category_refs: tuple[str, ...]
    category_definition_refs: tuple[str, ...]
    category_definition_sha256s: tuple[str, ...]
    _admission_token: InitVar[object | None] = None

    def __post_init__(self, _admission_token: object | None) -> None:
        """Prevent construction that bypasses the governed builder."""
        if _admission_token is not _CRITERION_TOKEN:
            raise ValueError(
                "EvaluationCriterionLineage must be created by "
                "build_evaluation_criterion_lineage"
            )

    @classmethod
    def from_mapping(cls, value: Any) -> "EvaluationCriterionLineage":
        """Translate an untrusted source-text-free criterion mapping."""
        payload = _mapping(value, "criterion lineage")
        _reject_unknown_fields(payload, _CRITERION_FIELDS, "criterion lineage")
        missing = _CRITERION_FIELDS - set(payload)
        if missing:
            raise EvaluationCriterionLineageError(
                "missing_field",
                f"criterion lineage is missing fields: {sorted(missing)}",
            )
        return build_evaluation_criterion_lineage(**payload)

    def to_mapping(self) -> dict[str, Any]:
        """Return the source-text-free criterion lineage payload."""
        return {
            "criterion_ref": self.criterion_ref,
            "criterion_revision_ref": self.criterion_revision_ref,
            "definition_ref": self.definition_ref,
            "definition_sha256": self.definition_sha256,
            "admissible_evidence_rule_ref": self.admissible_evidence_rule_ref,
            "admissible_evidence_rule_sha256": self.admissible_evidence_rule_sha256,
            "exclusion_rule_ref": self.exclusion_rule_ref,
            "exclusion_rule_sha256": self.exclusion_rule_sha256,
            "response_semantics_ref": self.response_semantics_ref,
            "response_semantics_sha256": self.response_semantics_sha256,
            "abstention_rule_ref": self.abstention_rule_ref,
            "abstention_rule_sha256": self.abstention_rule_sha256,
            "not_observable_rule_ref": self.not_observable_rule_ref,
            "not_observable_rule_sha256": self.not_observable_rule_sha256,
            "category_refs": list(self.category_refs),
            "category_definition_refs": list(self.category_definition_refs),
            "category_definition_sha256s": list(self.category_definition_sha256s),
        }


def build_evaluation_criterion_lineage(
    *,
    criterion_ref: str,
    criterion_revision_ref: str,
    definition_ref: str,
    definition_sha256: str,
    admissible_evidence_rule_ref: str,
    admissible_evidence_rule_sha256: str,
    exclusion_rule_ref: str,
    exclusion_rule_sha256: str,
    response_semantics_ref: str,
    response_semantics_sha256: str,
    abstention_rule_ref: str,
    abstention_rule_sha256: str,
    not_observable_rule_ref: str,
    not_observable_rule_sha256: str,
    category_refs: Sequence[str],
    category_definition_refs: Sequence[str],
    category_definition_sha256s: Sequence[str],
) -> EvaluationCriterionLineage:
    """Build one criterion whose evaluative meaning is complete and auditable."""
    normalized_category_refs = _reference_tuple(
        category_refs,
        "category_refs",
        minimum=2,
        maximum=MAX_CRITERION_CATEGORIES,
    )
    normalized_definition_refs = _reference_tuple(
        category_definition_refs,
        "category_definition_refs",
        minimum=2,
        maximum=MAX_CRITERION_CATEGORIES,
    )
    normalized_definition_digests = _digest_tuple(
        category_definition_sha256s,
        "category_definition_sha256s",
        minimum=2,
        maximum=MAX_CRITERION_CATEGORIES,
    )
    lengths = {
        len(normalized_category_refs),
        len(normalized_definition_refs),
        len(normalized_definition_digests),
    }
    if len(lengths) != 1:
        raise EvaluationCriterionLineageError(
            "category_definition_mismatch",
            "category identities, definitions, and digests must have equal length",
        )
    return EvaluationCriterionLineage(
        criterion_ref=_reference(criterion_ref, "criterion_ref"),
        criterion_revision_ref=_reference(
            criterion_revision_ref, "criterion_revision_ref"
        ),
        definition_ref=_reference(definition_ref, "definition_ref"),
        definition_sha256=_sha256(definition_sha256, "definition_sha256"),
        admissible_evidence_rule_ref=_reference(
            admissible_evidence_rule_ref, "admissible_evidence_rule_ref"
        ),
        admissible_evidence_rule_sha256=_sha256(
            admissible_evidence_rule_sha256,
            "admissible_evidence_rule_sha256",
        ),
        exclusion_rule_ref=_reference(exclusion_rule_ref, "exclusion_rule_ref"),
        exclusion_rule_sha256=_sha256(
            exclusion_rule_sha256, "exclusion_rule_sha256"
        ),
        response_semantics_ref=_reference(
            response_semantics_ref, "response_semantics_ref"
        ),
        response_semantics_sha256=_sha256(
            response_semantics_sha256, "response_semantics_sha256"
        ),
        abstention_rule_ref=_reference(abstention_rule_ref, "abstention_rule_ref"),
        abstention_rule_sha256=_sha256(
            abstention_rule_sha256, "abstention_rule_sha256"
        ),
        not_observable_rule_ref=_reference(
            not_observable_rule_ref, "not_observable_rule_ref"
        ),
        not_observable_rule_sha256=_sha256(
            not_observable_rule_sha256, "not_observable_rule_sha256"
        ),
        category_refs=normalized_category_refs,
        category_definition_refs=normalized_definition_refs,
        category_definition_sha256s=normalized_definition_digests,
        _admission_token=_CRITERION_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class EvaluationCriterionSetLineage:
    """Immutable non-empty evaluation criterion set for one blueprint revision."""

    criterion_set_snapshot_ref: str
    criterion_set_sha256: str
    blueprint_revision_ref: str
    rubric_revision_ref: str
    intended_use_ref: str
    construct_ref: str
    population_scope_ref: str
    language_scope_ref: str
    domain_scope_ref: str
    criteria: tuple[EvaluationCriterionLineage, ...]
    _admission_token: InitVar[object | None] = None

    def __post_init__(self, _admission_token: object | None) -> None:
        """Prevent construction that bypasses criterion-set validation."""
        if _admission_token is not _SET_TOKEN:
            raise ValueError(
                "EvaluationCriterionSetLineage must be created by "
                "build_evaluation_criterion_set_lineage"
            )

    @property
    def criterion_refs(self) -> tuple[str, ...]:
        """Return all governed criterion identities in snapshot order."""
        return tuple(criterion.criterion_ref for criterion in self.criteria)

    def to_mapping(self) -> dict[str, Any]:
        """Return the source-text-free criterion-set lineage payload."""
        return {
            "criterion_set_snapshot_ref": self.criterion_set_snapshot_ref,
            "criterion_set_sha256": self.criterion_set_sha256,
            "blueprint_revision_ref": self.blueprint_revision_ref,
            "rubric_revision_ref": self.rubric_revision_ref,
            "intended_use_ref": self.intended_use_ref,
            "construct_ref": self.construct_ref,
            "population_scope_ref": self.population_scope_ref,
            "language_scope_ref": self.language_scope_ref,
            "domain_scope_ref": self.domain_scope_ref,
            "criteria": [criterion.to_mapping() for criterion in self.criteria],
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "EvaluationCriterionSetLineage":
        """Translate an untrusted criterion-set lineage mapping."""
        payload = _mapping(value, "criterion set lineage")
        _reject_unknown_fields(payload, _SET_FIELDS, "criterion set lineage")
        missing = _SET_FIELDS - set(payload)
        if missing:
            raise EvaluationCriterionLineageError(
                "missing_field",
                f"criterion set lineage is missing fields: {sorted(missing)}",
            )
        return build_evaluation_criterion_set_lineage(**payload)


def build_evaluation_criterion_set_lineage(
    *,
    criterion_set_snapshot_ref: str,
    criterion_set_sha256: str,
    blueprint_revision_ref: str,
    rubric_revision_ref: str,
    intended_use_ref: str,
    construct_ref: str,
    population_scope_ref: str,
    language_scope_ref: str,
    domain_scope_ref: str,
    criteria: Sequence[EvaluationCriterionLineage | Mapping[str, Any]],
) -> EvaluationCriterionSetLineage:
    """Build a non-empty criterion set before any item or observation exists."""
    if not isinstance(criteria, (tuple, list)):
        raise TypeError("criteria must be a tuple or list")
    if not 1 <= len(criteria) <= MAX_EVALUATION_CRITERIA:
        raise EvaluationCriterionLineageError(
            "invalid_criterion_set",
            f"criteria must contain 1..{MAX_EVALUATION_CRITERIA} definitions",
        )
    normalized = tuple(
        criterion
        if type(criterion) is EvaluationCriterionLineage
        else EvaluationCriterionLineage.from_mapping(criterion)
        for criterion in criteria
    )
    if any(type(criterion) is not EvaluationCriterionLineage for criterion in normalized):
        raise TypeError("criteria must contain criterion lineage values or mappings")
    refs = tuple(criterion.criterion_ref for criterion in normalized)
    if len(set(refs)) != len(refs):
        raise EvaluationCriterionLineageError(
            "duplicate_criterion", "criterion set identities must be unique"
        )
    return EvaluationCriterionSetLineage(
        criterion_set_snapshot_ref=_reference(
            criterion_set_snapshot_ref, "criterion_set_snapshot_ref"
        ),
        criterion_set_sha256=_sha256(
            criterion_set_sha256, "criterion_set_sha256"
        ),
        blueprint_revision_ref=_reference(
            blueprint_revision_ref, "blueprint_revision_ref"
        ),
        rubric_revision_ref=_reference(rubric_revision_ref, "rubric_revision_ref"),
        intended_use_ref=_reference(intended_use_ref, "intended_use_ref"),
        construct_ref=_reference(construct_ref, "construct_ref"),
        population_scope_ref=_reference(
            population_scope_ref, "population_scope_ref"
        ),
        language_scope_ref=_reference(language_scope_ref, "language_scope_ref"),
        domain_scope_ref=_reference(domain_scope_ref, "domain_scope_ref"),
        criteria=normalized,
        _admission_token=_SET_TOKEN,
    )
