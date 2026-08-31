# ADR 0325 — Name leftover-map singular values on leftover-axis report badges independently of leftover-map axis share

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map singular values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)), leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of leftover-map
singular values on leftover-map graphic-display axes
([ADR 0324](0324-leftover-map-plot-axis-singular.md)), leftover-map singular
values on leftover-axis report badges on the grouping comparison strip
([ADR 0323](0323-leftover-map-compare-axis-singular.md)), leftover-map
singular values on the grouping comparison leftover-map graphic
([ADR 0321](0321-leftover-map-compare-plot-singular.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0322 captions leftover-axis report badges
with `leftover axis {axis} σ {value} {share}%` when `σ_k` is finite, and
falls back to `leftover axis {axis} {share}%` when `σ_k` is omitted. Those
badges still couple leftover-map singular values to leftover-map axis share:
a missing, non-finite leftover-map axis share is formatted as `NaN%` beside
a finite `σ_k`, so Gabriel (1971) singular values appear to invent leftover-map
axis share. ADR 0323 already omits share and singular value independently on
grouping comparison leftover-axis badges. ADR 0324 already omits share and
singular value independently on leftover-map graphic-display axes. Period
leftover-axis badges still hide the σ-only copy `leftover axis {k} σ {value}`.
A missing, non-finite, or negative singular value is not a leftover score and
must omit independently of leftover-map axis share. Rank-0 unused axes still
persist `σ_k = 0`. A finite negative leftover is shown, never clamped. Do not
invent `σ_k` from leftover-map axis share. Do not invent leftover-map axis
share from `σ_k`.

This increment captions leftover-axis report badges with already persisted
leftover-map singular values independently of leftover-map axis share.
Leftover-axis report badges stay `leftover axis {k} σ {value}` when share is
omitted so they stay distinct from leftover-axis `leftover axis {k} σ {value} {share}%`
(ADR 0322), from hyphen `leftover-map axis {k} σ {value}` (ADR 0324), from
comparison leftover-axis `leftover map comparison leftover axis {k} σ {value}`
(ADR 0323), and from comparison graphic
`leftover map comparison graphic leftover-map axis {k} σ {value}`.
It does not add columns. Do not invent a leftover score. Do not invent a
theta.

This protected increment uses **0325** so it does not collide with leftover-map
singular values on leftover-map graphic-display axes (0324), leftover-map
singular values on leftover-axis report badges on the grouping comparison
strip (0323), leftover-map singular values on leftover-axis report badges
(0322), leftover-map singular values on the grouping comparison leftover-map
graphic (0321), leftover-map axis share persistence (0148), or the dashboard
stacks.

## Decision

On leftover-axis report badges, caption leftover-map axis `k` with persisted
leftover-map singular value `σ_k` when that singular value is finite and
non-negative, including rank-0 zero singular values. Share and singular
value omit independently: no share and no `σ_k` omits that leftover-axis
report badge; share only is `leftover axis {k} {share}%`; `σ_k` only is
`leftover axis {k} σ {value}`; both is `leftover axis {k} σ {value} {share}%`.
A missing or non-finite leftover-map axis share omits that share caption and
does not invent leftover-map axis share from `σ_k`. A missing, non-finite, or
negative singular value omits that `σ` badge and keeps a usable leftover-axis
share caption. Rank-0 unused axes still name `σ 0.00`. Click a leftover pair
to open that post.

Leftover-axis report badge leftover-map singular values omit independently of
leftover-map graphic-display leftover-map axis singular values and leftover-map
comparison leftover-axis singular values. A missing leftover-map axis share
omits that leftover-axis share caption and keeps a usable leftover-axis `σ`
caption, leftover-map graphic leftover-map axis `σ` caption, leftover-map
comparison leftover-axis `σ` caption, leftover-map comparison graphic leftover-map
axis `σ` caption, leftover-map graphic leftover-map axis ticks, leftover-map
distance caption, leftover-map rank caption, leftover expected `E`, leftover
observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`,
leftover-map reconstruction `R̂`, and leftover-map graphic coverage notes.

This increment does not change leftover-map singular values on leftover-map
graphic-display axes. Those leftover-map graphic axes stay
`leftover-map axis {axis} σ {value} ({share}%)` (ADR 0324). This increment does
not change leftover-map singular values on leftover-axis report badges on the
grouping comparison strip (ADR 0323). This increment does not persist leftover-map
inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-axis report badges name persisted leftover-map
singular values when finite even when leftover-map axis share is omitted;
click a leftover pair opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-axis `σ 0.00`. Leftover-map graphic-display leftover-map
singular values (ADR 0324), leftover-axis report badge leftover-map singular
values with share (ADR 0322), and grouping comparison leftover-axis report
badge leftover-map singular values (ADR 0323) remain.

## Related

Independent of leftover-map singular values on leftover-map graphic-display
axes ([ADR 0324](0324-leftover-map-plot-axis-singular.md)). Independent of
leftover-map singular values on leftover-axis report badges on the grouping
comparison strip ([ADR 0323](0323-leftover-map-compare-axis-singular.md)).
Independent of leftover-map singular values on leftover-axis report badges
that still require leftover-map axis share in the combined caption
([ADR 0322](0322-leftover-map-axis-singular.md)). Independent of leftover-map
comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
([ADR 0326](0326-leftover-map-compare-plot-axis-badge.md)).

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
