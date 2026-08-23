# ADR 0145 — Lineage channel-fusion weights come from psychometric estimation, not hand-picked constants

**Decision status:** Proposed
**Date:** 2026-08-23

> Numbering note: parallel branches are assigning ADR numbers concurrently
> (0143 exists on an unmerged branch). `0145` was the next free number on
> `docs/customer-master-scope-adr` at time of writing and may need
> renumbering when branches converge.

## Context

`lineageweave.reconstruct` fuses four evidence channels (temporal,
secondary-key, text-similarity, llm adjudication) into one convex score
per candidate parent-child pair. The fusion weights,
`DEFAULT_CHANNEL_WEIGHTS = {"temporal": 0.15, "secondary_key": 0.15,
"text": 0.30, "llm": 0.40}`, were hand-picked: the module's own comment
justifies them with a qualitative argument ("llm ... is the only channel
that actually reasons about the content"), not with any estimate from
data. The product's standing requirement — repeated across many
sessions — is that scoring weights be grounded in published measurement
methodology through the organization's own psychometric libraries
(`fast-mlsirm`, TEPP), never asserted by fiat.

The measurement literature gives an exact grounding. Treat each channel
as an *item* observing the latent trait "these two posts are genuinely
related", and each scored candidate pair as a *respondent*. Under the
two-parameter logistic model, the information-optimal scoring weight of
an item is proportional to its discrimination parameter (Birnbaum, 1968;
Lord, 1980) — an unweighted or arbitrarily-weighted composite discards
exactly that information (McNeish & Wolf, 2020). Pairs are nested inside
reconstruction groups (process unit / corporate entity / thread), so a
single-level fit would commit the ecological/atomistic inference error
the standing mandate calls out (Robinson, 1950); `fast-mlsirm`'s MLS2PLM
is a *multilevel* 2PL whose `cluster_id` models exactly this nesting, and
its `MLSIRMParams.alpha` field is the per-item log-discrimination
(natural-scale discrimination `exp(alpha)` is positive by construction,
so normalizing to sum 1 always yields valid convex weights).

`fast-mlsirm` is not yet published to PyPI, so LineageWeave cannot take
a hard install dependency today. This repository's established pattern
for every optional capability is fail-closed clients (Null client when
unconfigured, never a fabricated result); the same pattern applies here.

## Decision

1. **Estimation, not assertion.** A new module,
   `lineageweave/channel_weight_estimation.py`, estimates channel
   weights by fitting `fast-mlsirm`'s MLS2PLM over observed channel
   scores: items = channels, respondents = candidate pairs sampled the
   same way `reconstruct` forms them (same grouping, same candidate
   window), `factor_id` assigns every channel item to the one relatedness
   trait, and `cluster_id` = the pair's reconstruction group (multilevel
   nesting per Robinson, 1950). Estimated weights are the normalized
   natural-scale discriminations, `exp(alpha_j) / Σ exp(alpha_k)`
   (Birnbaum, 1968).
2. **Dichotomization at the fusion floor.** MLS2PLM is dichotomous;
   channel scores in [0, 1] are dichotomized at
   `DEFAULT_MIN_FUSED_SCORE` (0.3) — the same threshold `reconstruct`
   already treats as the boundary between "evidence of a link" and
   "no plausible candidate", so the measurement model observes the same
   binary event the fusion decision acts on.
3. **Fail closed, never fabricate.** When `fast-mlsirm` is not
   importable, the sample is too small, or the fit degenerates (any
   non-finite alpha), estimation returns nothing and callers keep the
   documented fallback constants — now explicitly labeled as
   *ungrounded fallback* in `reconstruct.py`'s docstring, not as a
   justified default.
4. **Persisted, provenance-bearing weights.** An operator script
   (`scripts/estimate_channel_weights.py`) runs the estimation against
   the real corpus and upserts one row per channel into a new
   `lineage_channel_weight` table (migration 0135) carrying the weight,
   the estimation method code, the sample size, and the estimation
   timestamp. `rebuild_lineage` loads these rows and passes them to
   `reconstruct`; it uses them **only when the persisted channel set
   exactly matches the active channel set** (no partial mixing of
   estimated and hand-picked weights — a mixed vector is neither
   grounded nor the documented fallback), otherwise it falls back
   entirely.
