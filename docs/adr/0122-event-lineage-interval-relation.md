# ADR 0122 — Name Allen interval relations on Event Lineage edges

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

Event Lineage already refuses a parent that occurred after its child
(`reconstruct.py` looks only backward). Buyers still see only a fused
score on the edge. They cannot tell whether the child happened after
the parent or on the same day. Allen (1983) partitions every pair of
closed intervals into thirteen relations. CHRONOS (Anagnostopoulos et
al., 2013) uses that
algebra as temporal-consistency evidence, not as a causal claim.

A post's observed dated window is the UTC calendar day of
`source_post.created_at`, represented as a point interval. An
`issue_ticket.due_date` is mutable and may be entered manually; without an
immutable source reference and derivation state it is not observed Event
Lineage evidence. Ticket-aware interval ends are therefore deferred until a
provenance-bearing interval-evidence contract exists. The product does not
invent a duration or promote the relation to a reconstructed parent.

## Decision

Persist `interval_relation_code` on `post_lineage_edge` (3NF,
two-or-more-word `snake_case`) as a `common_lookup_value` code in
the `interval_relation` category. Compute it in
`lineageweave/interval_relation.py` from the two posts' UTC creation-day
points after reconstruct has chosen the parent. Rebuild and seed write the
code in the same transaction as the edge. The thirteen-relation algebra stays
available for future evidence-bearing intervals, but current post projection
uses only observed creation-day points.

`GET /api/lineage` and `GET /api/posts/{id}/lineage` return the
lookup label next to the fused score. The DAG shows that label as
visible text, not hover-only, and lists each edge as a keyboard
button whose next action is to open the other post. Indirect
Keyman links stay unlabeled -- they are not reconstructed parents.

Do not store a second fused score. Do not treat During/Contains as
causation. A hidden endpoint still drops the edge.

## Consequences

After `make seed`, the A-100 pricing follow-up is **before** the revised quote
and delivery question. Ticket creation, editing, closing, or deletion does not
rewrite that observed chronology. Click a directed relation row to open the
other post. Migration
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
