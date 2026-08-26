# ADR 0049 — Leftover pairs sit above the report member list

**Decision status:** Accepted
**Date:** 2026-08-17
**Amended by:** [ADR 0162](0162-leftover-residual-disclosure.md) (signed residual R);
[ADR 0163](0163-leftover-observed-expected.md) (observed Y and expected E);
[ADR 0164](0164-leftover-map-rank.md) (full map rank);
[ADR 0182](0182-leftover-map-unexplained.md) (unexplained leftover U);
[ADR 0158](0158-leftover-criterion-evaluation-landing.md) (criterion evaluation landing);
[ADR 0185](0185-leftover-map-cross-share.md) (leftover-map cross share);
[ADR 0201](0201-leftover-map-reconstruction.md) (signed reconstruction R̂);
[ADR 0232](0232-leftover-map-explained-share.md) (leftover-map explained share)

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
distance, full map rank, observed `Y`, expected `E` when finite,
unexplained leftover `U`, signed reconstruction `R̂` when finite,
leftover-map cross share next to distance when finite, and leftover-map
explained share `e = R̂² / R²` of raw residual when finite. The next action names every available
measurement before opening the post; no amendment hides another, rank 0
explicitly names no leftover structure, and unexplained leftover names
"leftover map leaves unexplained `U` after IRT main effects; open this
post to read the named criterion" when present. When leftover-map
explained share is also present, the next action names how much of the
raw residual two leftover-map axes explain after IRT main effects.
A missing or non-finite value falls back in order —
explained share, then cross share, then reconstruction, then unexplained leftover, then the existing
closest/farthest next action. Clicking the button opens that post with
leftover focus so Post quality marks the named criterion current
(ADR 0158). Residual naming is
[ADR 0162](0162-leftover-residual-disclosure.md), observed/expected
naming is [ADR 0163](0163-leftover-observed-expected.md), rank naming
is [ADR 0164](0164-leftover-map-rank.md), unexplained leftover naming
is [ADR 0182](0182-leftover-map-unexplained.md), leftover-map cross
share naming is [ADR 0185](0185-leftover-map-cross-share.md).
Reconstruction naming is [ADR 0201](0201-leftover-map-reconstruction.md).
Explained-share naming is [ADR 0232](0232-leftover-map-explained-share.md).

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
[ADR 0003](0003-fast-mlsirm-report-integration.md). Complete-case
coverage of the leftover map is [ADR 0168](0168-leftover-map-complete-case-coverage.md).

[ADR 0003](0003-fast-mlsirm-report-integration.md). The grouping
comparison strip reuses this leftover store ([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)).
