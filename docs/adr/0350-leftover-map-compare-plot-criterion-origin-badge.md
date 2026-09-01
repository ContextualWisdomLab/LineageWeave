# ADR 0350 — Name leftover-map origin on leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates

**Decision status:** Accepted
**Date:** 2026-09-02

Amends leftover-map item coordinates on leftover-map comparison graphic leftover-map criterion markers independently of leftover-map post ξ markers
([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)). Independent of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0349](0349-leftover-map-compare-plot-post-origin-badge.md)). Independent of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
([ADR 0348](0348-leftover-map-plot-post-origin-badge.md)). Independent of leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map person coordinates
([ADR 0347](0347-leftover-map-plot-criterion-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks on the competing origin-tick stack (do not mix #877).

## Context

ADR 0336 already names leftover-map comparison graphic leftover-map criterion leftover-map item coordinates
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`. Rank-0 unused axes still persist leftover-map
origin `(0.00, 0.00)` (`formatSignedLeftoverValue(0)` emits no plus). Origin leftover-map
item coordinates still interpolate leftover-map origin only through leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate keys. A missing or non-finite leftover-map item coordinate pair omits independently
of leftover-map person coordinates `ξ`. A finite negative leftover is shown, never clamped.
Do not invent leftover-map origin from leftover-map person coordinates `ξ`. leftoverMapPlotCriterionBadge stays
`leftover-map criterion {label} at leftover-map origin ζ {item}`
this increment. leftoverMapComparePlotPostBadge stays
`Open leftover map comparison graphic leftover-map post {title} at leftover-map origin ξ {person}`
this increment.

This increment names leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map
item coordinates as leftoverMapComparePlotCriterionBadge. Leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map
item coordinates stay
`leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}`
when leftoverMapPlotCoordinatePairIsOrigin returns true, so they stay distinct from leftover-map
comparison graphic leftover-map criterion leftover-map item coordinates
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`,
leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover-map criterion {label} at leftover-map origin ζ {item}`,
and leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates
`Open leftover map comparison graphic leftover-map post {title} at leftover-map origin ξ {person}`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0350** so it does not collide with leftover-map comparison graphic leftover-map
post leftover-map origin leftover-map person coordinates independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates
(0349) or leftover-map leftover-axis origin ticks (#877).

## Decision

On leftover-map comparison graphic leftover-map criterion markers, caption leftover-map origin
when leftoverMapPlotCoordinatePairIsOrigin returns true. Rank-0 unused axes still name leftover-map
origin `(0.00, 0.00)`. Non-origin leftover-map item coordinates stay leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate keys. leftoverMapPlotCriterionBadge, leftoverMapComparePlotPostBadge,
leftoverMapPlotPostBadge, leftoverMapListCriterionBadge, leftoverMapCompareListCriterionBadge, leftoverMapPlotTickAxisBadge,
leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge
do not change leftover-map origin naming this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item
coordinates name leftover-map origin independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates. Rank-0 unused
axes still name leftover-map origin `(0.00, 0.00)`. leftoverMapPlotCriterionBadge stays leftover-map graphic leftover-map
criterion leftover-map origin leftover-map item coordinate keys. leftoverMapComparePlotPostBadge
stays leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinate keys. leftover-map comparison graphic leftover-map
criterion leftover-map item coordinates independently of leftover-map post ξ markers
(ADR 0336) remain.

## Related

Independent of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person
coordinates independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0349](0349-leftover-map-compare-plot-post-origin-badge.md)). Independent of leftover-map
item coordinates on leftover-map comparison graphic leftover-map criterion markers independently of leftover-map
post ξ markers ([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)). Independent of leftover-map
graphic leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map
person coordinates ([ADR 0347](0347-leftover-map-plot-criterion-origin-badge.md)). Independent of leftover-map
leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)).

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
