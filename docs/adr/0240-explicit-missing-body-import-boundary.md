# ADR 0240: Explicit missing-body import boundary

**Status:** Accepted
**Date:** 2026-08-26
**Extends:** [ADR 0102](0102-semantic-source-unit-boundaries.md)

## Context

An authorized source export can contain titles, lifecycle fields, customer and
project codes, lineage keys, actors, timestamps, and source-artifact provenance
while exposing no record body. Requiring a non-empty body makes every such row
unimportable. Copying the title into the body would instead manufacture body
evidence and falsely imply semantic-unit coverage.

## Decision

1. The PostgreSQL importer accepts exactly one of a mapped body column or
   `--no-body-dimension-evidence` containing a non-blank operator statement.
   The importer records that attestation but does not use an arbitrary text-
   length threshold as a proxy for evidence quality.
2. A missing body persists as the empty source representation. The title stays
   `post_title`; it is never copied into `post_body` or emitted as a paragraph.
3. Content-unit, embedding, summary, VISION, and body-search coverage remain
   unavailable until an authoritative body/file source is connected.
4. Structured source fields retain their existing raw provenance columns and
   semantic-hint boundaries. Their presence does not prove an entity binding.
5. The import result repeats the evidence statement so an operator can retain
   it with private runtime evidence. Repository artifacts contain aggregates
   only.
6. `scripts/audit_source_semantic_coverage.py` reproduces availability counts
   from caller-mapped columns and emits no source values.
7. RDF `bodyAvailable` and its published SHACL constraint use the same
   whitespace predicate as the Python projector, including Unicode separator,
   next-line, and legacy information-separator characters. A body containing
   only those characters is unavailable; validators must not reinterpret it as
   semantic evidence.
8. A no-body-dimension re-import preserves an already-populated target body
   atomically in the source-post UPSERT. The preserved body is also the input
   to revision and semantic-content persistence; an unavailable source
   dimension must not erase evidence acquired from an authoritative body
   source.

## Consequences

Title-only structured records can participate in explicitly supported
lineage and source-metadata views without fabricated prose. Semantic body
coverage remains honestly incomplete and can be retried after the owning
source supplies bodies.

## Evidence

A 2026-08-26 aggregate-only source inspection found 43,814 rows, 43,814
non-empty titles, zero non-empty bodies, 40,001 customer-code rows, 4,490
project-code rows, and complete process-unit, sales-pool, actor, and
source-artifact provenance fields. No source value, identifier, organization,
or artifact path was copied into this repository.
