# ADR 0145 — Channel-weight estimation remains unavailable without an independent anchor

**Decision status:** Rejected proposal
**Date:** 2026-08-23
**Reconciles with:** [ADR 0003](0003-fast-mlsirm-report-integration.md)
**Implemented activation boundary:** [ADR 0205](0205-tepp-lineage-anchor.md)

## Context

`lineageweave.reconstruct` currently uses hand-picked convex weights for its
temporal, secondary-key, text-similarity, and optional LLM channels. Those
constants are an explicitly ungrounded historical fallback; a citation does
not turn them into calibrated measurement.

The rejected proposal treated channels as 2PL items, candidate pairs as
respondents, and normalized item discriminations as fusion weights. That does
not establish the product construct. An unanchored IRT fit can describe common
response structure, but it provides no independent evidence that its latent
factor is “these posts are genuinely related.” Birnbaum's 2PL item information
is also conditional on trait location and item difficulty,
`I_j(theta) = a_j^2 P_j(theta) (1 - P_j(theta))`; it is not a global constant
proportional only to `a_j`. Normalizing discriminations therefore is not an
information-optimal convex fusion rule.

The official pinned `fast-mlsirm` contract makes two further boundaries
explicit: `factor_id` assigns items to latent dimensions, while `cluster_id`
represents respondent nesting; and a `FitResult` exposes
`convergence_status` plus package diagnostics that callers must inspect. Those
contracts can validate a fit's execution, but cannot supply the missing
criterion validity.

Accepted ADR 0003 assigns temporal/event measurement to TEPP and limits this
repository's fast-mlsirm integration to the approved LLM-judge/report path.
This proposed lineage-weight path cannot silently expand that boundary.

## Decision

1. **No unanchored estimate.** LineageWeave does not run the proposed
   candidate-pair IRT fit and does not persist or activate weights from it.
   Estimation reports unavailable until an independent lineage anchor and its
   upstream contract exist.
2. **No scientific claim for fallback constants.** Existing constants remain
   unchanged for compatibility, but are neither calibrated nor
   paper-grounded. This ADR does not promote them to measurement evidence.
3. **A future proposal must be ADR-first.** It must amend ADR 0003, identify an
   independent outcome/anchor (for example, an accepted TEPP contract rather
   than a local proxy), use official fast-mlsirm diagnostics, reject every
   non-converged fit, and prove criterion validity before product activation.
4. **Future persisted vectors must be self-consistent and reproducible.** The
   schema requires a known channel vocabulary, finite positive weights, an
   exact sum of one at runtime, one estimation run identity, estimator and
   anchor method versions, sample size, immutable source-snapshot digest, and
   knowledge cutoff. Current code has no supported anchor method and therefore
   loads no vector.
5. **Grouping repair is independent of measurement.** Source row identifiers
   that were mapped as grouping values are normalized only in derived
   reconstruction fields. Their caller-mapped raw values remain preserved in
   separate source-provenance columns across backfill and re-import.

## Consequences

- `scripts/estimate_channel_weights.py` exits without writing because no
  scientifically authorized anchor exists.
- Missing migration 0135 remains a normal rollout state and is detected via a
  non-error PostgreSQL catalog probe, so an outer rebuild transaction is not
  aborted.
- The persistence contract is fail-closed: malformed, mixed-provenance, or
  unsupported-anchor rows are ignored rather than renormalized or repaired.
- Parameter-recovery tests cannot substitute for criterion validity; they may
  return only with a future accepted anchored estimator.

## References

Birnbaum, A. (1968). Some latent trait models and their use in inferring an
examinee's ability. In F. M. Lord & M. R. Novick, *Statistical theories of
mental test scores* (pp. 397–479). Addison-Wesley.

Fox, J.-P., & Glas, C. A. W. (2001). Bayesian estimation of a multilevel IRT
model using Gibbs sampling. *Psychometrika, 66*(2), 271–288.
https://doi.org/10.1007/BF02294839

McNeish, D., & Wolf, M. G. (2020). Thinking twice about sum scores.
*Behavior Research Methods, 52*(6), 2287–2305.
https://doi.org/10.3758/s13428-020-01398-0

ContextualWisdomLab. (2026). *fast-mlsirm*, pinned LineageWeave dependency
contract at commit `5006c38286a4fa1d81bcf57eeed5ce27ae743f50`.
https://github.com/ContextualWisdomLab/fast-mlsirm/tree/5006c38286a4fa1d81bcf57eeed5ce27ae743f50
