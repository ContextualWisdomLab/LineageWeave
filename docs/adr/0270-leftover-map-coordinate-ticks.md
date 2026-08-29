# ADR 0270 — Name leftover-map coordinates as graphic-display axis ticks

**Decision status:** Accepted
**Date:** 2026-08-29

Amends [ADR 0268](0268-leftover-map-graphic-display.md) and
[ADR 0267](0267-leftover-map-coordinates.md). Independent of leftover-map
axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map
explained leftover share ([ADR 0266](0266-leftover-map-explained-share.md)),
leftover-map unexplained leftover share
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map
reconstruction ([ADR 0201](0201-leftover-map-reconstruction.md)), and
leftover-map axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).
Independent of leftover-map distance on pair segments
([ADR 0271](0271-leftover-map-segment-distance.md)).

## Context

ADR 0267 already persists two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}` on leftover pair rows so
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay
auditable. ADR 0268 already draws those positions. ADR 0269 captions
leftover-map axes with persisted Gabriel inertia share. The plot still
has no coordinate scale, so a buyer who reads `ξ (x, y) ζ (x, y)` on
the pair row cannot match those numbers to leftover-map location.
Hiding ticks lets leftover residual `R`, leftover-map distance `d`, or
reconstruction `R̂` be read as leftover-map location even after the
coordinates themselves are named and plotted.

This increment names leftover-map graphic-display axes with persisted
coordinate ticks. It does not add columns. It does not persist
leftover-map inner product, cosine, or length. It does not land Post
quality on the leftover criterion. Leftover-map distance stays
two-axis Euclidean. Do not invent a leftover score. Do not invent a
theta.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected increment uses **0270** so it does not
collide with leftover-map axis share on the graphic display (0269),
leftover-map graphic display (0268), leftover-map coordinates (0267 /
migration 0245), leftover-map explained leftover share (0266 /
migration 0244), leftover-map unexplained leftover share (0233 /
migration 0233), leftover-map reconstruction (0201 / migration 0206),
leftover-map cross share (0185), leftover residual disclosure,
leftover observed `Y` / expected `E`, leftover-map rank, two-axis
leftover-map distance, leftover coverage, leftover-map axis share
persistence (0148), leftover interaction-map persistence, occupational
construct catalog search (0265), or the dashboard stacks.

## Decision

On the leftover-map graphic display, tick leftover-map axis 1 and
leftover-map axis 2 at the origin and at each unique finite persisted
`ξ` / `ζ` coordinate projected onto that axis. Tick labels use the
same signed leftover-map coordinate formatter as the pair-row badge.
The origin is always named `0` because it is the rank-0 unused-axis
location, not a leftover score. Duplicate coordinates share one tick.
A rank-0 origin cell names only `0`; the unit drawing window used to
keep that origin visible is drawing scale and must not sprout `−1` or
`+1` ticks. Do not invent evenly spaced ticks that no persisted
coordinate occupies. Click a post marker to open that post. Criterion
markers are not post buttons. The grouping comparison strip
(ADR 0149) stays on its reduced leftover payload and does not gain
these ticks.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a
leftover score. Do not invent a theta.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the
member list with the leftover-map graphic display of persisted `ξ`
and `ζ`, leftover-map axes name persisted Gabriel inertia share when
finite, and leftover-map axis ticks name the same coordinates shown
on the pair row; click a post marker or a pair button opens that
post. Hidden posts stay hidden. Rank-0 unused axes still plot at the
origin and still name zero leftover-map axis share with a `0` tick.
When coordinates, reconstruction, and distance are all finite,
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` remain the
same identities already persisted by ADR 0267.

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
graphic display, leftover-map axis share on the graphic display, and
leftover-map distance on pair segments.

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
