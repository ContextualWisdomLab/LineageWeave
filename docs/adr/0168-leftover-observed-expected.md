# ADR 0168 — Persist leftover observed Y and expected E[Y|θ, item]

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md). Independent of leftover-map
coordinates, leftover criterion landing, leftover complete-case
coverage, leftover-map axis share, leftover comparison-strip reuse,
and two-axis leftover-map distance.

## Context

ADR 0048 already computes leftover residual `R = Y − E[Y|θ, item]`
after IRT main effects (Jeon et al., 2021, eq. 3; Gabriel, 1971) and
persists closest/farthest pairs with `leftover_distance` and
`leftover_residual`. The buyer could see distance `d` but could not
check that residual identity: observed `Y` and expected `E` were
computed, then dropped.

Backfilling `Y = R` and `E = 0` would invent an expected score.
Persisting only `R` leaves the identity uncheckable.

## Decision

Each leftover pair persists `leftover_observed_score` (`Y`) and
`leftover_expected_score` (`E[Y|θ, item]`) next to
`leftover_residual`. The check
`abs(R − (Y − E)) < 1e-9` is named
`leftover_pair_residual_identity`. Missing or non-finite cells never
become pairs. Existing leftover rows are derived: migration `0108`
deletes incomplete rows so rebuild/seed rewrites honest `Y` and `E`
instead of fabricating them.

Do not invent a leftover score. Do not invent a second theta.

After `make seed`, leftover pair badges name observed, expected, and
leftover residual above the member list. Click still opens that post.
Copy tells the buyer to check leftover residual equals observed minus
expected.

## Consequences

`GET /api/reports/{grouping}/{period}` returns `leftover_observed_score`
and `leftover_expected_score` on each pair. Hidden posts stay hidden
through the same ABAC join as members. Migration `0108` upgrades
volumes that already applied `0012`. Fresh `0001` schema includes the
same columns and identity check.

## Related

Does not mix into leftover persist-map, leftover criterion landing,
leftover complete-case coverage, leftover-map axis share, leftover
comparison-strip reuse, or two-axis leftover-map distance. Issues #79
and #87 stay open.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
