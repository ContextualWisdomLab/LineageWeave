# ADR 0320 — Name leftover-map coordinate ticks on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0321](0321-leftover-map-compare-plot-singular.md)
(leftover-map singular values on the grouping comparison leftover-map graphic)

Amends leftover-map coordinate ticks on graphic-display axes
([ADR 0270](0270-leftover-map-coordinate-ticks.md)), leftover-map distance
on the grouping comparison leftover-map graphic
([ADR 0319](0319-leftover-map-compare-plot-distance.md)), leftover-map rank
on the grouping comparison leftover-map graphic
([ADR 0318](0318-leftover-map-compare-plot-rank.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map coordinates
([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map
singular values on leftover-axis report badges.

## Context

ADR 0267 already persists two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}` so `R̂ = ξ_{1:2} · ζ_{1:2}`
and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay auditable. ADR 0270 already ticks
period-report leftover-map axes at the origin and at each unique finite
persisted `ξ` / `ζ` projection under accessible name
`leftover-map axis {axis} tick {value}`. ADR 0319 already captions
leftover-map distance on the grouping comparison leftover-map graphic.
The comparison graphic still reuses `leftover-map axis {axis} tick {value}`,
so a buyer who compares leftover pairs can treat the period-report graphic
tick as the comparison graphic leftover-map coordinate even after the strip
names `ξ` / `ζ`. Hiding a distinct comparison-graphic leftover-map coordinate
tick lets leftover-map distance `d`, leftover-map rank, or leftover-map axis
share be read as leftover-map location without a next action. When
coordinates, reconstruction, and distance are finite, `R̂ = ξ · ζ` and
`d = ‖ξ − ζ‖`; the comparison graphic must name the same persisted
coordinates the pair row already shows. A finite negative leftover is shown,
never clamped.

This increment captions leftover-map coordinate ticks on the grouping
comparison leftover-map graphic from already-named leftover-map coordinates.
Comparison copy uses the accessible name
`leftover map comparison graphic leftover-map axis {axis} tick {value}` so it
stays distinct from `leftover-map axis {axis} tick {value}` on the
period-report graphic and from comparison axis-share copy
`leftover map comparison axis {axis} ({share}%)`. It does not add columns.
It does not invent evenly spaced ticks that no persisted coordinate occupies.
Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0320** so it does not collide with leftover-map
distance on the grouping comparison leftover-map graphic (0319), leftover-map
rank on that graphic (0318), leftover-map coordinate ticks on pair-segment
graphic display (0270), leftover-map coordinates (0267), leftover-map graphic
display (0268), leftover-map axis share on that comparison graphic (0305), or
the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, tick leftover-map axis 1 and
leftover-map axis 2 at the origin and at each unique finite persisted `ξ` /
`ζ` coordinate projected onto that axis. Use the distinct accessible name
`leftover map comparison graphic leftover-map axis {axis} tick {value}` so the
graphic tick is not the period-report graphic tick
(`leftover-map axis {axis} tick {value}`) and is not comparison axis-share copy
(`leftover map comparison axis {axis} ({share}%)`). Tick labels use the same
signed leftover-map coordinate formatter as the pair-row badge. The origin is
always named `0` because it is the rank-0 unused-axis location, not a leftover
score. Duplicate coordinates share one tick. A rank-0 origin cell names only
`0`; the unit drawing window used to keep that origin visible is drawing scale
and must not sprout `−1` or `+1` ticks. Do not invent evenly spaced ticks that
no persisted coordinate occupies. Click a post marker to open that post.
Criterion markers are not post buttons.

Leftover-map comparison graphic leftover-map axis ticks omit independently of
leftover-map distance captions. A missing coordinate omits that leftover-map
comparison graphic leftover-map axis tick and keeps a usable leftover-map
distance caption, leftover-map rank caption, leftover expected `E`, leftover
observed `Y`, leftover residual `R`, leftover-map unexplained leftover `U`,
leftover-map reconstruction `R̂`, leftover-map comparison graphic coverage
notes, plus the pair-row leftover-map coordinate badge.

This increment does not caption leftover-map singular values on the comparison
graphic with a distinct comparison-graphic name. Those leftover singular values
already persist on leftover-map axes through ADR 0148.

Do not add SQL migrations. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover-map
coordinate ticks on that graphic at the origin and at each unique finite
projection. Rank-0 unused axes still plot at the origin and still name
leftover-map comparison graphic leftover-map axis tick `0.00`. Click a post
marker or a pair button opens that post. When coordinates, reconstruction,
and distance are finite, `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖`.

## Related

Independent of leftover-map singular values on leftover-axis report badges.
Independent of leftover-map comparison graphic leftover-map axis tick leftover-map
singular values independently of leftover-map axis share
([ADR 0328](0328-leftover-map-compare-plot-tick-axis-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
