# ADR 0278 — Name leftover observed Y on graphic-display pair segments

**Decision status:** Accepted
**Date:** 2026-08-30

Amends [ADR 0268](0268-leftover-map-graphic-display.md),
[ADR 0049](0049-leftover-pair-report-ui.md), and leftover observed `Y` /
expected `E` ([ADR 0163](0163-leftover-observed-expected.md)). Independent of
leftover residual on pair segments
([ADR 0277](0277-leftover-map-segment-residual.md)), leftover-map unexplained leftover on pair segments
([ADR 0276](0276-leftover-map-segment-unexplained-leftover.md)), leftover-map
cross share on pair segments
([ADR 0275](0275-leftover-map-segment-cross-share.md)), leftover-map
unexplained leftover share on pair segments
([ADR 0274](0274-leftover-map-segment-unexplained-share.md)), leftover-map
explained leftover share on pair segments
([ADR 0273](0273-leftover-map-segment-explained-share.md)), leftover-map
reconstruction on pair segments
([ADR 0272](0272-leftover-map-segment-reconstruction.md)), leftover-map
distance on pair segments ([ADR 0271](0271-leftover-map-segment-distance.md)),
leftover-map coordinate ticks ([ADR 0270](0270-leftover-map-coordinate-ticks.md)),
leftover-map axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)), leftover residual
disclosure ([ADR 0162](0162-leftover-residual-disclosure.md)), leftover-map
explained leftover share persistence
([ADR 0266](0266-leftover-map-explained-share.md)), leftover-map
unexplained leftover share persistence
([ADR 0233](0233-leftover-map-unexplained-share.md)), leftover-map
reconstruction persistence ([ADR 0201](0201-leftover-map-reconstruction.md)),
leftover-map cross share persistence
([ADR 0185](0185-leftover-map-cross-share.md)), leftover-map unexplained leftover
persistence ([ADR 0182](0182-leftover-map-unexplained.md)), and leftover-map axis share
persistence ([ADR 0148](0148-leftover-map-axis-share.md)).

## Context

ADR 0163 already persists observed category `Y` and expected
`E[Y|θ, item]` on leftover pair rows. ADR 0277 already names persisted
leftover residual `R` on the leftover-map graphic-display pair segment.
The segment still has no observed-category label, so a buyer who reads
`Y 2.40` on the pair row cannot match that observed response to the
graphic pair. Hiding `Y` on the segment lets leftover residual `R` be
read as the category that entered the truncated map even after `R` is
named on the segment. When `Y`, `E`, and `R` are finite, `Y − E = R`;
the graphic must name the same persisted `Y` the pair row already shows.

This increment names leftover-map graphic-display pair segments with
persisted leftover observed `Y`. It does not add columns. It does not
recompute `Y` from `R` and `E` or from plotted coordinates. It does not
persist leftover-map inner product, cosine, or length as separate
columns. It does not land Post quality on the leftover criterion.
Leftover-map distance stays two-axis Euclidean. Do not invent a leftover
score. Do not invent a theta. Expected `E` on pair segments stays a later
increment.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected increment uses **0278** so it does not
collide with leftover residual on pair segments (0277), leftover-map
unexplained leftover on pair segments (0276), leftover-map cross share
on pair segments (0275), leftover-map unexplained leftover share
on pair segments (0274), leftover-map explained leftover share on pair
segments (0273), leftover-map reconstruction on pair segments (0272), leftover-map
distance on pair segments (0271), leftover-map coordinate ticks (0270), leftover-map
axis share on the graphic display (0269), leftover-map graphic display (0268), leftover-map
coordinates (0267 / migration 0245), leftover-map explained leftover share persistence
(0266 / migration 0244), leftover-map unexplained leftover share
persistence (0233 / migration 0233), leftover-map reconstruction
persistence (0201 / migration 0206), leftover-map cross share persistence
(0185), leftover-map unexplained leftover persistence (0182), leftover
residual disclosure (0162), leftover observed `Y` / expected `E` persistence
(0163), leftover-map rank, two-axis leftover-map distance persistence, leftover coverage,
leftover-map axis share persistence (0148), leftover interaction-map
persistence, occupational construct catalog search (0265), or the
dashboard stacks.

