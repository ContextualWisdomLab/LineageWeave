# ADR 0163 — Persist observed Y and expected E on leftover pairs

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance and leftover residual
`R = Y − E[Y|θ, item]` on `report_leftover_pair`. ADR 0049 already
renders closest and farthest pairs above the member list and opens the
named post. Residual disclosure without naming `Y` and `E` leaves a
buyer unable to tell whether a leftover cell is a high observed
response or a low expected category after IRT main effects.

Jeon et al. (2021, eq. 3) leftover interaction is `−γ‖ξ_p − ζ_i‖`.
Gabriel (1971) supplies the leftover-map coordinates from a residual
biplot of `R`. `R` is not an invented leftover score: it is the
observed category minus the already-fitted expected category. Those
two inputs must travel with the pair row.

This increment does not persist leftover-map coordinates, does not
change leftover-map axis count, and does not land Post quality on the
leftover criterion.

## Decision

Each leftover pair names:

1. `observed_response` — the observed category `Y` for that
   post–criterion cell;
2. `expected_response` — `E[Y|θ, item]` from the already-fitted
   GRM/GPCM main effects;
3. `leftover_residual`, which must equal `Y − E` within `1e-6`.

Fresh `0001` / `0012` tables require both columns. Migration `0163`
adds nullable columns so older leftover rows keep distance and
residual without fabricating `Y` or `E`. The pair button shows
`Y {observed} · E {expected}` next to leftover-map distance `d` when
both values are finite. The next action is: read observed `Y` and
expected `E` after IRT main effects, then open this post. Omit the
`Y` / `E` badge when either value is missing or non-finite. Do not
invent a leftover score. Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns `observed_response`
and `expected_response`. After `make seed`, closest and farthest
leftover pairs sit above the member list with named `Y` and `E`;
click opens that post. Hidden posts stay hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual UI extraction, and two-axis
leftover-map distance.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
