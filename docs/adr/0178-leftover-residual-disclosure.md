# ADR 0178 — Disclose leftover residual on period-report pair rows

**Decision status:** Accepted
**Date:** 2026-08-24

Amends [ADR 0049](0049-leftover-pair-report-ui.md).

## Context

ADR 0048 already persists leftover-map distance and leftover residual
`R = Y − E[Y|θ, item]` on `report_leftover_pair`. ADR 0049 already
renders closest and farthest pairs above the member list and opens the
named post. The pair button showed only `d`, so a buyer could not tell
a large leftover response from a merely distant map pair.

Jeon et al. (2021, eq. 3) leftover interaction is
`−γ‖ξ_p − ζ_i‖`. Distance is that map gap. Residual is the observed
leftover *after IRT main effects* that entered the biplot. They are
different quantities. Hiding residual would keep the persisted column
as an unpublished measurement.

This increment does not persist leftover-map coordinates, does not name
observed `Y` / expected `E`, does not name leftover-map rank, and does
not land Post quality on the leftover criterion. No schema change:
`leftover_residual` already exists from ADR 0048 / migration `0012`.

The unprotected-stack ADR for the same buyer fact was 0162. This
protected-main reconstruction uses **0178** so it does not collide with
two-axis leftover-map distance (0166), leftover coverage (0168),
leftover-map axis share (0148), leftover-map rank (0172), leftover
observed Y / expected E (0177), or analysis-run status same clock
(0171).

## Decision

Each leftover pair button shows signed leftover residual `R` with two
decimal places next to leftover-map distance `d`. Next action: leftover
residual `R` after IRT main effects; open this post to read the named
criterion. A non-finite residual renders an em dash rather than a
fabricated leftover score. Click still uses the same post-open handler
as ADR 0049.

## Consequences

`GET /api/reports/{grouping}/{period}` already returns
`leftover_residual`. The frontend now names that value. After
`make seed`, closest and farthest leftover pairs sit above the member
list with `R` next to `d`; click opens that post.

## Related

Independent of leftover interaction-map persistence, leftover-criterion
evaluation landing, leftover-map complete-case coverage, leftover-map
axis share, leftover pairs on the grouping comparison strip, two-axis
leftover-map distance, leftover observed `Y` / expected `E`, and
leftover-map rank.

## References

Gabriel, K. R. (1971). The biplot graphic display of matrices with
application to principal component analysis. *Biometrika, 58*(3),
453–467. https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
