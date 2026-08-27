# ADR 0248: Evidence-bound occupational constructs

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0011](0011-prov-o-standard-relations.md), [ADR 0065](0065-prov-o-provenance-boundary.md), [ADR 0184](0184-ontology-provenance-explorer.md), [ADR 0232](0232-worker-function-taxonomy-in-the-published-ontology.md)

## Context

ADR 0232 publishes the 24 DOT/FJA Data, People, and Things worker
functions, but those functions describe how work relates to data, people,
or things. They are not cognitive abilities, affective reactions,
personality tendencies, or observed behavior. Treating Data as cognition,
People as affect, or Things as behavior would invent a crosswalk that the
authorities do not publish.

The O*NET 31.0 Content Model already supplies maintained identifiers and
hierarchies for abilities, work styles, skills, work activities, work
context, and tasks. It also publishes specific Ability-to-Work-Activity and
Work-Style-to-Work-Activity linkages. Its downloadable RDF graph is the
authoritative reusable semantic source; copying thousands of changing terms
into the LineageWeave namespace would create a stale second vocabulary.
O*NET work styles are personality tendencies, not momentary affect.
EmotionML likewise requires an explicitly named emotion vocabulary because
affective science has no single default category set.

## Decision

1. Keep five non-equivalent construct classes in the published ontology:
   `CognitiveAbility`, `WorkStyle`, `WorkActivity`, `AffectiveReaction`, and
   `PerformanceBehavior`, all subclasses of `OccupationalConstruct`.
   FJA `WorkerFunction` remains a separate class and concept scheme.
2. Reuse official, versioned external identifiers and relationships. O*NET
   31.0 RDF is authoritative for O*NET concepts and its published linkages;
   LineageWeave does not remint or paraphrase those terms. Affect must name an
   EmotionML-compatible vocabulary. No configured source means unavailable.
3. A source Post may `supportsOccupationalConstruct` only through an
   `OccupationalConstructAssertion`: an RDF-reified statement with exactly
   one Post subject, the fixed predicate, one construct object, a non-empty
   verbatim evidence span, `prov:wasDerivedFrom` that same Post, and
   `prov:generatedAtTime`. SHACL rejects incomplete projections.
4. The assertion is evidence about record content, not a person trait,
   diagnosis, ability score, job requirement, or causal effect. Person-,
   job-, task-, or position-level binding needs a separate normalized schema
   decision with authorization, subject identity, event/system time,
   validity, and measurement provenance.
5. Only source-published cross-scheme links may be materialized. The O*NET
   Ability-to-Work-Activity and Work-Style-to-Work-Activity datasets qualify.
   A documented loose FJA/GWA orientation may be cited as a qualified
   association, never as `owl:equivalentClass`, `owl:sameAs`,
   `skos:exactMatch`, `skos:closeMatch`, or a rank mapping. Transitive chains
   must not manufacture a DPT-to-ability or DPT-to-work-style assertion.
6. No rank, confidence, intensity, importance, level, or weight is computed
   locally. Published measurements remain tied to their source scale and
   sampling metadata; TEPP and fast-mlsirm retain numerical authority under
   ADR 0208.

## Considered options

| Option | Outcome |
|---|---|
| Map Data/People/Things directly to cognitive/affective/behavioral facets | Rejected: intuitive but unsupported, collapses work functions into psychological constructs |
| Copy the complete O*NET vocabulary into local IRIs | Rejected: duplicates a maintained linked-data source and creates quarterly drift |
| Link external constructs through evidence-bearing assertions | Accepted: preserves authoritative identifiers, provenance, uncertainty, and an additive persistence path |

## Consequences

- The semantic layer can represent the requested construct families and their
  evidence relationship without claiming that the first source mention is a
  measured person attribute.
- Complete O*NET breadth remains available through its maintained RDF graph;
<<<<<<< HEAD
  runtime ingestion and persistence are still unavailable until a connector
  and normalized assertion tables are accepted and shipped.
=======
  ADRs 0249 and 0250 add normalized assertion persistence and official catalog
  synchronization. ADR 0253 supplies catalog-bound record extraction through
  contextual-orchestrator without a local similarity or scoring heuristic.
>>>>>>> origin/main
- Actual affect stays absent unless the evidence names a conforming affect
  vocabulary and supports the reaction; work style is never relabeled affect.
- Unsupported equivalence and causal links fail closed rather than becoming
  graph navigation facts.

## Verification

- `tests/test_ontology.py` pins class separation, direct assertion direction,
  prohibited FJA equivalence, and PROV-O requirements.
- `tests/test_ontology_shapes.py` validates complete assertion projections and
  rejects missing evidence or derivation.
- Ontology publication tests continue to prove deterministic Turtle,
  JSON-LD, N-Triples, SHACL, and human-readable output.

## References

See
[`docs/doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md`](../doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md)
for the APA 7 evidence register and adoption limits.
