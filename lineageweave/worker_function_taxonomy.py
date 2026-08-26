"""The DOT/FJA worker-function taxonomy as a typed read model over the
published ontology (ADR 0232).

Functional Job Analysis expresses every job's relationship to *Data*,
*People*, and *Things* through three ordered worker-function lists that
the Dictionary of Occupational Titles carried verbatim in Appendix B
(U.S. Department of Labor, 1991): Data ranks 0-6, People ranks 0-8,
Things ranks 0-7, each ordered so the lower digit names the more complex
function. This module is the application-side projection of those
concepts from `docs/ontology/lineageweave-kg.ttl`, where they live as a
`skos:ConceptScheme` of `:WorkerFunction` concepts carrying the official
definitions, their definitional ordinal ranks, and qualitative
cognitive / affective / behavioral facet tags.

Provenance discipline mirrors the rest of this repository:

- Ranks are scale positions copied from the published table -- never
  fitted, calibrated, or renormalized here. Nothing in this module may
  produce numeric weights (measurement stays governed by ADR 0145).
- Facet tags name published Fleishman ability families and O*NET basic /
  cross-functional skills (Fleishman, Costanza, & Marshall-Mies, 1999;
  Mumford, Peterson, & Childs, 1999) projected editorially onto each
  official definition. They carry no weight and make no calibration
  claim.
- Lookups fail closed: an absent concept returns ``None``/empty rather
  than a placeholder, the same missing-vs-negative rule as the Null
  channels.

References
----------
Fine, S. A., & Cronshaw, S. F. (1999). *Functional job analysis: A
foundation for human resources management*. Lawrence Erlbaum
Associates.

U.S. Department of Labor. (1991). *Dictionary of occupational titles*
(4th ed., rev., Appendix B). U.S. Government Printing Office.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

from .ontology import LW, ONTOLOGY

#: The three DOT lists with their published rank ranges. The bounds are
#: definitional table extents (U.S. Department of Labor, 1991, Appendix
#: B), not tunable parameters.
WORKER_FUNCTION_DOMAINS: dict[str, tuple[int, int]] = {
    "data": (0, 6),
    "people": (0, 8),
    "things": (0, 7),
}

#: Canonical DOT digit order -- Data is the 4th code digit, People the
#: 5th, Things the 6th -- used for deterministic sorting.
_DOMAIN_ORDER: tuple[str, ...] = ("data", "people", "things")

#: Facet annotation groups read off each concept, mapped to the record
#: field names they populate.
_FACET_PROPERTIES: tuple[tuple[str, URIRef], ...] = (
    ("cognitive_facets", LW.cognitiveFacet),
    ("affective_facets", LW.affectiveFacet),
    ("behavioral_facets", LW.behavioralFacet),
)


@dataclass(frozen=True)
class WorkerFunctionRecord:
    """One worker-function concept exactly as the ontology declares it.

    Attributes mirror the TTL annotations one-for-one; nothing is
    derived, inferred, or scored at read time.
    """

    iri: str
    """The canonical repository-case ontology IRI for this function."""

    domain: str
    """Which DOT list the function belongs to: ``data``, ``people``, or
    ``things``."""

    rank: int
    """The function's definitional position on its list; the lower digit
    names the more complex function."""

    label: str
    """The SKOS preferred label, e.g. ``"Synthesizing"``."""

    definition: str
    """The official DOT Appendix B definition, stored verbatim as the
    term's ``rdfs:comment``."""

    cognitive_facets: tuple[str, ...]
    """Published Fleishman ability families or O*NET skills exercised
    cognitively, alphabetically sorted for deterministic output."""

    affective_facets: tuple[str, ...]
    """Published O*NET work styles or social skills exercised
    affectively, alphabetically sorted for deterministic output."""

    behavioral_facets: tuple[str, ...]
    """Published Fleishman psychomotor/physical abilities or O*NET
    behavioral skills exercised behaviorally, alphabetically sorted for
    deterministic output."""


