# ADR 0003 — fast-mlsirm integration for weekly/monthly PU/team/project reports

**Decision status:** Accepted (scope for the first slice only; the full
report pipeline is deliberately staged across multiple PRs)
**Date:** 2026-08-13

## Context

The product brief asks for automatically-published weekly/monthly
reports per PU/team/project, built on genuinely calibrated post-quality
metrics rather than an invented score: RAGAS/LLM-as-a-Judge evaluation
of posts, multidimensional/multilevel/multiple-membership IRT modeling
(atomistic-fallacy avoidance, per this org's standing development
rules), and Fixed-Item Parameter Calibration / CAT-style linking so
scores stay comparable across reporting periods. The brief explicitly
names `ContextualWisdomLab/fast-mlsirm` as the tool to use, with PRs
back into it if it is missing something.

`fast-mlsirm`'s own README (checked directly, not assumed) already
implements almost exactly this contract:

- `LLMJudgeResult.to_irt_row()` -- an LLM-as-a-Judge result becomes one
  IRT response-matrix row only through this method, after
  `validate_irt_response_matrix()` accepts the assembled matrix (a
  multi-item dichotomous or explicitly-categorized polytomous matrix).
  This is a **provider-neutral contextual-orchestrator integration** --
  the same orchestrator this repo already depends on for every other
  LLM channel.
- `fixed_item_calibration_diagnostics()` / fixed-item linking / CAT
  item-information selection -- the Fixed-Item Parameter Calibration
  and Computer-Assisted-Testing techniques the brief names by name.
- Multigroup and multilevel-context fit summaries from person-level
  group/cluster IDs -- the multilevel/multiple-membership modeling the
  org's standing rules require to avoid atomistic fallacy.
- Its own ADRs (0005 IRT response-matrix contract, 0006 polytomous
  LLM-judge bias calibration, 0008 fast-judge review hardening,
  referenced from its README) already document exactly the same
  missing-vs-fabricated-score discipline this repo's other pluggable
  channels keep (`NullXClient` never invents a result).

