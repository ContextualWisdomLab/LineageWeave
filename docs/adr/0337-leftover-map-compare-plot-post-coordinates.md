# ADR 0337 — Name leftover-map person coordinates on leftover-map comparison graphic leftover-map post markers independently of leftover-map criterion leftover-map item coordinates

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0338](0338-leftover-map-plot-post-coordinates.md)
(leftover-map person coordinates on leftover-map graphic leftover-map post markers);
[ADR 0349](0349-leftover-map-compare-plot-post-origin-badge.md)
(leftover-map origin on leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates)

Amends leftover-map graphic display of persisted coordinates on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)), leftover-map comparison graphic leftover-map criterion leftover-map item coordinates
([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)), leftover-map
graphic leftover-map criterion leftover-map item coordinates
([ADR 0335](0335-leftover-map-plot-criterion-coordinates.md)), leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-axis
tick leftover-map axis share independently of leftover-map singular values
([ADR 0334](0334-leftover-map-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values ([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)).

## Context

ADR 0267 already persists two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}` on leftover pair rows so
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay
auditable. ADR 0268 already draws leftover-map graphic leftover-map
post markers at persisted `ξ` and leftover-map graphic leftover-map
criterion markers at persisted `ζ`. ADR 0304 reuses that graphic on the grouping
comparison strip. ADR 0335 already names leftover-map graphic leftover-map
criterion markers `leftover-map criterion {label} at ζ {item}` independently of leftover-map
post `ξ` markers. ADR 0336 already names leftover-map comparison graphic leftover-map
criterion markers `leftover map comparison graphic leftover-map criterion {label} at ζ {item}`
independently of leftover-map post `ξ` markers. Those leftover-map comparison graphic leftover-map
post markers still read `Open leftover-map post {title} at ξ {person}`, so a buyer who
reads leftover-map comparison graphic leftover-map post markers can treat leftover-map location as leftover-map graphic leftover-map
post `ξ` without a next action on leftover-map comparison graphic leftover-map post leftover-map person coordinates. A missing or
non-finite leftover-map person coordinate pair is not a leftover score and
must omit independently of leftover-map criterion leftover-map item coordinates. Rank-0 unused
axes still persist leftover-map person coordinates `(0.00, 0.00)`. A finite
negative leftover is shown, never clamped. Do not invent leftover-map
person coordinates from leftover-map item coordinates `ζ`. Do not invent leftover-map
item coordinates `ζ` from leftover-map person coordinates `ξ`. Leftover-map graphic leftover-map
post markers stay `Open leftover-map post {title} at ξ {person}` this increment.

This increment names leftover-map comparison graphic leftover-map post markers leftover-map
person coordinates as leftoverMapComparePlotPostBadge, matching leftover-map
comparison graphic leftover-map criterion leftover-map item coordinates. Leftover-map comparison graphic leftover-map
post markers stay
`Open leftover map comparison graphic leftover-map post {title} at ξ {person}`
when leftover-map person coordinates are finite, so they stay distinct from leftover-map
graphic leftover-map post markers `Open leftover-map post {title} at ξ {person}` and from leftover-map
comparison graphic leftover-map criterion markers `leftover map comparison graphic leftover-map criterion {label} at ζ {item}`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0337** so it does not collide with leftover-map
comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(0336), leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(0335), leftover-axis tick leftover-map axis share independently of leftover-map singular values
(0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0331), leftover-map graphic display on the grouping comparison strip (0304), leftover-map graphic display (0268), leftover-map coordinates (0267),
or the dashboard stacks.

## Decision

On leftover-map comparison graphic leftover-map post markers, caption leftover-map
person coordinates `ξ_{1:2}` when leftoverMapComparePlotPostBadge
returns a usable leftover-map comparison graphic leftover-map post leftover-map person coordinate caption.
A missing or non-finite leftover-map person coordinate pair omits that leftover-map
comparison graphic leftover-map post leftover-map person coordinate caption and keeps
`Open leftover-map post {title}`. Rank-0 unused axes still name leftover-map
person coordinates `(0.00, 0.00)`. Click a leftover pair or a leftover-map
post marker to open that post. Criterion markers are not post buttons.

Leftover-map comparison graphic leftover-map post leftover-map person coordinates omit
independently of leftover-map criterion leftover-map item coordinates. This increment does not
change leftover-map graphic leftover-map post markers,
leftover-map graphic leftover-map criterion markers,
leftover-axis ticks, leftover-map graphic leftover-map axis ticks, leftover-map
comparison leftover-axis ticks, or leftover-map comparison graphic leftover-map
axis ticks. This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison graphic leftover-map post markers name persisted
leftover-map person coordinates when leftoverMapComparePlotPostBadge returns a usable
leftover-map comparison graphic leftover-map post leftover-map person coordinate caption; click a leftover pair
or a leftover-map post marker opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map comparison graphic leftover-map post leftover-map person coordinates
`(0.00, 0.00)`. Leftover-map graphic leftover-map post markers stay
`Open leftover-map post {title} at ξ {person}`. Leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers (ADR 0336), leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers (ADR 0335), leftover-axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0331), leftover-map graphic display on the grouping comparison strip (ADR 0304), leftover-map graphic display (ADR 0268), and leftover-map
coordinates (ADR 0267) remain.

## Related

Independent of leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers
([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)). Independent of leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers
([ADR 0335](0335-leftover-map-plot-criterion-coordinates.md)). Independent of leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0334](0334-leftover-map-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)). Independent of leftover-map
graphic display on the grouping comparison strip ([ADR 0304](0304-leftover-map-compare-graphic.md)). Independent of leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)). Independent of leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates
([ADR 0339](0339-leftover-map-list-post-coordinates.md)).

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
