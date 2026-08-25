# ADR 0121 — Persist leftover interaction-map coordinates

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

ADR 0048 persists the closest and farthest leftover post–criterion
pairs after IRT main effects. Those pairs are two cells on the Jeon
et al. (2021, eq. 3) leftover interaction map `−γ‖ξ_p − ζ_i‖`. The
Gabriel (1971) biplot that produces the pairs already computes person
positions `ξ` and item positions `ζ`, then discards them. A reader
who sees only two named pairs cannot see *why* those cells sat
closest or farthest, or where the other complete-case posts and
criteria sit on the same leftover map.

fast-mlsirm now exposes the Rust-backed residual interaction-map contract
adopted by ADR 0207. LineageWeave must not fork that calculation, invent a
second IRT fit, or treat a missing residual cell as a zero residual.

## Decision

After a real GRM/GPCM score, keep the complete-case Gabriel
coordinates that leftover pairs already use. Persist every complete-
case post as `report_leftover_map_person` (`axis_one`, `axis_two`)
and every complete-case criterion as `report_leftover_map_item`.
Pad unused axes with zero when residual rank is below two. Do not
invent a second component. Closest/farthest selection and persisted
distance use those same two reader-visible axes; unpersisted higher
components never silently change a highlighted map pair. Incomplete
rows and columns stay out of the factorization.

Cascade the rows with `report_period_score`. A leftover-map post
must also be a `report_member_score` row. A leftover-map criterion
must be a `report_item_information` item on that same report. Do not
store a second theta. A rank-0 residual still emits origin
coordinates so `make seed` is not empty; those zeros are not a
fabricated interaction.

Closest and farthest pairs remain ADR 0048 / ADR 0049. The map sits
**above** that pair list on the period-report group. Clicking a
person node opens that post with the same handler as a leftover
pair. Pair-member criterion nodes open that leftover-pair post
([ADR 0126](0126-leftover-map-criterion-node.md)). Hidden posts stay hidden: leftover-map persons join
`source_post` and use the same ABAC gate as members and leftover
pairs. Missing map rows render nothing.

The biplot calculation lives in fast-mlsirm. `lineageweave/leftover_pairs.py`
maps returned indices and values to authorized product identifiers and selects
the closest/farthest cells; it contains no factorization or cross-term formula.

## Consequences

Rebuild and seed write leftover-map coordinates in the same
transaction as leftover pairs. `GET /api/reports/{grouping}/{period}`
returns `leftover_map_persons` (with post title) and
`leftover_map_items`. Migration
`0172_report_leftover_interaction_map.sql` upgrades volumes that
already applied `0001` / `0012`. `migrate.sh` already replays every
four-digit `NNNN_*.sql` file (ADR 0166), so 0172 lands on existing
volumes without a new allowlist entry.

## Related

Depends on [ADR 0048](0048-persist-lsirm-leftover-pairs.md),
[ADR 0049](0049-leftover-pair-report-ui.md), and
[ADR 0003](0003-fast-mlsirm-report-integration.md).

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
