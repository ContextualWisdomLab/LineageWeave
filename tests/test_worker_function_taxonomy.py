"""Correctness checks for the DOT/FJA worker-function read model
(ADR 0232).

The tests treat the published Dictionary of Occupational Titles
Appendix B tables as ground truth: every declared concept must carry
the official definition verbatim, the definitional rank from the
published table, and facet tags drawn only from the published Fleishman
ability / O*NET skill vocabularies. Nothing here may accept an invented
weight or a placeholder for missing evidence.
"""

from __future__ import annotations

import pytest
from rdflib import RDF

from lineageweave.ontology import LW, ONTOLOGY, all_declared_lookup_codes
from lineageweave.worker_function_taxonomy import (
    WORKER_FUNCTION_DOMAINS,
    facets_for,
    worker_function,
    worker_function_records,
)

#: Verbatim opening fragments of official DOT Appendix B definitions,
#: keyed by ``(domain, rank)`` -- a real-world accuracy check that the
#: ontology carries the published text rather than a paraphrase.
_OFFICIAL_DEFINITION_PREFIXES: dict[tuple[str, int], str] = {
    ("data", 0): "Integrating analyses of data to discover facts",
    ("data", 1): "Determining time, place, and sequence of operations",
    ("data", 2): "Examining and evaluating data.",
    ("data", 3): "Gathering, collating, or classifying information about data",
    ("data", 4): "Performing arithmetic operations",
    ("data", 5): "Transcribing, entering, or posting data.",
    ("data", 6): "Judging the readily observable functional, structural",
    ("people", 0): "Dealing with individuals in terms of their total personality",
    ("people", 1): "Exchanging ideas, information, and opinions with others",
    ("people", 2): "Teaching subject matter to others",
    ("people", 3): "Determining or interpreting work procedures",
    ("people", 4): "Amusing others",
    ("people", 5): "Influencing others in favor of a product, service",
    ("people", 6): "Talking with and/or signalling people",
    ("people", 7): "Attending to the needs or requests of people",
    ("people", 8): "Attending to the work assignment instructions or orders",
    ("things", 0): "Preparing machines, equipment, or work stations",
    ("things", 1): "Using body members and/or tools or work aids to work on",
    ("things", 2): "Starting, stopping, and controlling the actions of machines and equipment",
    ("things", 3): "Starting, stopping, and controlling the actions of machines or vehicles",
    ("things", 4): "Using body members, handtools, and/or special devices",
    ("things", 5): "Starting, stopping, and observing the functioning of machines",
    ("things", 6): "Inserting, throwing, dumping, or placing materials",
    ("things", 7): "Using body members, handtools, and/or special devices to install",
}

#: The closed facet-tag vocabulary this ADR allows: published Fleishman
#: ability families plus O*NET basic / cross-functional skill names.
_ALLOWED_FACET_TAGS = {
    # Fleishman ability families (Fleishman et al., 1999)
    "Arm-Hand Steadiness",
    "Category Flexibility",
    "Control Precision",
    "Deductive Reasoning",
    "Extent Flexibility",
    "Finger Dexterity",
    "Fluency of Ideas",
    "Inductive Reasoning",
    "Manual Dexterity",
    "Mathematical Reasoning",
    "Multilimb Coordination",
    "Number Facility",
    "Oral Comprehension",
    "Oral Expression",
    "Perceptual Speed",
    "Rate Control",
    "Reaction Time",
    "Response Orientation",
    "Spatial Orientation",
    "Static Strength",
    "Vigilance",
    "Written Comprehension",
    # O*NET basic / cross-functional skills and work styles
    # (Mumford et al., 1999; Peterson et al., 1999)
    "Active Listening",
    "Cooperation",
    "Coordination",
    "Critical Thinking",
    "Equipment Maintenance",
    "Instructing",
    "Management of Personnel Resources",
    "Monitoring",
    "Negotiation",
    "Operation Monitoring",
    "Persuasion",
    "Service Orientation",
    "Social Perceptiveness",
    "Speaking",
    "Time Management",
}


def _record_map() -> dict[tuple[str, int], object]:
    """Index every declared record by its ``(domain, rank)`` pair."""
    return {(record.domain, record.rank): record for record in worker_function_records()}


def test_every_published_worker_function_is_declared() -> None:
    """The taxonomy declares exactly the 24 DOT functions: Data 0-6,
    People 0-8, Things 0-7 -- no more, no fewer."""
    assert len(WORKER_FUNCTION_DOMAINS) == 3
    assert len(worker_function_records()) == 24


def test_domain_ranks_match_the_published_table_extents() -> None:
    """Each domain declares exactly one concept per published rank."""
    records_by_domain: dict[str, set[int]] = {}
    for record in worker_function_records():
        records_by_domain.setdefault(record.domain, set()).add(record.rank)
    for domain, (low, high) in WORKER_FUNCTION_DOMAINS.items():
        assert records_by_domain[domain] == set(range(low, high + 1))


