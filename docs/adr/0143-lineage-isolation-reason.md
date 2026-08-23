# ADR 0143 — Event Lineage distinguishes a genuinely isolated post from a post with no comparison group

**Decision status:** Proposed
**Date:** 2026-08-22

## Context

`docs/product-technical-gap-baseline.md` (§5, "Lineage coverage") records:
"the persisted graph has 1,308 post-lineage edges across 1,929 participating
posts, while the bounded current view exposed one edge and some focused
posts had no component. Add a rebuild/coverage gate that distinguishes
genuinely isolated posts from missing extraction or grouping evidence before
presenting a reader-facing branching DAG as complete."

Today, when a post has no Event Lineage DAG, `EventLineageSection`
(`frontend/src/App.tsx`) renders one flat message: "No linked posts yet."
This is the same undiagnosability shape ADR 0141 already fixed for R&R
catalog links — a reader cannot tell "reconstruct compared this post
against real candidates and found no relation" from "there was nothing to
compare this post against in the first place."

### Why "nothing to compare against" is a real, common case

`reconstruct_group_key` (`backend/app/lineage_ingestion.py`) determines the
comparison scope `reconstruct()` (`lineageweave/reconstruct.py`) ever
considers for a post: the persisted `thread_group_key`, falling back to
`process_unit_id` or `corporate_entity_id`. Critically,
`scripts/import_postgresql_posts.py`'s import sets
`thread_group_key = mapping.thread_group value, or the import's own
process_unit_code` when the source mapping has no explicit thread column —
so `thread_group_key` is populated for essentially every imported post
either way. A non-empty `thread_group_key` therefore does **not** mean "a
real thread was identified"; it can just as easily mean "no explicit thread
mapping existed, so this row fell back to its whole process unit's code."

The signal that actually distinguishes the two cases the gap doc names is
**group membership size**, not key presence:

- If a post's `reconstruct_group_key` group (among ABAC-visible, eligible
  posts) has **more than one member**, real candidates existed for
  `reconstruct()` to compare against. Zero resulting edges is
  `reconstruct()`'s own considered conclusion — a real fact about the
  channels' similarity scoring, not a data gap.
- If a post's group has **exactly one member** (itself), there was nothing
  to compare against at all. Reporting this the same way as the case above
  falsely implies the post was checked and found unrelated to everything,
  when in fact its true thread was likely never distinguished from a coarse
  process-unit/corporate-entity fallback.

This is independent of, and does not duplicate, the separate open PR fixing
`rebuild_lineage()`'s adjudication-client wiring (a different bug: the
highest-weighted comparison channel not running at all). This ADR's signal
is available regardless of which channels ran; it answers "was there a
comparison group," not "which channels compared it."

## Decision

1. `visible_lineage_graph` (`backend/app/lineage_ingestion.py`) gains an
   `isolation_reason` computation for the focused-post case
   (`GET /api/lineage?post_id=...`, the query `EventLineageSection` drives).
   Using data it already fetches (`thread_group_key`, `process_unit_id`,
   `corporate_entity_id` on every ABAC-visible eligible post — no new query,
   no schema change), it groups the visible set by `reconstruct_group_key`
   and reports one of:
   - `null` — the post has a non-empty DAG; no reason needed.
   - `"no_relation_found"` — the post's group has other visible members, but
     `reconstruct()` produced zero edges for it.
   - `"no_comparison_group"` — the post is the only visible member of its
     group; there was nothing to compare it against.
2. The API response shape stays additive: `{"nodes": [...], "edges": [...],
   "truncated": false, "isolation_reason": null | "no_relation_found" |
   "no_comparison_group"}`. `isolation_reason` is only meaningful (non-null)
   when `focus_post_id` was supplied and the resulting `nodes` list is
   empty; it is always `null` for the un-focused landing-view call.
3. `frontend/src/api.ts`'s `LineageGraph` gains `isolation_reason?: string |
   null`. `EventLineageSection`'s existing "No linked posts yet." branch
   (the `!hasLinks` case only — the doc's complaint is specifically about
   the DAG being presented as complete, not about the separate
   knowledge-graph-edge-based `direct`/`indirect` lists `RelatedPostsSection`
   already reports honestly) replaces that one string with a lookup: a
   specific message for `no_relation_found`, a different one for
   `no_comparison_group`, and today's generic message as the fallback when
   `isolation_reason` is `null`/absent (e.g. an older backend).
4. This does not change `reconstruct()`'s clustering, scoring, or channel
   weights, does not add a migration, and does not gate or block anything —
   it is read-only diagnostic text, the same discipline ADR 0141 used.

## Considered alternatives

- **A corpus-wide aggregate ("N% coverage") instead of a per-post reason.**
  Rejected for this iteration: the gap doc's complaint is specifically about
  a reader opening one post and being told a DAG is complete when it isn't
  diagnosable; a global percentage doesn't answer "why is *this* post's DAG
  empty." A corpus-wide aggregate is a reasonable follow-up for an
  operator-facing rebuild/health view, not a substitute for the per-post fix.
- **Treat `thread_group_key` presence as the signal.** Rejected: as shown
  above, the import path back-fills `thread_group_key` from the process
  unit code whenever no explicit thread mapping exists, so presence alone
  is not evidence a real thread was identified. Group *size* is the honest
  signal available today without a schema change.
- **Wait for the adjudication-client wiring fix to land first.** Rejected:
  that fix (a different, already-open PR) changes how many real edges
  `reconstruct()` finds; it does not change whether a post had any
  candidates to compare against in the first place. The two fixes are
  complementary, not sequential — shipping this one first does not need to
  be redone once the other lands.

## Consequences

- A demo/synthetic dataset where most posts fall back to a shared
  process-unit group will show few `no_comparison_group` results (most
  groups have many members) and mostly `no_relation_found` instead — which
  is an honest reflection of today's coarse fallback grouping, not a defect
  in this feature. A future fix to make thread identification more precise
  at import time is separate, tracked work.
- `isolation_reason` is computed on every focused `GET /api/lineage` call by
  scanning the already-fetched ABAC-visible post list once (O(n) group-by);
  no new database round-trip is added.
