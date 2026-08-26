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
| `lineageweave/embedding_client.py` and `backend/app/post_chat_ingestion.py` | cosine similarity, vector norms, maximum semantic score | Future Rust retrieval-scoring owner is unassigned; RankWeave owns the current Python fusion/evaluation contract only | ranked evidence envelope over ABAC-visible semantic units | reconstruction text channel and Global Ask retrieval; embedding/post-chat tests |
| `lineageweave/knowledge_graph.py` | random walk with restart, convergence delta, adaptive relevance cutoff | Future Rust graph-ranking owner is unassigned; RankWeave's current contract does not prove this migration | ranked-node artifact with contribution and convergence evidence | related-person/entity API paths; knowledge-graph tests |
| `lineageweave/reconstruct.py` | channel-weight renormalization, candidate-score fusion and minimum-score decision | RankWeave fusion; TEPP supplies independent lineage criterion | accepted edge-ranking artifact; LineageWeave persists selected edge and channel provenance | lineage rebuild/start/seed/server; reconstruct, persistence, API tests |
| `lineageweave/rankweave_client.py` | channel construction and token overlap remain; **owner-bound:** classic/weighted RRF and contribution arithmetic now come from RankWeave #47, whose Python core still awaits the required Rust CPU/GPU migration | RankWeave | Rust-backed strict ranking artifact exposing owner-computed contributions and owned channel construction | `/api/rankings`, frontend Rankings; `tests/test_rankweave_client.py` and frontend tests |

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
- **RankWeave:** current dependency-free Python retrieval fusion, evaluation,
  comparison, and audit artifacts. A future Rust vector/graph-scoring contract
  is migration evidence that still needs an accepted owner; this audit does not
  call the current RankWeave package a Rust owner or require it to adopt MLX.

## Persistence and UI blast radius

Owner envelopes require normalized run/artifact tables keyed by analysis run,
owner contract version, model version, source snapshot SHA-256, knowledge
cutoff, and authorization scope. Topic, membership, level-specific importance,
uncertainty, and source-post evidence occupy separate child rows; arrays or
labels do not replace foreign keys. Dashboard and post detail endpoints read
only accepted persisted rows and preserve source-post ABAC. Storybook covers
accepted, pending, failed, stale-digest, non-converged, hidden-evidence, and
multiple-membership cases before UI activation.

## 2026-08-26 stacked-PR audit

The exact reviewed heads were PR #692 `583059edcffe994b18a6fbf3cb3b00bf4647c2a3`,
PR #693 `776eee91e8401df15f86bd60a7448136d4e642c0`, and PR #694
`7086455e4f8f011ee37710dc3b64c886d894a322`. The review used CodeGraph before
diff inspection.

- PR #692 adds evidence-span normalization, unique/miss/tie catalog binding,
  persistence, and projection. It adds no statistical score, vector algebra,
  fitted weight, or local model.
- PR #693's Python code validates vector shape and finiteness, serializes the
  exact UTF-8 request body, and chooses a prefix under an upstream-advertised
  byte ceiling. Those are transport and schema-validation operations allowed
  by ADR 0208, not token estimation or vector scoring. Tokenization, token
  ranges, provider-limit packing, checked token totals, and shard construction
  are owned by contextual-orchestrator's Rust/PyO3 extension pinned by the
  Docker build. The owner follow-up PR #863 fails closed at an undecodable
  token ceiling and preserves complete UTF-8 scalars when a nominal token
  boundary divides their byte representation.
- PR #694 delegates overlap counts and the shared eligible denominator to one
  authorization-filtered SQL aggregate. Converting those returned counts to a
  displayed percentage is presentation formatting, explicitly outside the
  model-ownership inventory. It supplies no threshold, category weight,
  probability model, or forced winner.

No new Python mathematical or psychometric implementation was found in this
stack. The highest-leverage newly exercised owner path is therefore the Rust
token packer rather than a duplicate LineageWeave implementation. Existing
cosine, graph-ranking, fusion, period-report, and anchored channel-weight debt
remains frozen under the owner and acceptance criteria above; this audit does
not reclassify it as complete.
