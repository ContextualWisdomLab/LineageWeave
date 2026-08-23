# ADR 0049 — Leftover pairs sit above the report member list

**Decision status:** Accepted
**Date:** 2026-08-17

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
title, criterion short label, leftover-map distance, and the next
action (“Open this post so the leftover criterion is current in Post
quality.”). Clicking the button opens that post with leftover focus
so Post quality marks the named criterion current (ADR 0125).

After `make seed`, closest and farthest leftover pairs sit above the
member list. Click a pair to open that post with the leftover
criterion current in Post quality.

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
