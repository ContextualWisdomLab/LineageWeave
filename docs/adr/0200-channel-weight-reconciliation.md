# ADR 0200 — Reconciling channel-weight measurement across the two active lines

**Decision status:** Accepted, point 3 superseded by [ADR 0205](0205-tepp-lineage-anchor.md)
**Date:** 2026-08-24
**Amends:** [ADR 0003](0003-fast-mlsirm-report-integration.md) (scope
boundary), both lines' ADR 0145 (each in part — see Context)
**Answers:** the main-line ADR 0145's "a future proposal must be
ADR-first" conditions, issue #289's durable-worker requirement, and the
operator's no-bulk-synchronous-LLM directive of 2026-08-24.

> Numbering note: `0200` is deliberately above every number in use on
> `main` (≤ 0167), on `docs/customer-master-scope-adr` (≤ 0145), and in
> any open PR (≤ 0185), so it cannot collide when the lines converge.

## Context

Two long-lived lines implemented "ADR 0145" with **opposite decisions**:

- `docs/customer-master-scope-adr` estimates convex fusion weights with
  fast-mlsirm's multilevel 2PL (channels = items, candidate pairs =
  respondents, reconstruction groups = cluster intercepts), deletes the
  hand-picked `DEFAULT_CHANNEL_WEIGHTS` outright, and fails product
  reconstruction closed (HTTP 503 with an estimate-first next action)
  whenever no persisted estimate matches the active channels. Weight
  sets are keyed by `channel_set_code` (migration 0136).
- `main` records ADR 0145 as a **Rejected proposal** ("Channel-weight
  estimation remains unavailable without an independent anchor"),
  authorizes zero anchor methods (`_SUPPORTED_ANCHOR_METHOD_CODES =
  frozenset()`, so its provenance-gated loader never activates a
  vector), stubs the operator estimation command to an unconditional
  refusal, and **retains the hand-picked constants "for
  compatibility"**. Its `lineage_channel_weight` schema carries per-run
  provenance columns instead of `channel_set_code`.

The same ADR number carrying contradictory decisions violates the
organization's exact-head consistency rule by itself. Beyond the
paperwork, the lines now diverge on the table schema, the loader
contract, the operator tooling, and — most importantly — on whether any
hand-picked constant may keep flowing through product reconstruction.

The operator's standing directive is explicit and repeated: **no
arbitrary weights anywhere; use weights estimated by a paper-grounded
psychometric model (fast-mlsirm or TEPP)**. The main line's retention of
uncalibrated constants "for compatibility" — however carefully labeled —
keeps exactly those arbitrary numbers in the product and cannot stand
under that directive.

At the same time, the main line's methodological critique of the first
estimation design is substantially correct and deserves engagement
rather than override:

1. **Criterion validity.** An unanchored IRT fit describes common
   response structure among the channels; it does not by itself prove
   that its latent factor is "these two posts are genuinely related."
2. **Conditional information.** Birnbaum's item information is
   `I_j(θ) = a_j² P_j(θ) Q_j(θ)` — conditional on trait location — so a
   weight proportional to the discrimination alone is not a globally
   information-optimal fusion rule (Birnbaum, 1968; Lord, 1980).
3. **Scope boundary.** Accepted ADR 0003 assigned this repository's
   fast-mlsirm integration to the LLM-judge/report path; the lineage
   weight path must expand that boundary explicitly, not silently.

Operational facts sharpened this cycle: three estimation runs against
the shared orchestrator died to transport-lifetime failures before one
completed; the 400-pair sequential judge workload measurably saturated
the shared gateway (a concurrent `/api/ask` round-trip reached 158 s),
after which the operator directed that bulk LLM work must use the
repository's durable queue idiom rather than blocking synchronous HTTP;
and the shared development database was rebuilt from `main`, wiping the
imported corpus and every persisted estimate. Sequential-blocking
estimation is architecturally dead independent of the measurement
argument.

## Decision

1. **The directive governs both lines.** No hand-picked fusion weight
   reaches any product path on any line. The scope line's fail-closed
   contract (refuse with an estimate-first next action) becomes the
   single product behavior; main's compatibility constants are retired.
   Cormack et al.'s (2009) parameter-free reciprocal rank fusion remains
   the Rankings surface's rule (no weights exist there to pick).
2. **Expected-information weights** replace discrimination-proportional
   weights, answering critique (2): the fusion weight of channel *j* is
   the normalized **expected item information over the fitted latent
   distribution**,
   `w_j ∝ E_θ[I_j(θ)] = ∫ a_j² P_j(θ) Q_j(θ) dF(θ)`,
   with `F(θ)` the fitted multilevel latent distribution (mixture over
   cluster intercepts). Integrating the conditionality instead of
   ignoring it is the standard device of optimal test-design practice
   (van der Linden, 2005). Method code:
   `mls2plm_expected_information`. Every fit must pass fast-mlsirm's
   official diagnostics; any non-converged fit is rejected outright
   (`convergence_status`, per the pinned contract).
3. **Superseded anchor transition**, answering critique (1): estimation originally activated, but
   every persisted set carries `anchor_method_code =
   'unanchored_internal_structure'` until an independent anchor exists,
   and provenance (method, estimator version, sample size, snapshot
   digest, knowledge cutoff) is surfaced wherever the set is disclosed.
   When TEPP reaches production, a criterion-validity gate correlates
   fused scores with TEPP's event measurement on a frozen snapshot; a
   set that fails the gate is retired and reconstruction fails closed
   again. ADR 0205 completed that gate: internally anchored vectors are now
   inactive and only an exact accepted, persisted TEPP criterion anchor may
   activate a vector.
4. **Schema merge.** `lineage_channel_weight` takes the union of both
   lines: primary key `(channel_set_code, channel_code)` from the scope
   line — one persisted set per active-channel combination — plus the
   main line's per-run provenance columns (`estimation_run_id`,
   `estimation_method_code`, `estimator_version`, `anchor_method_code`,
   `source_snapshot_sha256`, `sample_pair_count`, `knowledge_cutoff`).
   The loader requires an exact active-channel match AND single-run
   provenance integrity AND the sole authorized anchor method code
   (`tepp_lineage_criterion_v1`, per ADR 0205). One migration with rollbacks lands the
   union on whichever predecessor schema a database has.
