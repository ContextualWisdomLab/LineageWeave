# ADR 0326 — Name leftover-map comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map singular values on the grouping comparison leftover-map
graphic ([ADR 0321](0321-leftover-map-compare-plot-singular.md)), leftover-map
axis share on that comparison graphic
([ADR 0305](0305-leftover-map-compare-plot-axis-share.md)), leftover-map axis
share persistence ([ADR 0148](0148-leftover-map-axis-share.md)). Independent of
leftover-map singular values on leftover-map graphic-display axes
([ADR 0324](0324-leftover-map-plot-axis-singular.md)), leftover-map singular
values on leftover-axis report badges independently of leftover-map axis share
([ADR 0325](0325-leftover-map-axis-singular-only.md)), leftover-map singular
values on leftover-axis report badges on the grouping comparison strip
([ADR 0323](0323-leftover-map-compare-axis-singular.md)), leftover-map singular
values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)).

## Context

ADR 0148 already persists leftover-map singular values `σ_k` and leftover-map
axis share `σ_k² / Σ_j σ_j²`. ADR 0321 already captions leftover-map singular
values on the grouping comparison leftover-map graphic with
`leftover map comparison graphic leftover-map axis {k} σ {value}` when `σ_k`
is finite. Those comparison graphic leftover-map axes still inline σ and share
in leftoverMapPlotAxisText instead of fail-closing through a named helper.
leftoverMapPlotAxisBadge (ADR 0324), leftoverMapCompareAxisBadge (ADR 0323),
and leftoverMapAxisBadge (ADR 0325) already fail-close leftover-map singular
values through named helpers. Pair-list leftover-map coverage fail-closes
through leftoverMapCoverageCounts (ADR 0288). An inlined comparison graphic
leftover-map axis can invent leftover-map inner product, cosine, or length,
or couple `σ_k` to leftover-map axis share. A missing, non-finite, or negative
singular value is not a leftover score and must omit independently of leftover-map
axis share. Rank-0 unused axes still persist `σ_k = 0`. A finite negative leftover
is shown, never clamped. Do not invent `σ_k` from leftover-map axis share. Do not
invent leftover-map axis share from `σ_k`.

This increment names leftover-map comparison graphic leftover-map axis leftover-map
singular values as leftoverMapComparePlotAxisBadge, matching leftoverMapPlotAxisBadge,
leftoverMapCompareAxisBadge, and leftoverMapAxisBadge. Comparison copy stays
`leftover map comparison graphic leftover-map axis {k} σ {value}` when share is
omitted so it stays distinct from leftover-axis `leftover axis {k} σ {value}`
(ADR 0325), from hyphen `leftover-map axis {k} σ {value}` (ADR 0324), and from
comparison leftover-axis `leftover map comparison leftover axis {k} σ {value}`
(ADR 0323). It does not add columns. Do not invent a leftover score. Do not invent
a theta.

This protected increment uses **0326** so it does not collide with leftover-map
singular values on leftover-axis report badges independently of leftover-map axis
share (0325), leftover-map singular values on leftover-map graphic-display axes
(0324), leftover-map singular values on leftover-axis report badges on the grouping
comparison strip (0323), leftover-map singular values on leftover-axis report badges
(0322), leftover-map singular values on the grouping comparison leftover-map graphic
(0321), leftover-map axis share persistence (0148), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption leftover-map axis `k`
with persisted leftover-map singular value `σ_k` when leftoverMapComparePlotAxisBadge
returns a usable leftover-map axis caption. Share and singular value omit
independently through that helper: no share and no `σ_k` returns null and the
graphic keeps `leftover map comparison axis {k}`; share only is
`leftover map comparison axis {k} ({share}%)`; `σ_k` only is
`leftover map comparison graphic leftover-map axis {k} σ {value}`; both is
`leftover map comparison graphic leftover-map axis {k} σ {value} ({share}%)`.
A missing or non-finite leftover-map axis share omits that share caption and
does not invent leftover-map axis share from `σ_k`. A missing, non-finite, or
negative singular value omits that `σ` badge and keeps a usable leftover-map
comparison axis share caption. Rank-0 unused axes still name `σ 0.00`. Click a
post marker to open that post. Criterion markers are not post buttons.

Leftover-map comparison graphic leftover-map singular values omit independently
of leftover-map graphic-display leftover-map axis singular values, leftover-axis
report badge leftover-map singular values, and leftover-map comparison leftover-axis
singular values. A missing leftover-map axis share omits that leftover-map
comparison graphic leftover-map axis share caption and keeps a usable leftover-map
comparison graphic leftover-map axis `σ` caption, leftover-map graphic leftover-map
axis `σ` caption, leftover-axis `σ` caption, leftover-map comparison leftover-axis
`σ` caption, leftover-map graphic leftover-map axis ticks, leftover-map distance
caption, leftover-map rank caption, leftover expected `E`, leftover observed `Y`,
leftover residual `R`, leftover-map unexplained leftover `U`, leftover-map
reconstruction `R̂`, and leftover-map graphic coverage notes.

This increment does not change leftover-map singular values on leftover-map
graphic-display axes. Those leftover-map graphic axes stay
`leftover-map axis {axis} σ {value} ({share}%)` (ADR 0324). This increment does
not change leftover-map singular values on leftover-axis report badges
(ADR 0325). This increment does not change leftover-map singular values on
leftover-axis report badges on the grouping comparison strip (ADR 0323). This
increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover-map graphic leftover-map axes
name persisted leftover-map singular values when leftoverMapComparePlotAxisBadge
returns a usable leftover-map axis caption even when leftover-map axis share is
omitted; click a leftover pair opens that post. Hidden posts stay hidden. Rank-0
unused axes still name leftover-map comparison graphic leftover-map axis `σ 0.00`.
Leftover-map graphic-display leftover-map singular values (ADR 0324), leftover-axis
report badge leftover-map singular values independently of leftover-map axis share
(ADR 0325), and grouping comparison leftover-axis report badge leftover-map
singular values (ADR 0323) remain.

## Related

Independent of leftover-map singular values on leftover-map graphic-display
axes ([ADR 0324](0324-leftover-map-plot-axis-singular.md)). Independent of
leftover-map singular values on leftover-axis report badges independently of
leftover-map axis share ([ADR 0325](0325-leftover-map-axis-singular-only.md)).
Independent of leftover-map singular values on leftover-axis report badges on
the grouping comparison strip ([ADR 0323](0323-leftover-map-compare-axis-singular.md)).
Independent of leftover-map singular values on leftover-axis report badges
([ADR 0322](0322-leftover-map-axis-singular.md)). Independent of leftover-map
singular values on the grouping comparison leftover-map graphic that still
inline σ and share ([ADR 0321](0321-leftover-map-compare-plot-singular.md)).
Independent of leftover-map graphic leftover-map axis tick leftover-map singular
values independently of leftover-map axis share
([ADR 0327](0327-leftover-map-plot-tick-axis-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)).

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
