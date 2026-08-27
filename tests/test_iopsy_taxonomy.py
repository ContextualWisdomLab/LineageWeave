"""Unit and integration tests for the Industrial and Organizational (I/O)
Psychology Semantic Layer (ADR 0251).

Verifies the formal mapping from Functional Job Analysis (FJA Data/People/Things)
to cognitive, affective, and behavioral constructs, ensuring theoretical
grounding, deterministic ordering, and fail-closed validation.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef
from rdflib.namespace import RDF, SKOS

from lineageweave.iopsy_taxonomy import (
    IOPSY_CATEGORIES,
    IOPsyConstructRecord,
    IOPsyRelationRecord,
    WorkerFunctionIOPsyProfile,
    affective_construct_records,
    all_iopsy_construct_records,
    all_iopsy_relation_records,
    behavioral_construct_records,
    cognitive_construct_records,
    derive_composite_job_profile,
    iopsy_construct_record,
    iopsy_profile_for_worker_function,
    relations_for_construct,
)
from lineageweave.ontology import LW, ONTOLOGY
from lineageweave.worker_function_taxonomy import worker_function_records


def test_iopsy_categories_constant() -> None:
    """The three standard psychological domains are declared."""
    assert IOPSY_CATEGORIES == ("cognitive", "affective", "behavioral")


def test_cognitive_constructs_coverage() -> None:
    """All declared cognitive constructs parse with complete metadata."""
    records = cognitive_construct_records()
    assert len(records) >= 20
    for record in records:
        assert isinstance(record, IOPsyConstructRecord)
        assert record.category == "cognitive"
        assert record.iri.startswith("https://contextualwisdomlab.github.io/LineageWeave/ontology#cog")
        assert len(record.label) > 0
        assert len(record.dimension) > 0
        assert len(record.theoretical_basis) > 0
        assert len(record.definition) > 0


def test_affective_constructs_coverage() -> None:
    """All declared affective constructs parse with complete metadata."""
    records = affective_construct_records()
    assert len(records) >= 20
    for record in records:
        assert isinstance(record, IOPsyConstructRecord)
        assert record.category == "affective"
        assert record.iri.startswith("https://contextualwisdomlab.github.io/LineageWeave/ontology#aff")
        assert len(record.label) > 0
        assert len(record.dimension) > 0
        assert len(record.theoretical_basis) > 0
        assert len(record.definition) > 0


def test_behavioral_constructs_coverage() -> None:
    """All declared behavioral constructs parse with complete metadata."""
    records = behavioral_construct_records()
    assert len(records) >= 25
    for record in records:
        assert isinstance(record, IOPsyConstructRecord)
        assert record.category == "behavioral"
        assert record.iri.startswith("https://contextualwisdomlab.github.io/LineageWeave/ontology#beh")
        assert len(record.label) > 0
        assert len(record.dimension) > 0
        assert len(record.theoretical_basis) > 0
        assert len(record.definition) > 0


def test_all_iopsy_construct_records_aggregation() -> None:
    """Aggregation matches the sum of domain-specific collections."""
    all_recs = all_iopsy_construct_records()
    cog_recs = cognitive_construct_records()
    aff_recs = affective_construct_records()
    beh_recs = behavioral_construct_records()

    assert len(all_recs) == len(cog_recs) + len(aff_recs) + len(beh_recs)
    iris = {r.iri for r in all_recs}
    assert len(iris) == len(all_recs)


def test_iopsy_construct_lookup_by_iri_and_local_name() -> None:
    """Constructs can be resolved by full canonical IRI or local fragment."""
    wm = iopsy_construct_record("cogWorkingMemoryAllocation")
    assert wm is not None
    assert wm.label == "Working Memory Allocation"
    assert wm.category == "cognitive"
    assert "Baddeley" in wm.theoretical_basis

    wm_full = iopsy_construct_record(str(LW.cogWorkingMemoryAllocation))
    assert wm_full == wm

    burnout = iopsy_construct_record("affBurnoutEmotionalExhaustion")
    assert burnout is not None
    assert burnout.category == "affective"
    assert "Maslach" in burnout.theoretical_basis

    ocb = iopsy_construct_record("behOcbIndividualAltruism")
    assert ocb is not None
    assert ocb.category == "behavioral"
    assert "Organ" in ocb.theoretical_basis

    assert iopsy_construct_record("nonExistentConstruct") is None


def test_every_worker_function_has_iopsy_profile() -> None:
    """Every one of the 24 FJA worker functions maps to a valid profile."""
    for wf in worker_function_records():
        profile = iopsy_profile_for_worker_function(wf.domain, wf.rank)
        assert profile is not None
        assert isinstance(profile, WorkerFunctionIOPsyProfile)
        assert profile.function_domain == wf.domain
        assert profile.function_rank == wf.rank
        assert profile.function_label == wf.label

        # Every worker function demands at least one cognitive process
        assert len(profile.cognitive_demands) > 0

        # High-complexity Data functions demand problem solving or decision making
        if wf.domain == "data" and wf.rank == 0:
            demands = {c.label for c in profile.cognitive_demands}
            assert "Complex Problem Solving" in demands

        # People functions demand emotional labor or interpersonal interactions
        if wf.domain == "people":
            assert (
                len(profile.emotional_labor_demands) > 0
                or len(profile.interpersonal_behaviors) > 0
                or len(profile.affective_demands) > 0
            )

        # Things functions demand psychomotor behavior or safety
        if wf.domain == "things":
            behaviors = {b.label for b in profile.behavioral_manifestations}
            assert "Safety Compliance" in behaviors or len(profile.psychomotor_behaviors) > 0


def test_iopsy_profile_invalid_domain_or_rank() -> None:
    """Profile retrieval fails closed for undeclared domains or ranks."""
    with pytest.raises(ValueError, match="unknown worker-function domain"):
        iopsy_profile_for_worker_function("invalid_domain", 0)

    assert iopsy_profile_for_worker_function("data", 99) is None


def test_all_iopsy_relations_declared() -> None:
    """Relation records capture demand links and nomological inter-construct paths."""
    relations = all_iopsy_relation_records()
    assert len(relations) > 50

    predicates = {r.predicate_iri for r in relations}
    assert str(LW.requiresCognitiveDemand) in predicates
    assert str(LW.elicitsEmotionalDemand) in predicates
    assert str(LW.manifestsInBehavior) in predicates
    assert str(LW.cognitivelyMediates) in predicates
    assert str(LW.affectivelyDrives) in predicates
    assert str(LW.buffersBurnout) in predicates


def test_relations_for_construct_queries() -> None:
    """Relations linked to a specific construct can be retrieved bidirectionally."""
    exhaustion_rels = relations_for_construct("affBurnoutEmotionalExhaustion")
    assert len(exhaustion_rels) > 0

    # Surface acting induces burnout risk of emotional exhaustion
    inducing = [
        r for r in exhaustion_rels
        if r.target_iri == str(LW.affBurnoutEmotionalExhaustion)
        and r.predicate_iri == str(LW.inducesBurnoutRisk)
    ]
    assert len(inducing) > 0

    # Emotional exhaustion drives turnover behavior
    driving = [
        r for r in exhaustion_rels
        if r.source_iri == str(LW.affBurnoutEmotionalExhaustion)
        and r.target_iri == str(LW.behTurnover)
    ]
    assert len(driving) > 0


def test_derive_composite_job_profile() -> None:
    """Composite job psychological profile aggregates multi-domain FJA ratings."""
    ratings = {"data": 1, "people": 3, "things": 2}
    composite = derive_composite_job_profile(ratings)

    assert composite["fja_ratings"] == ratings
    assert len(composite["profiles"]) == 3
    assert len(composite["cognitive_demands"]) > 0
    assert len(composite["affective_demands"]) > 0
    assert len(composite["behavioral_manifestations"]) > 0

    cog_labels = {c.label for c in composite["cognitive_demands"]}
    assert "Strategic Decision Making" in cog_labels
    assert "Task Structuring" in cog_labels
    assert "Situational Awareness" in cog_labels

    beh_labels = {b.label for b in composite["behavioral_manifestations"]}
    assert "Transactional Supervision" in beh_labels
    assert "Safety Compliance" in beh_labels


def test_derive_composite_job_profile_validation() -> None:
    """Invalid ranks in composite profile request raise ValueError."""
    with pytest.raises(ValueError, match="Invalid rank"):
        derive_composite_job_profile({"data": 10})
