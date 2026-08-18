# ADR 0033 — Name leftover on the matching Keyman chip

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0018 puts leftover pairs above the period-report member list.
The member list is already the click-through to Event Lineage,
Keyman, and evaluation. After a leftover pair opens that post, the
Keyman chips still do not name the leftover criterion.

Do not invent a second leftover store. Do not invent a fused score
or a theta. Do not invent leftover on a person. Leftover is a
post–criterion pair (Jeon leftover map). The Keyman extracted from
that post, and a related-post chip that *is* a leftover pair, only
show the authorized caption. Do not change existing accessible
names (`Related nodes for {name}`, `Open related post: {title}`).

## Decision

When an authorized leftover pair names the opened post, each Keyman
person chip on that post shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` next to the name.

When a related-node walk returns a post that is itself a leftover
pair, that related-post chip shows the same leftover caption.

A Keyman that is not on a leftover post stays unmarked. A related
person or organization chip stays unmarked. A leftover pair for a
hidden post never reaches Keyman (ADR 0017 ABAC). A report fetch
error clears leftover captions and leaves the Keyman list intact —
never an invented pair.

After `make seed`, open the leftover Public post: Ada West reads
**Closest leftover · sales-lead**; click still opens related nodes.
A related leftover post chip reads **Farthest leftover · negative**;
click still opens that post.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Event
Lineage leftover stays on #255 / ADR 0032. Home-row leftover stays
on #254 / ADR 0031. This slice only labels the already-visible
Keyman chips.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5
