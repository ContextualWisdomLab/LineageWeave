# LineageWeave Ubiquitous Language

These terms are the product/domain vocabulary for code, schemas, API contracts, tests, UI, and current architecture documents. Historical documents keep their original wording as evidence; new work uses the terms below unless a superseding ADR changes the domain model.

## Measurement policy and administration

**Instrument**  
A governed collection of items, instructions, evidence rules, response semantics, scoring policy, and intended interpretation for a defined use. An instrument is not interchangeable with one fitted model.

**Instrument Version**  
An immutable published measurement contract. Draft and pilot revisions may change; a published version is never silently rewritten.

**Item**  
One governed evaluative prompt/criterion with an explicit response contract and evidence rule. An item is not an LLM prompt implementation.

**Rubric**  
A versioned rule describing what evidence supports each admissible observation. For a dichotomous item, `0` and `1` mean criterion not-supported/supported under the rubric; they are not compressed ordinal scores.

**Evidence Rule**  
The admissibility rule connecting source evidence to an item response. It specifies required evidence and invalidating conditions before scoring.

**Observation**  
A recorded response produced under a known instrument version and judging/measurement condition. Missing, not-observable, abstain, invalid-evidence, and unresolved-adjudication states are not coerced into an observed category.

**Dichotomous Observation**  
A binary `0`/`1` observation under an explicit criterion. New importance, significance, actionability, evidence, decision, and related evaluative indicators use this as the default unless empirical evidence and an accepted ADR justify a polytomous contract.

**Ordinal Observation**  
A response with ordered categories under its own versioned contract. Historical/shipped ordinal observations are preserved as ordinal and are not mechanically dichotomized.

**Paired-Comparison Observation**  
A separate dichotomous comparison/ranking channel in which one alternative is preferred over another. Its Bradley-Terry/Thurstone-style semantics must not be conflated with a binary item response.

**Pilot**  
A non-operational instrument state in which observations may be collected for simulation, recovery, calibration, dimensionality, local-dependence, linking, DIF/invariance, rater-facet, and external-validity evidence. Pilot output is not a production score merely because a model converges.

**Activation**  
The governed transition from pilot to operational scoring after the instrument's declared evidence criteria are satisfied. Activation is fail-closed: insufficient evidence preserves observations without issuing a latent score.

## Model families

**Rasch**  
A Rasch-family measurement model with its own measurement-theoretic requirements, including the intended invariance/specific-objectivity interpretation, common discrimination as part of the model, targeting, and Rasch-specific fit expectations. `rasch` is never an alias, label, or shorthand for generic one-parameter logistic IRT.

**2PLM (`irt_2plm`)**  
A logistic IRT family allowing item discrimination to vary. It is the default logistic IRT candidate for psychology/SEM-lineage measurement when varying discrimination is substantively allowed.

**3PLM (`irt_3plm`)**  
A dichotomous IRT family with a lower asymptote. It is considered only when a substantive lower-asymptote/guessing mechanism is justified and identifiable; better likelihood alone is insufficient.

**4PLM (`irt_4plm`)**  
A dichotomous IRT family with lower and upper asymptotes. It is considered where both mechanisms are theoretically meaningful and recoverable, including gambling/gaming-risk or analogous domains when supported by evidence; better likelihood alone is insufficient.

**Generic 1PL Logistic IRT**  
Not a normal production model choice in this ecosystem. It must not be exposed as `Rasch`, `Rasch/1PL`, or `Rasch (1PL)`. A future use requires an explicit scientific ADR and a distinct identifier such as `irt_1pl_logistic`.

**Measurement Model Family**  
The versioned scientific family selected for scoring. The family identifier is distinct from a judge policy, provider/model identity, item rubric, and fitted parameter artifact.

## LLM-as-rater vocabulary

**Judge Observation**  
A fallible observation returned through contextual-orchestrator under a versioned judging policy. It is never ground truth simply because one or several models agree.

**Judge Policy**  
The LineageWeave-facing reference to a contextual-orchestrator orchestration/prompt policy used to obtain judge observations. Provider routing, model discovery, fallback, role allocation, and credentials are not part of the LineageWeave policy implementation.

**Judge Facet**  
A reproducible judging condition that may affect observations: judge model, provider observation identity/provenance, prompt/policy revision, language, occasion, agent role, and other declared method conditions. Scientifically material facets are retained for severity/leniency, interaction, repeatability, calibration, and DIF/invariance analysis.

**Adjudication**  
The governed use of evidence and one or more fallible observations to support a product decision. Adjudication is not synonymous with accepting an LLM answer.

**Disagreement**  
A reproducible difference among judge observations or between judge and independent criterion evidence. Disagreement is retained/analyzed; it is not automatically resolved by majority vote.

## Evidence, provenance, and interpretation

**Source Evidence**  
The authorized source material bound to an item, lineage decision, claim, or interpretation. Source evidence is distinct from a generated explanation.

**Evidence Binding**  
The immutable/auditable link between a product observation or interpretation and the authorized source evidence that justified it at a known revision/cutoff.

**Provenance**  
The identities and versions needed to reproduce or audit an observation/result: source revision, instrument/rubric version, judge policy and scientifically material judge facets, owner-service result/model version, timestamps/occasion, and applicable processing receipts.

**Scientific Result**  
A versioned result returned by the canonical computation owner, such as fast-mlsirm or TEPP, together with the diagnostics/evidence required by its contract. LineageWeave stores/projects it but does not privately refit the same reusable model.

**Interpretation**  
A buyer-facing meaning assigned to validated evidence/results within the instrument's intended-use boundary. Interpretation must distinguish observed evidence, model estimates, uncertainty, pilot status, and generated explanation.

## Ownership terms

**Consumer Contract**  
A published versioned package/API/event schema through which LineageWeave consumes another bounded context. Internal modules, provider SDKs, private tables, or copied source are not consumer contracts.

**Anti-Corruption Layer (ACL)**  
A LineageWeave adapter that translates between this domain's concepts and a foreign bounded context without importing that context's internal model. Model-backed adapters target contextual-orchestrator; temporal/multilevel adapters target TEPP; reusable psychometric numerics target fast-mlsirm.

**Canonical Owner**  
The CWL repository/bounded context with stable responsibility for a reusable capability. Duplicate production implementations in LineageWeave are migration defects even when they are convenient.

**Fail-Closed**  
When required evidence, owner service, authorization, measurement validity, or contract verification is unavailable, the product reports an unavailable/unscored state rather than manufacturing a response, estimate, fallback provider call, or placeholder success.
