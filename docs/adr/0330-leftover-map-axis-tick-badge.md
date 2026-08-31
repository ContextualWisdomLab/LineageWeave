# ADR 0330 — Name leftover-map singular values on leftover-axis ticks independently of leftover-map axis share

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map singular values on leftover-axis report badges independently of leftover-map
axis share ([ADR 0325](0325-leftover-map-axis-singular-only.md)), leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0329](0329-leftover-map-compare-axis-tick-badge.md)), leftover-map comparison graphic leftover-map
axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)), leftover-map graphic leftover-map axis
tick leftover-map singular values independently of leftover-map axis share
([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0325 already captions leftover-axis report
badges as leftoverMapAxisBadge independently of leftover-map axis share. ADR 0270
already ticks leftover-map graphic leftover-map axes at persisted `ξ` / `ζ`
projections. ADR 0327 already captions leftover-map graphic leftover-map axis ticks
with `σ_k` through leftoverMapPlotTickAxisBadge. ADR 0329 already captions leftover-map
comparison leftover-axis ticks with `σ_k` through leftoverMapCompareAxisTickBadge.
Those leftover-axis report badges still omit leftover-axis ticks, so a buyer who
reads leftover-axis badges or leftover-map graphic leftover-map axis ticks can treat leftover-map
coordinate ticks or leftover-map axis share as leftover-map structure without a next action.
A missing, non-finite, or negative singular value is not a leftover score and must omit
independently of leftover-map axis share. Rank-0 unused axes still persist `σ_k = 0`.
A finite negative leftover is shown, never clamped. Do not invent `σ_k` from leftover-map
axis share. Do not invent leftover-map axis share from `σ_k`. Leftover-axis ticks never
name leftover-map axis share.

This increment names leftover-axis ticks leftover-map singular values as leftoverMapAxisTickBadge,
matching leftoverMapAxisBadge, leftoverMapCompareAxisTickBadge, leftoverMapPlotTickAxisBadge,
leftoverMapComparePlotTickAxisBadge, leftoverMapCompareAxisBadge, leftoverMapComparePlotAxisBadge,
and leftoverMapPlotAxisBadge. Leftover-axis ticks reuse `layoutLeftoverMapPlot` ticks so origin
`0.00` plus unique finite `ξ` / `ζ` projections match the leftover-map graphic. Copy stays
`leftover axis {k} tick {value} σ {singular}` when `σ_k` is finite so they stay distinct from leftover-map
comparison leftover-axis ticks `leftover map comparison leftover axis {k} tick {value} σ {singular}`
(ADR 0329), from leftover-map comparison graphic leftover-map axis ticks
`leftover map comparison graphic leftover-map axis {k} tick {value} σ {singular}` (ADR 0328), from leftover-map
graphic leftover-map axis ticks `leftover-map axis {k} tick {value} σ {singular}` (ADR 0327), from leftover-axis
`leftover axis {k} σ {value}` (ADR 0325), and from leftover-map graphic leftover-map axis
`leftover-map axis {k} σ {value}` (ADR 0324). It does not add columns. Do not invent a leftover score.
Do not invent a theta.

This protected increment uses **0330** so it does not collide with leftover-map comparison leftover-axis
tick leftover-map singular values independently of leftover-map axis share (0329), leftover-map comparison graphic leftover-map
axis tick leftover-map singular values independently of leftover-map axis share (0328), leftover-map graphic leftover-map
axis tick leftover-map singular values independently of leftover-map axis share (0327), leftover-map singular values on leftover-axis
report badges independently of leftover-map axis share (0325), leftover-map axis share persistence (0148), or the dashboard stacks.

## Decision

On leftover-axis ticks on the leftover-pair list leftover-axis surface, caption leftover-map axis `k`
tick `{value}` with persisted leftover-map singular value `σ_k` when leftoverMapAxisTickBadge returns a
usable leftover-axis tick caption that includes that singular value. Share and singular value omit
independently through that helper, and leftover-map axis share is never named on leftover-axis ticks:
no `σ_k` keeps `leftover axis {k} tick {value}`; `σ_k` only is
`leftover axis {k} tick {value} σ {singular}`. A missing, non-finite, or negative singular value
omits that `σ` tick caption and keeps a usable leftover-axis tick coordinate caption. Rank-0 unused
axes still name `σ 0.00`. Origin `0.00` plus each unique finite persisted `ξ` / `ζ` projection still
name leftover-axis ticks. If `layoutLeftoverMapPlot` is null, omit leftover-axis ticks. Click a leftover
pair to open that post.

Leftover-axis tick leftover-map singular values omit independently of leftover-map comparison leftover-axis
tick leftover-map singular values, leftover-map comparison graphic leftover-map axis tick leftover-map singular
values, leftover-map graphic leftover-map axis tick leftover-map singular values, leftover-map graphic-display leftover-map
axis singular values, leftover-axis report badge leftover-map singular values, and leftover-map comparison leftover-axis
singular values. A missing leftover-map axis share omits leftover-map axis share and keeps a usable leftover-axis
tick `σ` caption.

This increment does not change leftover-map comparison leftover-axis ticks. Those leftover-map comparison leftover-axis
ticks stay `leftover map comparison leftover axis {axis} tick {value} σ {singular}` (ADR 0329). This increment
does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover score. Do not invent a theta.

## Consequences

After `make seed`, leftover-axis ticks name persisted leftover-map singular values when leftoverMapAxisTickBadge
returns a usable leftover-axis tick `σ` caption even when leftover-map axis share is omitted; click a leftover
pair opens that post. Hidden posts stay hidden. Rank-0 unused axes still name leftover-axis tick `σ 0.00`.
Leftover-map comparison leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0329), leftover-map comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map
axis share (ADR 0328), leftover-map graphic leftover-map axis tick leftover-map singular values independently of leftover-map
axis share (ADR 0327), leftover-axis report badge leftover-map singular values independently of leftover-map axis share
(ADR 0325), leftover-map graphic-display leftover-map singular values (ADR 0324), leftover-map singular values on leftover-axis
report badges on the grouping comparison strip (ADR 0323), and leftover-map graphic leftover-map axis ticks (ADR 0270) remain.

## Related

Independent of leftover-map comparison leftover-axis tick leftover-map singular values independently of leftover-map
axis share ([ADR 0329](0329-leftover-map-compare-axis-tick-badge.md)). Independent of leftover-map comparison graphic leftover-map
axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)). Independent of leftover-map graphic leftover-map axis tick leftover-map
singular values independently of leftover-map axis share
([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)). Independent of leftover-map singular values on leftover-axis report badges
independently of leftover-map axis share ([ADR 0325](0325-leftover-map-axis-singular-only.md)). Independent of leftover-map
coordinate ticks on the leftover-map graphic ([ADR 0270](0270-leftover-map-coordinate-ticks.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)).

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