5. **The llm channel is estimated only when adjudication is
   configured.** Scoring sampled pairs through the adjudication client
   costs provider calls; the script includes the llm channel when a
   client is available and skips it otherwise (the exact-match rule in
   (4) then keeps rebuilds on the fallback until a full estimate
   exists). Accuracy over speed, per the standing mandate.

## Consequences

**Positive.** Fusion weights become an estimable, auditable quantity
with a citation trail instead of a code comment: the persisted row
records how many pairs supported the estimate and when. Re-running the
operator script after corpus growth re-calibrates the fusion without a
code change. The multilevel fit respects group nesting rather than
pooling pairs atomistically.

**Negative.** A new optional dependency surface (fast-mlsirm via git
until it reaches PyPI) and a new operator step. Dichotomizing at 0.3
discards within-interval score variation; a graded/continuous-response
model (fast-mlsirm ships `grm.py`/`crm.py`) is the natural upgrade once
this loop is validated end-to-end — deliberately out of scope for the
first landing. TEPP-side calibration (event-level theta as the latent
anchor) is a further integration this ADR does not attempt while TEPP
remains non-production (see the standing `tepp_readiness_watch`).

## Rejected Alternatives

- **Keep hand-picked constants.** The standing product requirement
  explicitly forbids this; no citation supports the current 0.15/0.15/
  0.30/0.40 split.
- **Reciprocal Rank Fusion for this surface.** RRF (Cormack et al.,
  2009) is parameter-free and already grounds RankWeave's *rank* fusion
  constant (η = 60), but reconstruct's decision is a thresholded
  *score* over at most `candidate_window` candidates, not a deep
  ranked-list merge; discarding score magnitude here would also discard
  `DEFAULT_MIN_FUSED_SCORE`'s "no plausible parent" semantics.
- **Supervised weight learning (logistic regression on labeled pairs).**
  There is no labeled corpus: the source system carries no ground-truth
  thread links (their absence is why this library exists). IRT estimates
  discriminations from response structure without per-pair labels.

## Implementation Notes

1. Migration `0135_lineage_channel_weight.sql`:
   `lineage_channel_weight(channel_code text primary key, weight_value
   double precision not null, estimation_method_code text not null,
   sample_pair_count bigint not null, estimated_at timestamptz not null
   default now())`, plus rollback. Two-word snake_case per ADR 0120.
2. `estimate_channel_weights()` returns `None` on: import failure,
   fewer than `_MIN_SAMPLE_PAIRS` pairs, any channel with fewer than two
   distinct dichotomized responses, or any non-finite estimated alpha.
3. `lineage_edge_specs` and `rebuild_lineage` gain an optional
   `weights` pass-through; `None` keeps today's behavior exactly.
4. Tests: fail-closed paths run everywhere; a parameter-recovery test
   (planted discriminations recovered within tolerance, the
   organization's RMSE standard) runs when `fast_mlsirm` is importable
   and skips honestly otherwise, same as this repo's live-service
   skips.

## References (APA 7th)

Birnbaum, A. (1968). Some latent trait models and their use in
inferring an examinee's ability. In F. M. Lord & M. R. Novick,
*Statistical theories of mental test scores* (pp. 397–479).
Addison-Wesley.

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal
rank fusion outperforms Condorcet and individual rank learning methods.
*Proceedings of the 32nd International ACM SIGIR Conference on Research
and Development in Information Retrieval*, 758–759.
https://doi.org/10.1145/1571941.1572114

Lord, F. M. (1980). *Applications of item response theory to practical
testing problems*. Lawrence Erlbaum Associates.

McNeish, D., & Wolf, M. G. (2020). Thinking twice about sum scores.
*Behavior Research Methods, 52*(6), 2287–2305.
https://doi.org/10.3758/s13428-020-01398-0

Robinson, W. S. (1950). Ecological correlations and the behavior of
individuals. *American Sociological Review, 15*(3), 351–357.
https://doi.org/10.2307/2087176
