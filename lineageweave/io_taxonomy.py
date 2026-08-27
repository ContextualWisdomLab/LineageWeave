"""The I-O occupational-classification and worker-characteristic
taxonomy as a typed read model over the published ontology (ADR 0245).

The 2018 Standard Occupational Classification major groups -- which the
O*NET program publishes as its job families -- give stored evidence an
addressable occupational classification. The O*NET job zones carry the
published preparation levels; Holland's RIASEC interest types, the O*NET
work-value clusters, the revised O*NET Work Styles dimensions, and
Fleishman's ability domains carry distinct source-native worker
characteristics. They must not be collapsed into a single
cognition/affect/behavior factor or used to infer an individual's traits
from an occupation (Holland, 1997; Peterson et al., 1999; Peterson et al.,
2001).

Provenance discipline mirrors `worker_function_taxonomy`:

- Names and codes are copied from the published tables; nothing here
  derives or scores them.
- No numeric importance or level rating from any occupational profile
  is imported: measurement stays governed by ADR 0145 and nothing in
  this module may produce a weight.
- Lookups fail closed: an absent concept returns ``None`` rather than a
  placeholder, and an unrecognized key is caller error raising
  ``ValueError`` -- the same missing-vs-negative rule as the Null
  channels.

References
----------

U.S. Department of Labor. (2018). *2018 Standard Occupational
Classification System*. Bureau of Labor Statistics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from rdflib import RDF, URIRef
from rdflib.namespace import DCTERMS, PROV, RDFS, SKOS

from .ontology import LW, ONTOLOGY

#: Official major-group code shape from the published 2018 SOC table:
#: two digits, a hyphen, then four zeros.
_MAJOR_GROUP_CODE_PATTERN = re.compile(r"^\d{2}-0000$")
<<<<<<< HEAD
=======
_SOC_CODE_PATTERN = re.compile(r"^\d{2}-\d{4}$")
_SOC_LEVEL_CLASSES = (
    ("major_group", LW.OccupationalMajorGroup),
    ("minor_group", LW.OccupationalMinorGroup),
    ("broad_occupation", LW.BroadOccupation),
    ("detailed_occupation", LW.DetailedOccupation),
)
>>>>>>> origin/feat/onet-rating-occupation-filter

#: Published preparation-level ordering extent for the O*NET job zones.
#: The bounds are the definitional table extents, not tunable parameters.
JOB_ZONE_LEVELS: tuple[int, ...] = (2, 3, 4, 5)

#: The published RIASEC hexagonal ring order used for deterministic
#: sorting (Holland, 1997): adjacent positions in this tuple name the
#: published adjacency pairs.
_RIASEC_RING_ORDER: tuple[str, ...] = (
    "Realistic",
    "Investigative",
    "Artistic",
    "Social",
    "Enterprising",
    "Conventional",
)


@dataclass(frozen=True)
class MajorGroupRecord:
    """One occupational major group exactly as the ontology declares it.

    Attributes mirror the TTL declarations one-for-one; nothing is
    derived, inferred, or scored at read time.
    """

    iri: str
    """The canonical repository-case ontology IRI for this major group."""

    code: str
    """The official ``NN-0000`` code from the published 2018 SOC table."""

    label: str
    """The official major-group title, e.g. ``"Management Occupations"``."""


@dataclass(frozen=True)
<<<<<<< HEAD
=======
class SocClassificationRecord:
    """One source-published node in the complete 2018 SOC hierarchy."""

    iri: str
    """Canonical repository-case ontology IRI."""

    code: str
    """Official 2018 SOC code."""

    label: str
    """Official preferred title."""

    level: str
    """Source level: major, minor, broad, or detailed."""

    broader_code: str | None
    """Exact source parent code; ``None`` only for a major group."""


@dataclass(frozen=True)
>>>>>>> origin/feat/onet-rating-occupation-filter
class JobZoneRecord:
    """One O*NET job zone exactly as the ontology declares it."""

    iri: str
    """The canonical repository-case ontology IRI for this job zone."""

    level: int
    """The published O*NET 31.0 zone value, 2-5."""

    label: str
    """The published O*NET 31.0 preparation-category name."""


@dataclass(frozen=True)
class InterestTypeRecord:
    """One Holland RIASEC interest type exactly as declared.

    ``adjacent_labels`` names the two types Holland's hexagon places next
    to this one -- a published structural relation, not a similarity
    score.
    """

    iri: str
    """The canonical repository-case ontology IRI for this interest type."""

    label: str
    """The type's published name, e.g. ``"Realistic"``."""

    description: str
    """The standard O*NET Interest Profiler family description stored
    verbatim as the term's ``rdfs:comment``."""

    adjacent_labels: tuple[str, ...]
    """The two hexagonal neighbors of this type, deterministically
    sorted."""


