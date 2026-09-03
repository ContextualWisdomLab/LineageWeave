# ADR 0359 — Name leftover-map origin on leftover-map pair independently of leftover-map leftover-axis leftover-map origin

**Decision status:** Proposed
**Date:** 2026-09-03

Amends leftover-map origin on leftover-map leftover-axis independently of leftover-map comparison leftover-axis leftover-map origin
([ADR 0358](0358-leftover-map-axis-origin-badge.md)). Independent of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0351](0351-leftover-map-list-post-origin-badge.md)). Independent of leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0352](0352-leftover-map-list-criterion-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks on the competing origin-tick stack (do not mix #877). Independent of dirty draft leftoverMapPlotOriginBadge reconstruction (do not mix #890 stale ADR 0347 / v2.104.0 identity). Do not mix `feat/leftover-map-list-origin-badge-v21140`.

## Context

ADR 0358 already names leftover-map leftover-axis leftover-map origin
`leftover axis leftover-map origin {origin}` when leftoverMapAxisOriginBadge returns a usable leftover-map origin caption.
Rank-0 unused axes still persist leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). Leftover-map pair leftover-map origin stayed unnamed
that increment (`leftoverMapListOriginBadge` was not exported).
Do not invent leftover-map origin from leftover-map pair leftover-map
criterion leftover-map origin leftover-map item coordinates `ζ`. leftoverMapAxisOriginBadge stays leftover-map leftover-axis leftover-map origin keys from ADR 0358.
leftoverMapCompareAxisOriginBadge stays leftover-map comparison leftover-axis leftover-map origin keys from ADR 0357.
leftoverMapComparePlotOriginBadge stays leftover-map comparison graphic leftover-map origin keys from ADR 0356.
leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys from ADR 0355.
leftoverMapListPostBadge stays leftover-map pair leftover-map post leftover-map origin leftover-map person coordinate keys from ADR 0351.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys from ADR 0352.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys from ADR 0346.

This increment names leftover-map pair leftover-map origin as leftoverMapListOriginBadge.
Leftover-map pair leftover-map origin stays
`leftover pair leftover-map origin {origin}`
when leftoverMapListOriginBadge returns a usable leftover-map origin caption, so it stays distinct from leftover-map
leftover-axis leftover-map origin
`leftover axis leftover-map origin {origin}`,
leftover-map comparison leftover-axis leftover-map origin
`leftover map comparison leftover axis leftover-map origin {origin}`,
leftover-map comparison graphic leftover-map origin
`leftover map comparison graphic leftover-map origin {origin}`,
leftover-map graphic leftover-map origin
`leftover-map origin {origin}`,
leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates
`leftover pair leftover-map post {title} at leftover-map origin ξ {person}`,
and leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates
`leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}`.
Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). leftoverMapCompareListOriginBadge stays unnamed
this increment. It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0359** / **v2.116.0** so it does not collide with leftover-map leftover-axis leftover-map origin independently of leftover-map comparison leftover-axis leftover-map origin
(0358 / v2.115.0), leftover-map comparison leftover-axis leftover-map origin independently of leftover-map comparison graphic leftover-map origin
(0357 / v2.114.0), leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates (0352 / v2.109.0), leftover-map leftover-axis origin ticks (#877), dirty draft #890, or the stale remote `feat/leftover-map-list-origin-badge-v21140`.

## Decision

On leftover-map pair, caption leftover-map origin
when leftoverMapListOriginBadge returns a usable leftover-map origin caption. Rank-0 unused axes still name leftover-map
origin `(0.00, 0.00)`. Do not invent leftover-map origin from leftover-map item coordinates `ζ`, leftover-map axis share, or leftover-map singular values `σ_k`.
leftoverMapAxisOriginBadge, leftoverMapCompareAxisOriginBadge, leftoverMapComparePlotOriginBadge, leftoverMapPlotOriginBadge, leftoverMapListPostBadge, leftoverMapListCriterionBadge,
leftoverMapCompareListPostBadge, leftoverMapCompareListCriterionBadge, leftoverMapPlotTickAxisBadge, leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge
do not change leftover-map origin naming this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map pair leftover-map origin names
leftover-map origin independently of leftover-map leftover-axis leftover-map origin, leftover-map comparison leftover-axis leftover-map origin, leftover-map comparison graphic leftover-map origin, leftover-map graphic leftover-map origin, leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
leftoverMapAxisOriginBadge stays leftover-map leftover-axis leftover-map origin keys.
leftoverMapCompareAxisOriginBadge stays leftover-map comparison leftover-axis leftover-map origin keys.
leftoverMapComparePlotOriginBadge stays leftover-map comparison graphic leftover-map origin keys.
leftoverMapPlotOriginBadge stays leftover-map graphic leftover-map origin keys.
leftoverMapListCriterionBadge stays leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinate keys.
leftoverMapListPostBadge stays leftover-map pair leftover-map post leftover-map origin leftover-map person coordinate keys.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys.
leftover-map leftover-axis leftover-map origin independently of leftover-map comparison leftover-axis leftover-map origin
(ADR 0358) remain.

## Related

Independent of leftover-map leftover-axis leftover-map origin independently of leftover-map comparison leftover-axis leftover-map origin
([ADR 0358](0358-leftover-map-axis-origin-badge.md)). Independent of leftover-map comparison leftover-axis leftover-map origin independently of leftover-map comparison graphic leftover-map origin
([ADR 0357](0357-leftover-map-compare-axis-origin-badge.md)). Independent of leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates independently of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0352](0352-leftover-map-list-criterion-origin-badge.md)). Independent of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates
([ADR 0351](0351-leftover-map-list-post-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map
axis share and leftover-map singular values
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
