# ADR 0287 — Name leftover-map incomplete item coverage on the pair list

**Decision status:** Accepted
**Date:** 2026-08-30

Amends [ADR 0049](0049-leftover-pair-report-ui.md) and leftover-map complete-case
coverage ([ADR 0168](0168-leftover-map-complete-case-coverage.md)). Independent of
leftover-map incomplete post coverage on the pair list
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

ADR 0168 already persists `incomplete_item_count` on
`report_leftover_map_coverage` and captions the pair list with post
complete-case coverage. ADR 0284 already names persisted leftover-map
incomplete item coverage on the leftover-map graphic display. ADR 0285 already
names item complete-case coverage on the pair list. ADR 0286 already names
incomplete post coverage on the pair list. The pair-list note still does not
name dropped incomplete criteria, so a buyer who reads `used N of M scored
criteria (complete-case)` above the pair buttons can treat those N criteria
as the full scored census even after incomplete columns were dropped.
Incomplete columns are dropped from Gabriel factorization; hiding dropped
criteria on the pair list lets a sparse criterion with one missing post vanish
without a next action.

This increment names leftover-map incomplete item coverage on the pair-list
note. It does not add columns. It does not recompute dropped criteria from
scored minus used, plotted criterion marker count, leftover-map distance, or
leftover-map rank. It does not persist leftover-map inner product, cosine, or
length as separate columns. It does not land Post quality on the leftover
criterion. Leftover-map distance stays two-axis Euclidean. Do not invent a
leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0287** so it does not collide with
leftover-map incomplete post coverage on the pair list (0286), leftover-map
item complete-case coverage on the pair list (0285), leftover-map incomplete
item coverage on the graphic display (0284), leftover-map incomplete post
coverage on the graphic display (0283), leftover-map item complete-case
coverage on the graphic display (0282), leftover-map complete-case coverage on
the graphic display (0281), leftover-map rank on pair segments (0280), leftover
expected on pair segments (0279), leftover observed on pair segments (0278),
leftover residual on pair segments (0277), leftover-map unexplained leftover on
pair segments (0276), leftover-map cross share on pair segments (0275),
leftover-map unexplained leftover share on pair segments (0274), leftover-map
explained leftover share on pair segments (0273), leftover-map reconstruction
on pair segments (0272), leftover-map distance on pair segments (0271),
leftover-map coordinate ticks (0270), leftover-map axis share on the graphic
display (0269), leftover-map graphic display (0268), leftover-map coordinates
(0267 / migration 0245), leftover-map explained leftover share persistence
(0266 / migration 0244), leftover-map unexplained leftover share persistence
(0233 / migration 0233), leftover-map reconstruction persistence (0201 /
migration 0206), leftover-map cross share persistence (0185), leftover-map
unexplained leftover persistence (0182), leftover residual disclosure (0162),
leftover observed `Y` / expected `E` persistence (0163), leftover-map rank
persistence (0164), leftover coverage persistence (0168), two-axis leftover-map
distance persistence, leftover-map axis share persistence (0148), leftover
interaction-map persistence, occupational construct catalog search (0265), or
the dashboard stacks.

## Decision

On the leftover pair list, caption persisted leftover-map incomplete item
coverage as `Leftover map dropped {dropped} incomplete criteria`, using the
persisted `incomplete_item_count` integer. A missing coverage row, a
non-integer dropped count, a negative dropped count, or a dropped count that
contradicts usable item complete-case integers (`dropped !== scored − used`
when `map_item_count` / `scored_item_count` are usable) omits that leftover-map
incomplete item note and keeps the pair-list post coverage note, the pair-list
item coverage note, the pair-list incomplete post note, and any leftover-map
distance, reconstruction, explained leftover share, unexplained leftover share,
leftover-map cross share, unexplained leftover, leftover residual, leftover
observed, leftover expected, leftover-map rank, leftover-map post coverage,
leftover-map item coverage, leftover-map incomplete post, or leftover-map
incomplete item caption on the graphic. Dropped `0` is shown when that
persisted dropped count is a non-negative integer. Do not invent dropped
criteria from scored minus used, plotted criterion marker count, leftover-map
distance, leftover-map rank, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete post coverage, or the count of unused axes.
Click a pair button to open that post. The grouping comparison strip
(ADR 0149) stays on its reduced leftover payload and does not gain this
leftover-map incomplete item caption.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the member
list with the leftover-map graphic display of persisted `ξ` and `ζ`,
leftover-map axes name persisted Gabriel inertia share when finite,
leftover-map axis ticks name the same coordinates shown on the pair row,
pair segments name persisted leftover-map distance `d`, persisted leftover-map
reconstruction `R̂`, persisted leftover-map explained leftover share `e`,
persisted leftover-map unexplained leftover share `s`, persisted leftover-map
cross share `x`, persisted leftover-map unexplained leftover `U`, persisted
leftover residual `R`, persisted leftover observed `Y`, persisted leftover
expected `E`, persisted leftover-map rank, the plot names persisted leftover-map
complete-case coverage, the plot names persisted leftover-map item
complete-case coverage, the plot names persisted leftover-map incomplete
post coverage, the plot names persisted leftover-map incomplete item
coverage, the pair list names persisted leftover-map item complete-case
coverage, the pair list names persisted leftover-map incomplete post
coverage, and the pair list names persisted leftover-map incomplete item
coverage; click a post marker or a pair button opens that post.
Hidden posts stay hidden. Rank-0 unused axes still plot at the origin and still
name incomplete criteria on the pair list when that dropped count is persisted.

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
leftover-map item complete-case coverage on the pair list, and leftover-map
incomplete post coverage on the pair list.

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
`R̂ = ξ_{1:2} · ζ_{1:2}`. Incomplete columns are dropped from the
complete-case residual rectangle; pair-list incomplete item coverage names
how many scored criteria stayed out of that factorization.)
