# ADR 0293 — Name leftover-map reconstruction on grouping comparison strip pair rows

**Decision status:** Accepted
**Date:** 2026-08-30

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
leftover-map reconstruction on pair segments
([ADR 0272](0272-leftover-map-segment-reconstruction.md)), leftover-map
complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)), leftover-map item
complete-case coverage on the grouping comparison strip
([ADR 0290](0290-leftover-map-compare-item-coverage.md)), leftover-map
incomplete post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), and leftover-map
incomplete item coverage on the grouping comparison strip
([ADR 0292](0292-leftover-map-compare-incomplete-item.md)). Independent of leftover-map
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
cross share persistence
([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map unexplained leftover
persistence ([ADR 0182](0182-leftover-map-unexplained.md)), leftover-map rank
persistence ([ADR 0164](0164-leftover-map-rank.md)), and leftover-map axis
share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0201 already persists leftover-map reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}` on leftover pair rows. ADR 0049 already names
that reconstruction on the period-report pair list. ADR 0272 already names
it on leftover-map graphic-display pair segments. ADR 0149 already carries
the same ABAC-filtered leftover pairs onto the grouping comparison strip,
and ADR 0292 already captions leftover-map incomplete item coverage on
each grouping row. The strip pair button still names only leftover-map
distance `d`, so a buyer who compares leftover pairs can treat Euclidean
gap as the leftover the two-axis map reconstructs even after the pair
list and graphic already name `R̂`. Hiding reconstruction on the strip
lets leftover residual `R` or leftover-map distance `d` be read as
leftover-map reconstruction without a next action.

This increment captions persisted leftover-map reconstruction on each
grouping comparison leftover-pair button through
formatLeftoverMapReconstruction. It does not add columns. It does not
recompute `R̂` from leftover-map distance, plotted coordinates, leftover
residual, unexplained leftover, or a pixel inner product. It does not
persist leftover-map inner product, cosine, or length as separate columns
(`R̂` already is the two-axis inner product). Do not invent a leftover
score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0293** so it does not collide with
leftover-map incomplete item coverage on the grouping comparison strip
(0292), leftover-map incomplete post coverage on the grouping comparison
strip (0291), leftover-map item complete-case coverage on the grouping
comparison strip (0290), leftover-map complete-case coverage on the
grouping comparison strip (0289), leftover-map post complete-case coverage
fail-closed on the pair list (0288), leftover-map incomplete item coverage
on the pair list (0287), leftover-map incomplete post coverage on the pair
list (0286), leftover-map item complete-case coverage on the pair list
(0285), leftover-map incomplete item coverage on the graphic display
(0284), leftover-map incomplete post coverage on the graphic display
(0283), leftover-map item complete-case coverage on the graphic display
(0282), leftover-map complete-case coverage on the graphic display (0281),
leftover-map rank on pair segments (0280), leftover-map reconstruction on
pair segments (0272), leftover-map reconstruction persistence (0201), or
the dashboard stacks.

## Decision

On the grouping comparison strip, caption each leftover pair button with
the same persisted leftover-map reconstruction formatter as the pair-row
`R̂` badge, next to leftover-map distance `d`. Use the distinct accessible
name `Leftover map comparison reconstruction` so the strip badge is not
the graphic caption (`leftover-map reconstruction {label}`). A missing or
non-finite `R̂` omits that leftover-map comparison reconstruction badge and
keeps leftover-map distance `d`, the strip leftover-map post coverage note,
leftover-map item coverage note, leftover-map incomplete post note,
leftover-map incomplete item note, leftover pairs, and any leftover-map
captions on the pair list and graphic. Rank-0 origin cells still name
`R̂ 0.00` when that persisted reconstruction is finite. Do not invent `R̂`
from leftover-map distance, plotted coordinates, leftover residual,
unexplained leftover, leftover-map rank, leftover-map post coverage,
leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, or the count of unused axes. Do not
add the leftover-map graphic to the strip. Click a leftover pair on the
strip to open that post.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, the grouping comparison strip names persisted leftover-map
post complete-case coverage, persisted leftover-map item complete-case
coverage, persisted leftover-map incomplete post coverage, and persisted
leftover-map incomplete item coverage on each grouping row when
leftoverMapCoverageCounts / leftoverMapItemCoverageCounts /
leftoverMapIncompletePostCount / leftoverMapIncompleteItemCount return usable
integers, then names leftover pairs with leftover-map distance `d` and
persisted leftover-map reconstruction `R̂` when finite. Closest and farthest
leftover pairs still sit above the member list with the leftover-map graphic
display; click a post marker or a pair button opens that post.
Hidden posts stay hidden. When coordinates, reconstruction, and distance
are all finite, `R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖`
remain the same identities already persisted by ADR 0267.

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
leftover-map reconstruction on pair segments, leftover-map reconstruction
persistence, leftover-map item complete-case coverage on the graphic display,
leftover-map item complete-case coverage on the pair list, leftover-map
incomplete post coverage on the graphic display, leftover-map incomplete
post coverage on the pair list, leftover-map incomplete item coverage on
the graphic display, leftover-map incomplete item coverage on the pair list,
and leftover-map post complete-case coverage fail-closed on the pair list.

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
`R̂ = ξ_{1:2} · ζ_{1:2}`. Grouping comparison reconstruction names that
persisted inner product on the strip pair row only when
formatLeftoverMapReconstruction returns a usable signed badge.)