@dataclass(frozen=True)
class CharacteristicFamilyRecord:
    """One characteristic-family concept without further structure.

    Work-value clusters, work-style families, and ability domains are
    published families whose members live in the source literature; the
    ontology carries only the family identity, so the record mirrors
    exactly that.
    """

    iri: str
    """The canonical repository-case ontology IRI for this family."""

    label: str
    """The family's published name, e.g. ``"Achievement"``."""


@dataclass(frozen=True)
class TaxonomySourceRecord:
    """One declared source entity behind an occupational concept scheme."""

    iri: str
    """Canonical IRI of the source entity."""

    title: str
    """Published title of the source."""

    version: str | None
    """Declared source version, or ``None`` when the source has none."""

    publisher: str | None
    """Declared publisher, or ``None`` for creator-owned literature."""

    source_url: str | None
    """Versioned source URL when one is available."""

    license_url: str | None
    """Applicable license URL, never inferred from a related source."""

    rights_url: str | None
    """Applicable rights URL, never inferred from a related source."""

    artifact_sha256: str | None
    """Verified artifact digest, or ``None`` when no stable artifact exists."""


def _label_of(subject: URIRef) -> str:
    """Return the SKOS preferred label of one subject.

    Raises ``ValueError`` when the declaration omits the label: a
    malformed declaration must surface loudly rather than degrade into
    an invented default, matching the repository's fail-closed rule.
    """
    label_literal = ONTOLOGY.value(subject, SKOS.prefLabel)
    if label_literal is None:
        raise ValueError(
            f"taxonomy term {subject} is missing required skos:prefLabel"
        )
    return str(label_literal)


def _scheme_subjects(scheme: URIRef) -> list[URIRef]:
    """Every concept declared inside one concept scheme.

    Membership is asserted through ``skos:inScheme`` so the returned
    subjects are exactly the concepts the ontology declares, never an
    inferred set.
    """
    return sorted(
        (subject for subject in ONTOLOGY.subjects(SKOS.inScheme, scheme)),
        key=str,
    )


def _optional_single_text(subject: URIRef, predicate: URIRef) -> str | None:
    """Return one optional metadata value and reject multivalued ambiguity."""
    values = list(ONTOLOGY.objects(subject, predicate))
    if len(values) > 1:
        raise ValueError(
            f"source entity {subject} declares multiple values for {predicate}"
        )
    return str(values[0]) if values else None


