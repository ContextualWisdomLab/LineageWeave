# ADR 0335 — Name leftover-map item coordinates on leftover-map graphic leftover-map criterion markers independently of leftover-map post ξ markers

**Decision status:** Accepted
**Date:** 2026-08-31

Amends leftover-map graphic display of persisted coordinates
([ADR 0268](0268-leftover-map-graphic-display.md)), leftover-map
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
criterion markers at persisted `ζ`. Post markers already name
`Open leftover-map post {title} at ξ {person}`. Those leftover-map
graphic leftover-map criterion markers still read only
`Criterion ζ {label}`, so a buyer who reads leftover-map graphic leftover-map
criterion markers can treat leftover-map location as leftover-map post
`ξ` without a next action on leftover-map item coordinates. A missing or
non-finite leftover-map item coordinate pair is not a leftover score and
must omit independently of leftover-map post `ξ` markers. Rank-0 unused
axes still persist leftover-map item coordinates `(0.00, 0.00)`. A finite
negative leftover is shown, never clamped. Do not invent leftover-map
item coordinates from leftover-map post `ξ`. Do not invent leftover-map
post `ξ` from leftover-map item coordinates. Leftover-map comparison graphic leftover-map
criterion markers stay `Criterion ζ {label}` this increment.

This increment names leftover-map graphic leftover-map criterion markers leftover-map
item coordinates as leftoverMapPlotCriterionBadge, matching leftover-map
graphic leftover-map post `ξ` markers. Leftover-map graphic leftover-map
criterion markers stay
`leftover-map criterion {label} at ζ {item}`
when leftover-map item coordinates are finite, so they stay distinct from leftover-map
post markers `Open leftover-map post {title} at ξ {person}` and from leftover-map
comparison graphic leftover-map criterion markers `Criterion ζ {label}`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0335** so it does not collide with leftover-axis
tick leftover-map axis share independently of leftover-map singular values
(0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(0331), leftover-map graphic display (0268), leftover-map coordinates (0267),
or the dashboard stacks.

## Decision

On leftover-map graphic leftover-map criterion markers, caption leftover-map
item coordinates `ζ_{1:2}` when leftoverMapPlotCriterionBadge
returns a usable leftover-map criterion leftover-map item coordinate caption.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map
criterion leftover-map item coordinate caption and keeps
`Criterion ζ {label}`. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Click a leftover pair or a leftover-map
post marker to open that post. Criterion markers are not post buttons.

Leftover-map graphic leftover-map criterion leftover-map item coordinates omit
independently of leftover-map post `ξ` markers. This increment does not
change leftover-map comparison graphic leftover-map criterion markers,
leftover-axis ticks, leftover-map graphic leftover-map axis ticks, leftover-map
comparison leftover-axis ticks, or leftover-map comparison graphic leftover-map
axis ticks. This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map graphic leftover-map criterion markers name persisted
leftover-map item coordinates when leftoverMapPlotCriterionBadge returns a usable
leftover-map criterion leftover-map item coordinate caption; click a leftover pair
or a leftover-map post marker opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map graphic leftover-map criterion leftover-map item coordinates
`(0.00, 0.00)`. Leftover-map comparison graphic leftover-map criterion markers stay
`Criterion ζ {label}`. Leftover-axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0334), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0333), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0332), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map
singular values (ADR 0331), leftover-map graphic display (ADR 0268), and leftover-map
coordinates (ADR 0267) remain.

## Related

Independent of leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0334](0334-leftover-map-axis-tick-share-badge.md)). Independent of leftover-map
comparison leftover-axis tick leftover-map axis share independently of leftover-map
singular values
([ADR 0333](0333-leftover-map-compare-axis-tick-share-badge.md)). Independent of leftover-map
graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0332](0332-leftover-map-plot-tick-share-badge.md)). Independent of leftover-map
comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
([ADR 0331](0331-leftover-map-compare-plot-tick-share-badge.md)). Independent of leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)). Independent of leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)).

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
