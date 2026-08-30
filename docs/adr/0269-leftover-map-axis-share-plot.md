# ADR 0269 — Name leftover-map axis share on the graphic display

**Decision status:** Accepted
**Date:** 2026-08-28

**Amended by:** [ADR 0305](0305-leftover-map-compare-plot-axis-share.md)
(leftover-map axis share on the grouping comparison leftover-map graphic)

Amends [ADR 0148](0148-leftover-map-axis-share.md) and
[ADR 0268](0268-leftover-map-graphic-display.md). Independent of leftover-map
explained leftover share ([ADR 0266](0266-leftover-map-explained-share.md)),
leftover-map unexplained leftover share ([ADR 0233](0233-leftover-map-unexplained-share.md)),
leftover-map reconstruction ([ADR 0201](0201-leftover-map-reconstruction.md)),
and leftover-map coordinates ([ADR 0267](0267-leftover-map-coordinates.md)).
Independent of leftover-map coordinate ticks
([ADR 0270](0270-leftover-map-coordinate-ticks.md)).

## Context

ADR 0148 already persists leftover-map axis share
`σ_k² / Σ_j σ_j²` on each period report as two leftover-map axes.
ADR 0268 already draws the leftover-map graphic display of persisted
`ξ_{1:2}` and `ζ_{1:2}`. Those plot axes still read only
"leftover-map axis 1" and "leftover-map axis 2", so Gabriel inertia
lives on report badges and not on the graphic display Gabriel (1971)
captioned. Hiding share on the axes lets leftover residual `R`,
leftover-map distance `d`, or reconstruction `R̂` be read as leftover-map
structure even after axis share itself is persisted.

This increment captions the leftover-map graphic display with already
persisted leftover-map axis share. It does not add columns. It does not
persist leftover-map inner product, cosine, or length. It does not land
Post quality on the leftover criterion. Leftover-map distance stays
two-axis Euclidean. Do not invent a leftover score. Do not invent a
theta.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected increment uses **0269** so it does not
collide with leftover-map graphic display (0268), leftover-map
coordinates (0267 / migration 0245), leftover-map explained leftover
share (0266 / migration 0244), leftover-map unexplained leftover share
(0233 / migration 0233), leftover-map reconstruction (0201 / migration
0206), leftover-map cross share (0185), leftover residual disclosure,
leftover observed `Y` / expected `E`, leftover-map rank, two-axis
leftover-map distance, leftover coverage, leftover-map axis share
persistence (0148), leftover interaction-map persistence, occupational
construct catalog search (0265), or the dashboard stacks.

## Decision

On the leftover-map graphic display, caption leftover-map axis `k`
with persisted leftover-map axis share when that share is finite,
including rank-0 zero-share axes. The caption is
`leftover-map axis {k} ({share}%)` from `σ_k² / Σ_j σ_j²`. A missing
or non-finite share omits that axis badge and keeps the existing
leftover-map axis text. Axis 1 and axis 2 stay independently named:
one missing share does not hide the other. Click a post marker to
open that post. Criterion markers are not post buttons. The grouping
comparison strip later captions leftover-map axis share on its leftover-map
graphic from already-named leftover-map axes (ADR 0305).

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a
leftover score. Do not invent a theta.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the
member list with the leftover-map graphic display of persisted `ξ`
and `ζ`, and each leftover-map axis names its persisted Gabriel
inertia share; click a post marker or a pair button opens that post.
Hidden posts stay hidden. Rank-0 unused axes still plot at the origin
and still name zero leftover-map axis share. Report-level leftover-axis
badges (ADR 0148) remain.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share persistence, leftover pairs on the grouping comparison
strip, two-axis leftover-map distance, leftover-map rank, leftover-map
inner product, leftover-map cosine, leftover-map length, leftover-map
reconstruction, leftover-map unexplained leftover, leftover-map cross
share, leftover-map unexplained leftover share, leftover-map explained
leftover share, leftover-map coordinate persistence, leftover-map
graphic display, and leftover-map coordinate ticks.

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