This means the correct move is **reuse, not reimplementation** --
building a second LLM-as-Judge-to-IRT-row pipeline inside LineageWeave
when `fast-mlsirm` already has one, reviewed and ADR'd on its own
terms, would be exactly the kind of duplication this org's ecosystem
rules warn against ("소프트웨어 간 연계를 고려하고... Ecosystem을
만드세요").

One real constraint changes the integration shape: `fast-mlsirm` ships
a Rust-backed fitting core built via PyO3/maturin (`fast_mlsirm._core`,
with a NumPy fallback only for parity testing, not for production
correctness). `requirements: cargo test --workspace` in its own README
confirms a working Rust toolchain is required to build it from source
(no PyPI wheel exists yet, matching `rankweave`'s current git-dependency
pattern in this repo's `pyproject.toml`). LineageWeave's own org rule
already requires Rust for psychometrics compute layers ("수리과학 및
Psychometrics 소프트웨어의 연산 레이어는 무조건 Rust") -- `fast-mlsirm`
already satisfies that rule; LineageWeave does not need its own Rust
layer, it needs a Rust *toolchain* in the backend's build image to
compile the dependency.

## Decision

This PR is the ADR only -- no dependency, no Dockerfile change, no
product behavior. Integrate `fast-mlsirm` as a pinned git dependency
in later slices (mirroring `rankweave`'s existing pattern), and stage
the full report pipeline across independently-mergeable PRs rather
than one large PR:

1. **Infra slice** (next PR, not this one): add the pinned git
   dependency, add a Rust toolchain to `backend/Dockerfile`'s build
   stage, and prove the import actually works in the built image -- no
   product behavior yet.
2. **Evaluation slice**: a pluggable `PostEvaluationClient` (same
   `Null`/`ContextualOrchestrator` discipline as every other channel in
   this repo) that produces a structured judge result per post against
   a small, versioned rubric (general positive/negative sentiment +
   one or two industry/sales-lead-relevant criteria, per the brief's
   "범용 Factor와 특화 Factor" split), persisted through
   `LLMJudgeResult.to_irt_row()` into a new 3NF table
   (`post_evaluation_response`, one row per post per criterion,
   `common_lookup_value`-backed criterion codes).
3. **Calibration/report slice** (shipped in 0.28.0): `fixed_item_calibration_diagnostics()`
   run per PU/team/project grouping to produce a fitted period score,
   persisted to a `report_period_score` table, and a
   `GET /api/reports/{grouping}/{period}` endpoint + frontend view
   that renders the actual computed numbers -- never a placeholder
   or invented figure.
4. **Cross-period FIPC slice** (shipped in 0.29.0): persist the
   free-calibrated item bank (`report_item_parameter`) and EAP-score
   later weeks on those fixed parameters so thetas are comparable
   across weeks. Independent per-week refits stay available only as
   the first-period reference.
5. **Shared-metric slice** (shipped in 0.31.0): free-calibrate one
   item bank on the pooled first-period posts (`shared_metric` /
   `all`) and FIPC-score every process unit, corporate entity, and
   thread group on that bank so PU/team/project thetas are comparable.
   Independent per-group refits stay available only as a diagnostic.
6. **CAT item-information slice** (shipped in 0.32.0): rank the shared
   bank's items by Fisher information at each group's mean θ via
   `information_polytomous` (Lord, 1980 max-info). Persist the ranking
   (`report_item_information`) and show the rank-1 item on the Period
   reports panel. Do not reimplement an information function here.
7. **Leftover-pair slice** (shipped in 0.71.2; ADR 0017 / 0018 / 0048 /
   0049): after IRT main effects, persist closest and farthest
   post–criterion pairs from the residual leftover map. Consume fast-mlsirm's
   Rust-backed residual interaction-map contract and keep only identifier
   mapping, authorization, persistence, and pair selection here (ADR 0211).
   Category probabilities and expected responses must use `fast-mlsirm`'s
   public Rust-backed prediction API (upstream PR #1279); LineageWeave must
   not reproduce GRM/GPCM parameter conventions locally.
8. **Leftover evidence extensions:** unexplained leftover shipped in 2.12.26
   (ADR 0182), cross-share evidence shipped in 2.12.29 (ADR 0185), and
   reconstruction evidence is Unreleased for 2.12.31 (ADR 0201). Do not
   persist explained share, unexplained share, or another unsupported alias.
9. **Leftover-map axis-share slice** (ADR 0148): persist Gabriel inertia
   `σ_k² / Σ_j σ_j²` of leftover-map axes 1 and 2 on the same residual
   SVD. Rank-0 residuals emit two zero-share axes. Do not invent a
   leftover score.

**TEPP boundary.** [ARCHITECTURE.md](../../ARCHITECTURE.md) already
assigns calibrated temporal/event measurement to
[TEPP](https://github.com/ContextualWisdomLab/TEPP); this repo wires
TEPP's published `AnalysisRunRequest` contract
(`lineageweave/tepp_client.py`) and must not reimplement TEPP's model.
`fast-mlsirm` is the IRT compute library the brief names for
LLM-judge-to-score calibration -- not a second TEPP, and not a fork
of TEPP's temporal engine. If TEPP later exposes a live report
endpoint that covers this surface, consume it through `tepp_client`
rather than growing a parallel measurement engine here.

Each slice ships with the same real-verification discipline already
established in this repo: real LLM calls through contextual-orchestrator
for the judge step, and `fast-mlsirm`'s own `recovery_report`/
`fit_diagnostics` machinery (not a hand-rolled metric) proving the
fitted parameters behave sanely against the true generative structure
where a synthetic ground truth is available for the test itself.

## Rationale

- Ponytail: `fast-mlsirm` already exists, is already ADR'd, and already
  implements the exact contract the brief names by name -- reuse is the
  correct rung of the ladder, not a fresh implementation.
- Staging avoids a single unreviewable PR spanning a new Rust build
  dependency, a new pluggable LLM channel, a new 3NF schema, a
  calibration step, and a new report UI -- each slice is independently
  testable and mergeable, matching this repo's PR-review-merge-loop
  discipline under the confirmed-active parallel-process risk (small
  PRs rebase cleanly; one giant PR does not).
- Infra-first ordering (Rust toolchain proven before any product code
  depends on it) means slice 2 never merges against a backend image
  that can't actually build the dependency it imports.

## Consequences

- `backend/Dockerfile`'s build stage grows a Rust toolchain install
  step, increasing image build time -- justified because it is required
  for a dependency this org's own rules already mandate a Rust
  psychometrics layer for; not merely an optional convenience.
- No product-visible behavior change ships in the infra-first PR;
  buyer-perceptible payoff lands with slice 2 and slice 3.
- If `fast-mlsirm` is missing something this integration needs (e.g. a
  specific multilevel grouping shape LineageWeave's schema doesn't map
  onto directly), the brief's own instruction is to PR it back into
  `fast-mlsirm` rather than route around it inside LineageWeave.
- This ADR does not change `tepp_client.py`. Temporal/event
  measurement stays TEPP's job; IRT calibration of LLM-judge post
  scores is the only new compute this path adds, and it goes through
  `fast-mlsirm`.

## Related

Complements [ADR 0001](0001-demo-identity-and-data-boundary.md) (real
infrastructure, synthetic content -- report scores are computed from
real LLM judge calls over synthetic demo posts, never fabricated),
this repo's existing pluggable-client discipline
(`lineageweave/post_summary.py`, `lineageweave/keyman_extraction.py`),
and `lineageweave/tepp_client.py` (TEPP's published wire contract --
wire TEPP, do not fork it).

## References

Lord, F. M. (1980). *Applications of item response theory to practical
testing problems*. Erlbaum.

Muraki, E. (1993). Information functions of the generalized partial
credit model. *Applied Psychological Measurement, 17*(4), 351–363.
https://doi.org/10.1177/014662169301700403

Bock, R. D., & Mislevy, R. J. (1982). Adaptive EAP estimation of
ability in a microcomputer environment. *Applied Psychological
Measurement, 6*(4), 431–444. https://doi.org/10.1177/014662168200600405

Dempster, A. P., Laird, N. M., & Rubin, D. B. (1977). Maximum
likelihood from incomplete data via the EM algorithm. *Journal of the
Royal Statistical Society: Series B (Methodological), 39*(1), 1–22.
https://doi.org/10.1111/j.2517-6161.1977.tb01600.x

Muraki, E. (1992). A generalized partial credit model: Application of
an EM algorithm. *Applied Psychological Measurement, 16*(2), 159–176.
https://doi.org/10.1177/014662169201600206

Samejima, F. (1969). Estimation of latent ability using a response
pattern of graded scores. *Psychometrika, 34*(S1), 1–97.
https://doi.org/10.1007/BF03372160
