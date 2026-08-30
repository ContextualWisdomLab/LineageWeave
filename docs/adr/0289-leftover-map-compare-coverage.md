# ADR 0289 — Name leftover-map complete-case coverage on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)) and leftover-map
complete-case coverage ([ADR 0168](0168-leftover-map-complete-case-coverage.md)).
Independent of leftover-map post complete-case coverage fail-closed on the pair
list ([ADR 0288](0288-leftover-map-list-post-coverage-helper.md)), leftover-map
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

ADR 0168 already persists `map_post_count` / `scored_post_count` on
`report_leftover_map_coverage`. ADR 0149 already carries ABAC-filtered leftover
pairs on `GET /api/reports/compare/{period}`. ADR 0281 already fail-closes that
same coverage on the leftover-map graphic. ADR 0288 already fail-closes that
same coverage on the leftover pair list. The grouping comparison strip still
names leftover pairs and `d` without naming how many scored posts entered the
Gabriel factorization for that grouping, so a buyer who compares PU / corp /
thread leftover pairs can treat a 2-of-8 complete-case map as if it used the
same census as an 8-of-8 map.

This increment includes persisted leftover-map complete-case coverage on the
comparison payload and captions each grouping row through leftoverMapCoverageCounts.
It does not add columns. It does not recompute post coverage from leftover pair
count, plotted marker count, leftover-map distance, or leftover-map rank. It
does not persist leftover-map inner product, cosine, or length as separate
columns. It does not land Post quality on the leftover criterion. Leftover-map
distance stays two-axis Euclidean. Do not invent a leftover score. Do not invent
a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0289** so it does not collide with
leftover-map post complete-case coverage fail-closed on the pair list (0288),
leftover-map incomplete item coverage on the pair list (0287), leftover-map
incomplete post coverage on the pair list (0286), leftover-map item
complete-case coverage on the pair list (0285), leftover-map incomplete
item coverage on the graphic display (0284), leftover-map incomplete post
coverage on the graphic display (0283), leftover-map item complete-case
coverage on the graphic display (0282), leftover-map complete-case coverage
on the graphic display (0281), leftover-map rank on pair segments (0280),
leftover expected on pair segments (0279), leftover observed on pair
segments (0278), leftover residual on pair segments (0277), leftover-map
unexplained leftover on pair segments (0276), leftover-map cross share on
pair segments (0275), leftover-map unexplained leftover share on pair
segments (0274), leftover-map explained leftover share on pair segments
(0273), leftover-map reconstruction on pair segments (0272), leftover-map
distance on pair segments (0271), leftover-map coordinate ticks (0270),
leftover-map axis share on the graphic display (0269), leftover-map graphic
display (0268), leftover-map coordinates (0267 / migration 0245), leftover-map
explained leftover share persistence (0266 / migration 0244), leftover-map
unexplained leftover share persistence (0233 / migration 0233), leftover-map
reconstruction persistence (0201 / migration 0206), leftover-map cross share
persistence (0185), leftover-map unexplained leftover persistence (0182),
leftover residual disclosure (0162), leftover observed `Y` / expected `E`
persistence (0163), leftover-map rank persistence (0164), leftover coverage
persistence (0168), two-axis leftover-map distance persistence, leftover-map
axis share persistence (0148), leftover interaction-map persistence,
occupational construct catalog search (0265), or the dashboard stacks.

## Decision

