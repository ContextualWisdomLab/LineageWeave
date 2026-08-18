# ADR 0029 — Name leftover on an accepted Rankings hit

**Decision status:** Accepted
**Date:** 2026-08-18

## Context

ADR 0024 lists accepted RankWeave hits above Calendar. ADR 0018 puts
leftover pairs above the period-report member list. A buyer who starts
from Rankings still sees only title and fused rank. The leftover post
is already in that list when RankWeave accepts it; the hit just does
not name the leftover criterion.

Do not invent a second leftover store. Do not invent a fused score or
a theta. Unavailable Rankings stay **Rankings · RankWeave not
available**.

## Decision

When an authorized leftover pair names an accepted ranking hit, that
button shows `Closest leftover · {criterion}` or
`Farthest leftover · {criterion}` and includes the same caption in
its accessible name.

A hit that is not a leftover pair stays unmarked. A leftover pair
for a hidden post never reaches Rankings (ADR 0017 ABAC plus ADR
0024 hidden-post omit). RankWeave unavailability still renders no
hits.

After `make seed` with RankWeave accepted, the leftover ranking hit
reads **Closest leftover · sales-lead** next to rank; click still
opens that post.

Leftover evidence is the same authorized `leftover_pairs` already
on the period-report payload. A report fetch error clears the list
— never an invented pair.

## Consequences

Leftover buttons above the member list stay (ADR 0018). Member
badges stay on #234 / ADR 0028. Comparison-strip leftover is #233.
Opened-post leftover copy is #224. This slice only labels the
already-visible ranking hit.

## Related

Depends on [ADR 0017](0017-persist-lsirm-leftover-pairs.md),
[ADR 0018](0018-leftover-pair-report-ui.md), and
[ADR 0024](0024-rankweave-fusion-fail-closed.md).

## References

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping
unobserved item–respondent interactions: A latent space item response
model with interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
rank fusion outperforms condorcet and individual rank learning
methods. In *Proceedings of the 32nd international ACM SIGIR
conference on Research and development in information retrieval*
(pp. 758–759). ACM. https://doi.org/10.1145/1571941.1572114
