# ADR 0024 — Fail-closed RankWeave ranking port

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

LineageWeave already calls RankWeave inside `reconstruct.py` to fuse
per-candidate channel scores into a parent choice. Demo Analyst had no
buyer-facing Rankings surface over the same visible `source_post` rows.
RankWeave is an in-process library
([README](https://github.com/ContextualWisdomLab/RankWeave)): it does
not define HTTP, a mailbox host, or authentication. A missing package
or a disabled port must not become an invented fused score or a
calibrated theta (TEPP owns theta; see ADR 0022 on #214).

This ADR does not replace `reconstruct.py`, does not read naruon
tables, and does not bind the demo IdP to production Keyverse.

## Decision

1. Consume RankWeave only through `RankWeaveClient`. The default
   transport raises `RankWeaveNotAvailable`. `build_rankweave_client
   (disabled=False)` uses `LibraryRankWeaveTransport`, which imports
   `weighted_reciprocal_rank_fuse` inside the call so a missing
   package fail-closes.
2. `GET /api/rankings` (`post_read`) loads ABAC-visible posts as two
   rank-only channels: temporal (newest first) and lexical (token
   overlap with the synthetic demo query `pricing quote delivery`).
   Hidden posts are omitted from every channel. Never invent a score.
3. Fusion is weighted RRF with Cormack et al. (2009) η = 60 and
   Samuel et al. (2025) unequal-channel weights (`temporal` 0.25,
   `lexical` 0.75). The buyer sees 1-based `fused_rank` and the post
   title — not a TEPP theta.
4. After login, Rankings sits above Calendar. Customer copy describes the
   available action and result state without naming the internal ranking
   dependency. An accepted hit lists the title; click opens that
   `source_post`.
5. Accepted hits also disclose owned-channel evidence (ADR 0167):
   1-based `channel_rank` and Cormack contribution
   `weight / (η + rank)` for each channel the post actually appears
   in. Missing channels are omitted. RankWeave extra fields are
   ignored. Copy states this is not a calibrated score.

## Consequences

`RANKWEAVE_DISABLED=1` keeps the fail-closed transport. The default
seeded stack uses the in-process library already required by
`reconstruct.py`. Mailbox stays on ADR 0020 / #217. Conversations stay
on ADR 0021 / #219. Leftover pairs stay on #211. TEPP stays on #214.
Keyverse IdP remains a later slice.

## References

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
rank fusion outperforms condorcet and individual rank learning
methods. In *Proceedings of the 32nd international ACM SIGIR
conference on Research and development in information retrieval*
(pp. 758–759). ACM. https://doi.org/10.1145/1571941.1572114

Samuel, D., MacAvaney, S., Yates, A., Zhang, E., Zhang, S.,
Macdonald, C., & Ounis, I. (2025). *Weighted reciprocal rank fusion
for multi-channel retrieval* [Preprint].

Contextual Wisdom Lab. (2026). *RankWeave* [Software documentation].
https://github.com/ContextualWisdomLab/RankWeave
