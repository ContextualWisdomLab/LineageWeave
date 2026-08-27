# ADR 0255: Occupational construct ontology navigation

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0184](0184-ontology-provenance-explorer.md), [ADR 0248](0248-occupational-construct-evidence-boundary.md), [ADR 0249](0249-occupational-construct-assertion-persistence.md)

## Context

Normalized occupational assertions are reviewable in Post detail but absent
from the bounded ontology neighborhood. Copying them into
`knowledge_graph_edge` would duplicate the authoritative assertion and discard
its semantic-unit provenance. A catalog lookup without visible supporting
Posts would also turn the endpoint into an unauthorized vocabulary oracle.

## Decision

1. Project each eligible assertion at read time as Post
   `supportsOccupationalConstruct` OccupationalConstruct. The construct node id
   is the versioned `occupational_construct.construct_id`; its external IRI is
   still available in the authorized Post evidence view.
2. Admit the edge and both endpoint labels only through source-eligible Posts
   that pass the existing ABAC callback. Evidence references contain only
   those Post ids, never evidence text or internal unit ids.
3. Edge availability is the later of Post creation and assertion generation.
   Knowledge-cutoff and cursor snapshots apply to that same instant.
4. Preserve the persisted truth status. When assertions for one Post and
   construct disagree on truth status, omit the direct edge; do not rank,
   average, or invent a precedence. The earliest agreeing assertion is the
   edge availability time.
5. Register one governed node type and property alias in the ontology and
   common lookup catalog. Do not persist a duplicate graph edge and do not
   assign node truth or time from assertion-edge metadata.
6. Reuse the existing ontology explorer, exact-value table, evidence drawer,
   keyboard controls, bounded traversal, and opaque cursor. No new destination,
   score, person trait, job requirement, or causal interpretation is added.

## Consequences

- Authorized reviewers can traverse between one Post and its exact versioned
  occupational concepts without exposing hidden Posts or catalog membership.
- Multiple evidence units collapse only when their truth semantics agree.
- Catalog search remains a separate increment; this decision exposes only
  assertion-backed nodes in an already-authorized neighborhood. Authorized
  label search is [ADR 0256](0256-occupational-construct-catalog-search.md).

## Verification

- Ontology tests round-trip the new lookup codes and retain the Post-to-
  construct domain/range.
- Neighborhood tests cover the property alias, inferred truth, cutoff,
  authorization, conflict omission, labels, and cursor-safe SQL order.
- Frontend tests cover the localized node type and existing accessible shape.
