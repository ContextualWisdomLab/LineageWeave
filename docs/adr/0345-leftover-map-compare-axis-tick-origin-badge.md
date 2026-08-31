# ADR 0345 — Name leftover-map origin on leftover-map comparison leftover-axis ticks independently of leftover-map axis share and leftover-map singular values

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)

Amends leftover-map comparison leftover-axis ticks leftover-map singular values
([ADR 0329](0329-leftover-map-compare-axis-tick-badge.md)) and leftover-map comparison leftover-axis ticks leftover-map axis share
([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)). Independent of leftover-map
graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis origin ticks on the competing origin-tick stack (do not mix #877).

## Context

ADR 0329 already names leftover-map comparison leftover-axis ticks
`leftover map comparison leftover axis {axis} tick {value}`. ADR 0329 already names leftover-map
singular values `σ_k` on those ticks. ADR 0333 already names leftover-map
axis share on those ticks. Rank-0 unused axes still persist leftover-map
origin `0.00` (`formatSignedLeftoverValue(0)` emits no plus). Origin ticks
still interpolate leftover-map origin only through leftover-map comparison leftover-axis tick keys.
Share and singular omit independently. A finite negative leftover is shown,
never clamped. Do not invent leftover-map origin from leftover-map axis share
or leftover-map singular values `σ_k`. leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map
axis origin tick keys from ADR 0343. leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map
axis origin tick keys from ADR 0344. leftoverMapAxisTickBadge stays leftover-map tick keys
this increment.

This increment names leftover-map comparison leftover-axis origin ticks as
leftoverMapCompareAxisTickBadge. Leftover-map comparison leftover-axis origin ticks stay
`leftover map comparison leftover axis {axis} origin tick {value}`
when leftoverMapPlotTickIsOrigin returns true, so they stay distinct from leftover-map
comparison leftover-axis ticks
`leftover map comparison leftover axis {axis} tick {value}`,
leftover-map comparison graphic leftover-map axis origin ticks
`leftover map comparison graphic leftover-map axis {axis} origin tick {value}`,
and leftover-map graphic leftover-map axis origin ticks
`leftover-map axis {axis} origin tick {value}`.
Share and singular still omit independently:
`leftover map comparison leftover axis {axis} origin tick {value} σ {singular}`,
`leftover map comparison leftover axis {axis} origin tick {value} {share}%`, and
`leftover map comparison leftover axis {axis} origin tick {value} σ {singular} {share}%`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0345** so it does not collide with leftover-map
comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
(0344) or leftover-map comparison leftover-axis origin ticks (#877).

## Decision

On leftover-map comparison leftover-axis ticks, caption leftover-map origin
when leftoverMapPlotTickIsOrigin returns true. Rank-0 unused axes still name leftover-map
origin `0.00`. Share and singular omit independently of leftover-map origin.
Non-origin ticks stay leftover-map comparison leftover-axis tick keys. leftoverMapPlotTickAxisBadge,
leftoverMapComparePlotTickAxisBadge, and leftoverMapAxisTickBadge do not change leftover-map origin naming
this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison leftover-axis origin ticks name
leftover-map origin independently of leftover-map axis share and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `0.00`.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys.
leftover-map comparison leftover-axis ticks leftover-map singular values
independently of leftover-map axis share (ADR 0329) and leftover-map comparison leftover-axis
ticks leftover-map axis share independently of leftover-map singular values
(ADR 0333) remain.

## Related

Independent of leftover-map comparison graphic leftover-map axis origin ticks independently of leftover-map
axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)). Independent of leftover-map
graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis ticks leftover-map axis share independently of leftover-map
singular values ([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis ticks leftover-map singular values independently of leftover-map
axis share ([ADR 0329](0329-leftover-map-compare-axis-tick-badge.md)).

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