5. **Queued judge scoring.** The llm channel's pair scoring moves to the
   repository's durable queue idiom (`post_content_queue` /
   `post_content_worker` family): the operator command samples pairs
   deterministically, persists the run identity and per-pair job rows,
   and publishes Valkey wake-ups; a bounded worker drains judge jobs at
   a governed rate through contextual-orchestrator and persists each
   pair's score durably as it lands. The fit runs only when a run's
   pairs are complete, so a killed process loses nothing and re-running
   resumes instead of re-spending provider calls. This satisfies the
   operator's no-bulk-synchronous-LLM directive and issue #289's
   bounded-durable-worker requirement in one design.
6. **Convergence sequencing.** This ADR lands verbatim on both lines;
   each line's ADR 0145 gains a superseded-in-part pointer to it.
   Implementation lands on `main` first (the shared development
   environment now runs the main line), and `docs/customer-master-scope-adr`
   rebases its weights stack onto the merged schema. Corpus re-import
   and a fresh expected-information estimation run follow on the merged
   head — in that order, since estimation samples the imported corpus.

## Consequences

**Positive.** One contract instead of two contradictory ones; the
operator directive holds everywhere; the estimator answers the
strongest published objection to its own first design; a killed
estimation run stops costing hours of provider spend; the shared
gateway is never again saturated by a scoring loop; and TEPP gains a
named, gated integration point instead of an implied one.

**Negative.** A schema migration on both predecessors; the llm channel
estimate waits for the queue worker to land; and until the TEPP gate
exists the activated weights remain honestly labeled as internally
anchored only — reviewers must weigh that label rather than a hard
criterion coefficient.

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

Fox, J.-P., & Glas, C. A. W. (2001). Bayesian estimation of a multilevel
IRT model using Gibbs sampling. *Psychometrika, 66*(2), 271–288.
https://doi.org/10.1007/BF02294839

Lord, F. M. (1980). *Applications of item response theory to practical
testing problems*. Lawrence Erlbaum Associates.

McNeish, D., & Wolf, M. G. (2020). Thinking twice about sum scores.
*Behavior Research Methods, 52*(6), 2287–2305.
https://doi.org/10.3758/s13428-020-01398-0

Robinson, W. S. (1950). Ecological correlations and the behavior of
individuals. *American Sociological Review, 15*(3), 351–357.
https://doi.org/10.2307/2087176

van der Linden, W. J. (2005). *Linear models for optimal test design*.
Springer. https://doi.org/10.1007/0-387-29054-0