def test_definitions_carry_the_official_dot_text() -> None:
    """Every concept's comment is the official Appendix B definition,
    verified against verbatim opening fragments."""
    indexed = _record_map()
    for key, prefix in _OFFICIAL_DEFINITION_PREFIXES.items():
        record = indexed[key]
        assert record.definition.startswith(prefix), (
            f"{key} definition drifted from the official text: "
            f"{record.definition!r}"
        )


def test_labels_are_unique_across_the_scheme() -> None:
    """No two functions share a preferred label, so label-based display
    can never conflate two ranks."""
    labels = [record.label for record in worker_function_records()]
    assert len(labels) == len(set(labels))


def test_facet_tags_stay_inside_the_published_vocabularies() -> None:
    """Every facet tag names a Fleishman ability family or O*NET skill
    from the allowed set -- no invented construct may enter the layer."""
    for record in worker_function_records():
        all_tags = (
            *record.cognitive_facets,
            *record.affective_facets,
            *record.behavioral_facets,
        )
        unknown = set(all_tags) - _ALLOWED_FACET_TAGS
        assert not unknown, f"{(record.domain, record.rank)} invented facets: {unknown}"


def test_every_function_exercises_at_least_one_facet() -> None:
    """Each definition projects onto at least one facet group; a fully
    untagged function would mean the projection silently failed."""
    for record in worker_function_records():
        total = (
            len(record.cognitive_facets)
            + len(record.affective_facets)
            + len(record.behavioral_facets)
        )
        assert total >= 1, f"{(record.domain, record.rank)} has no facets"


def test_records_are_sorted_in_dot_digit_order_then_rank() -> None:
    """Output order is Data, People, Things with ascending ranks inside
    each domain -- byte-stable serialization input."""
    records = worker_function_records()
    domain_order = ["data"] * 7 + ["people"] * 9 + ["things"] * 8
    assert [record.domain for record in records] == domain_order
    assert [record.rank for record in records[:7]] == list(range(0, 7))
    assert [record.rank for record in records[7:16]] == list(range(0, 9))
    assert [record.rank for record in records[16:]] == list(range(0, 8))


def test_iri_is_the_canonical_repository_case_namespace() -> None:
    """Every record IRI uses the repository-case canonical namespace;
    no lowercase compatibility IRI may be minted here (ADR 0207)."""
    canonical_prefix = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
    for record in worker_function_records():
        assert record.iri.startswith(canonical_prefix)


def test_worker_functions_carry_no_lookup_code() -> None:
    """Worker-function concepts deliberately declare no ``lookupCode``,
    so the lookup-code round trip stays untouched by this extension."""
    from lineageweave.ontology import iri_for_lookup_code

    assert iri_for_lookup_code("worker_function_data_synthesizing") is None
    # The pre-existing governed vocabulary is unchanged in size: the 31
    # lookup codes the schema seeded before this ADR are still all there
    # is.
    assert len(all_declared_lookup_codes()) == 31


@pytest.mark.parametrize(
    ("domain", "rank", "expected_label"),
    [
        ("data", 0, "Synthesizing"),
        ("people", 0, "Mentoring"),
        ("people", 8, "Taking Instructions-Helping"),
        ("things", 0, "Setting Up"),
        ("things", 7, "Handling"),
    ],
)
def test_worker_function_resolves_real_pairs(domain: str, rank: int, expected_label: str) -> None:
    """Published (domain, rank) pairs resolve to their labeled record."""
    record = worker_function(domain, rank)
    assert record is not None
    assert record.label == expected_label


def test_worker_function_returns_none_for_an_absent_rank() -> None:
    """An undeclared rank inside a valid domain is an honest unknown,
    never a placeholder record."""
    assert worker_function("data", 99) is None


def test_worker_function_raises_on_an_unknown_domain() -> None:
    """An unrecognized domain is caller error, not missing evidence."""
    with pytest.raises(ValueError, match="unknown worker-function domain"):
        worker_function("machines", 0)


def test_facets_for_returns_groups_for_a_declared_pair() -> None:
    """Facet lookup returns exactly the record's three sorted groups."""
    record = worker_function("data", 2)
    assert record is not None
    facets = facets_for("data", 2)
    assert facets == {
        "cognitive_facets": record.cognitive_facets,
        "affective_facets": record.affective_facets,
        "behavioral_facets": record.behavioral_facets,
    }
    assert facets["cognitive_facets"] == tuple(sorted(facets["cognitive_facets"]))


def test_facets_for_is_empty_for_an_undeclared_rank() -> None:
    """Missing-vs-negative discipline mirrors ontology_annotations()."""
    assert facets_for("things", 42) == {}


def test_facets_for_raises_on_an_unknown_domain() -> None:
    """Domain validation propagates through the facet helper too."""
    with pytest.raises(ValueError, match="unknown worker-function domain"):
        facets_for("vibes", 0)
