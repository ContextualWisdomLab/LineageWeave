# ADR 0328 — Name leftover-map singular values on leftover-map comparison graphic leftover-map axis ticks independently of leftover-map axis share

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map coordinate ticks on the grouping comparison leftover-map graphic
([ADR 0320](0320-leftover-map-compare-plot-ticks.md)), leftover-map comparison graphic
leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
([ADR 0326](0326-leftover-map-compare-plot-axis-badge.md)), leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map singular values independently of leftover-map
axis share ([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)), leftover-map singular
values on leftover-map graphic-display axes
([ADR 0324](0324-leftover-map-plot-axis-singular.md)), leftover-map singular values on
leftover-axis report badges independently of leftover-map axis share
([ADR 0325](0325-leftover-map-axis-singular-only.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0320 already ticks leftover-map comparison
graphic leftover-map axes at persisted `ξ` / `ζ` projections as
`leftover map comparison graphic leftover-map axis {k} tick {value}`. ADR 0326
already captions leftover-map comparison graphic-display leftover-map axes with
`σ_k` through leftoverMapComparePlotAxisBadge. ADR 0327 already captions leftover-map
graphic leftover-map axis ticks with `σ_k` through leftoverMapPlotTickAxisBadge.
Those leftover-map comparison graphic leftover-map axis ticks still omit `σ_k`, so a
buyer who reads leftover-map comparison graphic leftover-map axis ticks can treat leftover-map
coordinate ticks or leftover-map axis share as leftover-map structure without a
next action. A missing, non-finite, or negative singular value is not a leftover
score and must omit independently of leftover-map axis share. Rank-0 unused axes
still persist `σ_k = 0`. A finite negative leftover is shown, never clamped. Do
not invent `σ_k` from leftover-map axis share. Do not invent leftover-map axis
share from `σ_k`. Leftover-map comparison graphic leftover-map axis ticks never name leftover-map
axis share.

This increment names leftover-map comparison graphic leftover-map axis ticks leftover-map
singular values as leftoverMapComparePlotTickAxisBadge, matching leftoverMapPlotTickAxisBadge,
leftoverMapComparePlotAxisBadge, leftoverMapPlotAxisBadge, leftoverMapCompareAxisBadge, and leftoverMapAxisBadge.
Leftover-map comparison graphic leftover-map axis ticks stay
`leftover map comparison graphic leftover-map axis {k} tick {value} σ {singular}` when `σ_k` is finite so they stay
distinct from leftover-map graphic leftover-map axis ticks
`leftover-map axis {k} tick {value} σ {singular}` (ADR 0327), from leftover-map graphic leftover-map axis
`leftover-map axis {k} σ {value}` (ADR 0324), from leftover-axis `leftover axis {k} σ {value}`
(ADR 0325), from comparison leftover-axis `leftover map comparison leftover axis {k} σ {value}`
(ADR 0323), from comparison graphic leftover-map axis
`leftover map comparison graphic leftover-map axis {k} σ {value}` (ADR 0326), and from comparison graphic leftover-map
axis ticks `leftover map comparison graphic leftover-map axis {k} tick {value}` (ADR 0320).
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0328** so it does not collide with leftover-map
graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(0327), leftover-map comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
(0326), leftover-map singular values on leftover-axis report badges independently of
leftover-map axis share (0325), leftover-map singular values on leftover-map graphic-display
axes (0324), leftover-map coordinate ticks on the grouping comparison leftover-map graphic
(0320), leftover-map axis share persistence (0148), or the dashboard stacks.

## Decision

On leftover-map comparison graphic leftover-map axis ticks, caption leftover-map axis `k`
with persisted leftover-map singular value `σ_k` when leftoverMapComparePlotTickAxisBadge
returns a usable leftover-map axis tick caption that includes that singular value.
Share and singular value omit independently through that helper, and leftover-map
axis share is never named on leftover-map comparison graphic leftover-map axis ticks: no `σ_k`
keeps `leftover map comparison graphic leftover-map axis {k} tick {value}`; `σ_k` only is
`leftover map comparison graphic leftover-map axis {k} tick {value} σ {singular}`. A missing, non-finite, or
negative singular value omits that `σ` tick caption and keeps a usable leftover-map
comparison graphic leftover-map axis tick coordinate caption. Rank-0 unused axes still name
`σ 0.00`. Click a post marker to open that post. Criterion markers are not post
buttons.

Leftover-map comparison graphic leftover-map axis tick leftover-map singular values omit
independently of leftover-map graphic leftover-map axis tick leftover-map singular values,
leftover-map comparison graphic leftover-map axis singular values, leftover-map graphic-display leftover-map axis
singular values, leftover-axis report badge leftover-map singular values, and leftover-map comparison leftover-axis
singular values. A missing leftover-map axis share omits leftover-map axis share and keeps a usable
leftover-map comparison graphic leftover-map axis tick `σ` caption.

This increment does not change leftover-map graphic leftover-map axis ticks. Those leftover-map
graphic leftover-map axis ticks stay `leftover-map axis {axis} tick {value} σ {singular}`
(ADR 0327). This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison graphic leftover-map axis ticks name persisted
leftover-map singular values when leftoverMapComparePlotTickAxisBadge returns a usable
leftover-map axis tick `σ` caption even when leftover-map axis share is omitted;
click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map comparison graphic leftover-map axis tick `σ 0.00`. Leftover-map
graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0327), leftover-map comparison graphic leftover-map axis leftover-map singular values (ADR 0326), leftover-map
graphic-display leftover-map singular values (ADR 0324), leftover-axis report badge
leftover-map singular values independently of leftover-map axis share (ADR 0325),
and grouping comparison leftover-map graphic leftover-map axis ticks (ADR 0320)
remain.

## Related

Independent of leftover-map graphic leftover-map axis tick leftover-map singular values
independently of leftover-map axis share
([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
([ADR 0326](0326-leftover-map-compare-plot-axis-badge.md)). Independent of leftover-map
singular values on leftover-map graphic-display axes
([ADR 0324](0324-leftover-map-plot-axis-singular.md)). Independent of leftover-map
singular values on leftover-axis report badges independently of leftover-map axis
share ([ADR 0325](0325-leftover-map-axis-singular-only.md)). Independent of leftover-map
coordinate ticks on the grouping comparison leftover-map graphic
([ADR 0320](0320-leftover-map-compare-plot-ticks.md)).

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
