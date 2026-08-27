# ADR 0249: Occupational construct assertion persistence

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0062](0062-semantic-unit-embedding.md), [ADR 0184](0184-ontology-provenance-explorer.md), [ADR 0248](0248-occupational-construct-evidence-boundary.md)

## Context

ADR 0248 defines the semantic assertion but intentionally leaves persistence
unavailable. A bare Post-to-construct edge would lose the exact semantic unit,
source vocabulary version, extraction session, truth status, and verbatim
evidence that make the assertion reviewable. Reusing `knowledge_graph_edge`
would also mix a provenance-bearing analysis artifact into the navigation
projection forbidden by ADR 0065.

## Decision

1. Persist source vocabularies, their versioned external constructs, and Post
   assertions in three normalized tables: `occupational_construct_vocabulary`,
   `occupational_construct`, and `post_occupational_construct_assertion`.
2. Every assertion references one existing `post_content_unit`, one construct,
   one ontology truth-status code, one extraction method, and the shared
   post-scoped contextual-orchestrator session identifier. It stores no score,
   weight, intensity, importance, causal flag, or person binding.
3. A database trigger rejects an assertion when the semantic unit belongs to a
   different Post or its evidence is not a non-empty verbatim substring of the
   stored unit text. Application validation mirrors this boundary before SQL.
4. Replacement is atomic per Post. Vocabulary and construct rows use natural
   versioned uniqueness and UPSERT; post assertions are deleted and recreated
   inside the same transaction so stale analysis cannot coexist with a new
   source-derived set.
5. The already-authorized `GET /api/posts/{post_id}` response may include the
   assertions after the Post ABAC decision succeeds. It exposes evidence,
   construct label/IRI/family, vocabulary/version, truth status, method, and
   generated time, but not internal database identifiers.
6. Search, ontology-neighborhood nodes, extraction prompts, UI presentation,
   and person/job/task binding remain separate increments. Absence returns an
   empty list.

## Considered options

| Option | Outcome |
|---|---|
| Store construct JSON on the Post | Rejected: duplicates vocabulary metadata and defeats 3NF/query integrity |
| Add bare knowledge-graph edges | Rejected: loses evidence-unit provenance and confuses navigation with assertion ownership |
| Versioned registry plus evidence-unit assertion | Accepted: normalized, replayable, provenance-bearing, and additive |

## Consequences

- Authorized clients can inspect persisted construct evidence without treating
  it as a measured person attribute.
- Vocabulary updates create a new version row instead of silently changing the
  meaning of historical assertions.
- The trigger adds one indexed unit lookup per written assertion; batch volume
  is bounded by the semantic units of one Post. A future measured throughput
  problem may replace it with a set-based staging validator.

## Verification

- `tests/test_occupational_construct_persistence.py` verifies trust-boundary
  validation, atomic replacement SQL, versioned UPSERT, and empty replacement.
- `tests/test_occupational_construct_schema.py` verifies replay safety, 3NF
  foreign keys, evidence trigger, prohibited numeric fields, and hot-path
  indexes.
- The existing Post-detail ABAC path loads the projection only after its
  visibility decision; focused tests verify the returned review model.
