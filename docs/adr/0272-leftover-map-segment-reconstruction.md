# ADR 0272 — Name leftover-map reconstruction on graphic-display pair segments

**Decision status:** Accepted
**Date:** 2026-08-29

**Amended by:** [ADR 0273](0273-leftover-map-segment-explained-share.md)
(leftover-map explained leftover share on pair segments)

Amends [ADR 0268](0268-leftover-map-graphic-display.md) and
[ADR 0049](0049-leftover-pair-report-ui.md). Independent of leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)),
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover-map
explained leftover share ([ADR 0266](0266-leftover-map-explained-share.md)),
leftover-map unexplained leftover share
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
and leftover-map axis share persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0201 already persists leftover-map reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}` on leftover pair rows. ADR 0267 already
persists the two-axis coordinates so that identity stays auditable
next to leftover-map distance `d`. ADR 0268 already draws the
connecting segment. ADR 0271 already names persisted `d` on that
segment. The segment still has no leftover-map reconstruction label,
so a buyer who reads `R̂ +0.35` on the pair row cannot match that
inner product to the graphic pair. Hiding `R̂` on the segment lets
leftover residual `R`, leftover-map distance `d`, or leftover-map
location be read as leftover-map reconstruction even after the
coordinates, ticks, and distance are named.

This increment names leftover-map graphic-display pair segments with
persisted leftover-map reconstruction. It does not add columns. It
does not recompute `R̂` from plotted coordinates. It does not persist
leftover-map inner product, cosine, or length as separate columns
(`R̂` already is the two-axis inner product). It does not land Post
quality on the leftover criterion. Leftover-map distance stays
two-axis Euclidean. Do not invent a leftover score. Do not invent a
theta.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected increment uses **0272** so it does not
collide with leftover-map distance on pair segments (0271),
leftover-map coordinate ticks (0270), leftover-map axis share on the
graphic display (0269), leftover-map graphic display (0268),
leftover-map coordinates (0267 / migration 0245), leftover-map
explained leftover share (0266 / migration 0244), leftover-map
unexplained leftover share (0233 / migration 0233), leftover-map
reconstruction persistence (0201 / migration 0206), leftover-map
cross share (0185), leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map rank, two-axis leftover-map distance
persistence, leftover coverage, leftover-map axis share persistence
(0148), leftover interaction-map persistence, occupational construct
catalog search (0265), or the dashboard stacks.

## Decision

On the leftover-map graphic display, caption each closest or farthest
pair segment with the same persisted leftover-map reconstruction
formatter as the pair-row `R̂` badge. A missing or non-finite `R̂`
omits that reconstruction caption and keeps the connecting line and
any leftover-map distance caption. Rank-0 origin cells still name
`R̂ 0.00` when that persisted reconstruction is finite. Do not invent
`R̂` from plotted coordinates or from a pixel inner product. Click a
post marker to open that post. Criterion markers are not post
buttons. The grouping comparison strip (ADR 0149) stays on its
reduced leftover payload and does not gain these reconstruction
captions.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a
leftover score. Do not invent a theta.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the
member list with the leftover-map graphic display of persisted `ξ`
and `ζ`, leftover-map axes name persisted Gabriel inertia share when
finite, leftover-map axis ticks name the same coordinates shown on
the pair row, pair segments name persisted leftover-map distance `d`
and persisted leftover-map reconstruction `R̂`, and pair segments name
persisted leftover-map explained leftover share `e` (ADR 0273); click a post marker
or a pair button opens that post. Hidden posts stay hidden. Rank-0
unused axes still plot at the origin, still name zero leftover-map
axis share with a `0` tick, still name `d 0.00` when that distance is
persisted, and still name `R̂ 0.00` when that reconstruction is
persisted. When coordinates, reconstruction, and distance are all
finite, `R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖`
remain the same identities already persisted by ADR 0267.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share persistence, leftover pairs on the grouping comparison
strip, two-axis leftover-map distance persistence, leftover-map rank,
leftover-map inner product, leftover-map cosine, leftover-map length,
leftover-map reconstruction persistence, leftover-map unexplained
leftover, leftover-map cross share, leftover-map unexplained leftover
share, leftover-map explained leftover share, leftover-map coordinate
persistence, leftover-map graphic display, leftover-map axis share on
the graphic display, leftover-map coordinate ticks, and leftover-map
distance on pair segments.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
(LSIRM interaction `−γ‖ξ_j − ζ_i‖` after main effects
`α_j − β_i`; typically `p = 2` for the interaction map. Gabriel
reconstruction of the leftover cell is the two-axis inner product
`R̂ = ξ_{1:2} · ζ_{1:2}`.)
