"""Read-only API projection over the FJA I/O-Psychology semantic layer.

These serializers expose the DOT/FJA worker-function I/O-Psychology
profiles and the cognitive/affective/behavioral construct catalog
(ADR 0251) as plain, JSON-safe dictionaries for the Evidence API,
without importing database or HTTP concerns. Fail-closed behavior
mirrors the semantic layer: an undeclared worker function or construct
is an honest ``None``, and invalid domains raise ``ValueError``.
"""

from __future__ import annotations

from typing import Any

from lineageweave.iopsy_taxonomy import (
    IOPsyConstructRecord,
    IOPsyRelationRecord,
    WorkerFunctionIOPsyProfile,
    all_iopsy_construct_records,
    all_iopsy_relation_records,
    iopsy_profile_for_worker_function,
)

#: Profile attribute names in the same order as the typed record slots.
_PROFILE_SLOTS: tuple[tuple[str, str], ...] = (
    ("cognitive_demands", "cognitive_demands"),
    ("mental_workload_demands", "mental_workload_demands"),
    ("affective_demands", "affective_demands"),
    ("emotional_labor_demands", "emotional_labor_demands"),
    ("behavioral_manifestations", "behavioral_manifestations"),
    ("psychomotor_behaviors", "psychomotor_behaviors"),
    ("interpersonal_behaviors", "interpersonal_behaviors"),
)


def construct_to_payload(construct: IOPsyConstructRecord) -> dict[str, str]:
    """Project one I/O psychology construct into its JSON-safe payload shape.

    Args:
        construct: The typed semantic-layer construct record.

    Returns:
        dict[str, str]: iri, category, label, dimension, theoretical_basis, and
            definition fields as plain strings.
    """
    return {
        "iri": construct.iri,
        "category": construct.category,
        "label": construct.label,
        "dimension": construct.dimension,
        "theoretical_basis": construct.theoretical_basis,
        "definition": construct.definition,
    }


def relation_to_payload(relation: IOPsyRelationRecord) -> dict[str, str]:
    """Project one I/O psychology relation into its JSON-safe payload shape.

    Args:
        relation: The typed semantic-layer relation record.

    Returns:
        dict[str, str]: source_iri, source_label, predicate_iri,
            predicate_label, target_iri, target_label, and target_category.
    """
    return {
        "source_iri": relation.source_iri,
        "source_label": relation.source_label,
        "predicate_iri": relation.predicate_iri,
        "predicate_label": relation.predicate_label,
        "target_iri": relation.target_iri,
        "target_label": relation.target_label,
        "target_category": relation.target_category,
    }


def _profile_slot(profile: WorkerFunctionIOPsyProfile, field: str) -> list[dict[str, str]]:
    """Serialize one named profile attribute into a sorted construct list.

    Args:
        profile: The typed worker-function I/O psychology profile.
        field: The profile attribute name (e.g. ``cognitive_demands``).

    Returns:
        list[dict[str, str]]: Construct payload dictionaries, label-sorted.
    """
    return sorted(
        (construct_to_payload(construct) for construct in getattr(profile, field)),
        key=lambda item: item["label"],
    )


def worker_function_profile_payload(domain: str, rank: int) -> dict[str, Any] | None:
    """Serialize one worker function's I/O psychology demand profile.

    Args:
        domain: FJA domain (``data``, ``people``, or ``things``).
        rank: Ordinal rank within the published domain limits.

    Returns:
        dict[str, Any] | None: The demand/manifestation profile payload, or
            ``None`` when the function is not declared. Raises ``ValueError``
            for an unrecognized domain (caller error).
    """
    profile = iopsy_profile_for_worker_function(domain, rank)
    if profile is None:
        return None
    payload: dict[str, Any] = {
        "function_domain": profile.function_domain,
        "function_rank": profile.function_rank,
        "function_label": profile.function_label,
    }
    for field, attribute in _PROFILE_SLOTS:
        payload[field] = _profile_slot(profile, attribute)
    return payload


def construct_catalog_payload() -> dict[str, Any]:
    """Serialize the full I/O psychology construct and relation catalog.

    Returns:
        dict[str, Any]: Deterministic, JSON-safe payload with a ``constructs``
            map grouped by category plus the complete ``relations`` list.
    """
    constructs = all_iopsy_construct_records()
    by_category: dict[str, list[dict[str, str]]] = {}
    for construct in constructs:
        by_category.setdefault(construct.category, []).append(
            construct_to_payload(construct)
        )
    for category in by_category:
        by_category[category] = sorted(by_category[category], key=lambda item: item["label"])
    relations = [relation_to_payload(relation) for relation in all_iopsy_relation_records()]
    return {
        "constructs": by_category,
        "relations": relations,
    }