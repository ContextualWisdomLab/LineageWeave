# ADR 0031 — Name leftover on the matching home post row

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0018 puts leftover pairs above the period-report member list.
The home post list is the last surface a buyer scans after Rankings,
Calendar, Period reports, and Event Lineage. The leftover post is
already in that list; the row just does not name the leftover
criterion.

Do not invent a second leftover store. Do not invent a fused score
or a theta. Do not change the existing `View post: {title}`
accessible name — leftover is a visible badge on the already-named
control.

## Decision

When an authorized leftover pair names a home post row, that button
shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` next to the visibility badge.

A row that is not a leftover pair stays unmarked. A leftover pair
for a hidden post never reaches the home list (ADR 0017 ABAC). A
report fetch error clears leftover badges and leaves the post list
intact — never an invented pair.

After `make seed`, the leftover home row reads **Closest leftover ·
sales-lead** next to visibility; click still opens that post.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Calendar
leftover stays on #253 / ADR 0030. Rankings leftover stays on #252
/ ADR 0029. This slice only labels the already-visible home row.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
