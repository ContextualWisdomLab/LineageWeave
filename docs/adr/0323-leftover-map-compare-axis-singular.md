# ADR 0323 — Name leftover-map singular values on leftover-axis report badges on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map singular values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)), leftover-map singular
values on the grouping comparison leftover-map graphic
([ADR 0321](0321-leftover-map-compare-plot-singular.md)), leftover-map
axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)), leftover-map
graphic display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)). Independent of leftover-map
singular values on leftover-axis report badges in the period-report panel
(ADR 0322).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` on
`report_leftover_map_axis` together with leftover-map axis share
`σ_k² / Σ_j σ_j²`. ADR 0322 already captions period-report leftover-axis
badges with `leftover axis {axis} σ {value} {share}%` when that singular
value is finite and non-negative. ADR 0321 already captions the grouping
comparison leftover-map graphic with
`leftover map comparison graphic leftover-map axis {axis} σ {value}`
when that singular value is finite and non-negative. The grouping
comparison strip still omits leftover-axis report badges, so a buyer
who compares leftover pairs can treat leftover-map graphic `σ_k` as
the leftover-axis report badge without a next action. Hiding persisted
`σ_k` on leftover-axis report badges lets leftover-map axis share be
read as a leftover score. A missing, non-finite, or negative singular
value is not a leftover score and must omit independently of leftover-map
axis share. Rank-0 unused axes still persist `σ_k = 0`. A finite negative
leftover is shown, never clamped. Do not invent `σ_k` from leftover-map
axis share.

This increment captions leftover-map singular values on leftover-axis
report badges on the grouping comparison strip from already-named
leftover-map axes. Comparison copy uses the accessible names
`leftover map comparison leftover axis {axis} σ {value}` and
`leftover map comparison leftover axis {axis} σ {value} {share}%`
so they stay distinct from hyphen `leftover-map axis {axis} σ {value}`,
from pair-list and period-report leftover-axis
`leftover axis {axis} σ {value} {share}%` (ADR 0322), from comparison
graphic `leftover map comparison graphic leftover-map axis {axis} σ {value}`,
and from comparison axis-share
`leftover map comparison axis {axis} ({share}%)`. It does not add
columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0323** so it does not collide with leftover-map
singular values on leftover-axis report badges in the period-report panel
(0322), leftover-map singular values on the grouping comparison leftover-map
graphic (0321), leftover-map coordinate ticks on that graphic (0320), leftover-map
axis share on that graphic (0305), leftover-map graphic display on the grouping
comparison strip (0304), leftover-map axis share persistence (0148), or the
dashboard stacks.

## Decision

On the grouping comparison strip, caption leftover-map axis 1 and leftover-map
axis 2 leftover-axis report badges with persisted leftover-map singular
values `σ_k` when that singular value is finite and non-negative. Share
and singular value omit independently: no share and no `σ_k` omits that
leftover-axis report badge; share only is
`leftover map comparison leftover axis {k} {share}%`; `σ_k` only is
`leftover map comparison leftover axis {k} σ {value}`; both is
`leftover map comparison leftover axis {k} σ {value} {share}%`.
A missing, non-finite, or negative singular value omits that `σ` badge
and does not invent `σ_k` from leftover-map axis share. Rank-0 unused
axes still name `σ 0.00`. Click a leftover pair to open that post.

Leftover-map comparison leftover-axis singular values omit independently
of leftover-map comparison graphic leftover-map axis singular values and
leftover-map axis share. A missing singular value omits that leftover-map
comparison leftover-axis `σ` caption and keeps a usable leftover-map
comparison leftover-axis share caption, leftover-map comparison graphic
leftover-map axis `σ` caption, leftover-map comparison graphic leftover-map
axis ticks, leftover-map distance caption, leftover-map rank caption,
leftover expected `E`, leftover observed `Y`, leftover residual `R`,
leftover-map unexplained leftover `U`, leftover-map reconstruction `R̂`,
and leftover-map comparison graphic coverage notes.

This increment does not change leftover-map singular values on leftover-axis
report badges in the period-report panel. Those leftover-axis badges stay
`leftover axis {axis} σ {value} {share}%` (ADR 0322). This increment does
not persist leftover-map inner product, cosine, or length.

Do not add SQL migrations. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
singular values on leftover-axis report badges when those persisted `σ_k`
are finite and non-negative. Rank-0 unused axes still name leftover-map
comparison leftover axis `σ 0.00`. Click a post marker or a pair button
opens that post. When coordinates, reconstruction, and distance are finite,
`R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`. When leftover-map singular values and
leftover-map axis share are finite, leftover-map axis share is
`σ_k² / Σ_j σ_j²`.

## Related

Independent of leftover-map singular values on leftover-axis report badges
in the period-report panel ([ADR 0322](0322-leftover-map-axis-singular.md)).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