## Decision

On the leftover-map graphic display, caption each closest or farthest
pair segment with persisted leftover observed `Y` as `Y n.nn`, using
the same observed formatter as the pair-row `Y` badge. A missing or
non-finite `Y` omits that leftover observed caption and keeps the
connecting line and any leftover-map distance, reconstruction,
explained leftover share, unexplained leftover share, leftover-map cross
share, unexplained leftover, or leftover residual caption. Rank-0 origin
cells still name `Y 0.00` when that persisted observed is finite. A
finite negative observed is shown; do not clamp to nonnegative. Do not
invent `Y` from `R` and `E` or from plotted coordinates. Click a post
marker to open that post. Criterion markers are not post buttons. The
grouping comparison strip (ADR 0149) stays on its reduced leftover
payload and does not gain these leftover observed captions.

Do not add SQL. Do not edit shipped migrations. Do not persist inner
product, cosine, or length as separate columns. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, closest and farthest leftover pairs sit above the
member list with the leftover-map graphic display of persisted `ξ`
and `ζ`, leftover-map axes name persisted Gabriel inertia share when
finite, leftover-map axis ticks name the same coordinates shown on
the pair row, pair segments name persisted leftover-map distance `d`,
persisted leftover-map reconstruction `R̂`, persisted leftover-map
explained leftover share `e`, persisted leftover-map unexplained leftover
share `s`, persisted leftover-map cross share `x`, persisted leftover-map
unexplained leftover `U`, persisted leftover residual `R`, and persisted
leftover observed `Y`; click a post marker or a pair button opens that
post. Hidden posts stay hidden. Rank-0 unused axes still plot at the
origin, still name zero leftover-map axis share with a `0` tick, still
name `d 0.00` when that distance is persisted, still name `R̂ 0.00` when
that reconstruction is persisted, still name `R̂²/R² 0.00` when that
explained leftover share is persisted, still name `U²/R² 0.00` when that
unexplained leftover share is persisted, still name `2R̂U/R² 0.00` when
that leftover-map cross share is persisted, still name `U 0.00` when that
unexplained leftover is persisted, still name `R 0.00` when that leftover
residual is persisted, and still name `Y 0.00` when that leftover
observed is persisted. When `Y`, `E`, and `R` are all finite,
`Y − E = R` remains the same identity already persisted by ADR 0162 and
ADR 0163. When `R`, `R̂`, and `U` are all finite, `U + R̂ = R` remains
the same identity already persisted by ADR 0162, ADR 0182, and ADR 0201.
When `R`, `R̂`, `U`, `x`, `s`, and `e` are all finite, `e + s + x = 1`
remains the same identity already persisted by ADR 0185, ADR 0233, and
ADR 0266.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover expected `E`
on pair segments, leftover-map complete-case coverage, leftover-map
axis share persistence, leftover pairs on the grouping comparison strip,
two-axis leftover-map distance persistence, leftover-map rank,
leftover-map inner product, leftover-map cosine, leftover-map length,
leftover-map reconstruction persistence, leftover-map unexplained leftover
persistence, leftover-map cross share persistence, leftover-map unexplained
leftover share persistence, leftover-map explained leftover share
persistence, leftover-map coordinate persistence, leftover-map graphic
display, leftover-map axis share on the graphic display, leftover-map
coordinate ticks, leftover-map distance on pair segments, leftover-map
reconstruction on pair segments, leftover-map explained leftover share
on pair segments, leftover-map unexplained leftover share on pair
segments, leftover-map cross share on pair segments, leftover-map
unexplained leftover on pair segments, and leftover residual on pair
segments.

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
`R̂ = ξ_{1:2} · ζ_{1:2}`. Leftover residual is the signed remainder
`R = Y − E[Y|θ, item]` after IRT main effects. Observed `Y` is the
category that entered that residual.)
