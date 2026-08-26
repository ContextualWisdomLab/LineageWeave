# Python mathematical-compute boundary audit

**Exact-head audit date:** 2026-08-25  
**Normative decision:** [ADR 0208](../adr/0208-externalize-local-mathematical-compute.md)

This inventory names migration debt; it is not evidence that the current
Python paths satisfy the Rust/GPU requirement.

## Product-boundary sources read

- LineageWeave `docs/product-requirements.md`, `ARCHITECTURE.md`, and accepted
  ADRs 0003, 0132, 0145, 0200, 0201, 0205, 0208, and 0245. The PRD is a
  supporting product contract and ADRs remain normative.
- TEPP `docs/product/prd-v0.4-approved.md`, whose approved TRSL-TM scope
  owns temporal, relational, multilingual, topic, event, and trajectory
  measurement.
- fast-mlsirm `docs/PRD.md`, whose reusable library scope owns
  multilevel/contextual/longitudinal psychometric estimation, diagnostics,
  recovery, and versioned artifacts rather than hosted product storage.
- RankWeave `README.md` and `ARCHITECTURE.md`. Its exact head has no PRD;
  those files define the current fusion/ranking/evaluation responsibility.
  A canonical RankWeave PRD is required before expanding that contract.

| Current LineageWeave path | Local computation | Owner | Consumer replacement | Principal callers / tests |
|---|---|---|---|---|
| `lineageweave/channels.py` | inverse elapsed-day scoring, numeric secondary-key scoring, and `SequenceMatcher` label similarity | TEPP for calibrated temporal/event criterion evidence; RankWeave for Rust-backed similarity/ranking only after an accepted owner API | ADR 0245 Event-Lineage owner envelope; no local score fallback | `lineageweave/reconstruct.py`, estimation script; `tests/test_channels.py` |
| `lineageweave/channel_weight_estimation.py` | dichotomization, synthetic simulation, MLS2PLM input construction, expected item information and normalization | fast-mlsirm, conditional on TEPP anchor | versioned anchored-weight artifact; strict digest/convergence validation | estimation scripts, seed/server/rebuild paths; `tests/test_channel_weight_estimation.py`, estimator-script tests |
| `lineageweave/period_report.py` | response matrix, GRM/GPCM fit/FIPC/EAP, likelihood, category expectation, information ordering | fast-mlsirm | period-measurement artifact with item bank, scores, uncertainty, diagnostics | report ingestion and demo seed; period-report and report API tests |
| `lineageweave/leftover_pairs.py` | residual matrix, complete-case selection, SVD/Gabriel coordinates, distances, reconstruction, axis shares | fast-mlsirm | residual-interaction artifact with observed/expected identity and coverage | `period_report.py`, report ingestion/seed; `tests/test_leftover_pairs.py`, report tests |
| `lineageweave/embedding_client.py` and `backend/app/post_chat_ingestion.py` | cosine similarity, vector norms, maximum semantic score | RankWeave retrieval-score contract | ranked evidence envelope over ABAC-visible semantic units | reconstruction text channel and Global Ask retrieval; embedding/post-chat tests |
| `lineageweave/knowledge_graph.py` | random walk with restart, convergence delta, adaptive relevance cutoff | RankWeave graph-ranking contract | ranked-node artifact with contribution and convergence evidence | related-person/entity API paths; knowledge-graph tests |
| `lineageweave/reconstruct.py` | channel-weight renormalization, candidate-score fusion and minimum-score decision | RankWeave fusion; TEPP supplies independent lineage criterion | accepted edge-ranking artifact; LineageWeave persists selected edge and channel provenance | lineage rebuild/start/seed/server; reconstruct, persistence, API tests |
| `lineageweave/corporate_hierarchy_resolution.py` | fixed legal-suffix deletion, `SequenceMatcher` candidate score, and fixed catalog-binding threshold | unassigned; no ecosystem PRD/API currently accepts corporate-master entity resolution | ADR 0245 corporate-entity resolution envelope; remain unbound when unavailable | corporate/team/Keyman/entity-relationship ingestion; corporate resolution and tie tests |
| `lineageweave/rankweave_client.py` | channel construction, token overlap, RRF weights and contribution arithmetic | RankWeave | strict ranking artifact exposing owner-computed contributions | `/api/rankings`, frontend Rankings; `tests/test_rankweave_client.py` and frontend tests |

`lineageweave/post_evaluation.py` imports fast-mlsirm only for its published
judge contract and `to_irt_row` projection. It performs no fitted numerical
estimation, but remains in the transition guard because any direct owner-package
import must be reviewed before LineageWeave's final wire-only state.

Validation-only uses of `math.isfinite` and database aggregation are not model
ownership and remain. Date ordering, counts, pagination, authorization, schema
validation, and presentation formatting also remain LineageWeave concerns.

## Required owner contracts

- **TEPP:** temporal-relational topic identity and Event-Lineage criterion
  artifacts, with snapshot/cutoff, posterior uncertainty, evidence status,
  lineage transitions, and deterministic Rust CPU/GPU execution evidence.
- **fast-mlsirm:** anchored channel information; GRM/GPCM fit, score and item
  information; Gabriel residual interaction map; and topic-conditional
  multiple-membership multilevel importance for business unit, PU, team, and
  person, with recovery/RMSE and coverage evidence.
- **RankWeave:** Rust-backed similarity, graph ranking, fusion, contribution,
  evaluation, and policy-selection artifacts. Its present Python calculation
  core is the correct product owner but not the final execution architecture.
- **Corporate entity resolution:** no owner is designated. A repository must
  explicitly accept this product responsibility and ADR 0245's versioned
  unique/miss/tie envelope before LineageWeave can replace the current local
  candidate scorer. Neither contextual-orchestrator nor Keyverse acquires this
  responsibility implicitly.

## Persistence and UI blast radius

Owner envelopes require normalized run/artifact tables keyed by analysis run,
owner contract version, model version, source snapshot SHA-256, knowledge
cutoff, and authorization scope. Topic, membership, level-specific importance,
uncertainty, and source-post evidence occupy separate child rows; arrays or
labels do not replace foreign keys. Dashboard and post detail endpoints read
only accepted persisted rows and preserve source-post ABAC. Storybook covers
accepted, pending, failed, stale-digest, non-converged, hidden-evidence, and
multiple-membership cases before UI activation.
