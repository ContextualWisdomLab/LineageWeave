"""Typed read model for the complete O*NET 31.0 conceptual hierarchy.

This module exposes source-published identities and parent relationships only.
It never turns a content-model element into an occupation rating, person trait,
causal claim, score, or weight (ADR 0250).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from rdflib import URIRef
from rdflib.namespace import PROV, RDF, SKOS

from .ontology import LW, ONTOLOGY

_ELEMENT_ID_PATTERN = re.compile(r"^[1-6](?:\.[A-Za-z0-9]+)*$")


@dataclass(frozen=True)
class OnetContentModelRecord:
    """One exact O*NET 31.0 Content Model Reference element."""

    iri: str
    """Canonical repository-case ontology IRI."""

    element_id: str
    """Published period-delimited O*NET outline position."""

    name: str
    """Published element name."""

    description: str
    """Published element description."""

    parent_element_id: str | None
    """Published outline parent; ``None`` only for one of the six roots."""

    root_element_id: str
    """Published root domain ID, from ``1`` through ``6``."""

    branch_element_id: str | None
    """Published second-level branch ID, or ``None`` for a root."""


@dataclass(frozen=True)
class OnetContentModelLinkageRecord:
    """One source-published directed O*NET content-model linkage."""

    source_element_id: str
    """Worker-side source element ID."""

    target_element_id: str
    """Work-activity or work-context target element ID."""

    relationship: str
    """Stable relationship code, never a score or causal claim."""

    provenance_iri: str
    """Pinned O*NET source-table entity that published this pair."""


def _single_text(subject: URIRef, predicate: URIRef) -> str:
    values = list(ONTOLOGY.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"O*NET element {subject} requires one {predicate}")
    return str(values[0])


@lru_cache(maxsize=1)
def content_model_records() -> tuple[OnetContentModelRecord, ...]:
    """Return all 3,006 O*NET 31.0 elements in source outline order."""
    subjects = sorted(
        (
            subject
            for subject in ONTOLOGY.subjects(
                SKOS.inScheme, LW.onet31ContentModelScheme
            )
            if isinstance(subject, URIRef)
        ),
        key=str,
    )
    ids = {subject: _single_text(subject, LW.onetElementId) for subject in subjects}
    if len(subjects) != 3006 or len(set(ids.values())) != 3006:
        raise ValueError("O*NET 31.0 content model must contain 3,006 unique IDs")
    by_id = {element_id: subject for subject, element_id in ids.items()}
    records = []
    for subject in subjects:
        element_id = ids[subject]
        if _ELEMENT_ID_PATTERN.fullmatch(element_id) is None:
            raise ValueError(f"malformed O*NET element ID {element_id!r}")
        parents = list(ONTOLOGY.objects(subject, SKOS.broader))
        parent_id = element_id.rsplit(".", 1)[0] if "." in element_id else None
        if parent_id is None:
            if parents:
                raise ValueError(f"O*NET root {element_id} declares a parent")
        elif len(parents) != 1 or parents[0] != by_id.get(parent_id):
            raise ValueError(f"O*NET element {element_id} has an invalid parent")
        parts = element_id.split(".")
        records.append(
            OnetContentModelRecord(
                iri=str(subject),
                element_id=element_id,
                name=_single_text(subject, SKOS.prefLabel),
                description=_single_text(subject, SKOS.definition),
                parent_element_id=parent_id,
                root_element_id=parts[0],
                branch_element_id=".".join(parts[:2]) if len(parts) > 1 else None,
            )
        )
    return tuple(
        sorted(records, key=lambda record: tuple(record.element_id.split(".")))
    )


def content_model_element(element_id: str) -> OnetContentModelRecord | None:
    """Return one declared element, or ``None`` for a valid absent ID."""
    if not isinstance(element_id, str) or _ELEMENT_ID_PATTERN.fullmatch(element_id) is None:
        raise ValueError(f"malformed O*NET element ID {element_id!r}")
    return next(
        (
            record
            for record in content_model_records()
            if record.element_id == element_id
        ),
        None,
    )


def child_elements(element_id: str) -> tuple[OnetContentModelRecord, ...]:
    """Return the exact direct children of one declared source element."""
    if content_model_element(element_id) is None:
        return ()
    return tuple(
        record
        for record in content_model_records()
        if record.parent_element_id == element_id
    )


@lru_cache(maxsize=1)
def _all_linkages() -> tuple[OnetContentModelLinkageRecord, ...]:
    by_iri = {URIRef(record.iri): record.element_id for record in content_model_records()}
    records = []
    for predicate, relationship in (
        (LW.relevantWorkActivity, "relevant_work_activity"),
        (LW.relevantWorkContext, "relevant_work_context"),
    ):
        for source, target in ONTOLOGY.subject_objects(predicate):
            if source not in by_iri or target not in by_iri:
                raise ValueError("O*NET linkage references an unknown content-model element")
            statements = [
                statement
                for statement in ONTOLOGY.subjects(RDF.subject, source)
                if (statement, RDF.predicate, predicate) in ONTOLOGY
                and (statement, RDF.object, target) in ONTOLOGY
            ]
            if len(statements) != 1:
                raise ValueError("O*NET linkage requires exactly one reified statement")
            provenance = list(ONTOLOGY.objects(statements[0], PROV.wasDerivedFrom))
            if len(provenance) != 1 or not isinstance(provenance[0], URIRef):
                raise ValueError("O*NET linkage requires exactly one provenance IRI")
            records.append(
                OnetContentModelLinkageRecord(
                    source_element_id=by_iri[source],
                    target_element_id=by_iri[target],
                    relationship=relationship,
                    provenance_iri=str(provenance[0]),
                )
            )
    if len(records) != 1417:
        raise ValueError("O*NET 31.0 content model must contain 1,417 linkages")
    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.source_element_id,
                record.relationship,
                record.target_element_id,
            ),
        )
    )


def content_model_linkages(element_id: str) -> tuple[OnetContentModelLinkageRecord, ...]:
    """Return published outgoing linkages for one declared content-model element."""
    if content_model_element(element_id) is None:
        return ()
    return tuple(
        record for record in _all_linkages() if record.source_element_id == element_id
    )
