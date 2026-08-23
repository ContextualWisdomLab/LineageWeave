# ADR 0049 — Leftover pairs sit above the report member list

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0171](0171-leftover-map-rank.md) (full map rank)

## Context

ADR 0048 persists closest and farthest leftover post–criterion pairs.
Those pairs only help if a buyer can see them on the Period reports
panel and open the named post without hunting through the member list.

The member list is already the click-through to Event Lineage, Keyman,
and evaluation. Leftover pairs must not replace that list or invent a
second navigation surface.

## Decision

On each period-report group, render leftover pairs **above** the
member list. Each pair is a button: closest or farthest label, post
title, criterion short label, leftover-map distance, leftover-map
rank when the value is a finite non-negative integer, and the next
action. Rank 0 next action: leftover map has no leftover structure
after IRT main effects; open this post. Rank ≥ 1 next action: read
leftover map rank after IRT main effects, then open this post.
Missing rank omits the badge and keeps the closest/farthest action.
Clicking the button opens that post with the same handler as a member
row. Rank naming is [ADR 0171](0171-leftover-map-rank.md).

After `make seed`, closest and farthest leftover pairs sit above the
member list. Click a pair to open that post.

Missing leftover rows render nothing — never a placeholder pair.
A hidden post never appears as a leftover pair.

## Consequences

The authorized report payload carries `leftover_pairs` next to
`members` and `selected_items`. Screen-reader names are
`Open leftover closest pair: {title}` and
`Open leftover farthest pair: {title}` so the control announces the
next action, not only the distance.

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0003](0003-fast-mlsirm-report-integration.md).