On the grouping comparison strip, include persisted `leftover_map_coverage` on
each comparison row and caption leftover-map post complete-case coverage as
`Leftover map used {used} of {scored} scored posts (complete-case)` only when
leftoverMapCoverageCounts returns usable complete-case integers from persisted
`map_post_count` / `scored_post_count`. Use the distinct accessible name
`Leftover map comparison coverage` so the strip caption is not the pair-list
note (`Leftover map coverage`) and is not the graphic caption
(`Leftover-map graphic coverage`). A missing coverage row, a non-integer
count, a negative used count, a non-positive scored count, or used greater
than scored omits that leftover-map comparison coverage note and keeps the
strip leftover pairs, leftover-map distance `d`, and any leftover-map
distance, reconstruction, explained leftover share, unexplained leftover
share, leftover-map cross share, unexplained leftover, leftover residual,
leftover observed, leftover expected, leftover-map rank, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post, or
leftover-map incomplete item caption on the pair list and graphic. Coverage
`0 of M` is shown when that persisted used count is a non-negative integer
and scored is a positive integer. Do not invent post coverage from leftover
pair count, plotted marker count, leftover-map distance, leftover-map rank,
leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, or the count of unused axes. Do not
caption leftover-map item coverage, leftover-map incomplete post coverage,
or leftover-map incomplete item coverage on the strip in this increment.
Do not add the leftover-map graphic to the strip. Coverage is aggregate and
non-identifying: ABAC that hides leftover pairs does not hide persisted
coverage counts. Click a leftover pair on the strip to open that post.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, the grouping comparison strip names persisted leftover-map
post complete-case coverage on each grouping row when leftoverMapCoverageCounts
returns usable integers, then names leftover pairs with leftover-map distance
`d`. Closest and farthest leftover pairs still sit above the member list with
the leftover-map graphic display of persisted `ξ` and `ζ`, leftover-map axes
name persisted Gabriel inertia share when finite, leftover-map axis ticks name
the same coordinates shown on the pair row, pair segments name persisted
leftover-map distance `d`, persisted leftover-map reconstruction `R̂`,
persisted leftover-map explained leftover share `e`, persisted leftover-map
unexplained leftover share `s`, persisted leftover-map cross share `x`,
persisted leftover-map unexplained leftover `U`, persisted leftover residual
`R`, persisted leftover observed `Y`, persisted leftover expected `E`,
persisted leftover-map rank, the plot names persisted leftover-map
complete-case coverage, the plot names persisted leftover-map item
complete-case coverage, the plot names persisted leftover-map incomplete
post coverage, the plot names persisted leftover-map incomplete item
coverage, the pair list names persisted leftover-map post complete-case
coverage only when leftoverMapCoverageCounts returns usable integers, the
pair list names persisted leftover-map item complete-case coverage, the pair
list names persisted leftover-map incomplete post coverage, and the pair list
names persisted leftover-map incomplete item coverage; click a post marker
or a pair button opens that post.
Hidden posts stay hidden. Rank-0 unused axes still plot at the origin and still
name post coverage on the comparison strip when that coverage is persisted as
usable complete-case integers.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, two-axis leftover-map
distance persistence, leftover-map rank persistence, leftover-map inner
product, leftover-map cosine, leftover-map length, leftover-map
reconstruction persistence, leftover-map unexplained leftover persistence,
leftover-map cross share persistence, leftover-map unexplained leftover
share persistence, leftover-map explained leftover share persistence,
leftover-map coordinate persistence, leftover-map graphic display,
leftover-map axis share on the graphic display, leftover-map coordinate
ticks, leftover-map distance on pair segments, leftover-map reconstruction
on pair segments, leftover-map explained leftover share on pair segments,
leftover-map unexplained leftover share on pair segments, leftover-map
cross share on pair segments, leftover-map unexplained leftover on pair
segments, leftover residual on pair segments, leftover observed on pair
segments, leftover expected on pair segments, leftover-map rank on pair
segments, leftover-map complete-case coverage on the graphic display,
leftover-map item complete-case coverage on the graphic display,
leftover-map incomplete post coverage on the graphic display,
leftover-map incomplete item coverage on the graphic display,
leftover-map item complete-case coverage on the pair list, leftover-map
incomplete post coverage on the pair list, leftover-map incomplete
item coverage on the pair list, and leftover-map post complete-case
coverage fail-closed on the pair list.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Gabriel
reconstruction of the leftover cell is the two-axis inner product
`R̂ = ξ_{1:2} · ζ_{1:2}`. Incomplete rows are dropped from the
complete-case residual rectangle; grouping comparison coverage names how
many scored posts entered that factorization for that grouping only when
leftoverMapCoverageCounts returns usable complete-case integers.)
