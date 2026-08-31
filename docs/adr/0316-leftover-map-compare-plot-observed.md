# ADR 0316 — Name leftover observed on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0317](0317-leftover-map-compare-plot-expected.md)
(leftover expected on the grouping comparison leftover-map graphic)

Amends leftover observed on graphic-display pair segments
([ADR 0278](0278-leftover-map-segment-observed.md)), leftover observed
on grouping comparison strip pair rows
([ADR 0299](0299-leftover-map-compare-observed.md)), leftover residual
on the grouping comparison leftover-map graphic
([ADR 0315](0315-leftover-map-compare-plot-residual.md)), leftover-map
unexplained leftover on the grouping comparison leftover-map graphic
([ADR 0314](0314-leftover-map-compare-plot-unexplained-leftover.md)), leftover-map
cross share on the grouping comparison leftover-map graphic
([ADR 0313](0313-leftover-map-compare-plot-cross-share.md)), leftover-map
unexplained leftover share on the grouping comparison leftover-map graphic
([ADR 0312](0312-leftover-map-compare-plot-unexplained-share.md)), leftover-map
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
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover observed
disclosure ([ADR 0163](0163-leftover-observed-expected.md)), leftover pairs on
the grouping comparison strip
([ADR 0149](0149-leftover-pairs-on-comparison-strip.md)), leftover residual
on grouping comparison strip pair rows
([ADR 0298](0298-leftover-map-compare-residual.md)), leftover residual
on pair segments ([ADR 0277](0277-leftover-map-segment-residual.md)), leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover
expected on the grouping comparison leftover-map graphic.

## Context

ADR 0163 already persists leftover observed `Y` and leftover expected
`E[Y|θ, item]`. ADR 0278 already captions period-report leftover-map pair
segments with `leftover observed {label}` when that leftover observed is
finite. ADR 0299 already captions grouping comparison leftover-pair
buttons with that same persisted leftover observed under accessible name
`Leftover map comparison observed`. ADR 0315 already captions leftover
residual on the grouping comparison leftover-map graphic. The comparison
graphic still reuses `leftover observed {label}`, so a buyer who compares leftover
pairs can treat the period-report graphic caption as the comparison graphic
leftover observed even after the strip names `Y`. Hiding a distinct
comparison-graphic leftover observed caption lets leftover residual `R` or leftover expected
`E` be read as leftover observed without a next action. When `Y`, `E`, and `R` are
finite, `Y − E = R`; the comparison graphic must name the same
persisted `Y` the pair row and strip already show. A finite negative leftover is
shown, never clamped.

This increment captions leftover observed on the grouping
comparison leftover-map graphic from already-named leftover observed
through formatLeftoverMapObserved. Comparison copy uses the accessible
name `leftover map comparison graphic leftover observed {label}` so it stays
distinct from `leftover observed {label}` on the
period-report graphic and from strip `Leftover map comparison observed`.
It does not add columns. It does not recompute leftover observed
from `R` and `E`, leftover residual, leftover-map unexplained leftover, leftover-map reconstruction, leftover-map distance,
plotted coordinates, leftover-map rank, leftover-map axis share, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, leftover pair count, or the count of unused
axes. Do not invent a leftover score. Do not invent a theta.

