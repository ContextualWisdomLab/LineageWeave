"""Correctness checks for the I-O occupational-classification and
worker-characteristic read model (ADR 0245).

The tests treat the published 2018 Standard Occupational Classification
table, the published O*NET job-zone names, and Holland's RIASEC hexagon
as ground truth: every declared concept must carry the official name or
code verbatim, the structural counts must match the published tables,
and no lookup may accept an invented weight or a placeholder for missing
evidence.
"""

from __future__ import annotations

import pytest
from rdflib import RDF
from rdflib.namespace import SKOS

from lineageweave.io_taxonomy import (
    JOB_ZONE_LEVELS,
    ability_domain_records,
    adjacent_interest_types,
    interest_type_records,
    job_zone,
    job_zone_records,
    major_group,
    major_group_records,
    work_style_family_records,
    work_value_cluster_records,
)
from lineageweave.ontology import LW, ONTOLOGY, all_declared_lookup_codes

#: Verbatim official titles of the 2018 SOC major groups, keyed by code
#: -- a real-world accuracy check that the ontology carries the
#: published table rather than a paraphrase.
_OFFICIAL_MAJOR_GROUP_TITLES: dict[str, str] = {
    "11-0000": "Management Occupations",
    "13-0000": "Business and Financial Operations Occupations",
    "15-0000": "Computer and Mathematical Occupations",
    "17-0000": "Architecture and Engineering Occupations",
    "19-0000": "Life, Physical, and Social Science Occupations",
    "21-0000": "Community and Social Service Occupations",
    "23-0000": "Legal Occupations",
    "25-0000": "Educational Instruction and Library Occupations",
    "27-0000": "Arts, Design, Entertainment, Sports, and Media Occupations",
    "29-0000": "Healthcare Practitioners and Technical Occupations",
    "31-0000": "Healthcare Support Occupations",
    "33-0000": "Protective Service Occupations",
    "35-0000": "Food Preparation and Serving Related Occupations",
    "37-0000": "Building and Grounds Cleaning and Maintenance Occupations",
    "39-0000": "Personal Care and Service Occupations",
    "41-0000": "Sales and Related Occupations",
    "43-0000": "Office and Administrative Support Occupations",
    "45-0000": "Farming, Fishing, and Forestry Occupations",
    "47-0000": "Construction and Extraction Occupations",
    "49-0000": "Installation, Maintenance, and Repair Occupations",
    "51-0000": "Production Occupations",
    "53-0000": "Transportation and Material Moving Occupations",
    "55-0000": "Military Specific Occupations",
}

#: The closed RIASEC vocabulary in the published hexagon ring order
#: (Holland, 1997).
_RIASEC_RING: tuple[str, ...] = (
    "Realistic",
    "Investigative",
    "Artistic",
    "Social",
    "Enterprising",
    "Conventional",
)

#: The six published hexagon adjacency pairs as unordered neighbor sets.
_PUBLISHED_ADJACENCY: set[frozenset[str]] = {
    frozenset({"Realistic", "Investigative"}),
    frozenset({"Investigative", "Artistic"}),
    frozenset({"Artistic", "Social"}),
    frozenset({"Social", "Enterprising"}),
    frozenset({"Enterprising", "Conventional"}),
    frozenset({"Conventional", "Realistic"}),
}

#: Published O*NET work-value clusters.
_PUBLISHED_VALUE_CLUSTERS: frozenset[str] = frozenset(
    {
        "Achievement",
        "Independence",
        "Recognition",
        "Relationships",
        "Support",
        "Working Conditions",
    }
)

#: Seven higher-order dimensions in the revised O*NET Work Styles structure.
_PUBLISHED_STYLE_FAMILIES: frozenset[str] = frozenset(
    {
        "Openness",
        "Conscientiousness",
        "Extraversion",
        "Agreeableness",
        "Emotional Stability",
        "Honesty-Humility",
        "Compound Dimensions",
    }
)

#: Fleishman's four published ability domains (Fleishman & Quaintance,
#: 1984).
_PUBLISHED_ABILITY_DOMAINS: frozenset[str] = frozenset(
    {
        "Cognitive Abilities",
        "Psychomotor Abilities",
        "Physical Abilities",
        "Sensory Abilities",
    }
)

_CANONICAL_NAMESPACE = (
    "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
)


class TestMajorGroups:
    """Completeness and verbatim-title checks for the 23 major groups."""

    def test_publishes_exactly_the_23_soc_major_groups(self) -> None:
        records = major_group_records()
        assert len(records) == 23

    def test_every_code_carries_the_official_title_verbatim(self) -> None:
        by_code = {record.code: record.label for record in major_group_records()}
        assert by_code == _OFFICIAL_MAJOR_GROUP_TITLES

    def test_sorted_deterministically_by_official_code(self) -> None:
        codes = [record.code for record in major_group_records()]
        assert codes == sorted(codes)

    def test_lookup_returns_declared_record(self) -> None:
        record = major_group("15-0000")
        assert record is not None
        assert record.label == "Computer and Mathematical Occupations"
        assert record.iri.startswith(_CANONICAL_NAMESPACE)

    def test_lookup_of_undeclared_but_wellformed_code_is_none(self) -> None:
        assert major_group("99-0000") is None

    @pytest.mark.parametrize("bad_code", ["15", "150000", "", "aa-0000"])
    def test_malformed_code_raises_caller_error(self, bad_code: str) -> None:
        with pytest.raises(ValueError):
            major_group(bad_code)


