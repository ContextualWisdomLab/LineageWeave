# ADR 0301: Govern dichotomous measurement policy at the LineageWeave boundary

- Status: Proposed
- Date: 2026-09-01
- Depends on: ADR 0300 (`contextual-orchestrator` ownership boundary)

## Context

LineageWeave owns instrument, rubric, evidence-binding, pilot lifecycle, and buyer-facing interpretation policy. It does not own reusable psychometric numerical estimation or model-provider orchestration. New importance/significance/actionability/evidence-style instruments need a versioned observation contract before an administrator can pilot or publish them.

Collapsing missingness or adjudication into a numeric response corrupts the measurement channel. Collapsing Rasch into a generic one-parameter logistic label also erases the model's measurement-theoretic requirements. Conversely, choosing 3PLM or 4PLM merely because they fit better statistically over-parameterizes the instrument without a substantive asymptote mechanism or recovery evidence.

## Decision

1. New evaluative instruments use dichotomous observations by default. `0` means the versioned not-supported criterion is met; `1` means the versioned supported criterion is met. Missing, not-observable, abstain, invalid-evidence, and adjudication-required states remain outside the binary response.
2. The normal production model-family identifiers are `rasch`, `irt_2plm`, `irt_3plm`, and `irt_4plm`. Rasch is not an alias for generic 1PL logistic IRT. Generic `irt_1pl_logistic` is not exposed without a future superseding scientific ADR.
3. Educational measurement selects Rasch only when Rasch requirements are intended. A 3PLM is eligible only when a lower-asymptote/guessing mechanism is substantively justified. If neither is defensible, model selection fails closed.
4. Psychology/SEM-lineage dichotomous measurement defaults to 2PLM when item discrimination may vary.
5. Gambling/gaming-risk or analogous use may select 4PLM only when both lower- and upper-asymptote mechanisms are substantively justified and identifiable. Better likelihood alone is insufficient.
6. Draft and pilot instruments may preserve observations without a latent scoring model. A published instrument must bind a model family and an activation-evidence reference. Insufficient evidence preserves observations without issuing a latent score.
7. This repository's policy contract performs no numerical estimation. fast-mlsirm owns reusable psychometric kernels and recovery diagnostics; TEPP owns temporal/event/multilevel measurement semantics; contextual-orchestrator owns all LLM model/provider routing and judge orchestration.

## Activation evidence

Operational scoring is fail-closed. The administrator must bind evidence appropriate to the intended use, including known-truth or controlled-data recovery, bias and MAE/RMSE, interval coverage, convergence, dimensionality/local dependence, linking/anchors, DIF/invariance, and judge-facet recovery when LLM raters are used. 3PLM additionally requires lower-asymptote recovery/identification evidence. 4PLM additionally requires lower- and upper-asymptote recovery/identification and boundary-behavior evidence.

## Consequences

- Existing ordinal observations are not mechanically dichotomized; they retain their existing versioned contract.
- Paired-comparison/ranking outcomes remain a separate Bradley-Terry/Thurstone-style dichotomous channel.
- LLM-as-a-Judge observations remain rater/method observations with provenance, never ground truth.
- The administrator workbench can build on a stable policy vocabulary without embedding estimation code or provider logic in LineageWeave.
- A future model-family change or activation rule change requires an explicit versioned policy/ADR update rather than a silent enum or UI relabel.

## Verification

`tests/test_measurement_policy.py` protects binary response semantics, missing/abstain separation, Rasch/2PLM/3PLM/4PLM identifiers, domain-default rules, and fail-closed publication activation. `tests/test_ddd_architecture_fitness.py` separately rejects Rasch↔1PL shorthand in production runtime vocabulary.
