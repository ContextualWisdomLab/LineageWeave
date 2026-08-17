# ADR 0026 — Name leftover pair context on the opened post

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0018 puts closest and farthest leftover pairs above the period-report
member list. Clicking a pair opened the post, but the popup did not name
why the buyer landed there. The evaluation list showed criterion scores
without marking the leftover criterion, so “Open this post to read the
criterion it sat closest to” had no next action on the destination.

## Decision

When the loaded period-report payload includes leftover pairs for the
open post, the popup names that leftover map result and marks the
matching evaluation row.

1. `ReportsPanel` lifts authorized `leftover_pairs` into `PostList`.
   A report fetch error clears the list — never an invented pair.
2. The popup status is
   `This post sat closest to {criterion} after main effects. Read that
   evaluation row next.` (or `farthest from`).
3. The evaluation row whose `criterion_code` matches a leftover pair
   shows `Closest leftover` or `Farthest leftover`. Other rows stay
   unmarked.
4. Opening the same post from the member list, home list, or leftover
   button uses the same loaded report evidence. A post that is not a
   leftover pair shows no leftover copy.

Do not invent leftover numbers. Do not persist a second leftover store.
Do not mix this into #74 or #92.

## Consequences

After `make seed`, opening the closest leftover pair (or that same
member) names the leftover criterion and points at the evaluation row.
Mean θ stays on the report panel. Rankings stay on ADR 0024. TEPP stays
on #214.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
