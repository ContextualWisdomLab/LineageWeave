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
3. LineageWeave does not infer a model family from a product domain, item label, or hand-authored mechanism flags. Model selection remains unavailable until an administrator explicitly binds a family to evidence from the intended use and the owning psychometric runtime validates the corresponding recovery contract.
4. Draft and pilot instruments may preserve observations without a latent scoring model. A published instrument must bind a model family and an activation-evidence reference. Insufficient evidence preserves observations without issuing a latent score.
5. This repository's policy contract performs no numerical estimation. fast-mlsirm owns reusable psychometric kernels and recovery diagnostics; TEPP owns temporal/event/multilevel measurement semantics; contextual-orchestrator owns all LLM model/provider routing and judge orchestration.

## Activation evidence

Operational scoring is fail-closed. The administrator must bind evidence appropriate to the intended use, including known-truth or controlled-data recovery, bias and MAE/RMSE, interval coverage, convergence, dimensionality/local dependence, linking/anchors, DIF/invariance, and judge-facet recovery when LLM raters are used. 3PLM additionally requires lower-asymptote recovery/identification evidence. 4PLM additionally requires lower- and upper-asymptote recovery/identification and boundary-behavior evidence.

## Consequences

- Existing ordinal observations are not mechanically dichotomized; they retain their existing versioned contract.
- Paired-comparison/ranking outcomes remain a separate Bradley-Terry/Thurstone-style dichotomous channel.
- LLM-as-a-Judge observations remain rater/method observations with provenance, never ground truth.
- The administrator workbench can build on a stable policy vocabulary without embedding estimation code or provider logic in LineageWeave.
- A future model-family change or activation rule change requires an explicit versioned policy/ADR update rather than a silent enum or UI relabel.

## Verification

`tests/test_measurement_policy.py` protects binary response semantics, missing/abstain separation, Rasch/2PLM/3PLM/4PLM identifiers, and fail-closed publication activation. `tests/test_ddd_architecture_fitness.py` separately rejects Rasch↔1PL shorthand in production runtime vocabulary.

## References (APA 7th)

American Educational Research Association, American Psychological
Association, & National Council on Measurement in Education. (2014).
*Standards for educational and psychological testing*. American
Educational Research Association.

Birnbaum, A. (1968). Some latent trait models and their use in inferring an
examinee's ability. In F. M. Lord & M. R. Novick, *Statistical theories of
mental test scores* (pp. 397–479). Addison-Wesley.

Lord, F. M. (1980). *Applications of item response theory to practical
testing problems*. Lawrence Erlbaum Associates.
