# ADR 0334 — Name leftover-map axis share on leftover-axis ticks independently of leftover-map singular values

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-axis tick leftover-map singular values independently of leftover-map
axis share
([ADR 0330](0330-leftover-map-axis-tick-badge.md)), leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0330 already captions leftover-axis
ticks with `σ_k` through leftoverMapAxisTickBadge independently of leftover-map
axis share. Those leftover-axis ticks still omit leftover-map
axis share, so a buyer who reads leftover-axis ticks can treat leftover-map
coordinate ticks or leftover-map singular values as leftover-map structure without
a next action. A missing or non-finite leftover-map axis share is not a leftover
score and must omit independently of leftover-map singular values. Rank-0 unused
axes still persist leftover-map axis share `0`. A finite negative leftover is
shown, never clamped. Do not invent leftover-map axis share from `σ_k`. Do not
invent `σ_k` from leftover-map axis share. Leftover-map graphic leftover-map axis
ticks already name leftover-map axis share (ADR 0332). Leftover-map comparison graphic leftover-map
axis ticks already name leftover-map axis share (ADR 0331). Leftover-map comparison leftover-axis
ticks already name leftover-map axis share (ADR 0333).

This increment names leftover-axis ticks leftover-map
axis share as leftoverMapAxisTickBadge, matching leftoverMapAxisBadge,
leftoverMapPlotTickAxisBadge leftover-map axis share, leftoverMapComparePlotTickAxisBadge leftover-map axis share,
leftoverMapCompareAxisTickBadge leftover-map axis share, and leftoverMapAxisTickBadge leftover-map singular values.
Leftover-axis ticks stay
`leftover axis {k} tick {value} {share}%` when leftover-map
axis share is finite and `σ_k` omits, and
`leftover axis {k} tick {value} σ {singular} {share}%`
when both are finite, so they stay distinct from leftover-map graphic leftover-map axis ticks
`leftover-map axis {k} tick {value} σ {singular} {share}%` (ADR 0332),
from leftover-map comparison graphic leftover-map axis ticks
`leftover map comparison graphic leftover-map axis {k} tick {value} σ {singular} {share}%` (ADR 0331),
from leftover-map comparison leftover-axis ticks
`leftover map comparison leftover axis {k} tick {value} σ {singular} {share}%` (ADR 0333),
from leftover-axis `leftover axis {k} {share}%` (ADR 0325), from leftover-map comparison leftover-axis
`leftover map comparison leftover axis {k} {share}%` (ADR 0323), and from leftover-axis ticks
`leftover axis {k} tick {value} σ {singular}` (ADR 0330).
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0334** so it does not collide with leftover-map comparison leftover-axis
tick leftover-map axis share independently of leftover-map singular values
(0333), leftover-map graphic leftover-map
axis tick leftover-map axis share independently of leftover-map singular values
(0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0331), leftover-axis tick leftover-map singular values independently of leftover-map axis share
(0330), leftover-map comparison leftover-axis tick leftover-map singular values independently of leftover-map axis share
(0329), leftover-map axis share persistence (0148), or the dashboard stacks.

## Decision

On leftover-axis ticks, caption leftover-map axis `k`
with persisted leftover-map axis share when leftoverMapAxisTickBadge
returns a usable leftover-axis tick caption that includes that share.
Share and singular value omit independently through that helper: no `σ_k` and no
share keeps `leftover axis {k} tick {value}`;
`σ_k` only is `leftover axis {k} tick {value} σ {singular}`;
share only is `leftover axis {k} tick {value} {share}%`;
both are `leftover axis {k} tick {value} σ {singular} {share}%`.
A missing or non-finite leftover-map axis share omits that share tick caption and
keeps a usable leftover-axis tick coordinate caption,
including any leftover-map singular value. Rank-0 unused axes still name leftover-map
axis share `0%`. Click a leftover pair to open that post.

Leftover-axis tick leftover-map axis share omits
independently of leftover-map graphic leftover-map axis tick leftover-map axis share,
leftover-map comparison graphic leftover-map axis tick leftover-map axis share, leftover-map comparison leftover-axis
tick leftover-map axis share, leftover-axis report badge leftover-map axis share,
and leftover-map comparison leftover-axis leftover-map axis share. A missing leftover-map singular value omits leftover-map singular
values and keeps a usable leftover-axis tick leftover-map
axis share caption.

This increment does not change leftover-map comparison leftover-axis ticks, leftover-map
graphic leftover-map axis ticks, or leftover-map comparison graphic leftover-map axis ticks. This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-axis ticks name persisted
leftover-map axis share when leftoverMapAxisTickBadge returns a usable
leftover-axis tick leftover-map axis share caption even when leftover-map singular
values are omitted; click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-axis tick leftover-map axis share `0%`. Leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0333), leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0331), leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0330), leftover-map comparison leftover-axis leftover-map singular values (ADR 0323), leftover-axis report badge
leftover-map singular values independently of leftover-map axis share (ADR 0325),
and leftover-map graphic leftover-map axis ticks (ADR 0270)
remain.

## Related

Independent of leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)). Independent of leftover-axis
tick leftover-map singular values independently of leftover-map axis share
([ADR 0330](0330-leftover-map-axis-tick-badge.md)). Independent of leftover-map
singular values on leftover-axis report badges independently of leftover-map axis share
([ADR 0325](0325-leftover-map-axis-singular-only.md)). Independent of leftover-map
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
`α_j − β_i`; typically `p = 2` for the interaction map.)
