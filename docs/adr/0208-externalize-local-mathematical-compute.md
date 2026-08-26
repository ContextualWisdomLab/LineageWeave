# ADR 0208 — Externalize local mathematical computation

**Decision status:** Accepted
**Date:** 2026-08-25
**Amends:** ADR 0003, ADR 0024, ADR 0064, ADR 0084, ADR 0132, ADR 0145,
ADR 0148, ADR 0167, ADR 0168, ADR 0182, ADR 0185, ADR 0200, ADR 0201, and
ADR 0205

## Context

LineageWeave's product boundary says that it reconstructs, authorizes,
persists, and presents evidence but does not own calibrated estimation. The
current exact head nevertheless contains Python implementations of IRT report
fitting and scoring, expected-information channel weights, residual SVD and
Gabriel coordinates, embedding cosine, graph random-walk ranking, score
normalization, and RRF contribution arithmetic. Calling a Rust-backed Python
package does not remove the local arithmetic that prepares, transforms, or
interprets its numerical result.

The ecosystem product boundaries are already sufficient:

- TEPP's approved PRD owns multilingual temporal and relational measurement,
  shared-latent topic identity, trajectories, uncertainty, and event lineage.
- fast-mlsirm's PRD owns reusable IRT/LSIRM estimation, prediction,
  diagnostics, recovery, multilevel and multiple-membership computation.
- RankWeave owns retrieval fusion, ranking, evaluation, comparison, and
  policy selection. Its calculation core must itself move behind a Rust
  CPU/GPU implementation before LineageWeave treats a new result as governed
  numerical evidence.

LineageWeave has no standalone canonical PRD file on this exact head. Until
one lands, `ARCHITECTURE.md` and the accepted ADR set are the product baseline;
this absence remains a product-documentation gap, not permission to infer a
different responsibility.

## Decision

1. **No new local numerical model.** LineageWeave adds no Python
   mathematical, statistical, psychometric, ranking, fusion, optimization,
   matrix-factorization, graph-centrality, or similarity implementation.
2. **Owner by construct.** TEPP owns temporal/topic/event/trajectory
   measurement. fast-mlsirm owns psychometric estimation, item information,
   expected responses, residual interaction maps, uncertainty, recovery, and
   multilevel/multiple-membership post importance. RankWeave owns retrieval
   fusion, ranking metrics, contribution evidence, comparisons, and policy
   selection. A construct is not moved merely to obtain a preferred language.
3. **Rust execution contract.** New or migrated owner computation executes in
   the owner's Rust core with GPU acceleration when supported and a
   deterministic multithreaded CPU path. Python may be a generated binding or
   transport adapter only; it may not reproduce a formula.
4. **Consumer-only LineageWeave.** This repository retains request/envelope
   validation, ABAC filtering, immutable input/output digests, run and model
   versions, knowledge cutoff, provenance persistence, and UI projection.
   Missing, malformed, non-converged, mixed-snapshot, or unsupported results
   fail closed. It never repairs, normalizes, estimates, or substitutes a
   numerical result.
5. **No big-bang rewrite.** Remaining local computation is frozen as named
   migration debt in
   `docs/doctoring/python-mathematical-compute-boundary-audit.md`. Each owner
   contract lands and proves recovery/equivalence before the corresponding
   LineageWeave implementation is deleted. Existing behavior is not relabeled
   as compliant while it remains local.
6. **Independent TEPP anchor.** Event-Lineage channel-weight activation keeps
   ADR 0205's exact TEPP anchor requirement. fast-mlsirm may estimate weights
   conditional on that accepted independent anchor; it does not manufacture
   the criterion.
7. **No heuristic exception.** Candidate windows, score floors, token overlap,
   string similarity, or equal weights are not promoted to measurement.
   Operational bounds may remain only as disclosed resource limits and may
   not determine a scientific score or ground truth.

## Implemented migration slices

- The backend dependency is immutably pinned to fast-mlsirm protected-main
  commit `09f762ded35786dd1078222a4577ff09d649816f`. The TEPP-specific contract
  proposed by closed, unmerged fast-mlsirm PR #1423 is not an owner contract
  and is not consumed. Channel-weight estimation remains unavailable until a
  domain-neutral owner contract lands; the legacy Python estimator remains
  frozen migration debt and MUST NOT activate calibrated weights. No customer
  projection exposes schema, transport, hash, TEPP, or fast-mlsirm internals.

- The residual interaction map consumes fast-mlsirm's protected-main
  `residual_interaction_map` and `polytomous_expected_response` contracts.
  Gabriel SVD, axis inertia, distance, reconstruction, unexplained residual,
  cross share, and coverage arithmetic were deleted from LineageWeave Python.
  Product-side identifier attachment and closest/farthest selection remain.
- Rankings call RankWeave's classic or convex-weighted RRF owner path and
  project its exact channel contributions. LineageWeave no longer evaluates
  the reciprocal-rank contribution formula. RankWeave's Rust CPU/GPU migration
  remains open, so this slice is owner-bound but not yet final execution-contract
  compliance.

## Stacked delivery order

1. Owner PRs publish versioned request/result schemas, model identity,
   convergence/uncertainty evidence, input digest, and deterministic recovery
   tests: TEPP first, fast-mlsirm second, RankWeave third.
2. A LineageWeave contract-only PR adds strict clients and provenance tables;
   no UI activates from an unpersisted envelope.
3. A shadow-validation PR compares owner outputs with frozen synthetic
   fixtures and records aggregate, non-identifying evidence.
4. Separate deletion PRs remove `channel_weight_estimation.py`, numerical
   portions of `period_report.py` and `leftover_pairs.py`, local cosine/RWR,
   and local ranking contribution/normalization code after their owner path is
   accepted.
5. The final PR removes NumPy/fast-mlsirm/RankWeave calculation imports from
   LineageWeave, updates architecture/PRD/ADRs, and makes the transition guard
   require an empty debt inventory.

## Consequences

The Dashboard may show TEPP topics and fast-mlsirm importance only from exact,
persisted owner artifacts. It can explain the source posts, memberships,
levels, time window, model version, uncertainty, and provenance, but cannot
recalculate or rank them locally. During migration, affected capabilities
remain explicitly legacy or unavailable rather than presenting local results
as Rust/GPU-backed.

## References (APA 7th)

Fox, J.-P., & Glas, C. A. W. (2001). Bayesian estimation of a multilevel item
response model using Gibbs sampling. *Psychometrika, 66*(2), 271–288.
https://doi.org/10.1007/BF02294839

Gabriel, K. R. (1971). The biplot graphic display of matrices with application
to principal component analysis. *Biometrika, 58*(3), 453–467.
https://doi.org/10.1093/biomet/58.3.453

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved
item-respondent interactions: A latent space item response model with
interaction map. *Psychometrika, 86*(2), 378–403.
https://doi.org/10.1007/s11336-021-09762-5

Roberts, M. E., Stewart, B. M., & Tingley, D. (2019). stm: An R package for
structural topic models. *Journal of Statistical Software, 91*(2), 1–40.
https://doi.org/10.18637/jss.v091.i02
