# ADR 0318 — Name leftover-map rank on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0319](0319-leftover-map-compare-plot-distance.md)
(leftover-map distance on the grouping comparison leftover-map graphic)

Amends leftover-map rank on graphic-display pair segments
([ADR 0280](0280-leftover-map-segment-rank.md)), leftover-map rank
on grouping comparison strip pair rows
([ADR 0301](0301-leftover-map-compare-rank.md)), leftover expected
on the grouping comparison leftover-map graphic
([ADR 0317](0317-leftover-map-compare-plot-expected.md)), leftover observed
on the grouping comparison leftover-map graphic
([ADR 0316](0316-leftover-map-compare-plot-observed.md)), leftover residual
on the grouping comparison leftover-map graphic
([ADR 0315](0315-leftover-map-compare-plot-residual.md)), leftover-map rank
([ADR 0164](0164-leftover-map-rank.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)). Independent of leftover-map
distance on the grouping comparison leftover-map graphic.

## Context

ADR 0164 already persists leftover-map rank — the number of Gabriel
singular values above the leftover singular floor. A rank-0 residual still
emits a stable closest/farthest pair so `make seed` is not empty; the stored
distance is then zero, not a fabricated interaction. ADR 0280 already captions
period-report leftover-map pair segments with `leftover-map rank {label}` when
that leftover-map rank is a non-negative integer. ADR 0301 already captions
grouping comparison leftover-pair buttons with that same persisted leftover-map
rank under accessible name `Leftover map comparison rank`. ADR 0317 already
captions leftover expected on the grouping comparison leftover-map graphic.
The comparison graphic still reuses `leftover-map rank {label}`, so a buyer who
compares leftover pairs can treat the period-report graphic caption as the
comparison graphic leftover-map rank even after the strip names `rank n`.
Hiding a distinct comparison-graphic leftover-map rank caption lets leftover
expected `E` or leftover-map distance `d` be read as leftover-map rank without
a next action. The comparison graphic must name the same persisted rank the
pair row and strip already show. Rank-0 origin cells still name `rank 0` when
that persisted leftover-map rank is a non-negative integer.

This increment captions leftover-map rank on the grouping comparison leftover-map
graphic from already-named leftover-map rank through formatLeftoverMapRank.
Comparison copy uses the accessible name
`leftover map comparison graphic leftover-map rank {label}` so it stays
distinct from `leftover-map rank {label}` on the period-report graphic and from
strip `Leftover map comparison rank`. It does not add columns. It does not
recompute leftover-map rank from plotted coordinates, leftover-map distance, or
the count of unused axes. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0318** so it does not collide with leftover
expected on the grouping comparison leftover-map graphic (0317), leftover observed
on that graphic (0316), leftover residual on that graphic (0315), leftover-map
rank on grouping comparison strip pair rows (0301), leftover-map rank on pair
segments (0280), leftover-map rank persistence (0164), leftover-map graphic
display (0268), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption each pair segment
with persisted leftover-map rank when formatLeftoverMapRank returns a usable
badge, next to leftover expected `E`. Use the distinct accessible name
`leftover map comparison graphic leftover-map rank {label}` so the graphic
caption is not the strip badge (`Leftover map comparison rank`) and is not the
period-report graphic caption (`leftover-map rank {label}`). A missing rank, a
negative rank, or a non-integer rank omits that leftover-map comparison graphic
leftover-map rank caption and keeps leftover expected `E` when
formatLeftoverMapExpected returns a usable badge, leftover observed `Y` when
formatLeftoverMapObserved returns a usable badge, leftover residual `R` when
formatLeftoverMapResidual returns a usable badge, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage notes, leftover expected `E`, leftover observed `Y`, plus the strip leftover-map rank badge.
Rank-0 origin cells still name `rank 0` when that persisted leftover-map rank is
a non-negative integer. Do not invent leftover-map rank from plotted coordinates,
leftover-map distance, leftover expected, leftover observed, leftover residual, leftover-map reconstruction, leftover-map unexplained leftover, leftover-map axis share, leftover-map post coverage, leftover-map item coverage, leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair count, or the count of unused axes. Click a post marker to open that post.

Leftover-map rank omits independently of leftover expected captions and leftover observed captions.
A missing leftover-map rank omits leftover-map comparison graphic leftover-map rank and keeps
a usable leftover expected caption and a usable leftover observed caption.

This increment does not caption leftover-map coordinate ticks on the comparison graphic
with a distinct comparison-graphic name. Leftover-map distance on that comparison
graphic is [ADR 0319](0319-leftover-map-compare-plot-distance.md). That leftover-map distance already sits
on the period-report graphic through ADR 0271.

Do not add SQL migrations. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
rank on that graphic when formatLeftoverMapRank returns a usable badge.
Rank-0 unused axes still plot at the origin and still name `rank 0` when that
persisted leftover-map rank is a non-negative integer. Click a post marker or a
pair button opens that post. When `Y`, `E`, and `R` are finite, `Y − E = R`.
When `R`, `R̂`, and `U` are finite, `U + R̂ = R`. When coordinates,
reconstruction, and distance are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover-map distance on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
