# ADR 0347 — Name leftover-map origin on leftover-map graphic independently of leftover-map axis origin ticks, leftover-map axis share, and leftover-map singular values

**Decision status:** Proposed
**Date:** 2026-08-31

**Numbering status:** provisional conflict. ADR 0347 is also claimed by the active leftover-map criterion-origin stack (#891). This proposal was retargeted behind the current #917 stack after that collision was detected and MUST receive a new non-conflicting ADR/version identity during conflict-preserving reconstruction before it can become Accepted or merge.

**Amended by:** none yet

Amends leftover-map graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)). Independent of leftover-map leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0346](0346-leftover-map-axis-tick-origin-badge.md)). Independent of leftover-map
comparison leftover-axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0345](0345-leftover-map-compare-axis-tick-origin-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map singular values
([ADR 0344](0344-leftover-map-compare-plot-tick-origin-badge.md)). Independent of leftover-map
comparison graphic leftover-map origin (do not mix #877).

## Context

ADR 0343 already names leftover-map graphic leftover-map axis origin ticks
`leftover-map axis {axis} origin tick {value}` when leftoverMapPlotTickIsOrigin returns true.
Rank-0 unused axes still persist leftover-map origin `0.00`
(`formatSignedLeftoverValue(0)` emits no plus). Leftover-map origin on leftover-map
graphic still interpolates leftover-map origin only through leftover-map axis origin tick keys.
Share and singular omit independently. A finite negative leftover is shown,
never clamped. Do not invent leftover-map origin from leftover-map axis share
or leftover-map singular values `σ_k`. leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map
axis origin tick keys from ADR 0344. leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys from ADR 0345.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys from ADR 0346.

This increment proposes naming leftover-map graphic leftover-map origin as
leftoverMapPlotOriginBadge. Leftover-map graphic leftover-map origin stays
`leftover-map origin {origin}`
when leftoverMapPlotOriginBadge returns a usable leftover-map origin caption, so it stays distinct from leftover-map
graphic leftover-map axis origin ticks
`leftover-map axis {axis} origin tick {value}`,
leftover-map comparison graphic leftover-map axis origin ticks
`leftover map comparison graphic leftover-map axis {axis} origin tick {value}`,
leftover-map comparison leftover-axis origin ticks
`leftover map comparison leftover axis {axis} origin tick {value}`,
and leftover-map leftover-axis origin ticks
`leftover axis {axis} origin tick {value}`.
Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`
(`formatLeftoverMapCoordinatePair(0, 0)`). leftoverMapComparePlotOriginBadge stays unnamed
this increment. It does not add columns. Do not invent a leftover score. Do not invent a theta.

The original branch allocated **0347**, but the live queue now contains a separate active ADR 0347 in #891 and its descendants. That allocation is therefore not authoritative. Preserve the feature delta, keep this decision Proposed, and renumber/version it only after reconstructing it on the current predecessor without overwriting intervening stack changes.

## Decision

On leftover-map graphic, caption leftover-map origin
when leftoverMapPlotOriginBadge returns a usable leftover-map origin caption. Rank-0 unused axes still name leftover-map
origin `(0.00, 0.00)`. Do not invent leftover-map origin from leftover-map axis share or leftover-map singular values `σ_k`.
leftoverMapPlotTickAxisBadge, leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisTickBadge, and leftoverMapAxisTickBadge
do not change leftover-map origin naming this increment. leftover-map comparison graphic leftover-map origin stays unnamed this increment.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After the proposal is reconstructed with a unique ADR/version identity and accepted, leftover-map graphic leftover-map origin names
leftover-map origin independently of leftover-map axis origin ticks, leftover-map axis share, and leftover-map
singular values. Rank-0 unused axes still name leftover-map origin `(0.00, 0.00)`.
leftoverMapPlotTickAxisBadge stays leftover-map graphic leftover-map axis origin tick keys.
leftoverMapComparePlotTickAxisBadge stays leftover-map comparison graphic leftover-map axis origin tick keys.
leftoverMapCompareAxisTickBadge stays leftover-map comparison leftover-axis origin tick keys.
leftoverMapAxisTickBadge stays leftover-map leftover-axis origin tick keys.
leftover-map graphic leftover-map axis origin ticks independently of leftover-map axis share and leftover-map
singular values (ADR 0343) remain.

## Related

Independent of leftover-map leftover-axis origin ticks independently of leftover-map
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
