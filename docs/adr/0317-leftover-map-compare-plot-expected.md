# ADR 0317 — Name leftover expected on the grouping comparison leftover-map graphic

**Decision status:** Accepted
**Date:** 2026-08-31

**Amended by:** [ADR 0318](0318-leftover-map-compare-plot-rank.md)
(leftover-map rank on the grouping comparison leftover-map graphic)

Amends leftover expected on graphic-display pair segments
([ADR 0279](0279-leftover-map-segment-expected.md)), leftover expected
on grouping comparison strip pair rows
([ADR 0300](0300-leftover-map-compare-expected.md)), leftover observed
on the grouping comparison leftover-map graphic
([ADR 0316](0316-leftover-map-compare-plot-observed.md)), leftover residual
on the grouping comparison leftover-map graphic
([ADR 0315](0315-leftover-map-compare-plot-residual.md)), leftover observed `Y` /
expected `E` ([ADR 0163](0163-leftover-observed-expected.md)), leftover-map graphic
display on the grouping comparison strip
([ADR 0304](0304-leftover-map-compare-graphic.md)). Independent of leftover-map
rank on the grouping comparison leftover-map graphic.

## Context

ADR 0163 already persists leftover expected `E[Y|θ, item]`. ADR 0279 already
captions period-report leftover-map pair segments with
`leftover expected {label}` when that leftover expected is finite. ADR 0300
already captions grouping comparison leftover-pair buttons with that same
persisted leftover expected under accessible name
`Leftover map comparison expected`. ADR 0316 already captions leftover
observed on the grouping comparison leftover-map graphic. The comparison
graphic still reuses `leftover expected {label}`, so a buyer who compares leftover
pairs can treat the period-report graphic caption as the comparison graphic
leftover expected even after the strip names `E`. Hiding a distinct
comparison-graphic leftover expected caption lets leftover observed `Y` or leftover residual
`R` be read as leftover expected without a next action. When `Y`, `E`, and `R` are
finite, `Y − E = R`; the comparison graphic must name the same
persisted `E` the pair row and strip already show. A finite negative leftover is
shown, never clamped.

This increment captions leftover expected on the grouping
comparison leftover-map graphic from already-named leftover expected
through formatLeftoverMapExpected. Comparison copy uses the accessible
name `leftover map comparison graphic leftover expected {label}` so it stays
distinct from `leftover expected {label}` on the
period-report graphic and from strip `Leftover map comparison expected`.
It does not add columns. It does not recompute leftover expected
from `Y` and `R`. Do not invent a leftover score. Do not invent a theta.

This protected increment uses **0317** so it does not collide with leftover
observed on the grouping comparison leftover-map graphic (0316), leftover residual
on that graphic (0315), leftover expected on grouping comparison strip pair rows
(0300), leftover expected on pair segments (0279), leftover observed / expected
disclosure (0163), leftover-map graphic display (0268), or the dashboard stacks.

## Decision

On the grouping comparison leftover-map graphic, caption each pair segment
with persisted leftover expected when formatLeftoverMapExpected
returns a usable badge, next to leftover observed `Y`. Use the
distinct accessible name `leftover map comparison graphic leftover expected {label}`
so the graphic caption is not the strip badge (`Leftover map comparison expected`)
and is not the period-report graphic caption (`leftover expected {label}`).
A missing or non-finite `E` omits that leftover-map comparison graphic
leftover expected caption and keeps leftover observed `Y` when
formatLeftoverMapObserved returns a usable badge, leftover residual `R` when
formatLeftoverMapResidual returns a usable badge, leftover-map unexplained leftover `U`, leftover-map cross share `x`, leftover-map unexplained leftover share `s`, leftover-map explained leftover share `e`, leftover-map reconstruction `R̂`, leftover-map distance `d`, leftover-map comparison graphic coverage notes, leftover-map rank, leftover observed `Y`, plus the strip leftover expected badge.
Rank-0 origin cells still name `E 0.00` when that persisted leftover
expected is finite. A finite negative leftover is shown, never clamped. Do not invent `E` from
`Y` and `R`. Click a post marker to open that post.

Leftover expected omits independently of leftover observed captions and leftover residual captions.
A missing leftover expected omits leftover-map comparison graphic leftover expected and keeps
a usable leftover observed caption and a usable leftover residual caption.

This increment does not caption leftover-map distance on the comparison graphic
with a distinct comparison-graphic name. Leftover-map rank on that comparison
graphic is [ADR 0318](0318-leftover-map-compare-plot-rank.md). That leftover-map rank already sits on
the strip through ADR 0301.

Do not add SQL migrations. Do not edit shipped migrations. Do not invent a leftover
score. Do not invent a theta.

## Consequences

After `make seed`, grouping comparison leftover pairs that already show
the leftover-map graphic of persisted `ξ` / `ζ` also name leftover
expected on that graphic when formatLeftoverMapExpected
returns a usable badge. Rank-0 unused axes still plot at
the origin and still name `E 0.00` when that persisted leftover
expected is finite. Click a post marker or a pair button opens that post. When `Y`, `E`, and `R` are finite, `Y − E = R`.

## Related

Independent of leftover-map rank on the grouping comparison leftover-map graphic.

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453
