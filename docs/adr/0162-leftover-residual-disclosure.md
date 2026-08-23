# ADR 0162 — Disclose leftover residual on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

ADR 0048 already persists `leftover_distance` (Euclidean leftover-map
gap from the Gabriel biplot of `R`) and `leftover_residual`
(`R = Y − E[Y|θ, item]`) on `report_leftover_pair`. ADR 0049 already
renders closest and farthest pairs above the member list and opens the
named post. The pair button showed only `d`, so a buyer could not tell
a large leftover response from a merely distant map pair.

Jeon et al. (2021, eq. 3) leftover interaction is
`−γ‖ξ_p − ζ_i‖`. Distance is that map gap. Residual is the observed
leftover *after IRT main effects* that entered the biplot. They are
different quantities. Hiding residual would keep the persisted column
as an unpublished measurement.

This increment does not persist leftover-map coordinates (ADR 0121 /
PR #481) and does not land Post quality on the leftover criterion
(ADR 0125 / PR #485).

## Decision

Each leftover pair button shows:

1. closest or farthest label, post title, and criterion short label;
2. leftover residual `R` with an explicit sign, two decimal places;
3. leftover-map distance `d`;
4. the next action: read residual `R` after IRT main effects, then
   open this post to read the named criterion.

Missing leftover rows still render nothing. A non-finite residual
renders an em dash rather than a fabricated leftover score. Click
still uses the same post-open handler as ADR 0049.

## Consequences

`GET /api/reports/{grouping}/{period}` already returns
`leftover_residual`. The frontend now names that value. After
`make seed`, closest and farthest leftover pairs sit above the member
list with `R` and `d`; click opens that post.

## Related

Amends [ADR 0049](0049-leftover-pair-report-ui.md). Depends on
[ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0003](0003-fast-mlsirm-report-integration.md). Independent of
leftover interaction-map persistence and leftover-criterion evaluation
landing.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
