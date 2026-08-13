# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-13

### Added

- Initial prototype: `reconstruct()` pipeline (group → bounded candidate
  window → multi-channel fusion via RankWeave → tree assembly via
  ThreadWeave).
- Four scoring channels: `temporal`, `secondary_key`, `text`
  (dependency-free stand-in for embedding-cosine similarity), and an
  optional `llm` channel via a pluggable `AdjudicationClient`.
- `ContextualOrchestratorAdjudicationClient`, calling
  [contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)'s
  `mode="verify"` with `reasoning_effort="high"`.
- `OpenAiCompatibleEmbeddingClient` for a real embedding-cosine text
  channel against any OpenAI-compatible `/v1/embeddings` endpoint.
- `TeppClient` / `AnalysisRunRequest`: validated wire shape matching
  [TEPP](https://github.com/ContextualWisdomLab/TEPP)'s published
  `analysis_run_request_v1.json` schema, pluggable transport (fails closed
  with `TeppNotAvailable` until TEPP ships a live HTTP endpoint).
- Minimum fused-score floor so weakly-related records surface as their own
  root instead of being force-attached to the best of a bad set of
  candidates.
- Stdlib HTTP demo server (`lineageweave/server.py`) and a self-contained
  SVG DAG viewer (`web/index.html`), no build step or external script
  dependency.
- Synthetic-only demo dataset (`lineageweave/fixtures.py`).
- `docs/lineage-bi-research-notes.md`: the literature this design is
  grounded in, APA 7th.
