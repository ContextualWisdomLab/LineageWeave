# ADR 0267 — Name leftover-map coordinates on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-28

**Amended by:** [ADR 0268](0268-leftover-map-graphic-display.md)
(leftover-map graphic display);
[ADR 0270](0270-leftover-map-coordinate-ticks.md)
(leftover-map coordinate ticks)

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0049](0049-leftover-pair-report-ui.md), and
[ADR 0201](0201-leftover-map-reconstruction.md). Builds on ADR 0201's
leftover-map reconstruction. Coordinate publication is independent of the
explained leftover share ([ADR 0266](0266-leftover-map-explained-share.md)),
leftover-map unexplained leftover share
([ADR 0233](0233-leftover-map-unexplained-share.md)), and leftover-map
axis share on the graphic display
([ADR 0269](0269-leftover-map-axis-share-plot.md)).

## Context

ADR 0201 already persists two-axis Gabriel reconstruction
`R̂ = ξ_{1:2} · ζ_{1:2}`. ADR 0119 already persists leftover-map
distance `d = ‖ξ_{1:2} − ζ_{1:2}‖`. Those terms are computed from
person and item coordinates that `_pad_map_axes` already produces,
then discards after `R̂` and `d`. A buyer who reads `R̂` next to `d`
cannot check either identity without the two leftover-map positions
the truncated map actually uses. Hiding `ξ` and `ζ` lets leftover
residual `R`, leftover-map distance `d`, or reconstruction `R̂` be
read as leftover-map location.

This increment persists leftover-map coordinates `ξ_{1:2}` and
`ζ_{1:2}`. It does not name leftover-map inner product, cosine, or
length as separate columns (`R̂` and `d` already are those two-axis
facts), and does not land Post quality on the leftover criterion.
Leftover-map distance stays two-axis Euclidean. Reconstruction `R̂`
and unexplained leftover `U` remain the same internal two-axis terms
already used for `e`, `s`, and `x`, so
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay
auditable from persisted coordinates.

The dashboard stack already used neighbouring leftover facts under
other numbers. This protected-main increment uses **0267**
(migration **0245**) so it does not collide with leftover-map
explained leftover share (0266 / migration 0244), leftover-map
unexplained leftover share (0233 / migration 0233), leftover-map
reconstruction (0201 / migration 0206), leftover-map cross share
(0185), leftover residual disclosure, leftover observed `Y` /
expected `E`, leftover-map rank, two-axis leftover-map distance,
leftover coverage, leftover-map axis share (0148), leftover
interaction-map persistence, occupational construct catalog search
(0265), I/O occupational taxonomy (ADR 0245), or source-post voice
history (migration 0243).

## Decision

Each leftover pair names `leftover_map_person_axis_1`,
`leftover_map_person_axis_2`, `leftover_map_item_axis_1`, and
`leftover_map_item_axis_2` — two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}`. Unused axes pad with
zero. Hidden SVD axes after the second are dropped. Migration
`0245` is the single source of the columns on every install path,
fresh or existing -- shipped migrations (`0001` / `0012`) are never
edited after the fact. The columns are nullable so older leftover
rows keep distance, residual, unexplained leftover, reconstruction,
cross share, unexplained leftover share, and explained leftover
share without fabricating a location. Fallback pairs that have no
complete-case leftover map omit the four values rather than
inventing them. A rank-0 origin cell stores `0.0` on every unused
axis, not a missing value. A non-finite coordinate omits all four
rather than inventing a leftover score. Signed coordinates are
stored, never clamped. Do not add an upper-bound or nonnegative
CHECK. Persist the four columns together so a buyer never reads a
partial location.

The pair button shows `ξ (x, y) ζ (x, y)` next to leftover-map
distance `d` when all four values are finite. Next action: leftover
map places this post at `ξ` and the criterion at `ζ` after IRT main
effects; open this post to read the named criterion. A missing or
non-finite coordinate omits the badge and keeps the existing
explained-share / unexplained-share / cross-share / reconstruction
/ unexplained-leftover next action. Do not invent a leftover score.
Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_person_axis_1`, `leftover_map_person_axis_2`,
`leftover_map_item_axis_1`, and `leftover_map_item_axis_2`. After
`make seed`, closest and farthest leftover pairs sit above the
member list with named `ξ` and `ζ` next to `d`; click opens that
post. Hidden posts stay hidden. When coordinates, reconstruction,
and distance are all finite,
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖`.

The grouping comparison strip (ADR 0149) stays on its reduced leftover
payload (distance, residual, reconstruction). Leftover-map coordinates
are a period-report pair fact, not a comparison-strip badge.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover-map rank, leftover-map inner product,
leftover-map cosine, leftover-map length, leftover-map reconstruction,
leftover-map unexplained leftover, leftover-map cross share,
leftover-map unexplained leftover share, leftover-map explained
leftover share, leftover-map graphic display, leftover-map axis
share on the graphic display, and leftover-map coordinate ticks.

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
