# ADR 0319 — Name leftover-map distance on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map distance on graphic-display pair segments
([ADR 0271](0271-leftover-map-segment-distance.md)), leftover-map rank
on the grouping comparison leftover-map graphic
([ADR 0318](0318-leftover-map-compare-plot-rank.md)), leftover expected
on the grouping comparison leftover-map graphic
([ADR 0317](0317-leftover-map-compare-plot-expected.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map coordinates
([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map
coordinate ticks on the grouping comparison leftover-map graphic.

## Context

ADR 0267 already persists leftover-map distance `d = ‖ξ_{1:2} − ζ_{1:2}‖`.
ADR 0271 already captions period-report leftover-map pair segments with
`leftover-map distance {label}` when that leftover-map distance is finite.
ADR 0318 already captions leftover-map rank on the grouping comparison leftover-map
graphic. The comparison graphic still reuses `leftover-map distance {label}`, so a
buyer who compares leftover pairs can treat the period-report graphic caption as
the comparison graphic leftover-map distance even after the strip names coordinates.
Hiding a distinct comparison-graphic leftover-map distance caption lets leftover-map
rank or leftover-map reconstruction `R̂` be read as leftover-map distance without a
next action. When coordinates, reconstruction, and distance are finite,
`R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`; the comparison graphic must name the same persisted
`d` the pair row already shows. A finite negative leftover is shown, never clamped.

This increment captions leftover-map distance on the grouping comparison leftover-map
graphic from already-named leftover-map distance through formatLeftoverMapDistance.
Comparison copy uses the accessible name
`leftover map comparison graphic leftover-map distance {label}` so it stays
distinct from `leftover-map distance {label}` on the period-report graphic. It does
not add columns. It does not recompute leftover-map distance from plotted pixel
length or from coordinates. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0319** so it does not collide with leftover-map
rank on the grouping comparison leftover-map graphic (0318), leftover expected on
that graphic (0317), leftover-map distance on pair segments (0271), leftover-map
coordinates (0267), leftover-map graphic display (0268), leftover-map coordinate
ticks (0270), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption each pair segment
with persisted leftover-map distance when formatLeftoverMapDistance returns a usable
badge, next to leftover-map rank. Use the distinct accessible name
`leftover map comparison graphic leftover-map distance {label}` so the graphic
caption is not the period-report graphic caption (`leftover-map distance {label}`).
A missing or non-finite `d` omits that leftover-map comparison graphic leftover-map
distance caption and keeps leftover-map rank when formatLeftoverMapRank returns a
usable badge, leftover expected `E`, leftover observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map comparison graphic coverage notes, leftover-map rank, plus the pair-row leftover-map distance badge.
Rank-0 origin cells still name `d 0.00` when that persisted leftover-map distance is
finite. A finite negative leftover is shown, never clamped. Do not invent leftover-map
distance from plotted coordinates, leftover-map rank, leftover expected, leftover observed, leftover residual, leftover-map reconstruction, leftover-map unexplained leftover, leftover-map axis share, leftover-map post coverage, leftover-map item coverage, leftover-map incomplete post coverage, leftover-map incomplete item coverage, leftover pair count, or the count of unused axes. Click a post marker to open that post.

Leftover-map distance omits independently of leftover-map rank captions.
A missing leftover-map distance omits leftover-map comparison graphic leftover-map distance and keeps
a usable leftover-map rank caption.

This increment does not caption leftover-map coordinate ticks on the comparison graphic
with a distinct comparison-graphic name. Those ticks already sit on the period-report
graphic through ADR 0270.

Do not add SQL migrations. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
distance on that graphic when formatLeftoverMapDistance returns a usable badge.
Rank-0 unused axes still plot at the origin and still name `d 0.00` when that
persisted leftover-map distance is finite. Click a post marker or a
pair button opens that post. When coordinates, reconstruction, and distance are
finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover-map coordinate ticks on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
