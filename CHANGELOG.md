# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-13

### Added

- Milestone 4, Phase 1 begins: LineageWeave's product schema.
  `migrations/0001_initial_schema.sql` -- a 3NF PostgreSQL schema
  (snake_case, 2+ word object names) covering accounts (corp/PU code as
  attributes, not the login key), a shared `common_lookup_value` ENUM
  table, posts + visibility, ABAC/RBAC, VOC-type and entity-relationship
  classification, Keyman (`cataloged_person` + N:N `person_affiliation`), a
  `knowledge_graph_edge` table, `issue_ticket`, and a self-referencing
  `corporate_hierarchy` via `corporate_entity.parent_entity_id`.
- `docs/adr/0001-demo-identity-and-data-boundary.md`: the identity/data
  scope decision for this expansion -- real infrastructure (Postgres,
  Valkey, a real OIDC provider), synthetic identities and content, because
  Keyman extraction catalogs real named individuals (including
  non-consenting external counterparties) and a real production identity
  provider would re-identify the source organization through account/data
  structure even with zero literal company-name strings in source files.
- `tests/test_schema.py`: real-database tests (skipped without a
  reachable PostgreSQL server) proving the migration applies cleanly, a
  multi-level corporate-hierarchy recursive query returns the right
  shape, and an invalid lookup code is genuinely rejected by a foreign
  key -- caught and fixed a real bug in the process (an accidental
  `deferrable initially deferred` on one FK silently weakened its
  integrity check within a transaction).
- New citations staged for Phase 2/3: Tong et al. (2006, random walk with
  restart -- Knowledge Graph per-node traversal depth) and Bhattacharya &
  Getoor (2007, collective entity resolution -- corporate hierarchy).

## [0.3.0] - 2026-08-13

### Fixed

- Embedding, adjudication, and vision clients now POST through a shared
  `http_client.post_json` helper that allowlists `http`/`https` and never
  calls `urllib.request.urlopen`. That closes the `file://` read concern
  Semgrep's `dynamic-urllib-use-detected` rule was flagging on the
  operator-configured base URLs. HTTPS posts wrap the connected socket
  with a certifi-backed `SSLContext` instead of constructing
  `http.client.HTTPSConnection`, so certificate verification is explicit
  on the Python 3.10+ runtime this project requires.

### Added

- `lineageweave/chunking.py`: semantic-unit chunking so the embedding
  channel compares meaning-identifiable units instead of whole flattened
  documents -- `chunk_by_paragraph` (Hearst, 1997, TextTiling subtopic
  boundaries), `chunk_by_sentence`, `chunk_by_dom` (WHATWG HTML Living
  Standard sectioning/flow block elements), and `chunk_by_conversation_turn`
  (RFC 5322 sender/receiver boundaries).
- `embedding_client.chunked_max_similarity`: chunks two documents, embeds
  every chunk, and returns the single highest-scoring pair -- the standard
  passage-retrieval strategy for "a relevant unit is buried in a longer
  document." Degrades to plain whole-text embedding for any document that
  chunks to zero or one piece (this project's real short-title dataset
  behaves exactly as it did before chunking existed).
- Real-provider test proving chunking works, not just that it type-checks:
  a short relevant paragraph buried inside a longer synthetic document
  scored higher via `chunked_max_similarity` than via whole-document
  embedding, against the live embedding provider.
- `docs/lineage-bi-research-notes.md`: new "Chunking" section with the
  four units' grounding and an explicit, honest note that this project's
  real dataset's only free-text field is too short to need chunking in
  practice -- the module exists for richer content sources (e.g. the raw
  MHTML artifacts that dataset's records were derived from).
- `lineageweave/image_content.py`: pluggable vision channel for base64
  images embedded in DOM content -- real OCR (Li et al., 2023, TrOCR) and
  object recognition/tagging (Radford et al., 2021, CLIP) via
  `OpenAiCompatibleVisionClient`, same never-fake-a-missing-channel
  discipline as the embedding/adjudication clients. `chunk_by_dom` now
  extracts embedded images as `"image"` chunks interleaved with text
  chunks in true document order, so an image's position relative to its
  surrounding text is preserved and reconstructable.
- Real-provider test proving OCR works, not just that it type-checks: a
  real PNG generated with real rendered text (not a fixture file) was
  read back correctly by `OpenAiCompatibleVisionClient` against the live
  vision-capable model.
- `docs/image-content-schema.md`: proposed DB schema (snake_case, 2+ word
  object names) for persisting and searching extracted image content,
  designed so a text/tag search hit stays traceable to which document and
  which position produced it, and so the same image (by content hash) is
  never *stored* twice (the primary key guarantees that part). Avoiding a
  duplicate vision-provider *call* for two concurrent ingests of the same
  new image is a separate concern the schema documents but does not solve
  by itself -- a real write path still needs an atomic claim/lease step.

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
