# ADR 0164 — Name leftover-map rank on leftover pairs

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance and leftover residual
`R = Y − E[Y|θ, item]` on `report_leftover_pair`. A rank-0 residual
still emits a stable closest/farthest pair so `make seed` is not empty;
the stored distance is then zero, not a fabricated interaction. ADR 0049
renders those pairs above the member list. Without leftover-map rank, a
buyer cannot tell a Gabriel biplot with leftover structure (Jeon et al.,
2021, eq. 3) from an origin collapse that still shows `d 0.00`.

This increment does not persist leftover-map coordinates, does not name
observed `Y` / expected `E`, does not change leftover-map axis count, and
does not land Post quality on the leftover criterion.

## Decision

Each leftover pair names `leftover_map_rank`: the number of Gabriel
singular values above the leftover singular floor on the complete-case
residual rectangle. Closest and farthest pairs on one period report share
that rank. A fallback pair that is not placed on a leftover map stores
rank `0`. Migration `0164` is the single source of the column on every
install path; shipped migrations (`0001` / `0012`) are never rewritten.
It adds a nullable column so older leftover rows keep distance and residual
without fabricating a rank.

The pair button shows `rank {n}` when the value is a finite
non-negative integer. Rank `0` next action: leftover map has no leftover
structure after IRT main effects; open this post. Rank `≥ 1` next action:
read leftover map rank after IRT main effects, then open this post. Omit
the rank badge when the value is missing. Do not invent a leftover score.
Do not invent a theta.

## Consequences

`GET /api/reports/{grouping}/{period}` returns `leftover_map_rank`. After
`make seed`, closest and farthest leftover pairs sit above the member
list with leftover-map rank; click opens that post. Hidden posts stay
hidden.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover residual UI extraction, two-axis leftover-map
distance, and leftover observed `Y` / expected `E`.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
