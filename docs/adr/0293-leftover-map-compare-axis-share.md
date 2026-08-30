# ADR 0293 — Name leftover-map axis share on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)) and leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).
Independent of leftover-map incomplete item coverage on the grouping
comparison strip ([ADR 0292](0292-leftover-map-compare-incomplete-item.md)),
leftover-map incomplete post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), leftover-map item
complete-case coverage on the grouping comparison strip
([ADR 0290](0290-leftover-map-compare-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)), leftover-map post
complete-case coverage fail-closed on the pair list
([ADR 0288](0288-leftover-map-list-post-coverage-helper.md)), leftover-map
incomplete item coverage on the pair list
([ADR 0287](0287-leftover-map-list-incomplete-item.md)), leftover-map incomplete
post coverage on the pair list
([ADR 0286](0286-leftover-map-list-incomplete-post.md)), leftover-map item
complete-case coverage on the pair list
([ADR 0285](0285-leftover-map-list-item-coverage.md)), leftover-map incomplete
item coverage on the graphic display
([ADR 0284](0284-leftover-map-plot-incomplete-item.md)), leftover-map incomplete
post coverage on the graphic display
([ADR 0283](0283-leftover-map-plot-incomplete.md)), leftover-map item
complete-case coverage on the graphic display
([ADR 0282](0282-leftover-map-plot-item-coverage.md)), leftover-map complete-case
coverage on the graphic display
([ADR 0281](0281-leftover-map-plot-coverage.md)), leftover-map rank on pair
segments ([ADR 0280](0280-leftover-map-segment-rank.md)), leftover expected on pair
segments ([ADR 0279](0279-leftover-map-segment-expected.md)), leftover observed on
pair segments ([ADR 0278](0278-leftover-map-segment-observed.md)), leftover
residual on pair segments ([ADR 0277](0277-leftover-map-segment-residual.md)),
leftover-map unexplained leftover on pair segments
([ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)), leftover-map
cross share on pair segments ([ADR 0275](0275-leftover-map-segment-cross-share.md)),
leftover-map unexplained leftover share on pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
explained leftover share on pair segments
([ADR 0273](0273-leftover-map-segment-explained-share.md)), leftover-map
reconstruction on pair segments
([ADR 0272](0272-leftover-map-segment-reconstruction.md)), leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)),
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover
observed `Y` / expected `E` ([ADR 0163](0163-leftover-observed-expected.md)),
leftover-map explained leftover share persistence
([ADR 0266](0266-leftover-map-explained-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
leftover-map cross share persistence
([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map unexplained leftover
persistence ([ADR 0182](0182-leftover-map-unexplained.md)), leftover-map rank
persistence ([ADR 0164](0164-leftover-map-rank.md)), leftover-map complete-case
coverage persistence ([ADR 0168](0168-leftover-map-complete-case-coverage.md)),
and leftover-map graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²` on `report_leftover_map_axis` and captions
leftover-axis report badges with share. ADR 0269 already captions leftover-map
graphic axes with that same persisted share. ADR 0149 already carries
ABAC-filtered leftover pairs on `GET /api/reports/compare/{period}`. ADR 0289
already includes leftover-map complete-case coverage on that comparison
payload. The grouping comparison strip still names leftover pairs, `d`, and
leftover-map coverage without naming leftover-map axis share for that grouping,
so a buyer who compares PU / corp / thread leftover pairs can treat a
rank-0 unused axis as if it had the same Gabriel inertia as an 82% first axis.

This increment includes persisted leftover-map axes on the comparison payload
and captions each grouping row through leftoverMapCompareAxisShare. It does
not add columns. It does not invent leftover-map axis share from leftover-map
singular value, leftover pair count, plotted marker count, leftover-map
distance, leftover-map rank, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. It does not persist leftover-map inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0293** so it does not collide with
leftover-map incomplete item coverage on the grouping comparison strip (0292),
leftover-map incomplete post coverage on the grouping comparison strip (0291),
leftover-map item complete-case coverage on the grouping comparison strip
(0290), leftover-map complete-case coverage on the grouping comparison strip
(0289), leftover-map post complete-case coverage fail-closed on the pair list
(0288), leftover-map incomplete item coverage on the pair list (0287),
leftover-map incomplete post coverage on the pair list (0286), leftover-map
item complete-case coverage on the pair list (0285), leftover-map incomplete
item coverage on the graphic display (0284), leftover-map incomplete post
coverage on the graphic display (0283), leftover-map item complete-case
coverage on the graphic display (0282), leftover-map complete-case coverage
on the graphic display (0281), leftover-map rank on pair segments (0280),
or the dashboard stacks.

## Decision

On the grouping comparison strip, include persisted `leftover_map_axes` on
each comparison row and caption leftover-map axis `k` as
`leftover map comparison axis {k} {share}%` only when leftoverMapCompareAxisShare
returns a usable share from persisted `leftover_share`. Use the distinct
accessible name `Leftover map comparison axis share` so the strip caption is
not the leftover-axis report badge (`leftover axis {k} {share}%`) and is not
the graphic caption (`leftover-map axis {k} ({share}%)`). A missing axis row
or a missing or non-finite share omits that leftover-map comparison axis
share badge and keeps the strip leftover-map post coverage note, leftover-map
item coverage note, leftover-map incomplete post note, leftover-map
incomplete item note, leftover pairs, leftover-map distance `d`, and any
leftover-map captions on the pair list and graphic. Share `0` is shown when
that persisted share is a finite number, including rank-0 unused axes. A
finite negative share is shown; do not clamp to nonnegative. Axis 1 and
axis 2 stay independently named. Do not invent leftover-map axis share from
leftover-map singular value, leftover pair count, plotted marker count,
leftover-map distance, leftover-map rank, leftover-map post coverage,
leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, or the count of unused axes. Do not
caption leftover-map singular values or the leftover-map graphic on the strip
in this increment. Click a leftover pair on the strip to open that post.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, the grouping comparison strip names persisted leftover-map
post complete-case coverage, persisted leftover-map item complete-case
coverage, persisted leftover-map incomplete post coverage, persisted
leftover-map incomplete item coverage, and persisted leftover-map axis share
on each grouping row when leftoverMapCoverageCounts /
leftoverMapItemCoverageCounts / leftoverMapIncompletePostCount /
leftoverMapIncompleteItemCount / leftoverMapCompareAxisShare return usable
values, then names leftover pairs with leftover-map distance `d`. Closest
and farthest leftover pairs still sit above the member list with the
leftover-map graphic display; click a post marker or a pair button opens that
post.
Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, leftover-map complete-case
coverage on the grouping comparison strip, leftover-map item complete-case
coverage on the grouping comparison strip, leftover-map incomplete post
coverage on the grouping comparison strip, leftover-map incomplete item
coverage on the grouping comparison strip, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map graphic display,
leftover-map item complete-case coverage on the graphic display, leftover-map
item complete-case coverage on the pair list, leftover-map incomplete post
coverage on the graphic display, leftover-map incomplete post coverage on the
pair list, leftover-map incomplete item coverage on the graphic display,
leftover-map incomplete item coverage on the pair list, leftover-map post
complete-case coverage fail-closed on the pair list, leftover-map axis share
on the graphic display, and leftover-map singular values.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Leftover-map
axis share is Gabriel inertia `σ_k² / Σ_j σ_j²` of residual SVD axes;
grouping comparison leftover-map axis share names that persisted share
for that grouping only when leftoverMapCompareAxisShare returns a usable
share.)
