# ADR 0335 — Name leftover-map origin on leftover-map comparison graphic leftover-map axis ticks independently of leftover-map axis share and leftover-map singular values

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)), leftover-map
comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)), leftover-map
coordinate ticks on the grouping comparison leftover-map graphic
([ADR 0320](0320-leftover-map-compare-plot-ticks.md)). Independent of leftover-map leftover-axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0334](0334-leftover-map-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)).

## Context

ADR 0320 already ticks leftover-map comparison graphic leftover-map axes at the origin
and at each unique finite persisted `ξ` / `ζ` projection. The origin is the rank-0
unused-axis location, not a leftover score. ADR 0331 already captions leftover-map
comparison graphic leftover-map axis ticks with leftover-map axis share through leftoverMapComparePlotTickAxisBadge
independently of leftover-map singular values. Those leftover-map comparison graphic leftover-map
axis origin ticks still reuse leftover-map comparison graphic leftover-map axis tick copy
`leftover map comparison graphic leftover-map axis {k} tick {value}`, so a buyer who reads leftover-map
comparison graphic leftover-map axis ticks can treat leftover-map origin `0.00` as leftover-map
coordinate structure without a next action. A missing or non-finite leftover-map axis share is
not a leftover score and must omit independently of leftover-map singular values. Rank-0 unused
axes still persist leftover-map origin at `0`. A finite negative leftover is shown, never
clamped. Do not invent leftover-map origin from leftover-map axis share or `σ_k`. Do not invent leftover-map
axis share from `σ_k`. Do not invent `σ_k` from leftover-map axis share. Leftover-map graphic leftover-map
axis ticks never name leftover-map origin this increment. Leftover-map comparison leftover-axis
ticks and leftover-axis ticks never name leftover-map origin this increment.

This increment names leftover-map comparison graphic leftover-map axis origin ticks as leftoverMapComparePlotTickAxisBadge,
matching leftoverMapComparePlotTickAxisBadge leftover-map axis share and leftover-map singular values.
Leftover-map comparison graphic leftover-map axis origin ticks stay
`leftover map comparison graphic leftover-map axis {k} origin tick {value}` when leftover-map axis share
and `σ_k` omit,
`leftover map comparison graphic leftover-map axis {k} origin tick {value} {share}%` when leftover-map
axis share is finite and `σ_k` omits,
`leftover map comparison graphic leftover-map axis {k} origin tick {value} σ {singular}` when `σ_k` is
finite and leftover-map axis share omits, and
`leftover map comparison graphic leftover-map axis {k} origin tick {value} σ {singular} {share}%`
when both are finite, so they stay distinct from leftover-map comparison graphic leftover-map axis ticks
`leftover map comparison graphic leftover-map axis {k} tick {value} σ {singular} {share}%` (ADR 0331),
from leftover-map graphic leftover-map axis ticks
`leftover-map axis {k} tick {value} σ {singular} {share}%` (ADR 0332),
from leftover-map comparison leftover-axis ticks
`leftover map comparison leftover axis {k} tick {value} σ {singular} {share}%` (ADR 0333),
from leftover-axis ticks
`leftover axis {k} tick {value} σ {singular} {share}%` (ADR 0334),
and from leftover-map comparison graphic leftover-map axis
`leftover map comparison graphic leftover-map axis {k} σ {value} ({share}%)` (ADR 0326).
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0335** so it does not collide with leftover-axis
tick leftover-map axis share independently of leftover-map singular values
(0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0331), leftover-map coordinate ticks on the grouping comparison leftover-map graphic
(0320), leftover-map axis share persistence (0148), or the dashboard stacks.

## Decision

On leftover-map comparison graphic leftover-map axis origin ticks, caption leftover-map axis `k`
origin `0.00` when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map origin tick
caption. Share and singular value omit independently through that helper: no `σ_k` and no
share keeps `leftover map comparison graphic leftover-map axis {k} origin tick {value}`;
`σ_k` only is `leftover map comparison graphic leftover-map axis {k} origin tick {value} σ {singular}`;
share only is `leftover map comparison graphic leftover-map axis {k} origin tick {value} {share}%`;
both are `leftover map comparison graphic leftover-map axis {k} origin tick {value} σ {singular} {share}%`.
A missing or non-finite leftover-map axis share omits that share origin tick caption and
keeps a usable leftover-map comparison graphic leftover-map axis origin tick coordinate caption,
including any leftover-map singular value. Rank-0 unused axes still name leftover-map origin
`0.00` and leftover-map axis share `0%`. Click a post marker to open that post. Criterion markers are not post
buttons.

Leftover-map comparison graphic leftover-map axis origin ticks omit independently of leftover-map
graphic leftover-map axis ticks, leftover-map comparison leftover-axis ticks, leftover-axis ticks, leftover-map
comparison graphic leftover-map axis leftover-map axis share, and leftover-map comparison graphic leftover-map
axis leftover-map singular values. A missing leftover-map singular value omits leftover-map singular
values and keeps a usable leftover-map comparison graphic leftover-map axis origin tick leftover-map
axis share caption. Do not invent leftover-map origin from leftover-map axis share or leftover-map singular
values. Coordinate ticks that are not leftover-map origin keep leftover-map comparison graphic leftover-map
axis tick copy.

This increment does not change leftover-map graphic leftover-map axis ticks, leftover-map comparison leftover-axis
ticks, or leftover-axis ticks. This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison graphic leftover-map axis origin ticks name leftover-map
origin when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map comparison graphic leftover-map
axis origin tick caption even when leftover-map axis share or leftover-map singular
values are omitted; click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map origin `0.00` and leftover-map axis share `0%`. Leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0331), leftover-map comparison leftover-axis leftover-map singular values (ADR 0323), leftover-axis report badge
leftover-map singular values independently of leftover-map axis share (ADR 0325),
and leftover-map graphic leftover-map axis ticks (ADR 0270)
remain.

## Related

Independent of leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0334](0334-leftover-map-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)). Independent of leftover-map
coordinate ticks on the grouping comparison leftover-map graphic
([ADR 0320](0320-leftover-map-compare-plot-ticks.md)). Independent of leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. The origin is the
rank-0 unused-axis location, not a leftover score.)
