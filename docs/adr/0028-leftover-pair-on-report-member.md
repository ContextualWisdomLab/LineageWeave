# ADR 0028 — Name leftover on the matching report member

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0018 puts leftover pairs above the member list. A buyer who scans
members first still sees only θ and the ticket. The leftover post is
already in that list; it just does not name the leftover criterion.

Do not invent a second leftover store. Do not invent a theta.

## Decision

When an authorized leftover pair names a member post, that member
button shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` and includes the same caption in
its accessible name.

A member that is not a leftover pair stays unmarked. A leftover pair
for a hidden post never reaches the member list (ADR 0017 ABAC).

After `make seed`, the leftover member reads **Closest leftover ·
sales-lead** next to θ; click still opens that post.

## Consequences

Leftover buttons above the list stay. This slice only labels the
already-visible member. Comparison-strip leftover is ADR 0025 / #233.
Opened-post leftover copy is #224.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
