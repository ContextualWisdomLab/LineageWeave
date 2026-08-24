# ADR 0168 — Name leftover complete-case coverage

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

ADR 0048 already factorizes the leftover residual
`R = Y − E[Y|θ, item]` on the **complete-case** rectangle (Gabriel,
1971). Incomplete rows are dropped; missing cells are never filled
with zero. ADR 0049 then shows closest and farthest pairs above the
member list.

The period report still does not tell the buyer how many scored
posts entered that factorization. A sparse post with one missing
criterion is excluded from the map, so closest/farthest pairs can
name two posts while three posts were scored. Without a coverage
caption, the buyer cannot tell whether the map used every scored
post or dropped incomplete rows.

This slice does not persist leftover-map coordinates (that is a
separate increment), does not disclose residual `R` on pair rows,
and does not change pair click-through.

## Decision

After a real GRM/GPCM score, persist one
`report_leftover_map_coverage` row per period report (3NF,
two-or-more-word `snake_case`):

- `map_post_count` — posts that entered the complete-case leftover
  map
- `scored_post_count` — posts with at least one observed cell
- `map_item_count` / `scored_item_count` — the same counts for
  criteria
- `incomplete_post_count` / `incomplete_item_count` — scored minus
  map, stored so the buyer fact is durable and check-constrained

Do not store a second theta. Do not fill missing cells with zero.
Do not invent coverage when the IRT matrix is unusable.

`GET /api/reports/{grouping}/{period}` returns
`leftover_map_coverage` next to `leftover_pairs`. The Period
reports panel renders a caption **above** the leftover pair list:

> Leftover map used N of M scored posts (complete-case)

Missing coverage renders nothing. A hidden post never appears as a
leftover pair (ADR 0049); coverage counts remain the fitted map,
not a visibility-filtered recount.

## Consequences

Rebuild and seed write coverage in the same transaction as leftover
pairs. Migration `0168_report_leftover_map_coverage.sql` upgrades
volumes that already applied `0001`. `migrate.sh` replays `0168_*`
on existing volumes.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md) and
[ADR 0049](0049-leftover-pair-report-ui.md). Complements, and does
not replace, leftover-map coordinates or residual-row disclosure.
