# ADR 0245: Occupational classification and worker-characteristic taxonomy in the published ontology

**Status:** Accepted
**Date:** 2026-08-26
**Extends:** [ADR 0004](0004-knowledge-graph-ontology.md), [ADR 0145](0145-psychometric-channel-weight-estimation.md), [ADR 0207](0207-repository-case-ontology-namespace-canonical.md), [ADR 0232](0232-worker-function-taxonomy-in-the-published-ontology.md)
<<<<<<< HEAD
=======
**Superseded in part by:** [ADR 0252](0252-complete-2018-soc-hierarchy.md), which expands the major-group-only scheme into the complete 2018 SOC hierarchy.
>>>>>>> origin/feat/onet-rating-occupation-filter

## Context

Industrial and organizational psychology classifies work twice: once by
*what* the occupation is -- the 2018 Standard Occupational Classification
major groups, which the O*NET program publishes as its job families --
and once by *which human characteristics* doing it exercises. The O*NET
content model organizes those characteristics under every occupation as
abilities, occupational interests, work values, and work styles
(Peterson et al., 1999; Peterson et al., 2001). Holland's RIASEC hexagon
supplies the interest vocabulary with a published structural claim about
adjacency (Holland, 1997); Hogan and Holland (2003) established the
relationship between personality and job performance but is not the source
of the O*NET vocabulary; the revised O*NET Work Styles report supplies its
seven higher-order dimensions. Fleishman and Quaintance (1984) supply the
four ability domains. O*NET 31.0 publishes four Job Zone categories under
source values 2 through 5 after combining the former first two zones.

ADR 0232 already publishes the DOT/FJA worker functions, so stored
evidence can name *how* a worker functioned on data, people, or things.
It cannot yet say *which occupational family* the evidence belongs to,
nor resolve its cognitive, affective, and behavioral content into the
published characteristic families. The ontology is again the correct
home, under the same two constraints that bound ADR 0232:

1. The lookup-code round trip (`tests/test_ontology.py`) must stay
   untouched: these concepts are not `common_lookup_value` rows.
2. Measurement stays governed by ADR 0145: no numeric importance or
   level rating from any occupational profile may be imported, fitted,
   or renormalized.

## Decision

1. Publish all 23 major groups of the 2018 Standard Occupational
   Classification verbatim -- official titles and ``NN-0000`` codes --
   as a `skos:ConceptScheme` (`:socMajorGroupScheme`) of
   `:OccupationalMajorGroup` concepts, matching the O*NET job-family
   grouping.
2. Publish the four O*NET 31.0 Job Zone categories (`:jobZoneScheme`) with
   their published names and source values (`:jobZoneLevel` 2-5). These
   values are source identifiers, not fitted or ordinal weights.
3. Publish distinct source-native worker-characteristic families, without
   collapsing them into cognition, affect, or behavior, as subclasses of
   `:WorkerCharacteristic` inside one scheme
   (`:workerCharacteristicScheme`):
   - Fleishman's four ability domains (`:AbilityDomain`);
   - Holland's six RIASEC interest types (`:InterestType`), each with
     the standard Interest Profiler family description verbatim;
   - the six historical O*NET work-value clusters (`:WorkValueCluster`),
     explicitly labeled legacy because O*NET 31.0 no longer publishes the
     Work Values branch;
   - the seven higher-order dimensions in the revised O*NET Work Styles
     structure (`:WorkStyleFamily`). The 21 lower-order dimensions and the
     separate four-component occupation-level analysis remain an explicit
     import gap; neither may be inferred from these family nodes.
4. Assert only the published structural relation between interest
   types: `:riasecAdjacentTo`, a symmetric property whose six asserted
   pairs are exactly the hexagonal ring edges Realistic-Investigative-
   Artistic-Social-Enterprising-Conventional-Realistic (Holland, 1997).
   Adjacency is a similarity ordering, not a score.
5. Declare `:OccupationalClassification` as the future common hierarchy
   class and four domain/range-typed derivation properties --
   `:occupationalAbilityDemand`, `:occupationalInterestProfile`,
   `:occupationalValueOrientation`, and `:occupationalWorkStyleNorm` --
   but assert **no instance binding**. Binding a major group to a
   characteristic requires importing a versioned released source
   profile (for example an O*NET database release) with provenance in
   its own future decision; inventing per-family profiles here would
   fabricate evidence.
