# ADR 0122 — Name Allen interval relations on Event Lineage edges

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

Event Lineage already refuses a parent that occurred after its child
(`reconstruct.py` looks only backward). Buyers still see only a fused
score on the edge. They cannot tell whether the child happened after
the parent, during the parent's open ticket window, or on the same
day. Allen (1983) partitions every pair of closed intervals into
thirteen relations. CHRONOS (Anagnostopoulos et al., 2013) uses that
algebra as temporal-consistency evidence, not as a causal claim.

A post's dated window is observed: `source_post.created_at` as the
start, and the earliest *open* `issue_ticket.due_date` as the end
when that due date is on or after the created day. A missing or
earlier due date is a point interval. The product does not invent a
duration, swap bounds, or promote the relation to a reconstructed
parent.

## Decision

Persist `interval_relation_code` on `post_lineage_edge` (3NF,
two-or-more-word `snake_case`) as a `common_lookup_value` code in
the `interval_relation` category. Compute it in
`lineageweave/interval_relation.py` from the two posts' dated
windows after reconstruct has chosen the parent. Rebuild and seed
write the code in the same transaction as the edge. Ticket-aware
windows run after fixture tickets exist so `make seed` is not a
point-only map.

`GET /api/lineage` and `GET /api/posts/{id}/lineage` return the
lookup label next to the fused score. The DAG shows that label as
visible text, not hover-only, and lists each edge as a keyboard
button whose next action is to open the other post. Indirect
Keyman links stay unlabeled -- they are not reconstructed parents.

Do not store a second fused score. Do not treat During/Contains as
causation. A hidden endpoint still drops the edge.

## Consequences

After `make seed`, the A-100 pricing follow-up **contains** the
revised quote (point 2026-01-10 inside the 2026-01-06..2026-01-12
ticket window) and **overlaps** the delivery question. Click the
Contains row to open the revised quote. Migration
`0105_post_lineage_interval_relation.sql` upgrades volumes that
already applied `0001`. Point-only backfill uses created days so
existing edges are never left null.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Anagnostopoulos, E., Batsakis, S., & Petrakis, E. G. M. (2013).
CHRONOS: A reasoning engine for qualitative temporal information in
OWL. *Procedia Computer Science, 22*, 70–77.
https://doi.org/10.1016/j.procs.2013.09.082
