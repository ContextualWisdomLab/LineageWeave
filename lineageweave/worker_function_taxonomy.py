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
definitions and their definitional ordinal ranks.

Provenance discipline mirrors the rest of this repository:

- Ranks are scale positions copied from the published table -- never
  fitted, calibrated, or renormalized here. Nothing in this module may
  produce numeric weights (measurement stays governed by ADR 0145).
- No DOT-to-O*NET or Fleishman crosswalk is inferred: the cited
  authorities do not publish one.
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
from rdflib.namespace import RDF, SKOS

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
    term's ``skos:definition``."""


def _record_for(subject: URIRef) -> WorkerFunctionRecord:
    """Build one record from its ontology subject.

    Raises ``ValueError`` when a declared concept is missing one of its
    structural annotations (domain, rank, label, or definition): a
    malformed declaration must surface loudly rather than degrade into
    an invented default, matching the repository's fail-closed rule.
    """
    if (subject, RDF.type, LW.WorkerFunction) not in ONTOLOGY or not str(subject).startswith(
        str(LW)
    ):
        raise ValueError(f"worker-function term {subject} has invalid type or namespace")
    values = {
        name: tuple(ONTOLOGY.objects(subject, predicate))
        for name, predicate in (
            (":fjaDomain", LW.fjaDomain),
            (":fjaRank", LW.fjaRank),
            ("skos:prefLabel", SKOS.prefLabel),
            ("skos:definition", SKOS.definition),
        )
    }
    invalid = [name for name, declared in values.items() if len(declared) != 1]
    if invalid:
        raise ValueError(
            f"worker-function term {subject} must declare exactly one of: "
            f"{', '.join(invalid)}"
        )
    domain_literal, rank_literal, label_literal, definition_literal = (
        values[name][0]
        for name in (":fjaDomain", ":fjaRank", "skos:prefLabel", "skos:definition")
    )
    domain = str(domain_literal)
    if domain not in WORKER_FUNCTION_DOMAINS:
        raise ValueError(
            f"worker-function term {subject} declares unknown :fjaDomain "
            f"{domain!r}"
        )
    try:
        rank = int(rank_literal)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"worker-function term {subject} has invalid :fjaRank") from exc
    low, high = WORKER_FUNCTION_DOMAINS[domain]
    if rank not in range(low, high + 1):
        raise ValueError(
            f"worker-function term {subject} declares out-of-range :fjaRank {rank}"
        )
    return WorkerFunctionRecord(
        iri=str(subject),
        domain=domain,
        rank=rank,
        label=str(label_literal),
        definition=str(definition_literal),
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
    keys = {(record.domain, record.rank) for record in records}
    if len(keys) != len(records):
        raise ValueError("worker-function terms declare a duplicate domain/rank pair")
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
