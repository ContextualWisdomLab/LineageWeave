# Python mathematical-compute boundary audit

**Exact-head audit date:** 2026-08-25  
**Normative decision:** [ADR 0208](../adr/0208-externalize-local-mathematical-compute.md)

This inventory names remaining migration debt and completed owner slices; it
does not relabel still-local Python paths as Rust/GPU compliant.

## Product-boundary sources read

- LineageWeave `ARCHITECTURE.md` and accepted ADRs 0003, 0132, 0145,
  0200, 0201, and 0205. This exact head has no standalone canonical PRD.
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
| `lineageweave/channel_weight_estimation.py` | dichotomization, synthetic simulation, MLS2PLM input construction, expected item information and normalization | fast-mlsirm, conditional on TEPP anchor | versioned anchored-weight artifact; strict digest/convergence validation | estimation scripts, seed/server/rebuild paths; `tests/test_channel_weight_estimation.py`, estimator-script tests |
| `lineageweave/period_report.py` | response matrix and owner-call orchestration remain; local category expectation and duplicate likelihood arithmetic removed | fast-mlsirm | `polytomous_expected_response`; diagnostics-owned held-out log likelihood; full period artifact remains debt | report ingestion and demo seed; period-report and report API tests |
| `lineageweave/leftover_pairs.py` | **migrated:** identifier projection and closest/farthest selection only | fast-mlsirm | protected-main Rust `residual_interaction_map` with residual, coverage, SVD/Gabriel coordinates, distances, reconstruction and shares | `period_report.py`, report ingestion/seed; owner contract and consumer projection tests |
| `lineageweave/embedding_client.py` and `backend/app/post_chat_ingestion.py` | cosine similarity, vector norms, maximum semantic score | RankWeave retrieval-score contract | ranked evidence envelope over ABAC-visible semantic units | reconstruction text channel and Global Ask retrieval; embedding/post-chat tests |
| `lineageweave/knowledge_graph.py` | random walk with restart, convergence delta, adaptive relevance cutoff | RankWeave graph-ranking contract | ranked-node artifact with contribution and convergence evidence | related-person/entity API paths; knowledge-graph tests |
| `lineageweave/reconstruct.py` | channel-weight renormalization, candidate-score fusion and minimum-score decision | RankWeave fusion; TEPP supplies independent lineage criterion | accepted edge-ranking artifact; LineageWeave persists selected edge and channel provenance | lineage rebuild/start/seed/server; reconstruct, persistence, API tests |
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

## Persistence and UI blast radius

Owner envelopes require normalized run/artifact tables keyed by analysis run,
owner contract version, model version, source snapshot SHA-256, knowledge
cutoff, and authorization scope. Topic, membership, level-specific importance,
uncertainty, and source-post evidence occupy separate child rows; arrays or
labels do not replace foreign keys. Dashboard and post detail endpoints read
only accepted persisted rows and preserve source-post ABAC. Storybook covers
accepted, pending, failed, stale-digest, non-converged, hidden-evidence, and
multiple-membership cases before UI activation.
