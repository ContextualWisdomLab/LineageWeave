# ADR 0229 — Separate the legacy ontology identifier from its compatibility document

**Decision status:** Accepted
**Date:** 2026-08-26
**Amends:** [ADR 0207](0207-repository-case-ontology-namespace-canonical.md), decisions 2, 3, and 6

## Context

ADR 0207 correctly made the repository-case namespace canonical and rejected a
second lowercase hosting surface. It nevertheless said that both namespace
documents return `200 OK`. Runtime verification contradicts that statement:
the three tested lowercase paths return `404`, while the canonical ontology and
its published `namespace-compatibility.ttl` artifact return `200`.

RFC 3986 separates identification from interaction: a URI can identify a
resource without guaranteeing network retrieval. RFC 9110 defines `404` as the
absence of a current representation at the target resource. A compatibility
mapping published at a different URL therefore does not make the legacy
namespace itself dereferenceable.

## Decision

1. The repository-case namespace remains the only canonical, dereferenceable
   LineageWeave ontology namespace.
2. Lowercase IRIs remain deprecated compatibility identifiers. They are not
   described as dereferenceable while their actual paths return `404`.
3. The term-kind-safe compatibility graph remains publicly retrievable at
   `https://contextualwisdomlab.github.io/LineageWeave/ontology/namespace-compatibility.ttl`.
   This artifact maps legacy identifiers; it is not a representation served
   from the legacy namespace.
4. Producers continue minting only repository-case IRIs. Historical RDF and
   provenance remain immutable, and the existing dry-run-first migration
   rewrites eligible stored lowercase values without touching provenance.
5. Documentation and release evidence report the canonical and compatibility
   artifact URLs separately and verify their actual HTTP status. A future
   owned lowercase route requires a new ADR and runtime proof before any
   dereferenceability claim.

## Consequences

- Consumers can resolve legacy terms through the published mapping document
  without treating a `404` namespace as a live endpoint.
- The product no longer promises a hosting surface it does not own.
- ADR 0207 remains authoritative for canonical identity, mappings, migration,
  OWL/SKOS term kinds, and SHACL; only its lowercase dereferenceability claim
  is amended.

## References

Berners-Lee, T., Fielding, R., & Masinter, L. (2005). *Uniform resource
identifier (URI): Generic syntax* (RFC 3986). RFC Editor.
https://doi.org/10.17487/RFC3986

Fielding, R., Nottingham, M., & Reschke, J. (2022). *HTTP semantics* (RFC
9110). RFC Editor. https://doi.org/10.17487/RFC9110
