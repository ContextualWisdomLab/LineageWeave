# ADR 0343 — Name leftover-map origin on leftover-map graphic leftover-map axis ticks independently of leftover-map axis share and leftover-map singular values

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)
(leftover-map origin on leftover-map comparison graphic leftover-map axis ticks independently of leftover-map axis share and leftover-map singular values)

Amends leftover-map coordinate ticks
([ADR 0270](0270-leftover-map-coordinate-ticks.md)), leftover-map graphic leftover-map axis ticks leftover-map singular values
([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)), and leftover-map graphic leftover-map axis ticks leftover-map axis share
([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison leftover-pair leftover-map criterion leftover-map item coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates
([ADR 0342](0342-leftover-map-compare-list-criterion-coordinates.md)). Independent of leftover-map
comparison graphic leftover-map axis origin ticks (do not mix #877).

## Context

ADR 0270 already names leftover-map graphic leftover-map axis ticks
`leftover-map axis {axis} tick {value}`. ADR 0327 already names leftover-map
singular values `σ_k` on those ticks. ADR 0332 already names leftover-map
axis share on those ticks. Rank-0 unused axes still persist leftover-map
origin `0.00` (`formatSignedLeftoverValue(0)` emits no plus). Origin ticks
still interpolate leftover-map origin only through leftover-map tick keys.
Share and singular omit independently. A finite negative leftover is shown,
never clamped. Do not invent leftover-map origin from leftover-map axis share
or leftover-map singular values `σ_k`. leftoverMapComparePlotTickAxisBadge stays
`leftover map comparison graphic leftover-map axis {axis} tick {value}`
this increment.

This increment names leftover-map graphic leftover-map axis origin ticks as
leftoverMapPlotTickAxisBadge. Leftover-map graphic leftover-map axis origin ticks stay
`leftover-map axis {axis} origin tick {value}`
when leftoverMapPlotTickIsOrigin returns true, so they stay distinct from leftover-map
graphic leftover-map axis ticks
`leftover-map axis {axis} tick {value}`
and leftover-map comparison graphic leftover-map axis ticks
`leftover map comparison graphic leftover-map axis {axis} tick {value}`.
Share and singular still omit independently:
`leftover-map axis {axis} origin tick {value} σ {singular}`,
`leftover-map axis {axis} origin tick {value} {share}%`, and
`leftover-map axis {axis} origin tick {value} σ {singular} {share}%`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0343** so it does not collide with leftover-map
item coordinates on leftover-map comparison leftover pair leftover-map criterion independently of leftover-map comparison leftover pair leftover-map post leftover-map person coordinates
(0342) or leftover-map comparison graphic leftover-map axis origin ticks (#877).

## Decision

On leftover-map graphic leftover-map axis ticks, caption leftover-map origin
when leftoverMapPlotTickIsOrigin returns true. Rank-0 unused axes still name leftover-map
origin `0.00`. Share and singular omit independently of leftover-map origin.
Non-origin ticks stay leftover-map tick keys. leftoverMapComparePlotTickAxisBadge,
leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge do not name leftover-map
origin this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map graphic leftover-map axis origin ticks name
leftover-map origin independently of leftover-map axis share and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `0.00`.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map
axis tick keys. leftover-map graphic leftover-map axis ticks leftover-map singular values
independently of leftover-map axis share (ADR 0327) and leftover-map graphic leftover-map
axis ticks leftover-map axis share independently of leftover-map singular values
(ADR 0332) remain.

## Related

Independent of leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates independently of leftover-map
comparison leftover-pair leftover-map post leftover-map person coordinates
([ADR 0342](0342-leftover-map-compare-list-criterion-coordinates.md)). Independent of leftover-map
graphic leftover-map axis ticks leftover-map axis share independently of leftover-map
singular values ([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis ticks leftover-map singular values independently of leftover-map
axis share ([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)). Independent of leftover-map
coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)).

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map.)
