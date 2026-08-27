# ADR 0253: Catalog-bound occupational construct extraction

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0248](0248-occupational-construct-evidence-boundary.md), [ADR 0249](0249-occupational-construct-assertion-persistence.md), [ADR 0250](0250-official-occupational-construct-catalog-sync.md)

## Context

The synchronized O*NET catalog contains 2,529 governed nodes. Sending the
whole release on every semantic-unit request is wasteful, while local text
similarity, embeddings, thresholds, or model-invented identifiers would add
an unsupported heuristic. contextual-orchestrator currently preserves tool
requests through a single-provider passthrough, which does not satisfy this
repository's multi-agent requirement.

## Decision

1. After semantic-unit persistence, traverse the official O*NET Content Model
   hierarchy encoded by its published element identifiers. One
   contextual-orchestrator `conduct` request receives only a node's immediate
   official children (at most 47 in O*NET 31.0). Descend only through selected
   nodes. The hierarchy determines the traversal; LineageWeave adds no score,
   threshold, weight, similarity, ranking, or synonym rule.
2. Each response may contain only an offered permanent construct IRI and a
   non-empty verbatim span from that semantic unit. Unknown IRIs, duplicates,
   malformed output, and non-verbatim evidence fail the entire ingestion
   attempt for bounded retry.
3. Persist every selected hierarchy node as `truth_inferred` with extraction
   method `contextual_orchestrator_onet_hierarchy_v1`, the existing post-scoped
   orchestrator session, and the ADR 0249 assertion boundary. This is evidence
   about record content, never a measured person trait or job requirement.
4. Record a source-body-digest extraction run even when no node applies, so a
   successful empty result remains distinct from unavailable extraction.
   Provider work runs without holding a pooled database connection.
5. Affect and performance behavior remain unavailable because ADR 0250 admits
   no governed vocabulary for those families. Extraction cannot invent one.
6. While contextual-orchestrator evidence is configured, recovery also wakes
   successful current-digest jobs that lack an extraction-run row. This runtime
   completeness check, rather than a one-time migration event, covers later
   orchestrator enablement.
7. A reclaimed successful job receives a fresh bounded retry budget for the
   newly required channel. Failure exhausts that budget into `Failed`; runtime
   recovery does not reclaim failed jobs again.

## Consequences

- Runtime evidence can populate the authorized construct projection without a
  local mathematical core or an unbounded catalog prompt.
- A selected parent is required before its children are considered. This is
  the official hierarchy's semantic containment boundary, not a relevance
  shortcut.
- Previously completed post-content jobs are reclaimed when the current body
  digest lacks an extraction-run record.
- A claimed retry repeats hierarchy extraction. `persist_post_content` replaces
  the semantic-unit rows before this stage, so the digest ledger proves the
  prior attempt but cannot safely act as a cache for assertions whose evidence
  is bound to those replaced unit identifiers. Reuse would require a separate
  stable-unit identity and invalidation decision; the worker does not infer one.

## Verification

- `tests/test_occupational_construct_extraction.py` verifies exact IRI/span
  admission and hierarchy descent.
- PostgreSQL schema tests verify the replay-safe extraction-run ledger.
- Worker tests verify successful persistence and retry behavior without
  retaining a database connection during provider work.

## References

The source, license, hierarchy, and APA 7 references remain registered in
[`docs/doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md`](../doctoring/OCCUPATIONAL_CONSTRUCT_REFERENCES.md).