@lru_cache(maxsize=1)
def taxonomy_source_records() -> tuple[TaxonomySourceRecord, ...]:
    """All source entities used by the occupational schemes, sorted by IRI."""
    subjects = {
        source
        for scheme in (
<<<<<<< HEAD
            LW.socMajorGroupScheme,
            LW.jobZoneScheme,
=======
            LW.soc2018Scheme,
            LW.jobZoneScheme,
            LW.onet31ContentModelScheme,
>>>>>>> origin/feat/onet-rating-occupation-filter
            LW.workerCharacteristicScheme,
        )
        for source in ONTOLOGY.objects(scheme, PROV.wasDerivedFrom)
    }
    records = []
    for subject in sorted(subjects, key=str):
        if not isinstance(subject, URIRef):
            raise ValueError(f"taxonomy source must be an IRI, got {subject!r}")
        title = _optional_single_text(subject, DCTERMS.title)
        if title is None:
            raise ValueError(f"source entity {subject} lacks dcterms:title")
        records.append(
            TaxonomySourceRecord(
                iri=str(subject),
                title=title,
                version=_optional_single_text(subject, DCTERMS.hasVersion),
                publisher=_optional_single_text(subject, DCTERMS.publisher),
                source_url=_optional_single_text(subject, DCTERMS.source),
                license_url=_optional_single_text(subject, DCTERMS.license),
                rights_url=_optional_single_text(subject, DCTERMS.rights),
                artifact_sha256=_optional_single_text(
                    subject, LW.sourceArtifactSha256
                ),
            )
        )
    return tuple(records)


@lru_cache(maxsize=1)
def major_group_records() -> tuple[MajorGroupRecord, ...]:
    """Every declared occupational major group, sorted by SOC code.

    Sorting by the official code keeps downstream serialization
    byte-stable across processes, matching the repository's
    deterministic-artifact rules.
    """
    records = []
<<<<<<< HEAD
    for subject in _scheme_subjects(LW.socMajorGroupScheme):
=======
    for subject in _scheme_subjects(LW.soc2018Scheme):
        if (subject, RDF.type, LW.OccupationalMajorGroup) not in ONTOLOGY:
            continue
>>>>>>> origin/feat/onet-rating-occupation-filter
        code_literal = ONTOLOGY.value(subject, LW.socCode)
        if code_literal is None:
            raise ValueError(
                f"major group {subject} is missing required :socCode"
            )
        code = str(code_literal)
        if not _MAJOR_GROUP_CODE_PATTERN.fullmatch(code):
            raise ValueError(
                f"major group {subject} declares malformed :socCode "
                f"{code!r}; expected the NN-0000 published form"
            )
        records.append(
            MajorGroupRecord(
                iri=str(subject),
                code=code,
                label=_label_of(subject),
            )
        )
    codes = [record.code for record in records]
    if len(set(codes)) != len(codes):
        raise ValueError("occupational major groups declare duplicate SOC codes")
    records.sort(key=lambda record: record.code)
    return tuple(records)


<<<<<<< HEAD
=======
@lru_cache(maxsize=1)
def soc_classification_records() -> tuple[SocClassificationRecord, ...]:
    """Return the complete source-published 2018 SOC hierarchy by code."""
    subjects = _scheme_subjects(LW.soc2018Scheme)
    codes: dict[URIRef, str] = {}
    for subject in subjects:
        values = list(ONTOLOGY.objects(subject, LW.socCode))
        if len(values) != 1 or not _SOC_CODE_PATTERN.fullmatch(str(values[0])):
            raise ValueError(f"SOC classification {subject} has invalid :socCode")
        codes[subject] = str(values[0])
    if len(set(codes.values())) != len(codes):
        raise ValueError("2018 SOC hierarchy declares duplicate codes")

    records = []
    counts = {level: 0 for level, _ in _SOC_LEVEL_CLASSES}
    for subject in subjects:
        levels = [
            level
            for level, rdf_class in _SOC_LEVEL_CLASSES
            if (subject, RDF.type, rdf_class) in ONTOLOGY
        ]
        if len(levels) != 1:
            raise ValueError(f"SOC classification {subject} has ambiguous level")
        parents = list(ONTOLOGY.objects(subject, SKOS.broader))
        if (levels[0] == "major_group") != (not parents) or len(parents) > 1:
            raise ValueError(f"SOC classification {subject} has invalid parent count")
        parent_code = None
        if parents:
            parent = parents[0]
            if not isinstance(parent, URIRef) or parent not in codes:
                raise ValueError(f"SOC classification {subject} has unknown parent")
            parent_code = codes[parent]
        counts[levels[0]] += 1
        records.append(
            SocClassificationRecord(
                iri=str(subject),
                code=codes[subject],
                label=_label_of(subject),
                level=levels[0],
                broader_code=parent_code,
            )
        )
    if counts != {
        "major_group": 23,
        "minor_group": 98,
        "broad_occupation": 459,
        "detailed_occupation": 867,
    }:
        raise ValueError(f"2018 SOC hierarchy has unexpected level counts: {counts}")
    return tuple(sorted(records, key=lambda record: record.code))