6. Like ADR 0232, none of these concepts carries `:lookupCode`; ranks
   and levels are scale positions from published tables and are never
   used as weights; every IRI is minted in the canonical
   repository-case namespace (ADR 0207).
7. The application read model lives in `lineageweave/io_taxonomy.py`:
   cached, deterministically sorted records for each scheme;
   well-formed-key lookups that return ``None`` for genuinely
   undeclared codes or levels (honest unknown); fail-closed
   ``ValueError`` for malformed keys, malformed TTL declarations,
   neighbors outside the closed RIASEC vocabulary, or a type without
   exactly two neighbors.
8. Each concept scheme names its source entities through
   `prov:wasDerivedFrom`. Source entities retain title, publisher or creator,
   explicit release/version, source URL, and applicable rights or license.
   `:sourceArtifactSha256` is present only when an exact stable artifact was
   downloaded and hashed; the O*NET 31.0 Job Zone JSON is pinned to SHA-256
   `f66d665a2e507c825a71aedb2c13ba22765e8259bc6c7fe5b3cdfd8105475a66`.
   A dynamic page without a reproducible artifact carries no invented digest.

## Consequences

- Job families, job zones, and the full published
  source-native characteristic-family vocabulary become addressable and
  citable inside the semantic layer before any persistence decision exists.
- A classification never supports inferring an individual's cognition,
  affect, personality, behavior, competence, suitability, or job
  performance. Those uses require their own intended-use validity and
  fairness evidence and are outside this decision.
- Per-major-group characteristic profiles remain deliberately absent:
  the derivation properties make their future shape typed and
  addressable without asserting anything the sources do not state at
  this granularity.
- Adding DB-backed profile bindings later means one migration plus
  provenance-bearing import of a released source database -- the
  extension path is additive by construction, mirroring ADR 0232.
- `tests/test_io_taxonomy.py` pins the published titles, counts,
  adjacency structure, closed vocabularies, and fail-closed lookups, so
  drift toward invented constructs fails CI.

## Verification

- `tests/test_io_taxonomy.py`: completeness (23 groups, 4 zones, 6
  types, 6 legacy clusters, 7 style dimensions, 4 ability domains), verbatim
  official titles, code-shape validation, published hexagon adjacency,
  deterministic ordering, canonical namespace, lookup round-trip
  isolation, and fail-closed lookups.
- `tests/test_ontology.py` continues to pass unchanged: the round trip
  sees no new lookup codes.
- Source-provenance tests require every new scheme to resolve to the declared
  PROV entity and verify O*NET version, publisher, CC BY 4.0 license, artifact
  digest, and SOC version/publisher/rights metadata.

## References

Fleishman, E. A., & Quaintance, M. K. (1984). *Taxonomies of human
performance: The description of human tasks*. Academic Press.

Hogan, J., & Holland, B. (2003). Using theory to evaluate personality
and job-performance relations: A socioanalytic interpretation.
*Journal of Applied Psychology, 88*(1), 100-112.
https://doi.org/10.1037/0021-9010.88.1.100

Holland, J. L. (1997). *Making vocational choices: A theory of
vocational personalities and work environments* (3rd ed.). Psychological
Assessment Resources.

Peterson, N. G., Mumford, M. D., Borman, W. C., Jeanneret, P. R.,
Fleishman, E. A., Levin, K. Y., Campion, M. A., Mayfield, M. S.,
Morgeson, F. P., Pearlman, K., Gowing, M. K., Lancaster, A. R., Silver,
M. B., & Dye, D. M. (2001). Understanding work using the Occupational
Information Network (O*NET): Implications for practice and research.
*Personnel Psychology, 54*(2), 451-492.
https://doi.org/10.1111/j.1744-6570.2001.tb00098.x

National Center for O*NET Development. (2024). *Revisiting the work
styles domain of the O*NET content model* (updated May 2026).
https://www.onetcenter.org/reports/Work_Styles_New.html

National Center for O*NET Development. (2026). *Job zone reference:
O*NET 31.0 database*.
https://www.onetcenter.org/dictionary/31.0/json/job_zone_reference.html

U.S. Department of Labor. (2018). *2018 Standard Occupational
Classification System*. Bureau of Labor Statistics.
https://www.bls.gov/soc/
