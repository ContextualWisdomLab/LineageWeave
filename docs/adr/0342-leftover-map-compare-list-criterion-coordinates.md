# ADR 0342 — Name leftover-map item coordinates on leftover-map comparison leftover pair leftover-map criterion independently of leftover-map comparison leftover pair leftover-map post leftover-map person coordinates

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0343](0343-leftover-map-plot-tick-origin-badge.md)
(leftover-map origin on leftover-map graphic leftover-map axis ticks independently of leftover-map axis share and leftover-map singular values);
[ADR 0354](0354-leftover-map-compare-list-criterion-origin-badge.md)
(leftover-map origin on leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map origin leftover-map person coordinates)

Amends leftover-map coordinates
([ADR 0267](0267-leftover-map-coordinates.md)) and leftover-map coordinates on grouping comparison strip pair rows
([ADR 0302](0302-leftover-map-compare-coordinates.md)). Independent of leftover-map
person coordinates on leftover-map comparison leftover pair leftover-map post independently of leftover-map comparison leftover pair leftover-map criterion leftover-map item coordinates
([ADR 0341](0341-leftover-map-compare-list-post-coordinates.md)). Independent of leftover-map
item coordinates on leftover-map pair leftover-map criterion independently of leftover-map pair leftover-map post leftover-map person coordinates
([ADR 0340](0340-leftover-map-list-criterion-coordinates.md)). Independent of leftover-map
pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates
([ADR 0339](0339-leftover-map-list-post-coordinates.md)). Independent of leftover-map
graphic leftover-map post leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post markers
([ADR 0338](0338-leftover-map-plot-post-coordinates.md)). Independent of leftover-map
comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
([ADR 0337](0337-leftover-map-compare-plot-post-coordinates.md)). Independent of leftover-map
comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)). Independent of leftover-map
graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
([ADR 0335](0335-leftover-map-plot-criterion-coordinates.md)). Independent of leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)). Independent of leftover-map
comparison graphic ([ADR 0304](0304-leftover-map-compare-graphic.md)).

## Context

ADR 0267 already persists two-axis Gabriel person coordinates
`ξ_{1:2}` and item coordinates `ζ_{1:2}` on leftover pair rows so
`R̂ = ξ_{1:2} · ζ_{1:2}` and `d = ‖ξ_{1:2} − ζ_{1:2}‖` stay
auditable. ADR 0302 already names leftover-map coordinates on grouping
comparison leftover-pair buttons through `formatLeftoverMapCoordinates`,
which requires both leftover-map person coordinates `ξ` and leftover-map
item coordinates `ζ`. ADR 0341 already names leftover-map comparison leftover-pair leftover-map
post leftover-map person coordinates
`leftover map comparison leftover pair leftover-map post {title} at ξ {person}`
independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinates. Grouping comparison leftover-pair leftover-map criterion leftover-map
item coordinates still interpolate leftover-map item coordinates only through
`formatLeftoverMapCoordinates`. A missing or non-finite leftover-map comparison leftover-pair leftover-map post leftover-map
person coordinate pair hides leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinates. Rank-0 unused axes still persist leftover-map
item coordinates `(0.00, 0.00)`. A finite negative leftover is shown, never
clamped. Do not invent leftover-map item coordinates from leftover-map person
coordinates `ξ`. Do not invent leftover-map person coordinates `ξ` from leftover-map
item coordinates `ζ`. Leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates stay
`leftover map comparison leftover pair leftover-map post {title} at ξ {person}`
this increment. Leftover-map pair leftover-map criterion leftover-map item coordinates stay
`leftover pair leftover-map criterion {label} at ζ {item}`
this increment. Leftover-map graphic leftover-map criterion markers stay
`leftover-map criterion {label} at ζ {item}`
this increment. Leftover-map comparison graphic leftover-map criterion markers stay
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`
this increment.

This increment names leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinates as leftoverMapCompareListCriterionBadge, matching leftover-map
pair leftover-map criterion leftover-map item coordinates independently of leftover-map
comparison leftover-pair leftover-map post leftover-map person coordinates. Leftover-map comparison leftover-pair leftover-map
criterion leftover-map item coordinates stay
`leftover map comparison leftover pair leftover-map criterion {label} at ζ {item}`
when leftover-map item coordinates are finite, so they stay distinct from leftover-map
pair leftover-map criterion leftover-map item coordinates
`leftover pair leftover-map criterion {label} at ζ {item}`,
leftover-map graphic leftover-map criterion markers
`leftover-map criterion {label} at ζ {item}`,
leftover-map comparison graphic leftover-map criterion markers
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`,
and leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates
`leftover map comparison leftover pair leftover-map post {title} at ξ {person}`.
It does not add columns. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0342** so it does not collide with leftover-map
person coordinates on leftover-map comparison leftover pair leftover-map post independently of leftover-map comparison leftover pair leftover-map criterion leftover-map item coordinates
(0341), leftover-map item coordinates on leftover-map pair leftover-map criterion independently of leftover-map pair leftover-map post leftover-map person coordinates
(0340), leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates
(0339), leftover-map graphic leftover-map post leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post markers
(0338), leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
(0337), leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(0336), leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(0335), leftover-map graphic display (0268), leftover-map coordinates (0267), leftover-map coordinates on grouping comparison strip pair rows
(0302), or the dashboard stacks.

