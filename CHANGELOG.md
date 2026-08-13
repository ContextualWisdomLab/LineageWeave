# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-13

### Added

- ADR-0016 grounding: `docs/lineage-bi-research-notes.md` now cites
  Doddington et al. (2004, ACE) and Anagnostopoulos et al. (2013, CHRONOS)
  alongside Allan (2002, TDT), and explains how `reconstruct.py` maps onto
  TEPP's three-layer event-intelligence separation (mention/instance,
  calibrated detection, temporal-consistency).
- `tests/test_real_provider_integration.py`: opt-in (env-var-gated, skipped
  by default so a credential-free clone stays green) tests proving
  `OpenAiCompatibleEmbeddingClient` and `ContextualOrchestratorAdjudicationClient`
  work end-to-end against real providers, not just that their interfaces
  are satisfiable by a stub.

### Fixed

- `embedding_client.py` / `adjudication_client.py`: both real-provider HTTP
  clients now build their SSL context from `certifi`'s CA bundle instead of
  the platform default. Some interpreter distributions (observed: a
  standalone uv-managed CPython on macOS) don't reliably inherit the OS
  trust store, which made every real-provider call fail closed with
  `CERTIFICATE_VERIFY_FAILED` even against a validly, publicly-trusted
  certificate. Full chain validation still applies -- nothing is weakened,
  the bundle source just changed.

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
