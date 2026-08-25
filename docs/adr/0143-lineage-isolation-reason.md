# ADR 0143 — Explain an empty focused Event Lineage graph

**Decision status:** Accepted  
**Date:** 2026-08-22

## Context

The focused Event Lineage endpoint can return an empty graph for two materially
different reasons: the authorized post has other visible comparison-group
members but no persisted link, or it is the only visible member of its group.
The former does not prove that a completed reconstruction considered the newest
source rows, and the latter must not be inferred from hidden posts. A generic
"No linked posts yet" message concealed this distinction.

`thread_group_key` presence is not sufficient evidence because import may fall
back to process-unit or corporate-entity scope. The only supported diagnostic
available without a new heuristic is the size of the ABAC-visible
`reconstruct_group_key` group already fetched for the focused graph.

## Decision

1. A focused `GET /api/lineage?post_id=...` adds `isolation_reason` only as an
   additive response field. It is `null` for landing graphs, inaccessible
   posts, and non-empty focused graphs.
2. `comparison_candidates_available` means another ABAC-visible post shares
   the comparison group, while the current projection has no Event Lineage
   link. It does not claim a rebuild ran or considered the latest rows.
3. `no_comparison_group` means the focused post is the only ABAC-visible member
   of its comparison group. Hidden posts cannot change the result or bridge a
   visible component.
4. The buyer surface names both states and gives a next action. Unknown or
   absent values retain the generic message for backward compatibility.
5. The batched multi-post Ask graph does not emit a single focused-post reason;
   attributing one reason to that multi-focus projection would be unsupported.

## Consequences

This is a read-only diagnostic. It changes no reconstruction channel, score,
weight, threshold, or persistence policy and introduces no new query. Runtime
acceptance still requires authorized, non-identifying aggregate evidence; an
empty graph is never evidence that every current source row was reconstructed.
