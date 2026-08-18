# ADR 0032 — Name leftover on the matching Event Lineage node

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0018 puts leftover pairs above the period-report member list.
Event Lineage is the surface a buyer scans to reconstruct the thread
before they reach the home post list. The leftover post is already a
DAG node; the node just does not name the leftover criterion.

Do not invent a second leftover store. Do not invent a fused score
or a theta. Do not change the existing `Open post: {title}`
accessible name — leftover is a visible caption on the already-named
control.

## Decision

When an authorized leftover pair names an Event Lineage node, that
node shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` under the post title.

A node that is not a leftover pair stays unmarked. A leftover pair
for a hidden post never reaches the DAG (ADR 0017 ABAC). A report
fetch error clears leftover captions and leaves the reconstructed
graph intact — never an invented pair.

After `make seed`, the leftover Event Lineage node reads **Closest
leftover · sales-lead** under the title; click still opens that post.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload. The home DAG and the popup DAG share
that list.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Home-row
leftover stays on #254 / ADR 0031. Calendar leftover stays on #253 /
ADR 0030. Rankings leftover stays on #252 / ADR 0029. This slice
only labels the already-visible Event Lineage node.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
