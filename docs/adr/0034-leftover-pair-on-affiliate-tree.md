# ADR 0034 — Name leftover on the matching affiliate-tree Keyman

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0018 puts leftover pairs above the period-report member list.
After a leftover pair opens that post, the affiliate tree still does
not name the leftover criterion. The leftover post already lists
affiliate people; those chips just do not name leftover.

Do not invent a second leftover store. Do not invent a fused score
or a theta. Do not invent leftover on an organization. Leftover is
a post–criterion pair (Jeon leftover map). Do not change the existing
`Affiliate Keyman: {name}` or `Affiliate org: {name}` accessible names.

## Decision

When an authorized leftover pair names the opened post, each
affiliate-tree person chip on that post shows
`Closest leftover · {criterion}` or `Farthest leftover · {criterion}`
next to the name.

An organization chip stays unmarked. A leftover pair for a hidden
post never reaches the tree (ADR 0017 ABAC). A report fetch error
clears leftover captions and leaves the tree intact — never an
invented pair.

After `make seed`, open the leftover Public post: Priya Nair on the
affiliate tree reads **Closest leftover · sales-lead**; click still
opens related nodes.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Keyman-chip
leftover stays on #256 / ADR 0033. Event Lineage leftover stays on
#255 / ADR 0032. This slice only labels the already-visible
affiliate-tree person chips.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
