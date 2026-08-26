# ADR 0167 — Disclose RankWeave ranking channel evidence

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

ADR 0024 already fuses ABAC-visible posts through RankWeave weighted
reciprocal-rank fusion (Cormack et al., 2009, η = 60; Samuel et al.,
2025, unequal weights). `GET /api/rankings` returned only `post_id`,
`post_title`, and 1-based `fused_rank`. A reader could open the hit
but could not see which owned channel ranked it, or how much that
rank contributed.

Event Lineage channel evidence (ADR 0124 on #387) explains
reconstructed parent→child edges from persisted convex-fusion
scores. Rankings is a different surface: two rank-only channels
(`temporal`, `lexical`) fused in-process at GET time. There is no
persisted ranking table and no TEPP theta. RankWeave extra fields
must not be trusted; a missing channel stays missing.

This ADR does not replace reconstruction fusion, leftover pairs,
TEPP receipts, Allen interval labels, or Event Lineage isolation
reasons.

## Decision

1. Compute ranking channel evidence from LineageWeave-owned rank
   lists, never from RankWeave payload extras. For each fused hit
   and each channel with a positive weight, take the 1-based rank
   of that `post_id` in the ordered id list. Skip a channel the
   post is absent from. Do not invent a rank.
2. Contribution is Cormack weighted RRF:
   `weight / (η + rank)` with η = 60. Sort by contribution
   descending, then `signal_code`. `rank` on the evidence row is
   that 1-based evidence order. `channel_rank` is the 1-based
   position in that channel.
3. Labels: `temporal` = **Newest first**, `lexical` = **Title
   overlap**. The payload never includes a fused score or a theta.
4. Rankings lists the evidence under each accepted hit as an
   accessible sibling list, not hover-only. Customer copy tells the reader
   to open a result to review its channel evidence and states that the result
   is not a calibrated measurement; it does not name the internal ranking
   dependency. Click still opens that post.
5. Unavailable RankWeave stays empty (`rankweave_not_available`).
   Hidden posts remain omitted from every channel.

## Consequences

Buyers can see why a Rankings hit landed without treating RRF as
measurement. A later channel or weight change recomputes evidence
on the next GET; nothing is persisted. Event Lineage evidence
remains the reconstruct/convex path.

## References

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
rank fusion outperforms Condorcet and individual rank learning
methods. In *Proceedings of the 32nd international ACM SIGIR
conference on Research and development in information retrieval*
(pp. 758–759). ACM. https://doi.org/10.1145/1571941.1572114

Samuel, D., MacAvaney, S., Yates, A., Zhang, E., Zhang, S.,
Macdonald, C., & Ounis, I. (2025). *Weighted reciprocal rank fusion
for multi-channel retrieval* [Preprint].

ADR 0024 (RankWeave fusion fail-closed)
ADR 0124 (Event Lineage channel evidence; separate surface)
