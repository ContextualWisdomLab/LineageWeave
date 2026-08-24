# ADR 0049 — Leftover pairs sit above the report member list

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0162](0162-leftover-residual-disclosure.md) (signed residual R);
[ADR 0163](0163-leftover-observed-expected.md) (observed Y and expected E);
[ADR 0164](0164-leftover-map-rank.md) (full map rank)

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
title, criterion short label, signed residual `R`, two-axis leftover-map
distance, full map rank, observed `Y`, expected `E` when finite, and
unexplained leftover share `s` of centered leftover after IRT main
effects when Gabriel coordinates exist. The next action names every
available measurement before opening the post; no amendment hides
another, rank 0 explicitly names no leftover structure, and a missing
share keeps the existing closest/farthest next action.
Clicking the button opens that post with the same handler as a member
row. Residual naming is [ADR 0162](0162-leftover-residual-disclosure.md),
observed/expected naming is [ADR 0163](0163-leftover-observed-expected.md),
rank naming is [ADR 0164](0164-leftover-map-rank.md), and unexplained
leftover share naming is
[ADR 0183](0183-leftover-map-unexplained-share.md).

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