def soc_classification(code: str) -> SocClassificationRecord | None:
    """Return one declared 2018 SOC node, or ``None`` for a valid absent code."""
    if not isinstance(code, str) or not _SOC_CODE_PATTERN.fullmatch(code):
        raise ValueError(f"malformed SOC code {code!r}; expected NN-NNNN")
    return next(
        (record for record in soc_classification_records() if record.code == code),
        None,
    )


>>>>>>> origin/feat/onet-rating-occupation-filter
def major_group(code: str) -> MajorGroupRecord | None:
    """One major group by its official SOC code, or ``None``.

    ``None`` means the code is genuinely undeclared -- the honest
    unknown -- never a placeholder. A string that cannot be an official
    major-group code raises ``ValueError`` because it is caller error,
    not missing evidence.
    """
    if not isinstance(code, str) or not _MAJOR_GROUP_CODE_PATTERN.fullmatch(code):
        raise ValueError(
            f"malformed SOC major-group code {code!r}; expected NN-0000"
        )
    for record in major_group_records():
        if record.code == code:
            return record
    return None


@lru_cache(maxsize=1)
def job_zone_records() -> tuple[JobZoneRecord, ...]:
    """Every declared job zone, sorted by ascending preparation level."""
    records = []
    for subject in _scheme_subjects(LW.jobZoneScheme):
        level_literals = list(ONTOLOGY.objects(subject, LW.jobZoneLevel))
        if len(level_literals) != 1:
            raise ValueError(
                f"job zone {subject} must declare exactly one :jobZoneLevel"
            )
        level = level_literals[0].toPython()
        if type(level) is not int or level not in JOB_ZONE_LEVELS:
            raise ValueError(
                f"job zone {subject} declares invalid :jobZoneLevel {level!r}"
            )
        records.append(
            JobZoneRecord(
                iri=str(subject),
                level=level,
                label=_label_of(subject),
            )
        )
    records.sort(key=lambda record: record.level)
    return tuple(records)


def job_zone(level: int) -> JobZoneRecord | None:
    """One job zone by its published preparation level, or ``None``.

    ``None`` means the level is genuinely undeclared. A value outside
    the published 2-5 values raises ``ValueError`` because it is caller
    error, not missing evidence.
    """
    if type(level) is not int or level not in JOB_ZONE_LEVELS:
        raise ValueError(
            f"unknown job-zone level {level!r}; expected one of "
            f"{list(JOB_ZONE_LEVELS)}"
        )
    for record in job_zone_records():
        if record.level == level:
            return record
    return None


