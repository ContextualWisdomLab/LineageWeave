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
action (“Open this post to read the criterion it sat closest to /
farthest from after main effects.”). Explained leftover share next
action: two leftover-map axes explain `e` of centered leftover after
IRT main effects; open this post to read the named criterion. A
missing share keeps the existing closest/farthest next action.
Clicking the button opens that post with the same handler as a member
row. Explained leftover share naming is
[ADR 0184](0184-leftover-map-explained-share.md).

After `make seed`, closest and farthest leftover pairs sit above the
member list. Click a pair to open that post.

Missing leftover rows render nothing — never a placeholder pair.
A hidden post never appears as a leftover pair.

## Consequences

The authorized report payload carries `leftover_pairs` next to
`members` and `selected_items`. Screen-reader names are
The visible pair label `{kind}: {title} · {criterion}` (for example
`Closest leftover: Public post · sales-lead`) doubles as the
screen-reader name so the announced text matches what the reader sees
and names the criterion, not only the distance. Earlier increments
documented an `Open leftover closest pair: {title}` shape; the
criterion-bearing label supersedes it.

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0003](0003-fast-mlsirm-report-integration.md).