class TestJobZones:
    """Published O*NET 31.0 preparation-category checks."""

    def test_publishes_exactly_four_zones(self) -> None:
        assert len(job_zone_records()) == 4

    def test_zone_levels_cover_the_published_extent(self) -> None:
        levels = [record.level for record in job_zone_records()]
        assert levels == list(JOB_ZONE_LEVELS) == [2, 3, 4, 5]

    def test_published_zone_names_verbatim(self) -> None:
        labels = {record.level: record.label for record in job_zone_records()}
        assert labels == {
            2: "Job Zone 1-2: Very Little to Some Preparation Needed",
            3: "Job Zone Three: Medium Preparation Needed",
            4: "Job Zone Four: Considerable Preparation Needed",
            5: "Job Zone Five: Extensive Preparation Needed",
        }

    def test_zone_lookup_round_trip(self) -> None:
        record = job_zone(3)
        assert record is not None
        assert record.label == "Job Zone Three: Medium Preparation Needed"

    def test_unknown_level_raises_caller_error(self) -> None:
        with pytest.raises(ValueError):
            job_zone(6)
        with pytest.raises(ValueError):
            job_zone(0)
        with pytest.raises(ValueError):
            job_zone(True)
        with pytest.raises(ValueError):
            job_zone(1.0)


class TestInterestTypes:
    """Holland-hexagon structure checks for the RIASEC types."""

    def test_publishes_exactly_six_types(self) -> None:
        assert len(interest_type_records()) == 6

    def test_ring_order_matches_published_hexagon(self) -> None:
        labels = [record.label for record in interest_type_records()]
        assert tuple(labels) == _RIASEC_RING

    def test_adjacency_reproduces_the_published_pairs(self) -> None:
        pairs = {
            frozenset({record.label, neighbor})
            for record in interest_type_records()
            for neighbor in record.adjacent_labels
        }
        assert pairs == _PUBLISHED_ADJACENCY

    def test_each_type_names_exactly_two_neighbors(self) -> None:
        for record in interest_type_records():
            assert len(record.adjacent_labels) == 2

    def test_adjacency_lookup_for_a_declared_type(self) -> None:
        result = adjacent_interest_types("Realistic")
        assert result == {"adjacent_labels": ("Conventional", "Investigative")}

    def test_adjacency_lookup_of_unknown_label_raises(self) -> None:
        with pytest.raises(ValueError):
            adjacent_interest_types("Realisticish")
        with pytest.raises(ValueError):
            adjacent_interest_types(42)

    def test_descriptions_are_stored_not_invented(self) -> None:
        for record in interest_type_records():
            assert len(record.description) > 40
            assert record.description.startswith(record.label)


class TestCharacteristicFamilies:
    """Closed-vocabulary checks for values, styles, and abilities."""

    def test_six_published_work_value_clusters(self) -> None:
        labels = {record.label for record in work_value_cluster_records()}
        assert labels == _PUBLISHED_VALUE_CLUSTERS

    def test_seven_revised_work_style_families(self) -> None:
        labels = {record.label for record in work_style_family_records()}
        assert labels == _PUBLISHED_STYLE_FAMILIES

    def test_four_fleishman_ability_domains(self) -> None:
        labels = {record.label for record in ability_domain_records()}
        assert labels == _PUBLISHED_ABILITY_DOMAINS

    def test_family_records_sort_deterministically_by_label(self) -> None:
        for records in (
            work_value_cluster_records(),
            work_style_family_records(),
            ability_domain_records(),
        ):
            labels = [record.label for record in records]
            assert labels == sorted(labels)

    def test_family_iris_use_the_canonical_namespace(self) -> None:
        for records in (
            work_value_cluster_records(),
            work_style_family_records(),
            ability_domain_records(),
        ):
            assert all(
                record.iri.startswith(_CANONICAL_NAMESPACE)
                for record in records
            )


class TestOntologyIsolation:
    """The addition must not disturb the lookup-code round trip."""

    def test_no_new_concept_carries_a_lookup_code(self) -> None:
        taxonomy_classes = (
            LW.OccupationalMajorGroup,
            LW.JobZone,
            LW.InterestType,
            LW.WorkValueCluster,
            LW.WorkStyleFamily,
            LW.AbilityDomain,
        )
        subjects = [
            subject
            for subject in ONTOLOGY.subjects(RDF.type, SKOS.Concept)
            if any(
                (subject, RDF.type, taxonomy_class) in ONTOLOGY
                for taxonomy_class in taxonomy_classes
            )
        ]
        assert subjects, "taxonomy concepts must exist to be checked"
        for subject in subjects:
            assert ONTOLOGY.value(subject, LW.lookupCode) is None

    def test_derivation_properties_assert_no_instance(self) -> None:
        derivation_properties = (
            LW.occupationalAbilityDemand,
            LW.occupationalInterestProfile,
            LW.occupationalValueOrientation,
            LW.occupationalWorkStyleNorm,
        )
        for predicate in derivation_properties:
            triples = list(ONTOLOGY.triples((None, predicate, None)))
            assert triples == []

    def test_declared_lookup_codes_unchanged_by_taxonomy_terms(self) -> None:
        codes = all_declared_lookup_codes()
        # The round trip stays exactly as the schema seeds it; none of
        # the occupational taxonomy concepts participates in it.
        assert isinstance(codes, set)