## Decision

On leftover-map comparison leftover-pair leftover-map criterion, caption leftover-map
item coordinates `ζ_{1:2}` when leftoverMapCompareListCriterionBadge
returns a usable leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinate caption.
A missing or non-finite leftover-map item coordinate pair omits that leftover-map
comparison leftover-pair leftover-map criterion leftover-map item coordinate caption. Rank-0 unused axes still name leftover-map
item coordinates `(0.00, 0.00)`. Click a leftover pair or a leftover-map
post marker to open that post. Criterion captions are not post buttons.

Leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates omit
independently of leftover-map comparison leftover-pair leftover-map post leftover-map person
coordinates. This increment does not change leftover-map pair leftover-map
post leftover-map person coordinates, leftover-map pair leftover-map criterion leftover-map item coordinates, leftover-map comparison leftover-pair leftover-map
post leftover-map person coordinates, leftover-map graphic leftover-map
post markers, leftover-map comparison graphic leftover-map
post markers, leftover-map graphic leftover-map criterion markers,
leftover-map comparison graphic leftover-map criterion markers,
leftover-axis ticks, leftover-map graphic leftover-map axis ticks, leftover-map
comparison leftover-axis ticks, or leftover-map comparison graphic leftover-map
axis ticks. This increment does not persist leftover-map inner product, cosine, or length.

Do not add SQL. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, leftover-map comparison leftover-pair leftover-map criterion name persisted
leftover-map item coordinates when leftoverMapCompareListCriterionBadge returns a usable
leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinate caption; click a leftover pair
or a leftover-map post marker opens that post. Hidden posts stay hidden. Rank-0 unused
axes still name leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates
`(0.00, 0.00)`. Leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates stay
`leftover map comparison leftover pair leftover-map post {title} at ξ {person}`. Leftover-map pair leftover-map criterion leftover-map item coordinates stay
`leftover pair leftover-map criterion {label} at ζ {item}`. Leftover-map graphic leftover-map criterion markers stay
`leftover-map criterion {label} at ζ {item}`. Leftover-map comparison graphic leftover-map criterion markers stay
`leftover map comparison graphic leftover-map criterion {label} at ζ {item}`. Leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates independently of leftover-map
comparison leftover-pair leftover-map criterion leftover-map item coordinates (ADR 0341), leftover-map pair leftover-map criterion leftover-map item coordinates independently of leftover-map
pair leftover-map post leftover-map person coordinates (ADR 0340), leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map
pair leftover-map criterion leftover-map item coordinates (ADR 0339), leftover-map graphic leftover-map post leftover-map person coordinates independently of leftover-map
comparison graphic leftover-map post markers (ADR 0338), leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map
criterion leftover-map item coordinates (ADR 0337), leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers (ADR 0336), leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers (ADR 0335), leftover-map graphic display (ADR 0268), leftover-map
coordinates (ADR 0267), and leftover-map coordinates on grouping comparison strip pair rows (ADR 0302) remain.

## Related

Independent of leftover-map person coordinates on leftover-map comparison leftover pair leftover-map post independently of leftover-map
comparison leftover pair leftover-map criterion leftover-map item coordinates
([ADR 0341](0341-leftover-map-compare-list-post-coordinates.md)). Independent of leftover-map item coordinates on leftover-map pair leftover-map criterion independently of leftover-map
pair leftover-map post leftover-map person coordinates
([ADR 0340](0340-leftover-map-list-criterion-coordinates.md)). Independent of leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map
pair leftover-map criterion leftover-map item coordinates
([ADR 0339](0339-leftover-map-list-post-coordinates.md)). Independent of leftover-map graphic leftover-map post leftover-map person coordinates independently of leftover-map
comparison graphic leftover-map post markers
([ADR 0338](0338-leftover-map-plot-post-coordinates.md)). Independent of leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map
criterion leftover-map item coordinates
([ADR 0337](0337-leftover-map-compare-plot-post-coordinates.md)). Independent of leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers
([ADR 0336](0336-leftover-map-compare-plot-criterion-coordinates.md)). Independent of leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map
post ξ markers
([ADR 0335](0335-leftover-map-plot-criterion-coordinates.md)). Independent of leftover-map
graphic display ([ADR 0268](0268-leftover-map-graphic-display.md)). Independent of leftover-map
comparison graphic ([ADR 0304](0304-leftover-map-compare-graphic.md)). Independent of leftover-map
coordinates ([ADR 0267](0267-leftover-map-coordinates.md)). Independent of leftover-map
coordinates on grouping comparison strip pair rows
([ADR 0302](0302-leftover-map-compare-coordinates.md)).

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
