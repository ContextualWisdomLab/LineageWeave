# ADR 0324 — Name leftover-map singular values on leftover-map graphic-display axes

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
singular values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)), leftover-map singular
values on leftover-axis report badges on the grouping comparison strip
([ADR 0323](0323-leftover-map-compare-axis-singular.md)), leftover-map
singular values on the grouping comparison leftover-map graphic
([ADR 0321](0321-leftover-map-compare-plot-singular.md)), leftover-map
coordinate ticks on that comparison graphic
([ADR 0320](0320-leftover-map-compare-plot-ticks.md)), leftover-map
axis share on that comparison graphic
([ADR 0305](0305-leftover-map-compare-plot-axis-share.md)), leftover-map
graphic display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)), leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)), and
leftover-map coordinate ticks on the graphic display
([ADR 0270](0270-leftover-map-coordinate-ticks.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0269 captions leftover-map graphic-display
axes with share only as `leftover-map axis {k} ({share}%)`. ADR 0321 already
captions the grouping comparison leftover-map graphic with persisted `σ_k`.
ADR 0322 already captions leftover-axis report badges with persisted `σ_k`.
ADR 0323 already captions grouping comparison leftover-axis report badges
with persisted `σ_k`. Period leftover-map graphic axes still hide `σ_k`, so
Gabriel (1971) singular values appear on leftover-axis badges and on the
comparison graphic and never on the leftover-map graphic-display axes that
name the same axes. Hiding `σ_k` on leftover-map graphic-display axes lets
leftover-map axis share be read as leftover-map structure even when the buyer
cannot tell whether axis 1 is large because `σ_1` is large or because axis 2
collapsed. A missing, non-finite, or negative singular value is not a leftover
score and must omit independently of leftover-map axis share. Rank-0 unused
axes still persist `σ_k = 0`. A finite negative leftover is shown, never
clamped. Do not invent `σ_k` from leftover-map axis share.

This increment captions leftover-map graphic-display axes with already persisted
leftover-map singular values. Leftover-map graphic-display axes stay
`leftover-map axis {k} σ {value} ({share}%)` so they stay distinct from
leftover-axis badges `leftover axis {k} σ {value} {share}%`, from comparison
leftover-axis `leftover map comparison leftover axis {k} σ {value} {share}%`,
and from comparison graphic
`leftover map comparison graphic leftover-map axis {k} σ {value} ({share}%)`.
It does not add columns. Do not invent a leftover score. Do not invent a
theta.

This protected increment uses **0324** so it does not collide with leftover-map
singular values on leftover-axis report badges on the grouping comparison
strip (0323), leftover-map singular values on leftover-axis report badges
(0322), leftover-map singular values on the grouping comparison leftover-map
graphic (0321), leftover-map coordinate ticks on that graphic (0320), leftover-map
axis share on that graphic (0305), leftover-map graphic display on the grouping
comparison strip (0304), leftover-map axis share persistence (0148), leftover-map
axis share on the graphic display (0269), or the dashboard stacks.

## Decision

On leftover-map graphic-display axes, caption leftover-map axis `k` with
persisted leftover-map singular value `σ_k` when that singular value is
finite and non-negative, including rank-0 zero singular values. Share and
singular value omit independently: no share and no `σ_k` keeps
`leftover-map axis {k}`; share only is `leftover-map axis {k} ({share}%)`;
`σ_k` only is `leftover-map axis {k} σ {value}`; both is
`leftover-map axis {k} σ {value} ({share}%)`. A missing, non-finite, or
negative singular value omits that `σ` caption and keeps the existing
`leftover-map axis {k} ({share}%)` text. Do not invent `σ_k` from leftover-map
axis share. Axis 1 and axis 2 stay independently named. Click a leftover pair
to open that post.

Leftover-map graphic-display singular values omit independently of leftover-map
comparison graphic leftover-map axis singular values and leftover-axis report
badges. A missing singular value omits that leftover-map graphic-display `σ`
caption and keeps a usable leftover-map axis share caption, leftover-map
comparison graphic leftover-map axis `σ` caption, leftover-axis report badge
`σ` caption, leftover-map comparison leftover-axis `σ` caption, leftover-map
graphic leftover-map axis ticks, leftover-map distance caption, leftover-map
rank caption, leftover expected `E`, leftover observed `Y`, leftover residual
`R`, leftover-map unexplained leftover `U`, leftover-map reconstruction `R̂`,
and leftover-map graphic coverage notes.

This increment does not change leftover-map singular values on leftover-axis
report badges. Those leftover-axis badges stay
`leftover axis {axis} σ {value} {share}%` (ADR 0322). This increment does
not change leftover-map singular values on leftover-axis report badges on the
grouping comparison strip (ADR 0323). This increment does not persist leftover-map
inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map graphic-display axes name persisted leftover-map
singular values when finite together with persisted leftover-map axis share;
click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map axis `σ 0.00`. Grouping comparison leftover-map
graphic leftover-map singular values (ADR 0321), leftover-axis report badge
leftover-map singular values (ADR 0322), and grouping comparison leftover-axis
report badge leftover-map singular values (ADR 0323) remain.

## Related

Independent of leftover-map singular values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)). Independent of leftover-map
singular values on leftover-axis report badges on the grouping comparison
strip ([ADR 0323](0323-leftover-map-compare-axis-singular.md)). Independent of
leftover-map singular values on the grouping comparison leftover-map graphic
([ADR 0321](0321-leftover-map-compare-plot-singular.md)).

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