def _facet_values(subject: URIRef) -> dict[str, tuple[str, ...]]:
    """Read the three facet annotation groups off one subject.

    Values are collected into sets first so duplicate annotations can
    never surface twice, then returned as deterministically sorted
    tuples keyed by record field name.
    """
    values: dict[str, tuple[str, ...]] = {}
    for field_name, predicate in _FACET_PROPERTIES:
        seen = {str(value) for value in ONTOLOGY.objects(subject, predicate)}
        values[field_name] = tuple(sorted(seen))
    return values


def _record_for(subject: URIRef) -> WorkerFunctionRecord:
    """Build one record from its ontology subject.

    Raises ``ValueError`` when a declared concept is missing one of its
    structural annotations (domain, rank, label, or definition): a
    malformed declaration must surface loudly rather than degrade into
    an invented default, matching the repository's fail-closed rule.
    """
    domain_literal = ONTOLOGY.value(subject, LW.fjaDomain)
    rank_literal = ONTOLOGY.value(subject, LW.fjaRank)
    label_literal = ONTOLOGY.value(subject, SKOS.prefLabel)
    definition_literal = ONTOLOGY.value(subject, RDFS.comment)
    missing = [
        name
        for name, literal in (
            (":fjaDomain", domain_literal),
            (":fjaRank", rank_literal),
            ("skos:prefLabel", label_literal),
            ("rdfs:comment", definition_literal),
        )
        if literal is None
    ]
    if missing:
        raise ValueError(
            f"worker-function term {subject} is missing required "
            f"annotations: {', '.join(missing)}"
        )
    domain = str(domain_literal)
    if domain not in WORKER_FUNCTION_DOMAINS:
        raise ValueError(
            f"worker-function term {subject} declares unknown :fjaDomain "
            f"{domain!r}"
        )
    facets = _facet_values(subject)
    return WorkerFunctionRecord(
        iri=str(subject),
        domain=domain,
        rank=int(rank_literal),
        label=str(label_literal),
        definition=str(definition_literal),
        cognitive_facets=facets["cognitive_facets"],
        affective_facets=facets["affective_facets"],
        behavioral_facets=facets["behavioral_facets"],
    )


@lru_cache(maxsize=1)
def worker_function_records() -> tuple[WorkerFunctionRecord, ...]:
    """Every declared worker-function concept, deterministically sorted.

    Sorting follows the DOT code-digit order (Data, People, Things) and,
    within a domain, ascending rank. Deterministic output keeps
    downstream serialization byte-stable across processes, matching the
    repository's deterministic-artifact rules.
    """
    records = [
        _record_for(subject)
        for subject in ONTOLOGY.subjects(SKOS.inScheme, LW.workerFunctionScheme)
    ]
    domain_index = {name: index for index, name in enumerate(_DOMAIN_ORDER)}
    records.sort(key=lambda record: (domain_index[record.domain], record.rank))
    return tuple(records)


def worker_function(domain: str, rank: int) -> WorkerFunctionRecord | None:
    """One worker function by its DOT domain and rank, or ``None``.

    ``None`` means the pair is genuinely undeclared -- the honest
    unknown -- never a placeholder. An unrecognized ``domain`` raises
    ``ValueError`` because it is caller error, not missing evidence.
    """
    if domain not in WORKER_FUNCTION_DOMAINS:
        raise ValueError(
            f"unknown worker-function domain {domain!r}; expected one of "
            f"{sorted(WORKER_FUNCTION_DOMAINS)}"
        )
    for record in worker_function_records():
        if record.domain == domain and record.rank == rank:
            return record
    return None


def facets_for(domain: str, rank: int) -> dict[str, tuple[str, ...]]:
    """The facet tag groups for one worker function.

    Returns the three sorted facet tuples for a declared function and
    ``{}`` for an undeclared rank inside a valid domain -- the same
    missing-vs-negative discipline as `ontology_annotations`. An
    unrecognized ``domain`` raises ``ValueError``.
    """
    record = worker_function(domain, rank)
    if record is None:
        return {}
    return {
        "cognitive_facets": record.cognitive_facets,
        "affective_facets": record.affective_facets,
        "behavioral_facets": record.behavioral_facets,
    }
