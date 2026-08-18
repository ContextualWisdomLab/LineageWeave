# ADR 0030 — Name leftover on a matching calendar commitment

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0018 puts leftover pairs above the period-report member list.
Calendar sits under Rankings and lists due commitments (Allen
intervals). A buyer who starts from Calendar still sees only the
commitment title, post title, status, and due date. The leftover
post is already on that list when it has a due ticket; the row just
does not name the leftover criterion.

Do not invent a second leftover store. Do not invent a fused score
or a theta. An empty calendar stays **No upcoming commitments**.

## Decision

When an authorized leftover pair names a calendar commitment, that
button shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` and includes the same caption in
its accessible name.

A commitment that is not a leftover pair stays unmarked. A leftover
pair for a hidden post never reaches Calendar (ADR 0017 ABAC). A
report fetch error clears leftover badges and leaves the due list
intact — never an invented pair.

After `make seed`, the leftover calendar commitment reads **Closest
leftover · sales-lead** next to the due date; click still opens
that post.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Rankings
leftover badges stay on #252 / ADR 0029. Member badges stay on
#234 / ADR 0028. This slice only labels the already-visible
calendar commitment.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md) and
[ADR 0018](0018-leftover-pair-report-ui.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434