def _interest_record_for(subject: URIRef, ring_index: dict[str, int]) -> InterestTypeRecord:
    """Build one interest-type record from its ontology subject.

    Raises ``ValueError`` when the declared type lacks a description or
    names a neighbor outside the closed RIASEC vocabulary: a malformed
    declaration must surface loudly rather than degrade.
    """
    description_literal = ONTOLOGY.value(subject, RDFS.comment)
    if description_literal is None:
        raise ValueError(
            f"interest type {subject} is missing required rdfs:comment"
        )
    label = _label_of(subject)
    if label not in ring_index:
        raise ValueError(
            f"interest type {subject} declares label {label!r} outside "
            f"the closed RIASEC vocabulary"
        )
    neighbors: set[str] = set()
    for neighbor in ONTOLOGY.objects(subject, LW.riasecAdjacentTo):
        if not isinstance(neighbor, URIRef):
            raise ValueError(
                f"interest type {subject} declares a non-IRI RIASEC "
                f"adjacency target {neighbor!r}"
            )
        neighbor_literal = ONTOLOGY.value(neighbor, SKOS.prefLabel)
        if neighbor_literal is None:
            raise ValueError(
                f"RIASEC adjacency target {neighbor} of interest type "
                f"{subject} lacks skos:prefLabel"
            )
        neighbors.add(str(neighbor_literal))
    for neighbor_label in sorted(neighbors):
        if neighbor_label not in ring_index:
            raise ValueError(
                f"interest type {subject} declares neighbor "
                f"{neighbor_label!r} outside the closed RIASEC vocabulary"
            )
    if len(neighbors) != 2:
        raise ValueError(
            f"interest type {subject} declares {len(neighbors)} RIASEC "
            f"neighbors; the published hexagon gives every type exactly "
            f"two"
        )
    return InterestTypeRecord(
        iri=str(subject),
        label=label,
        description=str(description_literal),
        adjacent_labels=tuple(sorted(neighbors)),
    )


@lru_cache(maxsize=1)
def interest_type_records() -> tuple[InterestTypeRecord, ...]:
    """Every declared interest type in the published hexagon-ring order.

    Deterministic ring order (Holland, 1997) makes adjacent pairs easy
    to audit against the published structure.
    """
    ring_index = {name: index for index, name in enumerate(_RIASEC_RING_ORDER)}
    records = [
        _interest_record_for(subject, ring_index)
        for subject in _scheme_subjects(LW.workerCharacteristicScheme)
        if (subject, RDF.type, LW.InterestType) in ONTOLOGY
    ]
    records.sort(key=lambda record: ring_index[record.label])
    return tuple(records)


def adjacent_interest_types(label: str) -> dict[str, tuple[str, ...]]:
    """The hexagonal neighbors of one interest type.

    Returns the single ``adjacent_labels`` mapping for a declared type.
    Any label that is not an exact declared RIASEC name raises
    ``ValueError`` because it is caller error, not missing evidence;
    there is no second dimension here that could be honestly unknown,
    so no placeholder ``{}`` path exists.
    """
    if not isinstance(label, str):
        raise ValueError(f"interest-type label must be a string, got {label!r}")
    for record in interest_type_records():
        if record.label == label:
            return {"adjacent_labels": record.adjacent_labels}
    known = [record.label for record in interest_type_records()]
    raise ValueError(
        f"unknown interest type {label!r}; expected one of {known}"
    )


def _characteristic_family_records(
    characteristic_class: URIRef,
) -> tuple[CharacteristicFamilyRecord, ...]:
    """Declared family concepts of one class, deterministically sorted."""
    records = [
        CharacteristicFamilyRecord(
            iri=str(subject), label=_label_of(subject)
        )
        for subject in _scheme_subjects(LW.workerCharacteristicScheme)
        if (subject, RDF.type, characteristic_class) in ONTOLOGY
    ]
    records.sort(key=lambda record: record.label)
    return tuple(records)


@lru_cache(maxsize=1)
def work_value_cluster_records() -> tuple[CharacteristicFamilyRecord, ...]:
    """Six legacy O*NET work-value clusters, alphabetically sorted."""
    return _characteristic_family_records(LW.WorkValueCluster)


@lru_cache(maxsize=1)
def work_style_family_records() -> tuple[CharacteristicFamilyRecord, ...]:
    """The seven revised O*NET Work Styles dimensions, sorted by label."""
    return _characteristic_family_records(LW.WorkStyleFamily)


@lru_cache(maxsize=1)
def ability_domain_records() -> tuple[CharacteristicFamilyRecord, ...]:
    """Fleishman's four published ability domains, alphabetically sorted."""
    return _characteristic_family_records(LW.AbilityDomain)
