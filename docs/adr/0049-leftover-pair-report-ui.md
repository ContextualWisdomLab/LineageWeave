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
[ADR 0233](0233-leftover-map-unexplained-share.md) (unexplained leftover share s);
[ADR 0266](0266-leftover-map-explained-share.md) (explained leftover share e);
[ADR 0267](0267-leftover-map-coordinates.md) (leftover-map coordinates ξ, ζ);
[ADR 0268](0268-leftover-map-graphic-display.md) (leftover-map graphic display);
[ADR 0269](0269-leftover-map-axis-share-plot.md) (leftover-map axis share on the graphic display);
[ADR 0270](0270-leftover-map-coordinate-ticks.md) (leftover-map coordinate ticks);
[ADR 0271](0271-leftover-map-segment-distance.md) (leftover-map distance on pair segments);
[ADR 0272](0272-leftover-map-segment-reconstruction.md) (leftover-map reconstruction on pair segments);
[ADR 0273](0273-leftover-map-segment-explained-share.md) (leftover-map explained leftover share on pair segments);
[ADR 0274](0274-leftover-map-segment-unexplained-share.md) (leftover-map unexplained leftover share on pair segments);
[ADR 0275](0275-leftover-map-segment-cross-share.md) (leftover-map cross share on pair segments);
[ADR 0276](0276-leftover-map-segment-unexplained-leftover.md) (leftover-map unexplained leftover on pair segments);
[ADR 0277](0277-leftover-map-segment-residual.md) (leftover residual on pair segments);
[ADR 0278](0278-leftover-map-segment-observed.md) (leftover observed Y on pair segments);
[ADR 0279](0279-leftover-map-segment-expected.md) (leftover expected E on pair segments)

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
leftover-map unexplained leftover share `s = U² / R²` when finite,
leftover-map explained leftover share `e = R̂² / R²` when finite,
leftover-map coordinates `ξ_{1:2}` and `ζ_{1:2}` when finite, and
leftover-map cross share next to distance when finite. When four finite
coordinates exist, the leftover-map graphic display of those positions
sits above the pair buttons (ADR 0268); click a post marker to open
that post. Leftover-map axis share captions those leftover-map axes
when finite (ADR 0269). Leftover-map axis ticks name persisted `ξ` /
`ζ` coordinates (ADR 0270). Pair segments name persisted leftover-map
distance `d` (ADR 0271). Pair segments name persisted leftover-map
reconstruction `R̂` (ADR 0272). Pair segments name persisted leftover-map
explained leftover share `e` (ADR 0273). Pair segments name persisted leftover-map
unexplained leftover share `s` (ADR 0274). Pair segments name persisted leftover-map
cross share `x` (ADR 0275). Pair segments name persisted leftover-map
unexplained leftover `U` (ADR 0276). Pair segments name persisted leftover
residual `R` (ADR 0277). Pair segments name persisted leftover observed
`Y` (ADR 0278). Pair segments name persisted leftover expected
`E` (ADR 0279). The pair renders every available finite measurement.
The next action uses the first available value in the priority below; no
amendment hides another badge, rank 0
explicitly names no leftover structure, and unexplained leftover names
"leftover map leaves unexplained `U` after IRT main effects; open this
post to read the named criterion" when present. When leftover-map
coordinates are also present, the next action instead names the two-axis
positions `ξ` and `ζ` after IRT main effects. A missing or non-finite value falls back in order —
leftover-map coordinates, then explained leftover share, then unexplained leftover share, then cross share, then reconstruction, then
unexplained leftover, then rank / observed `Y` / expected `E`, then the
existing residual next action. Clicking the button opens that post with
leftover focus so Post quality marks the named criterion current
(ADR 0158). Residual naming is
[ADR 0162](0162-leftover-residual-disclosure.md), observed/expected
naming is [ADR 0163](0163-leftover-observed-expected.md), rank naming
is [ADR 0164](0164-leftover-map-rank.md), unexplained leftover naming
is [ADR 0182](0182-leftover-map-unexplained.md), leftover-map cross
share naming is [ADR 0185](0185-leftover-map-cross-share.md).
Reconstruction naming is [ADR 0201](0201-leftover-map-reconstruction.md).
Unexplained leftover share naming is
[ADR 0233](0233-leftover-map-unexplained-share.md).
Explained leftover share naming is
[ADR 0266](0266-leftover-map-explained-share.md).
Leftover-map coordinate naming is
[ADR 0267](0267-leftover-map-coordinates.md).
Leftover-map graphic display is
[ADR 0268](0268-leftover-map-graphic-display.md).
Leftover-map axis share on the graphic display is
[ADR 0269](0269-leftover-map-axis-share-plot.md).
Leftover-map coordinate ticks are
[ADR 0270](0270-leftover-map-coordinate-ticks.md).
Leftover-map distance on pair segments is
[ADR 0271](0271-leftover-map-segment-distance.md).
Leftover-map reconstruction on pair segments is
[ADR 0272](0272-leftover-map-segment-reconstruction.md).
Leftover-map explained leftover share on pair segments is
[ADR 0273](0273-leftover-map-segment-explained-share.md).
Leftover-map unexplained leftover share on pair segments is
[ADR 0274](0274-leftover-map-segment-unexplained-share.md).
Leftover-map cross share on pair segments is
[ADR 0275](0275-leftover-map-segment-cross-share.md).
Leftover-map unexplained leftover on pair segments is
[ADR 0276](0276-leftover-map-segment-unexplained-leftover.md).
Leftover residual on pair segments is
[ADR 0277](0277-leftover-map-segment-residual.md).
Leftover observed Y on pair segments is
[ADR 0278](0278-leftover-map-segment-observed.md).
Leftover expected E on pair segments is
[ADR 0279](0279-leftover-map-segment-expected.md).

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
