# ADR 0148 — Persist leftover-map axis share

**Decision status:** Accepted
**Date:** 2026-08-24
**Amended by:** [ADR 0269](0269-leftover-map-axis-share-plot.md)
(leftover-map axis share on the graphic display);
[ADR 0289](0289-leftover-map-plot-singular.md)
(leftover-map singular values on the graphic display);
[ADR 0290](0290-leftover-map-axis-singular.md)
(leftover-map singular values on leftover-axis badges)

## Context

ADR 0048 persists closest and farthest leftover post–criterion pairs
from a Gabriel (1971) biplot of the residual `R = Y − E[Y|θ, item]`
after a real GRM/GPCM score (Jeon et al., 2021, eq. 3). Buyers can
open those pairs (ADR 0049) but cannot yet read how much leftover-map
structure sits on axis 1 versus axis 2.

Gabriel inertia of leftover-map axis `k` is `σ_k² / Σ_j σ_j²`. That
share is a report-level property of the residual SVD, not a
post-identifying leftover score and not a second theta. Denormalizing
it onto each leftover pair would violate 3NF.

`fast-mlsirm` still exposes no leftover-pair or leftover-map API.
LineageWeave must not fork LSIRM or invent leftover numbers when the
residual is rank-0.

## Decision

After the same residual SVD that produces leftover pairs, persist
exactly two leftover-map axes (axis 1 and axis 2) per period report in
`report_leftover_map_axis` (3NF, two-or-more-word `snake_case`).

Share is `σ_k² / Σ_j σ_j²` from the leftover singular values that
survive the leftover singular floor. Rank-0 residuals emit two
zero-share axes so `make seed` can name leftover-map structure without
inventing a leftover score. Missing response cells stay out of the
factorization.

Cascade the rows with `report_period_score`. Axes are aggregate and
non-identifying: ABAC that hides leftover pairs does not hide axis
share. Do not store a second theta. Do not invent leftover numbers.

The biplot lives in `lineageweave/leftover_pairs.py` so leftover tests
do not import `period_report` or `fast_mlsirm`.

## Consequences

Rebuild and seed write leftover-map axes in the same transaction as
leftover pairs. `GET /api/reports/{grouping}/{period}` returns
`leftover_map_axes` next to `leftover_pairs`. The Period reports panel
shows leftover-axis share badges and a caption that tells the buyer to
open a leftover pair. The leftover-map graphic display captions those
same leftover-map axes with the persisted share when finite (ADR 0269).
Migration `0169_report_leftover_map_axis.sql`
upgrades volumes that already applied `0001`.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