The dashboard stack already used neighbouring leftover facts under other
numbers. This protected increment uses **0316** so it does not collide with
leftover residual on the grouping comparison leftover-map graphic
(0315), leftover-map unexplained leftover on the grouping comparison leftover-map graphic
(0314), leftover-map cross share on the grouping comparison leftover-map graphic
(0313), leftover residual on grouping comparison strip pair rows
(0298), leftover residual on pair segments (0277), leftover observed
on grouping comparison strip pair rows (0299), leftover observed
on pair segments (0278), leftover observed / expected disclosure (0163), leftover-map
graphic display (0268), leftover-map coordinates (0267), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption each pair segment
with persisted leftover observed when formatLeftoverMapObserved
returns a usable badge, next to leftover residual `R`. Use the
distinct accessible name `leftover map comparison graphic leftover observed {label}`
so the graphic caption is not the strip badge (`Leftover map comparison observed`)
and is not the period-report graphic caption (`leftover observed {label}`).
A missing or non-finite `Y` omits that leftover-map comparison graphic
leftover observed caption and keeps leftover residual `R` when
formatLeftoverMapResidual returns a usable badge, leftover-map unexplained leftover `U` when
formatLeftoverMapUnexplained returns a usable badge, leftover-map cross share `x` when
formatLeftoverMapCrossShare returns a usable badge, leftover-map unexplained leftover share `s` when
formatLeftoverMapUnexplainedShare returns a usable badge, leftover-map explained leftover share `e` when
formatLeftoverMapExplainedShare returns a usable badge, leftover-map reconstruction `R̂` when
formatLeftoverMapReconstruction returns a usable signed badge, leftover-map distance `d`, leftover map comparison
axis share when finite, leftover map comparison axis text, leftover-map comparison
graphic coverage when leftoverMapCoverageCounts returns usable complete-case
integers, leftover-map comparison graphic item coverage when leftoverMapItemCoverageCounts
returns usable complete-case integers, leftover-map comparison graphic incomplete
posts when leftoverMapIncompletePostCount returns a usable dropped integer,
leftover-map comparison graphic incomplete items when leftoverMapIncompleteItemCount
returns a usable dropped integer, leftover-map rank when that rank is a non-negative
integer, leftover expected `E` when finite, leftover-map reconstruction `R̂` when
finite, leftover-map distance `d`, plus the strip leftover observed badge.
Rank-0 origin cells still name `Y 0.00` when that persisted leftover
observed is finite. A finite negative leftover is shown, never clamped. Do not invent `Y` from
`R` and `E`, leftover residual, leftover-map reconstruction, leftover-map unexplained leftover, leftover-map distance,
plotted coordinates, leftover-map rank, leftover-map axis share, leftover-map post
coverage, leftover-map item coverage, leftover-map incomplete post coverage,
leftover-map incomplete item coverage, leftover pair count, or the count of unused
axes. Click a post marker to open that post.

Leftover observed omits independently of leftover residual captions,
leftover-map unexplained leftover captions,
leftover-map cross share captions,
unexplained leftover share captions, explained leftover share captions, reconstruction captions,
coverage notes, and leftover-map distance. A missing leftover
observed omits leftover-map comparison graphic leftover observed and keeps
a usable leftover residual caption, a usable leftover-map unexplained leftover caption, a usable leftover-map cross share caption, a usable unexplained leftover share caption, a usable explained leftover share caption, a usable reconstruction caption, a usable
distance caption, a usable post caption, a usable item caption, a usable incomplete
posts caption, and a usable incomplete items caption.

This increment does not caption leftover-map rank on the comparison graphic
with a distinct comparison-graphic name. Leftover expected `E` on that comparison
graphic is [ADR 0317](0317-leftover-map-compare-plot-expected.md). A finite negative leftover on neighbouring fields is shown,
never clamped.

Do not add SQL migrations. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover
observed on that graphic when formatLeftoverMapObserved
returns a usable badge. Rank-0 unused axes still plot at
the origin and still name `Y 0.00` when that persisted leftover
observed is finite. Click a post marker or a pair button opens that post. Hidden posts
stay hidden. When `Y`, `E`, and `R` are finite, `Y − E = R`. When `R`, `R̂`,
and `U` are finite, `U + R̂ = R`. When `R`, `R̂`, `U`, `x`, `s`, and `e` are
finite, `e + s + x = 1`. When coordinates, reconstruction, and distance
are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover-map
complete-case coverage persistence, leftover pairs on the grouping comparison
strip, leftover residual on grouping comparison strip pair rows, leftover
expected on grouping comparison strip pair rows, leftover observed
on grouping comparison strip pair rows, leftover residual
on pair segments, leftover observed on pair segments, leftover expected on
pair segments, leftover-map unexplained leftover on the grouping
comparison leftover-map graphic, leftover residual on the grouping
comparison leftover-map graphic, leftover-map graphic display, leftover-map
coordinates, leftover-map coordinate ticks, leftover-map complete-case
coverage on the grouping comparison leftover-map graphic, leftover-map
axis share on the grouping comparison leftover-map graphic,
and leftover expected on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Observed
category after IRT main effects is persisted `Y`. Grouping comparison leftover
observed captions that persisted leftover on the grouping comparison leftover-map
graphic only when formatLeftoverMapObserved returns a usable badge.
Rank-0 unused axes still name `Y 0.00` when that leftover
observed is stored. A finite negative leftover is shown, never clamped.)

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
