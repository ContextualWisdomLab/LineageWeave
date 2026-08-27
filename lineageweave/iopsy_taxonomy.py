"""The Industrial and Organizational (I/O) Psychology Semantic Layer
projected over the published LineageWeave ontology (ADR 0251).

This module establishes the formal semantic layer connecting Sydney A.
Fine's Functional Job Analysis (FJA Data/People/Things worker functions;
Fine & Cronshaw, 1999) to foundational constructs in Industrial and
Organizational Psychology across three primary psychological domains:

1. **Cognitive Domain**: Information processing, working memory capacity,
   complex problem solving, strategic decision making, cognitive appraisal,
   metacognitive monitoring, executive functioning, situational awareness,
   selective/divided attention, and mental workload (Baddeley, 2000;
   Endsley, 1995; Flavell, 1979; Kahneman, 1973; Lazarus & Folkman, 1984;
   Miyake et al., 2000; Newell & Simon, 1972; Sweller, 1988).
2. **Affective Domain**: Emotional labor (surface acting, deep acting,
   genuine expression), emotion regulation (cognitive reappraisal,
   expressive suppression), burnout dimensions (emotional exhaustion,
   depersonalization/cynicism, reduced personal accomplishment), work
   engagement (vigor, dedication, absorption), psychological safety, job
   satisfaction, multidimensional organizational commitment (affective,
   continuance, normative), occupational stress/strain, and affectivity
   (Ashforth & Humphrey, 1993; Bakker & Demerouti, 2007; Edmondson, 1999;
   Grandey, 2000; Gross, 1998; Hochschild, 1983; Karasek, 1979; Locke, 1976;
   Maslach et al., 2001; Meyer & Allen, 1991; Schaufeli et al., 2002;
   Watson, Clark, & Tellegen, 1988).
3. **Behavioral Domain**: Core task performance, technical precision,
   error recovery, organizational citizenship behavior (OCB-I altruism and
   courtesy; OCB-O conscientiousness, civic virtue, sportsmanship),
   counterproductive work behavior (interpersonal, organizational,
   production, and property deviance), proactive and voice behavior,
   safety compliance and participation, adaptive performance dimensions,
   leadership and mentoring behaviors, collaborative teamwork, and
   withdrawal behaviors (absenteeism, presenteeism, turnover) (Bennett &
   Robinson, 2000; Borman & Motowidlo, 1993; Campbell, 1990; Christian et
   al., 2009; Mobley, 1977; Morrison, 2014; Neal & Griffin, 2006; Organ,
   1988; Parker et al., 2010; Pulakos et al., 2000; Spector et al., 2006;
   Van Dyne & LePine, 1998; Williams & Anderson, 1991).

Provenance and Psychological Discipline:
- All constructs and relations are projected verbatim from the authoritative
  `docs/ontology/lineageweave-kg.ttl` OWL/SKOS graph.
- Scale positions are non-fitted definitional anchors; no fabricated weights
  or speculative parameters are introduced (governed by ADR 0145).
- Queries fail closed: undeclared constructs or relations return `None` or
  empty collections rather than synthetic placeholders.

References
----------
Bakker, A. B., & Demerouti, E. (2007). The job demands-resources model: State
    of the art. Journal of Managerial Psychology, 22(3), 309-328.
Borman, W. C., & Motowidlo, S. J. (1993). Expanding the criterion domain to
    include elements of contextual performance. In N. Schmitt & W. C. Borman
    (Eds.), Personnel selection in organizations (pp. 71-98). Jossey-Bass.
Campbell, J. P. (1990). Modeling the performance prediction problem in
    industrial and organizational psychology. In M. D. Dunnette & L. M. Hough
    (Eds.), Handbook of industrial and organizational psychology (2nd ed.,
    Vol. 1, pp. 687-732). Consulting Psychologists Press.
Christian, M. S., Bradley, J. C., Wallace, J. C., & Burke, M. J. (2009).
    Workplace safety: A meta-analysis of the roles of person and situation
    factors. Journal of Applied Psychology, 94(5), 1103-1127.
Edmondson, A. (1999). Psychological safety and learning behavior in work
    teams. Administrative Science Quarterly, 44(2), 350-383.
Fine, S. A., & Cronshaw, S. F. (1999). Functional job analysis: A foundation
    for human resources management. Lawrence Erlbaum Associates.
Grandey, A. A. (2000). Emotion regulation in the workplace: A new way to
    conceptualize emotional labor. Journal of Occupational Health Psychology,
    5(1), 95-110.
Hochschild, A. R. (1983). The managed heart: Commercialization of human
    feeling. University of California Press.
Karasek, R. A. (1979). Job demands, job decision latitude, and mental strain:
    Implications for job redesign. Administrative Science Quarterly, 24(2),
    285-308.
Maslach, C., Schaufeli, W. B., & Leiter, M. P. (2001). Job burnout. Annual
    Review of Psychology, 52(1), 397-422.
Organ, D. W. (1988). Organizational citizenship behavior: The good soldier
    syndrome. Lexington Books.
Pulakos, E. D., Arad, S., Donovan, M. A., & Plamondon, K. E. (2000).
    Adaptability in the workplace: Development of a taxonomy of adaptive
    performance. Journal of Applied Psychology, 85(4), 612-624.
Schaufeli, W. B., Salanova, M., González-Romá, V., & Bakker, A. B. (2002).
    The measurement of engagement and burnout: A two sample confirmatory
    factor analytic approach. Journal of Happiness Studies, 3(1), 71-92.
Spector, P. E., Fox, S., Penney, L. M., Bruursema, K., Goh, A., & Kessler,
    S. (2006). The dimensionality of counterproductivity: Are all
    counterproductive behaviors created equal? Journal of Vocational
    Behavior, 68(3), 446-460.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from rdflib import URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from .ontology import LW, ONTOLOGY
from .worker_function_taxonomy import (
    WORKER_FUNCTION_DOMAINS,
    worker_function,
)

#: Standard psychological construct categories recognized by the semantic layer.
IOPSY_CATEGORIES: tuple[str, ...] = ("cognitive", "affective", "behavioral")

#: Predicate mappings for worker function demands and manifestations.
WORKER_FUNCTION_DEMAND_PREDICATES: tuple[tuple[str, URIRef], ...] = (
    ("cognitive_demands", LW.requiresCognitiveDemand),
    ("mental_workload_demands", LW.imposesMentalWorkload),
    ("affective_demands", LW.elicitsEmotionalDemand),
    ("emotional_labor_demands", LW.requiresEmotionalLabor),
    ("behavioral_manifestations", LW.manifestsInBehavior),
    ("psychomotor_behaviors", LW.requiresPsychomotorBehavior),
    ("interpersonal_behaviors", LW.requiresInterpersonalBehavior),
)

#: Inter-construct nomological relationship predicates.
INTER_CONSTRUCT_PREDICATES: tuple[tuple[str, URIRef], ...] = (
    ("cognitively_mediates", LW.cognitivelyMediates),
    ("affectively_drives", LW.affectivelyDrives),
    ("moderates_strain", LW.moderatesStrain),
    ("buffers_burnout", LW.buffersBurnout),
    ("induces_burnout_risk", LW.inducesBurnoutRisk),
    ("reciprocally_influences", LW.reciprocallyInfluences),
)


@dataclass(frozen=True)
class IOPsyConstructRecord:
    """An immutable, strongly-typed representation of an I/O psychology construct.

    Attributes directly project the formal OWL/SKOS declarations in the
    canonical knowledge graph ontology without runtime estimation or remapping.
    """

    iri: str
    """The canonical repository-case ontology IRI for this construct."""

    category: str
    """The high-level psychological category: ``cognitive``, ``affective``, or ``behavioral``."""

    label: str
    """The preferred label of the construct (e.g. ``'Working Memory Allocation'``)."""

    dimension: str
    """The specific psychological sub-dimension (e.g. ``'cognitive_capacity'``)."""

    theoretical_basis: str
    """The primary APA 7th academic literature foundation anchoring this construct."""

    definition: str
    """The comprehensive psychological definition of the construct."""


@dataclass(frozen=True)
class IOPsyRelationRecord:
    """A directional relationship triple between two nodes in the I/O psychology nexus.

    Captures functional-to-construct demands or inter-construct nomological links
    (such as cognitive mediation, affective drive, or burnout buffering).
    """

    source_iri: str
    """The IRI of the subject node (e.g. a worker function or psychological construct)."""

    source_label: str
    """Human-readable display label for the source node."""

    predicate_iri: str
    """The IRI of the ontological object property expressing the relationship."""

    predicate_label: str
    """Human-readable label for the relational predicate."""

    target_iri: str
    """The IRI of the target construct node."""

    target_label: str
    """Human-readable display label for the target construct."""

    target_category: str
    """The psychological category (``cognitive``, ``affective``, or ``behavioral``) of the target."""


@dataclass(frozen=True)
class WorkerFunctionIOPsyProfile:
    """The complete psychological demand and manifestation profile of an FJA worker function.

    Aggregates the cognitive capacities required, mental workload imposed, affective
    demands elicited, emotional labor expected, and behavioral performance dimensions.
    """

    function_domain: str
    """The Functional Job Analysis domain (``data``, ``people``, or ``things``)."""

    function_rank: int
    """The definitional ordinal rank (0 to 8) within the domain."""

    function_label: str
    """The official preferred label of the worker function."""

    cognitive_demands: tuple[IOPsyConstructRecord, ...]
    """Cognitive capacities and information-processing operations demanded by the function."""

    mental_workload_demands: tuple[IOPsyConstructRecord, ...]
    """Mental workload dimensions imposed during execution."""

    affective_demands: tuple[IOPsyConstructRecord, ...]
    """Emotional states, attitudes, or stress appraisals elicited."""

    emotional_labor_demands: tuple[IOPsyConstructRecord, ...]
    """Emotional labor strategies (surface/deep acting) required for interpersonal display."""

    behavioral_manifestations: tuple[IOPsyConstructRecord, ...]
    """Core task and contextual performance behaviors manifested."""

    psychomotor_behaviors: tuple[IOPsyConstructRecord, ...]
    """Physical, sensory-motor, or mechanical behaviors required."""

    interpersonal_behaviors: tuple[IOPsyConstructRecord, ...]
    """Social, collaborative, supervisory, or guidance behaviors required."""


def _parse_construct_record(subject: URIRef) -> IOPsyConstructRecord:
    """Parse one RDF subject into an ``IOPsyConstructRecord``."""
    types = set(ONTOLOGY.objects(subject, RDF.type))
    if LW.CognitiveConstruct in types:
        category = "cognitive"
    elif LW.AffectiveConstruct in types:
        category = "affective"
    elif LW.BehavioralConstruct in types:
        category = "behavioral"
    else:
        raise ValueError(f"Subject {subject} is not typed as a valid IOPsy construct")

    label = ONTOLOGY.value(subject, SKOS.prefLabel) or ONTOLOGY.value(subject, RDFS.label)
    if label is None:
        raise ValueError(f"I/O psychology construct {subject} lacks a preferred label")

    dimension = ONTOLOGY.value(subject, LW.constructDimension)
    if dimension is None:
        raise ValueError(f"I/O psychology construct {subject} lacks :constructDimension")

    theoretical_basis = ONTOLOGY.value(subject, LW.constructTheoreticalBasis)
    if theoretical_basis is None:
        raise ValueError(f"I/O psychology construct {subject} lacks :constructTheoreticalBasis")

    definition = ONTOLOGY.value(subject, SKOS.definition)
    if definition is None:
        raise ValueError(f"I/O psychology construct {subject} lacks skos:definition")

    return IOPsyConstructRecord(
        iri=str(subject),
        category=category,
        label=str(label),
        dimension=str(dimension),
        theoretical_basis=str(theoretical_basis),
        definition=str(definition),
    )


@lru_cache(maxsize=1)
def cognitive_construct_records() -> tuple[IOPsyConstructRecord, ...]:
    """Retrieve all declared cognitive construct records, deterministically sorted by label.

    Returns:
        tuple[IOPsyConstructRecord, ...]: Immutable sequence of cognitive constructs.
    """
    records = [
        _parse_construct_record(s)
        for s in ONTOLOGY.subjects(RDF.type, LW.CognitiveConstruct)
        if isinstance(s, URIRef)
    ]
    records.sort(key=lambda r: r.label)
    return tuple(records)


@lru_cache(maxsize=1)
def affective_construct_records() -> tuple[IOPsyConstructRecord, ...]:
    """Retrieve all declared affective construct records, deterministically sorted by label.

    Returns:
        tuple[IOPsyConstructRecord, ...]: Immutable sequence of affective constructs.
    """
    records = [
        _parse_construct_record(s)
        for s in ONTOLOGY.subjects(RDF.type, LW.AffectiveConstruct)
        if isinstance(s, URIRef)
    ]
    records.sort(key=lambda r: r.label)
    return tuple(records)


@lru_cache(maxsize=1)
def behavioral_construct_records() -> tuple[IOPsyConstructRecord, ...]:
    """Retrieve all declared behavioral construct records, deterministically sorted by label.

    Returns:
        tuple[IOPsyConstructRecord, ...]: Immutable sequence of behavioral constructs.
    """
    records = [
        _parse_construct_record(s)
        for s in ONTOLOGY.subjects(RDF.type, LW.BehavioralConstruct)
        if isinstance(s, URIRef)
    ]
    records.sort(key=lambda r: r.label)
    return tuple(records)


@lru_cache(maxsize=1)
def all_iopsy_construct_records() -> tuple[IOPsyConstructRecord, ...]:
    """Retrieve all cognitive, affective, and behavioral construct records across the ontology.

    Returns:
        tuple[IOPsyConstructRecord, ...]: Complete, deterministically sorted sequence of constructs.
    """
    all_records = list(cognitive_construct_records())
    all_records.extend(affective_construct_records())
    all_records.extend(behavioral_construct_records())
    all_records.sort(key=lambda r: (r.category, r.label))
    return tuple(all_records)


def iopsy_construct_record(iri_or_name: str) -> IOPsyConstructRecord | None:
    """Find a specific I/O psychology construct record by its IRI or local name.

    Args:
        iri_or_name: Full IRI (e.g. ``'https://...#cogWorkingMemoryAllocation'``)
            or local fragment name (e.g. ``'cogWorkingMemoryAllocation'``).

    Returns:
        IOPsyConstructRecord | None: The matching record or ``None`` if not found.
    """
    target = iri_or_name.strip()
    if not target.startswith("http"):
        target = f"{LW}{target}"

    for record in all_iopsy_construct_records():
        if record.iri == target:
            return record
    return None


@lru_cache(maxsize=1)
def all_iopsy_relation_records() -> tuple[IOPsyRelationRecord, ...]:
    """Retrieve all declared psychological relations across worker functions and constructs.

    Extracts all triples involving demand predicates and inter-construct links.

    Returns:
        tuple[IOPsyRelationRecord, ...]: Deterministically sorted sequence of relation records.
    """
    relations: list[IOPsyRelationRecord] = []
    predicates = [pred for _, pred in WORKER_FUNCTION_DEMAND_PREDICATES]
    predicates.extend([pred for _, pred in INTER_CONSTRUCT_PREDICATES])

    construct_map = {r.iri: r for r in all_iopsy_construct_records()}

    for pred_uri in predicates:
        pred_label = str(ONTOLOGY.value(pred_uri, RDFS.label) or pred_uri.split("#")[-1])
        for s, _, o in ONTOLOGY.triples((None, pred_uri, None)):
            if not isinstance(s, URIRef) or not isinstance(o, URIRef):
                continue
            s_iri = str(s)
            o_iri = str(o)

            # Determine source label
            if s_iri in construct_map:
                s_label = construct_map[s_iri].label
            else:
                s_label_val = ONTOLOGY.value(s, SKOS.prefLabel) or ONTOLOGY.value(s, RDFS.label)
                s_label = str(s_label_val) if s_label_val else s_iri.split("#")[-1]

            if o_iri not in construct_map:
                continue
            target_rec = construct_map[o_iri]

            relations.append(
                IOPsyRelationRecord(
                    source_iri=s_iri,
                    source_label=s_label,
                    predicate_iri=str(pred_uri),
                    predicate_label=pred_label,
                    target_iri=o_iri,
                    target_label=target_rec.label,
                    target_category=target_rec.category,
                )
            )

    relations.sort(key=lambda r: (r.source_iri, r.predicate_iri, r.target_iri))
    return tuple(relations)


def iopsy_profile_for_worker_function(domain: str, rank: int) -> WorkerFunctionIOPsyProfile | None:
    """Build the comprehensive I/O psychology profile for a given FJA worker function.

    Args:
        domain: FJA domain (``'data'``, ``'people'``, or ``'things'``).
        rank: Ordinal rank integer within the published domain limits.

    Returns:
        WorkerFunctionIOPsyProfile | None: The derived psychological demand and
            manifestation profile, or ``None`` if the function is not declared.
    """
    func = worker_function(domain, rank)
    if func is None:
        return None

    func_uri = URIRef(func.iri)
    construct_map = {r.iri: r for r in all_iopsy_construct_records()}

    def _get_targets(pred: URIRef) -> tuple[IOPsyConstructRecord, ...]:
        targets = [
            construct_map[str(o)]
            for o in ONTOLOGY.objects(func_uri, pred)
            if str(o) in construct_map
        ]
        targets.sort(key=lambda r: r.label)
        return tuple(targets)

    return WorkerFunctionIOPsyProfile(
        function_domain=domain,
        function_rank=rank,
        function_label=func.label,
        cognitive_demands=_get_targets(LW.requiresCognitiveDemand),
        mental_workload_demands=_get_targets(LW.imposesMentalWorkload),
        affective_demands=_get_targets(LW.elicitsEmotionalDemand),
        emotional_labor_demands=_get_targets(LW.requiresEmotionalLabor),
        behavioral_manifestations=_get_targets(LW.manifestsInBehavior),
        psychomotor_behaviors=_get_targets(LW.requiresPsychomotorBehavior),
        interpersonal_behaviors=_get_targets(LW.requiresInterpersonalBehavior),
    )


def relations_for_construct(iri_or_name: str) -> tuple[IOPsyRelationRecord, ...]:
    """Retrieve all incoming and outgoing relations for a specified construct.

    Args:
        iri_or_name: Full IRI or local name of the psychological construct.

    Returns:
        tuple[IOPsyRelationRecord, ...]: Sequence of associated relation records.
    """
    rec = iopsy_construct_record(iri_or_name)
    if rec is None:
        return ()

    target_iri = rec.iri
    return tuple(
        r
        for r in all_iopsy_relation_records()
        if r.source_iri == target_iri or r.target_iri == target_iri
    )


def derive_composite_job_profile(fja_ratings: dict[str, int]) -> dict[str, Any]:
    """Derive a job's composite psychological profile from its FJA domain ratings.

    Takes an FJA ratings dictionary (e.g. ``{'data': 1, 'people': 3, 'things': 2}``)
    and aggregates the combined psychological demands, emotional labor exposure,
    and performance behaviors across Data, People, and Things worker functions.

    The synthesis strictly preserves provenance:
    - No invented weights or heuristic scoring are applied.
    - Demands are aggregated into distinct, deduplicated collections preserving
      their theoretical anchors.

    Args:
        fja_ratings: Mapping of domain names to their integer ranks.

    Returns:
        dict[str, Any]: A structured composite psychological profile dictionary.
    """
    profiles: list[WorkerFunctionIOPsyProfile] = []
    for domain, (low, high) in sorted(WORKER_FUNCTION_DOMAINS.items()):
        if domain in fja_ratings:
            rank = fja_ratings[domain]
            if not isinstance(rank, int) or rank < low or rank > high:
                raise ValueError(
                    f"Invalid rank {rank!r} for domain {domain!r}; expected integer in [{low}, {high}]"
                )
            p = iopsy_profile_for_worker_function(domain, rank)
            if p is not None:
                profiles.append(p)

    all_cog: dict[str, IOPsyConstructRecord] = {}
    all_aff: dict[str, IOPsyConstructRecord] = {}
    all_beh: dict[str, IOPsyConstructRecord] = {}
    all_el: dict[str, IOPsyConstructRecord] = {}
    all_psychomotor: dict[str, IOPsyConstructRecord] = {}
    all_interpersonal: dict[str, IOPsyConstructRecord] = {}

    for prof in profiles:
        for c in prof.cognitive_demands:
            all_cog[c.iri] = c
        for c in prof.mental_workload_demands:
            all_cog[c.iri] = c
        for a in prof.affective_demands:
            all_aff[a.iri] = a
        for el in prof.emotional_labor_demands:
            all_el[el.iri] = el
        for b in prof.behavioral_manifestations:
            all_beh[b.iri] = b
        for pm in prof.psychomotor_behaviors:
            all_psychomotor[pm.iri] = pm
        for ip in prof.interpersonal_behaviors:
            all_interpersonal[ip.iri] = ip

    return {
        "fja_ratings": dict(sorted(fja_ratings.items())),
        "profiles": tuple(profiles),
        "cognitive_demands": tuple(sorted(all_cog.values(), key=lambda r: r.label)),
        "affective_demands": tuple(sorted(all_aff.values(), key=lambda r: r.label)),
        "emotional_labor_demands": tuple(sorted(all_el.values(), key=lambda r: r.label)),
        "behavioral_manifestations": tuple(sorted(all_beh.values(), key=lambda r: r.label)),
        "psychomotor_behaviors": tuple(sorted(all_psychomotor.values(), key=lambda r: r.label)),
        "interpersonal_behaviors": tuple(sorted(all_interpersonal.values(), key=lambda r: r.label)),
    }
