# ADR 0298 — Name leftover residual on grouping comparison strip pair rows

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover pairs on the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover residual
on pair segments
([ADR 0277](0277-leftover-map-segment-residual.md)), leftover-map unexplained
leftover on grouping comparison strip pair rows
([ADR 0297](0297-leftover-map-compare-unexplained-leftover.md)), leftover-map
cross share on grouping comparison strip pair rows
([ADR 0296](0296-leftover-map-compare-cross-share.md)), leftover-map
unexplained leftover share on grouping comparison strip pair rows
([ADR 0295](0295-leftover-map-compare-unexplained-share.md)), leftover-map
explained leftover share on grouping comparison strip pair rows
([ADR 0294](0294-leftover-map-compare-explained-share.md)), leftover-map
reconstruction on grouping comparison strip pair rows
([ADR 0293](0293-leftover-map-compare-reconstruction.md)), leftover-map
incomplete item coverage on the grouping comparison strip
([ADR 0292](0292-leftover-map-compare-incomplete-item.md)), leftover-map
incomplete post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), leftover-map item
complete-case coverage on the grouping comparison strip
([ADR 0290](0290-leftover-map-compare-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)), leftover-map unexplained
leftover persistence ([ADR 0182](0182-leftover-map-unexplained.md)), leftover-map
unexplained leftover on pair segments
([ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)), leftover-map
cross share persistence ([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map
cross share on pair segments
([ADR 0275](0275-leftover-map-segment-cross-share.md)), leftover-map unexplained
leftover share persistence ([ADR 0233](0233-leftover-map-unexplained-share.md)),
leftover-map unexplained leftover share on pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
explained leftover share persistence
([ADR 0266](0266-leftover-map-explained-share.md)), leftover-map explained
leftover share on pair segments
([ADR 0273](0273-leftover-map-segment-explained-share.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
and leftover-map reconstruction on pair segments
([ADR 0272](0272-leftover-map-segment-reconstruction.md)). Independent of leftover-map
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
pair segments ([ADR 0278](0278-leftover-map-segment-observed.md)), leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)),
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover observed `Y` /
expected `E` ([ADR 0163](0163-leftover-observed-expected.md)), leftover-map rank
persistence ([ADR 0164](0164-leftover-map-rank.md)), and leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0162 already discloses leftover residual `R = Y − E[Y|θ, item]` after
IRT main effects on leftover pair rows. ADR 0277 already names that residual
on leftover-map graphic-display pair segments. ADR 0297 already captions
persisted leftover-map unexplained leftover `U` on grouping comparison
leftover-pair buttons. The strip pair button still does not name `R`, so a
buyer who compares leftover pairs can treat leftover-map unexplained leftover
`U`, leftover-map cross share `x`, leftover-map unexplained leftover share
`s`, leftover-map explained leftover share `e`, leftover-map reconstruction
`R̂`, or leftover-map distance `d` as the leftover that entered the truncated
map even after the pair list and graphic already name `R`. When `Y`, `E`, and
`R` are finite, `Y − E = R`; when `R`, `R̂`, and `U` are finite, `U + R̂ = R`.
Hiding `R` on the strip lets those identities vanish without a next action.

This increment captions persisted leftover residual on each grouping
comparison leftover-pair button through formatLeftoverMapResidual. It does
not add columns. It does not recompute `R` from `Y` and `E`, from `U` and
`R̂`, leftover-map distance, plotted coordinates, leftover-map reconstruction,
leftover-map unexplained leftover, leftover-map explained leftover share,
leftover-map unexplained leftover share, or leftover-map cross share. It does
not persist leftover-map inner product, cosine, or length as separate columns.
Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0298** so it does not collide with
leftover-map unexplained leftover on grouping comparison strip pair rows
(0297), leftover-map cross share on grouping comparison strip pair rows
(0296), leftover-map unexplained leftover share on grouping comparison strip
pair rows (0295), leftover-map explained leftover share on grouping comparison
strip pair rows (0294), leftover-map reconstruction on grouping comparison
strip pair rows (0293), leftover-map incomplete item coverage on the grouping
comparison strip (0292), leftover-map incomplete post coverage on the grouping
comparison strip (0291), leftover-map item complete-case coverage on the
grouping comparison strip (0290), leftover-map complete-case coverage on the
grouping comparison strip (0289), leftover residual on pair segments (0277),
leftover residual disclosure (0162), leftover-map unexplained leftover on pair
segments (0276), leftover-map unexplained leftover persistence (0182), leftover-map
cross share on pair segments (0275), leftover-map cross share persistence
(0185), leftover-map unexplained leftover share on pair segments (0274),
leftover-map unexplained leftover share persistence (0233), leftover-map
explained leftover share on pair segments (0273), leftover-map explained
leftover share persistence (0266), leftover-map reconstruction on pair
segments (0272), leftover-map reconstruction persistence (0201), or the
dashboard stacks.

## Decision

On the grouping comparison strip, caption each leftover pair button with
the same persisted leftover residual formatter as the pair-row `R` badge,
next to leftover-map unexplained leftover `U`, leftover-map cross share `x`,
leftover-map unexplained leftover share `s`, leftover-map explained leftover
share `e`, leftover-map reconstruction `R̂`, and leftover-map distance `d`.
Use the distinct accessible name `Leftover map comparison leftover residual`
so the strip badge is not the graphic caption (`leftover residual {label}`).
A missing or non-finite `R` omits that leftover-map comparison leftover
residual badge and keeps leftover-map unexplained leftover `U` when finite,
leftover-map cross share `x` when finite, leftover-map unexplained leftover
share `s` when finite, leftover-map explained leftover share `e` when finite,
leftover-map reconstruction `R̂` when finite, leftover-map distance `d`, the
strip leftover-map post coverage note, leftover-map item coverage note,
leftover-map incomplete post note, leftover-map incomplete item note, leftover
pairs, and any leftover-map captions on the pair list and graphic. Rank-0
origin cells still name `R 0.00` when that persisted residual is finite. A
finite negative residual is shown, never clamped. Do not invent `R` from `Y`
and `E`, from `U` and `R̂`, leftover-map distance, plotted coordinates,
leftover-map reconstruction, leftover-map unexplained leftover, leftover-map
explained leftover share, leftover-map unexplained leftover share, leftover-map
cross share, leftover-map rank, leftover-map post coverage, leftover-map item
coverage, leftover-map incomplete post coverage, leftover-map incomplete item
coverage, or the count of unused axes. Do not add the leftover-map graphic to
the strip. Click a leftover pair on the strip to open that post.

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
integers, then names leftover pairs with leftover-map distance `d`, persisted
leftover-map reconstruction `R̂` when finite, persisted leftover-map
explained leftover share `e` when finite, persisted leftover-map unexplained
leftover share `s` when finite, persisted leftover-map cross share `x`
when finite, persisted leftover-map unexplained leftover `U` when finite,
and persisted leftover residual `R` when finite. Closest and farthest leftover
pairs still sit above the member list with the leftover-map graphic display;
click a post marker or a pair button opens that post.
Hidden posts stay hidden. When `Y`, `E`, and `R` are finite, `Y − E = R`.
When `R`, `R̂`, and `U` are finite, `U + R̂ = R`. When `R`, `R̂`, `U`, `x`,
`s`, and `e` are finite, `e + s + x = 1`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover-map axis share persistence,
leftover pairs on the grouping comparison strip, leftover-map complete-case
coverage on the grouping comparison strip, leftover-map item complete-case
coverage on the grouping comparison strip, leftover-map incomplete post
coverage on the grouping comparison strip, leftover-map incomplete item
coverage on the grouping comparison strip, leftover-map reconstruction on
grouping comparison strip pair rows, leftover-map explained leftover share
on grouping comparison strip pair rows, leftover-map unexplained leftover
share on grouping comparison strip pair rows, leftover-map cross share on
grouping comparison strip pair rows, leftover-map unexplained leftover on
grouping comparison strip pair rows, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map graphic display,
leftover residual on pair segments, leftover-map unexplained leftover on pair
segments, leftover-map unexplained leftover persistence, leftover-map cross
share on pair segments, leftover-map cross share persistence, leftover-map
unexplained leftover share on pair segments, leftover-map unexplained leftover
share persistence, leftover-map explained leftover share on pair segments,
leftover-map explained leftover share persistence, leftover-map reconstruction
on pair segments, leftover-map reconstruction persistence, leftover-map item
complete-case coverage on the graphic display, leftover-map item complete-case
coverage on the pair list, leftover-map incomplete post coverage on the graphic
display, leftover-map incomplete post coverage on the pair list, leftover-map
incomplete item coverage on the graphic display, leftover-map incomplete item
coverage on the pair list, and leftover-map post complete-case coverage
fail-closed on the pair list.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Leftover residual of
the leftover cell is `R = Y − E[Y|θ, item]` after IRT main effects.
Grouping comparison leftover residual names that persisted remainder on the
strip pair row only when formatLeftoverMapResidual returns a usable badge.
When finite, `Y − E = R`. When finite, `U + R̂ = R`. When finite,
`e + s + x = 1`.)
