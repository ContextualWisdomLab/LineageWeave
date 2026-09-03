# ADR 0358 — Name leftover-map origin on leftover-map leftover-axis independently of leftover-map comparison leftover-axis leftover-map origin

**Decision status:** Proposed
**Date:** 2026-09-03

**Amended by:** [ADR 0359](0359-leftover-map-list-origin-badge.md)

Amends leftover-map origin on leftover-map comparison leftover-axis independently of leftover-map comparison graphic leftover-map origin
([ADR 0357](0357-leftover-map-compare-axis-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0345](0345-leftover-map-compare-axis-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks on the competing origin-tick stack (do not mix #877). Independent of dirty draft leftoverMapPlotOriginBadge reconstruction (do not mix #890 stale ADR 0347 / v2.104.0 identity).

## Context

ADR 0357 already names leftover-map comparison leftover-axis leftover-map origin
`leftover map comparison leftover axis leftover-map origin {origin}` when leftoverMapCompareAxisOriginBadge returns a usable leftover-map origin caption.
Rank-0 unused axes still persist leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). Leftover-map leftover-axis leftover-map origin stayed unnamed
that increment (`leftoverMapAxisOriginBadge` was not exported).
Do not invent leftover-map origin from leftover-map comparison leftover-pair leftover-map
criterion leftover-map origin leftover-map item coordinates `ζ`. leftoverMapCompareAxisOriginBadge stays leftover-map comparison leftover-axis leftover-map origin keys from ADR 0357.
leftoverMapComparePlotOriginBadge stays leftover-map comparison graphic leftover-map origin keys from ADR 0356.
leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys from ADR 0355.
leftoverMapCompareListCriterionBadge stays leftover-map comparison leftover-pair leftover-map
criterion leftover-map origin leftover-map item coordinate keys from ADR 0354.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0352.
leftoverMapComparePlotCriterionBadge stays leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0350.
leftoverMapPlotCriterionBadge stays leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0347.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys from ADR 0343.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys from ADR 0344.
leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys from ADR 0345.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys from ADR 0346.

This increment names leftover-map leftover-axis leftover-map origin as leftoverMapAxisOriginBadge.
Leftover-map leftover-axis leftover-map origin stays
`leftover axis leftover-map origin {origin}`
when leftoverMapAxisOriginBadge returns a usable leftover-map origin caption, so it stays distinct from leftover-map
comparison leftover-axis leftover-map origin
`leftover map comparison leftover axis leftover-map origin {origin}`,
leftover-map comparison graphic leftover-map origin
`leftover map comparison graphic leftover-map origin {origin}`,
leftover-map graphic leftover-map origin
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
(`formatLeftoverMapCoordinatePair(0, 0)`). leftoverMapListOriginBadge stays unnamed
this increment. It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0358** / **v2.115.0** so it does not collide with leftover-map comparison leftover-axis leftover-map origin independently of leftover-map comparison graphic leftover-map origin
(0357 / v2.114.0), leftover-map comparison graphic leftover-map origin independently of leftover-map graphic leftover-map origin
(0356 / v2.113.0), leftover-map graphic leftover-map origin independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
(0355 / v2.112.0), leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates (0347 / v2.104.0), leftover-map leftover-axis origin ticks (#877), or dirty draft #890.

## Decision

On leftover-map leftover-axis, caption leftover-map origin
when leftoverMapAxisOriginBadge returns a usable leftover-map origin caption. Rank-0 unused axes still name leftover-map
origin `(0.00, 0.00)`. Do not invent leftover-map origin from leftover-map item coordinates `ζ`, leftover-map axis share, or leftover-map singular values `σ_k`.
leftoverMapCompareAxisOriginBadge, leftoverMapComparePlotOriginBadge, leftoverMapPlotOriginBadge, leftoverMapCompareListCriterionBadge, leftoverMapListCriterionBadge, leftoverMapComparePlotCriterionBadge, leftoverMapPlotCriterionBadge,
leftoverMapPlotTickAxisBadge, leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge
do not change leftover-map origin naming this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map leftover-axis leftover-map origin names
leftover-map origin independently of leftover-map comparison leftover-axis leftover-map origin, leftover-map comparison graphic leftover-map origin, leftover-map graphic leftover-map origin, leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
leftoverMapCompareAxisOriginBadge stays leftover-map comparison leftover-axis leftover-map origin keys.
leftoverMapComparePlotOriginBadge stays leftover-map comparison graphic leftover-map origin keys.
leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys.
leftoverMapCompareListCriterionBadge stays leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinate keys.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys.
leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys.
leftover-map comparison leftover-axis leftover-map origin independently of leftover-map comparison graphic leftover-map origin
(ADR 0357) remain.

## Related

Independent of leftover-map comparison leftover-axis leftover-map origin independently of leftover-map comparison graphic leftover-map origin
([ADR 0357](0357-leftover-map-compare-axis-origin-badge.md)). Independent of leftover-map comparison graphic leftover-map origin independently of leftover-map graphic leftover-map origin
([ADR 0356](0356-leftover-map-compare-plot-origin-badge.md)). Independent of leftover-map graphic leftover-map origin independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates
([ADR 0355](0355-leftover-map-plot-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map
axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0345](0345-leftover-map-compare-axis-tick-origin-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)). Independent of leftover-map
graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)).

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
