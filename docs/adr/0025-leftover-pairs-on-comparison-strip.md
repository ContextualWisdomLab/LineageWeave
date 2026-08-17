# ADR 0025 — Leftover pairs on the grouping comparison strip

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0018 puts closest and farthest leftover pairs above each period-report
member list. The home grouping comparison strip already shows mean θ and
post count for every process unit, corporate entity, and thread group on
the shared metric, but it does not name leftover pairs. A buyer comparing
A-100 and B-200 has to switch grouping and scan the report before they
can open the unexpectedly aligned or opposed post–criterion pair.

`GET /api/reports/compare/{period}` already ABAC-filters members. Leftover
pairs must use the same gate. Do not invent a second leftover store or a
theta.

## Decision

Carry authorized leftover pairs on each comparison-strip row.

1. `fetch_period_comparison` reads `report_leftover_pair` for the period
   and attaches `leftover_pairs` next to the existing grouping label and
   mean θ. The payload includes post title, criterion, leftover-map
   distance, and the same visibility columns members already use.
2. The compare endpoint drops leftover pairs the account cannot see,
   the same way it drops hidden members. A grouping with no visible
   leftover pair still appears when it has visible members.
3. The comparison strip renders leftover pair buttons under the grouping
   row. Clicking a pair opens that post. Clicking the grouping row still
   switches the Period reports grouping.
4. Missing leftover rows render nothing — never a placeholder pair.

After `make seed`, the A-100 comparison row names its closest leftover
pair above the member list path; click opens that post.

## Consequences

The comparison strip and the report panel share one leftover store
(ADR 0017). Mean θ stays on the strip. Rankings stay on ADR 0024.
Do not mix this into #74 or #92.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
