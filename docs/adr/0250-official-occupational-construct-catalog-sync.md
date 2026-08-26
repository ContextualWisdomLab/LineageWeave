# ADR 0250: Official occupational construct catalog synchronization

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0248](0248-occupational-construct-evidence-boundary.md), [ADR 0249](0249-occupational-construct-assertion-persistence.md)

## Context

The assertion store accepted by ADR 0249 needs a complete, reviewable catalog
before contextual-orchestrator can select a construct. Asking a model to invent
an O*NET label or IRI would defeat ADR 0248. Shipping a hand-maintained subset
would also drift from O*NET's quarterly releases and omit most of the requested
cognitive and behavioral domain.

O*NET 31.0 publishes a machine-readable Content Model Reference with stable
element identifiers, names, hierarchy positions, descriptions, release
documentation, and CC BY 4.0 attribution terms. Its hierarchy explicitly places
cognitive abilities below `1.A.1`, work styles below `1.D`, and work activities
below `4.A`. These are source classifications, not a LineageWeave heuristic.

## Decision

1. An operator-only synchronizer reads the fixed HTTPS O*NET 31.0 Content Model
   Reference JSON document. The URL, release, vocabulary IRI, license IRI, and
   attribution are code-reviewed constants; runtime input cannot redirect the
   process to an arbitrary host.
2. The synchronizer imports every element at or below the three published
   hierarchy roots: `1.A.1` as `cognitive_ability`, `1.D` as `work_style`, and
   `4.A` as `work_activity`. It preserves official labels, optional descriptions,
   and permanent `https://data.onetcenter.org/element/{element_id}` IRIs.
3. The canonical decoded JSON SHA-256 is stored on the vocabulary release.
   Replaying the same document is idempotent. A changed document under the same
   release, or conflicting construct metadata, aborts the transaction instead
   of rewriting history.
4. This catalog does not import occupation ratings, scores, scale values,
   ability-to-activity linkages, work-style linkages, FJA crosswalks, affective
   vocabularies, or person/job bindings. Those require their own provenance and
   decision records.
5. Catalog synchronization is a prerequisite for extraction. The extractor
   may select only catalog rows supplied to contextual-orchestrator; it may not
   mint a label, family, description, or IRI.

## Consequences

- The semantic layer gains the full official breadth needed for catalog-bound
  cognitive, work-style, and work-activity assertions without copying these
  terms into the LineageWeave ontology namespace.
- O*NET descriptions that are absent remain `NULL`; LineageWeave does not fill
  them with generated prose.
- Affective reactions and performance interpretation remain unavailable until
  an authoritative vocabulary and evidence contract are accepted.

## Verification

- Parser tests cover all three roots, exact IRI construction, ignored unrelated
  rows, malformed payloads, and deterministic source hashing.
- Schema tests require replay-safe catalog description and source-hash columns.
- Synchronization tests prove idempotent UPSERTs and post-write exact metadata
  comparison.

## References

See
[`docs/doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md`](../doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md).
