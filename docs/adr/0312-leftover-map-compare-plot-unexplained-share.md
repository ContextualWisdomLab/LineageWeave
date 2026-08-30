# ADR 0312 — Name leftover-map unexplained leftover share on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map unexplained leftover share on graphic-display pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
unexplained leftover share on grouping comparison strip pair rows
([ADR 0295](0295-leftover-map-compare-unexplained-share.md)), leftover-map
explained leftover share on the grouping comparison leftover-map graphic
([ADR 0311](0311-leftover-map-compare-plot-explained-share.md)), leftover-map
reconstruction on the grouping comparison leftover-map graphic
([ADR 0310](0310-leftover-map-compare-plot-reconstruction.md)), leftover-map
incomplete item coverage on the grouping comparison leftover-map graphic
([ADR 0309](0309-leftover-map-compare-plot-incomplete-item.md)), leftover-map
incomplete post coverage on the grouping comparison leftover-map graphic
([ADR 0308](0308-leftover-map-compare-plot-incomplete-post.md)), leftover-map item
complete-case coverage on the grouping comparison leftover-map graphic
([ADR 0307](0307-leftover-map-compare-plot-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison leftover-map graphic
([ADR 0306](0306-leftover-map-compare-plot-coverage.md)), leftover-map axis share
on the grouping comparison leftover-map graphic
([ADR 0305](0305-leftover-map-compare-plot-axis-share.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map explained leftover
share persistence ([ADR 0266](0266-leftover-map-explained-share.md)), leftover pairs on
the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover-map
coordinates on the compare leftover-pair payload
([ADR 0303](0303-leftover-map-compare-coordinates-payload.md)), leftover-map
coordinates on grouping comparison strip pair rows
([ADR 0302](0302-leftover-map-compare-coordinates.md)), leftover-map
rank on grouping comparison strip pair rows
([ADR 0301](0301-leftover-map-compare-rank.md)), leftover expected on grouping
comparison strip pair rows
([ADR 0300](0300-leftover-map-compare-expected.md)), leftover observed on
grouping comparison strip pair rows
([ADR 0299](0299-leftover-map-compare-observed.md)), leftover residual
on grouping comparison strip pair rows
([ADR 0298](0298-leftover-map-compare-residual.md)), leftover-map unexplained leftover
on grouping comparison strip pair rows
([ADR 0297](0297-leftover-map-compare-unexplained.md)), leftover-map cross share
on grouping comparison strip pair rows
([ADR 0296](0296-leftover-map-compare-cross-share.md)), leftover-map unexplained
leftover share on grouping comparison strip pair rows
([ADR 0295](0295-leftover-map-compare-unexplained-share.md)), leftover-map
reconstruction on grouping comparison strip pair rows
([ADR 0293](0293-leftover-map-compare-reconstruction.md)), leftover-map
incomplete item coverage on the grouping comparison strip
([ADR 0292](0292-leftover-map-compare-incomplete-item.md)), leftover-map
incomplete post coverage on the grouping comparison strip
([ADR 0291](0291-leftover-map-compare-incomplete-post.md)), leftover-map item
complete-case coverage on the grouping comparison strip
([ADR 0290](0290-leftover-map-compare-item-coverage.md)), leftover-map
complete-case coverage on the grouping comparison strip
([ADR 0289](0289-leftover-map-compare-coverage.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover
observed `Y` / expected `E` ([ADR 0163](0163-leftover-observed-expected.md)), leftover-map unexplained leftover persistence ([ADR 0182](0182-leftover-map-unexplained.md)),
leftover-map rank ([ADR 0164](0164-leftover-map-rank.md)), leftover-map rank on pair
segments ([ADR 0280](0280-leftover-map-segment-rank.md)), leftover-map coordinate ticks
([ADR 0270](0270-leftover-map-coordinate-ticks.md)), leftover-map graphic display
([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map axis share on
the graphic display ([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map
complete-case coverage on the graphic display
([ADR 0281](0281-leftover-map-plot-coverage.md)), leftover-map item complete-case
coverage on the graphic display
([ADR 0282](0282-leftover-map-plot-item-coverage.md)), leftover-map incomplete
post coverage on the graphic display
([ADR 0283](0283-leftover-map-plot-incomplete.md)), leftover-map incomplete
item coverage on the graphic display
([ADR 0284](0284-leftover-map-plot-incomplete-item.md)), leftover-map reconstruction
on pair segments ([ADR 0272](0272-leftover-map-segment-reconstruction.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)), and leftover-map coordinates
([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map
post complete-case coverage fail-closed on the pair list
([ADR 0288](0288-leftover-map-list-post-coverage-helper.md)), leftover-map
incomplete item coverage on the pair list
([ADR 0287](0287-leftover-map-list-incomplete-item.md)), leftover-map incomplete
post coverage on the pair list
([ADR 0286](0286-leftover-map-list-incomplete-post.md)), leftover-map item
complete-case coverage on the pair list
([ADR 0285](0285-leftover-map-list-item-coverage.md)), leftover expected on pair
segments ([ADR 0279](0279-leftover-map-segment-expected.md)), leftover observed
on pair segments ([ADR 0278](0278-leftover-map-segment-observed.md)), leftover
residual on pair segments ([ADR 0277](0277-leftover-map-segment-residual.md)),
leftover-map unexplained leftover on pair segments
([ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)), leftover-map
cross share on pair segments ([ADR 0275](0275-leftover-map-segment-cross-share.md)),
leftover-map unexplained leftover share on pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map cross share persistence ([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), and leftover-map
cross share on the grouping comparison leftover-map graphic.

## Context

ADR 0233 already persists leftover-map unexplained leftover share
`s = U² / R²` of raw residual after two-axis Gabriel reconstruction.
ADR 0274 already captions period-report leftover-map pair segments with
`leftover-map unexplained leftover share {label}` when that unexplained leftover
share is finite. ADR 0295 already captions grouping comparison leftover-pair
buttons with that same persisted unexplained leftover share under accessible name
`Leftover map comparison unexplained leftover share`. ADR 0311 already captions
leftover-map explained leftover share on the grouping comparison leftover-map graphic.
The comparison graphic still reuses hyphen
`leftover-map unexplained leftover share {label}`, so a buyer who compares leftover
pairs can treat the period-report graphic caption as the comparison graphic
unexplained leftover share even after the strip names `s`. Hiding a distinct
comparison-graphic unexplained leftover share caption lets leftover-map
explained leftover share `e` or leftover residual `R` be read as leftover-map
unexplained leftover share without a next action. When `R`, `R̂`, `U`, `x`, `s`,
and `e` are finite, `e + s + x = 1`; the comparison graphic must name the same
persisted `s` the pair row and strip already show.

This increment captions leftover-map unexplained leftover share on the grouping
comparison leftover-map graphic from already-named leftover-map unexplained leftover
share through formatLeftoverMapUnexplainedShare. Comparison copy uses the accessible
name `leftover map comparison graphic unexplained leftover share {label}` so it stays
distinct from hyphen `leftover-map unexplained leftover share {label}` on the
period-report graphic and from strip `Leftover map comparison unexplained leftover share`.
It does not add columns. It does not recompute leftover-map unexplained leftover share
from `U` and `R`, leftover-map reconstruction, leftover residual, leftover-map distance,
plotted coordinates, leftover-map rank, leftover-map axis share, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, leftover pair count, or the count of unused
axes. Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0312** so it does not collide with
leftover-map explained leftover share on the grouping comparison leftover-map graphic
(0311), leftover-map reconstruction on the grouping comparison leftover-map graphic
(0310), leftover-map incomplete item coverage on the grouping comparison leftover-map
graphic (0309), leftover-map incomplete post coverage on the grouping comparison leftover-map
graphic (0308), leftover-map item complete-case coverage on the grouping comparison leftover-map
graphic (0307), leftover-map complete-case coverage on the grouping comparison
leftover-map graphic (0306), leftover-map axis share on the grouping comparison leftover-map
graphic (0305), leftover-map graphic display on the grouping comparison strip
(0304), leftover-map unexplained leftover share on grouping comparison strip pair rows
(0295), leftover-map unexplained leftover share on pair segments (0274), leftover-map
unexplained leftover share persistence (0233), leftover-map graphic display (0268), leftover-map
coordinates (0267), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption each pair segment
with persisted leftover-map unexplained leftover share when formatLeftoverMapUnexplainedShare
returns a usable badge, next to leftover-map explained leftover share `e`. Use the
distinct accessible name `leftover map comparison graphic unexplained leftover share {label}`
so the graphic caption is not the strip badge (`Leftover map comparison unexplained leftover share`)
and is not the period-report graphic caption (`leftover-map unexplained leftover share {label}`).
A missing or non-finite `s` omits that leftover-map comparison graphic
unexplained leftover share caption and keeps leftover-map explained leftover share `e` when
formatLeftoverMapExplainedShare returns a usable badge, leftover-map reconstruction `R̂` when
formatLeftoverMapReconstruction returns a usable signed badge, leftover-map distance `d`, leftover map comparison
axis share when finite, leftover map comparison axis text, leftover-map comparison
graphic coverage when leftoverMapCoverageCounts returns usable complete-case
integers, leftover-map comparison graphic item coverage when leftoverMapItemCoverageCounts
returns usable complete-case integers, leftover-map comparison graphic incomplete
posts when leftoverMapIncompletePostCount returns a usable dropped integer,
leftover-map comparison graphic incomplete items when leftoverMapIncompleteItemCount
returns a usable dropped integer, leftover-map rank when that rank is a non-negative
integer, leftover expected `E` when finite, leftover observed `Y` when finite,
leftover residual `R` when finite, leftover-map unexplained leftover `U` when
finite, leftover-map cross share `x` when finite, leftover-map reconstruction `R̂` when
finite, leftover-map distance `d`, plus the strip unexplained leftover share badge.
Rank-0 origin cells still name `U²/R² 0.00` when that persisted unexplained leftover
share is finite. A share greater than 1 is shown, never clamped. Do not invent `s` from
`U` and `R`, leftover-map reconstruction, leftover residual, leftover-map distance,
plotted coordinates, leftover-map rank, leftover-map axis share, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, leftover pair count, or the count of unused
axes. Click a post marker to open that post.

Unexplained leftover share omits independently of explained leftover share captions,
reconstruction captions, coverage notes, and leftover-map distance. A missing unexplained
leftover share omits leftover-map comparison graphic unexplained leftover share and keeps
a usable explained leftover share caption, a usable reconstruction caption, a usable
distance caption, a usable post caption, a usable item caption, a usable incomplete
posts caption, and a usable incomplete items caption.

This increment does not caption leftover-map cross share on the comparison graphic
with a distinct comparison-graphic name. That leftover-map cross share already sits on
the strip through ADR 0296. A finite negative leftover on neighbouring fields is shown,
never clamped.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
unexplained leftover share on that graphic when formatLeftoverMapUnexplainedShare
returns a usable badge. Rank-0 unused axes still plot at
the origin and still name `U²/R² 0.00` when that persisted unexplained leftover
share is finite. Click a post marker or a pair button opens that post. Hidden posts
stay hidden. When `Y`, `E`, and `R` are finite, `Y − E = R`. When `R`, `R̂`,
and `U` are finite, `U + R̂ = R`. When `R`, `R̂`, `U`, `x`, `s`, and `e` are
finite, `e + s + x = 1`. When coordinates, reconstruction, and distance
are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover pairs on the grouping comparison
strip, leftover-map complete-case coverage on the grouping comparison strip,
leftover-map item complete-case coverage on the grouping comparison strip,
leftover-map incomplete post coverage on the grouping comparison strip,
leftover-map incomplete item coverage on the grouping comparison strip,
leftover-map reconstruction on grouping comparison strip pair rows,
leftover-map explained leftover share on grouping comparison strip pair rows,
leftover-map unexplained leftover share on grouping comparison strip pair rows,
leftover-map cross share on grouping comparison strip pair rows,
leftover-map unexplained leftover on grouping comparison strip pair rows,
leftover residual on grouping comparison strip pair rows, leftover observed
on grouping comparison strip pair rows, leftover expected on grouping
comparison strip pair rows, leftover-map rank on grouping comparison strip
pair rows, leftover-map coordinates on grouping comparison strip pair rows,
leftover-map coordinates on the compare leftover-pair payload, leftover-map
inner product, leftover-map cosine, leftover-map length, leftover residual
on pair segments, leftover observed on pair segments, leftover expected on
pair segments, leftover-map rank on pair segments, leftover-map unexplained
leftover on pair segments, leftover-map unexplained leftover persistence,
leftover-map cross share on pair segments, leftover-map cross share
persistence, leftover-map unexplained leftover share on pair segments,
leftover-map unexplained leftover share persistence, leftover-map explained leftover
share on pair segments, leftover-map explained leftover share
persistence, leftover-map reconstruction on pair segments, leftover-map
reconstruction persistence, leftover-map reconstruction on the grouping
comparison leftover-map graphic, leftover-map explained leftover share on the grouping
comparison leftover-map graphic, leftover-map item complete-case coverage on the
graphic display, leftover-map item complete-case coverage on the pair list,
leftover-map incomplete post coverage on the graphic display, leftover-map
incomplete post coverage on the pair list, leftover-map incomplete item
coverage on the graphic display, leftover-map incomplete item coverage on
the pair list, leftover-map post complete-case coverage fail-closed on the
pair list, leftover-map rank persistence, leftover-map coordinate
persistence, leftover-map coordinate ticks, leftover-map complete-case
coverage on the graphic display, leftover-map complete-case coverage on the
grouping comparison leftover-map graphic, leftover-map item complete-case
coverage on the grouping comparison leftover-map graphic, leftover-map
incomplete post coverage on the grouping comparison leftover-map graphic,
leftover-map incomplete item coverage on the grouping comparison leftover-map
graphic, leftover-map axis share on the grouping comparison leftover-map graphic,
and leftover-map cross share on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Gabriel
reconstruction of the leftover cell is the two-axis inner product
`R̂ = ξ_{1:2} · ζ_{1:2}`. Unexplained leftover is `U = R − R̂`. Unexplained leftover
share of raw residual is `s = U² / R²`. Grouping comparison leftover-map unexplained
leftover share captions that persisted share on the grouping comparison leftover-map
graphic only when formatLeftoverMapUnexplainedShare returns a usable badge.
Rank-0 unused axes still name `U²/R² 0.00` when that unexplained leftover
share is stored. A share greater than 1 is shown, never clamped.)

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
