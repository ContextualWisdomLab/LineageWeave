# ADR 0290 — Name leftover-map item complete-case coverage on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map
complete-case coverage ([ADR 0168](0168-leftover-map-complete-case-coverage.md)),
and leftover-map complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)). Independent of leftover-map
post complete-case coverage fail-closed on the pair list
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
persistence ([ADR 0164](0164-leftover-map-rank.md)), and leftover-map axis
share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0168 already persists `map_item_count` / `scored_item_count` on
`report_leftover_map_coverage`. ADR 0289 already captions leftover-map post
complete-case coverage on the grouping comparison strip. The strip still does
not name how many scored criteria entered each grouping's Gabriel factorization,
so a buyer who compares leftover pairs can treat a 2-of-5 complete-case criterion
map as if it used the same census as a 5-of-5 map.

This increment captions persisted leftover-map item complete-case coverage on
each grouping comparison row through leftoverMapItemCoverageCounts. It does not
add columns. It does not recompute item coverage from leftover pair count,
plotted criterion marker count, leftover-map distance, or leftover-map rank.
It does not persist leftover-map inner product, cosine, or length as separate
columns. Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0290** so it does not collide with
leftover-map complete-case coverage on the grouping comparison strip (0289),
leftover-map post complete-case coverage fail-closed on the pair list (0288),
leftover-map incomplete item coverage on the pair list (0287), leftover-map
incomplete post coverage on the pair list (0286), leftover-map item
complete-case coverage on the pair list (0285), leftover-map incomplete
item coverage on the graphic display (0284), leftover-map incomplete post
coverage on the graphic display (0283), leftover-map item complete-case
coverage on the graphic display (0282), leftover-map complete-case coverage
on the graphic display (0281), leftover-map rank on pair segments (0280),
or the dashboard stacks.

## Decision

On the grouping comparison strip, caption leftover-map item complete-case
coverage as `Leftover map used {used} of {scored} scored criteria (complete-case)`
only when leftoverMapItemCoverageCounts returns usable complete-case integers
from persisted `map_item_count` / `scored_item_count`. Use the distinct
accessible name `Leftover map comparison item coverage` so the strip caption
is not the pair-list note (`Leftover map item coverage`) and is not the graphic
caption (`Leftover-map graphic item coverage`). A missing coverage row, a
non-integer count, a negative used count, a non-positive scored count, or used
greater than scored omits that leftover-map comparison item coverage note and
keeps the strip leftover-map post coverage note, leftover pairs, leftover-map
distance `d`, and any leftover-map captions on the pair list and graphic.
Coverage `0 of M` is shown when that persisted used count is a non-negative
integer and scored is a positive integer. Do not invent item coverage from
leftover pair count, plotted criterion marker count, leftover-map distance,
leftover-map rank, leftover-map post coverage, leftover-map incomplete post
coverage, leftover-map incomplete item coverage, or the count of unused axes.
Do not caption leftover-map incomplete post coverage or leftover-map incomplete
item coverage on the strip in this increment. Do not add the leftover-map
graphic to the strip. Click a leftover pair on the strip to open that post.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, the grouping comparison strip names persisted leftover-map
post complete-case coverage and persisted leftover-map item complete-case
coverage on each grouping row when leftoverMapCoverageCounts /
leftoverMapItemCoverageCounts return usable integers, then names leftover pairs
with leftover-map distance `d`. Closest and farthest leftover pairs still sit
above the member list with the leftover-map graphic display; click a post
marker or a pair button opens that post.
Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, leftover-map complete-case
coverage on the grouping comparison strip, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map graphic display,
leftover-map item complete-case coverage on the graphic display, leftover-map
item complete-case coverage on the pair list, leftover-map incomplete post
coverage, leftover-map incomplete item coverage, and leftover-map post
complete-case coverage fail-closed on the pair list.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Incomplete
columns are dropped from the complete-case residual rectangle; grouping
comparison item coverage names how many scored criteria entered that
factorization for that grouping only when leftoverMapItemCoverageCounts
returns usable complete-case integers.)
