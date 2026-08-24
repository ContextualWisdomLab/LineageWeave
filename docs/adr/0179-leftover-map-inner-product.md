# ADR 0179 — Name leftover-map inner product on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance `d = ‖ξ_p − ζ_i‖` and
leftover residual `R = Y − E[Y|θ, item]` on `report_leftover_pair`.
ADR 0049 already renders closest and farthest pairs above the member
list and opens the named post. Distance is the Jeon et al. (2021,
eq. 3) map gap. Gabriel (1971) also reconstructs the leftover cell as
the inner product `ξ_p · ζ_i`. Hiding that inner product lets a buyer
read a distant map pair as a large leftover cell, or a close pair as a
reconstructed leftover, without the reconstructed value.

This increment does not persist leftover-map coordinates, does not name
observed `Y` / expected `E`, does not name leftover-map rank, does not
split leftover-map distance onto two axes, and does not land Post
quality on the leftover criterion.

The unprotected-stack reconstructions for neighbouring leftover facts
use 0162–0178. This protected-main increment uses **0179** so it does
not collide with leftover residual disclosure (0178), leftover observed
`Y` / expected `E` (0177), leftover-map rank (0172), two-axis
leftover-map distance (0166), leftover coverage (0168), leftover-map
axis share (0148), or leftover interaction-map persistence (0121).

## Decision

Each leftover pair names `leftover_inner_product` — the Gabriel inner
product `ξ·ζ` of the leftover-map person and item coordinates that
produced leftover-map distance `d`. Migration `0179` is the single
source of the column on every install path, fresh or existing --
shipped migrations (`0001` / `0012`) are never edited after the fact.
The column is nullable so older leftover rows keep distance and residual
without fabricating an inner product. Fallback pairs that have no
complete-case leftover map omit the value rather than inventing one.

The pair button shows `ξ·ζ {signed}` next to leftover-map distance `d`
when the value is finite. Next action: leftover-map inner product `ξ·ζ`
reconstructs leftover residual after IRT main effects; open this post
to read the named criterion. A missing or non-finite inner product
omits the badge and keeps the existing closest/farthest next action.
Do not invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns
`leftover_inner_product`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `ξ·ζ` next to `d`;
click opens that post. Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual disclosure, leftover observed
`Y` / expected `E`, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, and leftover-map rank.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
