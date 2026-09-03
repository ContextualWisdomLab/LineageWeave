# ADR 0356 — Name leftover-map origin on leftover-map comparison graphic independently of leftover-map graphic leftover-map origin

**Decision status:** Proposed
**Date:** 2026-09-03

Amends leftover-map origin on leftover-map graphic independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
([ADR 0355](0355-leftover-map-plot-origin-badge.md)). Independent of leftover-map comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)). Independent of leftover-map graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0345](0345-leftover-map-compare-axis-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks on the competing origin-tick stack (do not mix #877). Independent of dirty draft leftoverMapPlotOriginBadge reconstruction (do not mix #890 stale ADR 0347 / v2.104.0 identity).

## Context

ADR 0355 already names leftover-map graphic leftover-map origin
`leftover-map origin {origin}` when leftoverMapPlotOriginBadge returns a usable leftover-map origin caption.
Rank-0 unused axes still persist leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). Leftover-map comparison graphic leftover-map origin stayed unnamed
that increment (`leftoverMapPlotOriginText` returned null for comparison).
Do not invent leftover-map origin from leftover-map comparison leftover-pair leftover-map
criterion leftover-map origin leftover-map item coordinates `ζ`. leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys from ADR 0355.
leftoverMapCompareListCriterionBadge stays leftover-map comparison leftover-pair leftover-map
criterion leftover-map origin leftover-map item coordinate keys from ADR 0354.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0352.
leftoverMapComparePlotCriterionBadge stays leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0350.
leftoverMapPlotCriterionBadge stays leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0347.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys from ADR 0343.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys from ADR 0344.
leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys from ADR 0345.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys from ADR 0346.

This increment names leftover-map comparison graphic leftover-map origin as leftoverMapComparePlotOriginBadge.
Leftover-map comparison graphic leftover-map origin stays
`leftover map comparison graphic leftover-map origin {origin}`
when leftoverMapComparePlotOriginBadge returns a usable leftover-map origin caption, so it stays distinct from leftover-map
graphic leftover-map origin
`leftover-map origin {origin}`,
leftover-map graphic leftover-map axis origin ticks
`leftover-map axis {axis} origin tick {value}`,
leftover-map comparison graphic leftover-map axis origin ticks
`leftover map comparison graphic leftover-map axis {axis} origin tick {value}`,
leftover-map comparison leftover-axis origin ticks
`leftover map comparison leftover axis {axis} origin tick {value}`,
leftover-map leftover-axis origin ticks
`leftover axis {axis} origin tick {value}`,
leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover map comparison leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}`,
leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}`,
leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}`,
and leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover-map criterion {label} at leftover-map origin ζ {item}`.
Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). leftoverMapCompareAxisOriginBadge stays unnamed
this increment. It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0356** / **v2.113.0** so it does not collide with leftover-map graphic leftover-map origin independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
(0355 / v2.112.0), leftover-map comparison leftover-pair leftover-map
criterion leftover-map origin leftover-map item coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map origin leftover-map person coordinates
(0354 / v2.111.0), leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates (0347 / v2.104.0), leftover-map leftover-axis origin ticks (#877), or dirty draft #890.

## Decision

On leftover-map comparison graphic, caption leftover-map origin
when leftoverMapComparePlotOriginBadge returns a usable leftover-map origin caption. Rank-0 unused axes still name leftover-map
origin `(0.00, 0.00)`. Do not invent leftover-map origin from leftover-map item coordinates `ζ`, leftover-map axis share, or leftover-map singular values `σ_k`.
leftoverMapPlotOriginBadge, leftoverMapCompareListCriterionBadge, leftoverMapListCriterionBadge, leftoverMapComparePlotCriterionBadge, leftoverMapPlotCriterionBadge,
leftoverMapPlotTickAxisBadge, leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge
do not change leftover-map origin naming this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison graphic leftover-map origin names
leftover-map origin independently of leftover-map graphic leftover-map origin, leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys.
leftoverMapCompareListCriterionBadge stays leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinate keys.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys.
leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys.
leftover-map graphic leftover-map origin independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
(ADR 0355) remain.

## Related

Independent of leftover-map graphic leftover-map origin independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
([ADR 0355](0355-leftover-map-plot-origin-badge.md)). Independent of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item
coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0354](0354-leftover-map-compare-list-criterion-origin-badge.md)). Independent of leftover-map
graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map
axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0345](0345-leftover-map-compare-axis-tick-origin-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)).

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
