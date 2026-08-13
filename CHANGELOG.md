# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-08-13

### Added

- `frontend/`: React + Vite + TypeScript, pinned Node via `mise.toml`,
  pnpm via Corepack -- a real client, not mocked and not static HTML.
  `react-oidc-context` drives an actual Authorization Code redirect
  through Keycloak; the post list and detail popup call the FastAPI
  backend over real `fetch()` with the token Keycloak issued.
  `src/App.test.tsx` covers the login-redirect and fetch-then-render
  paths (`useAuth` mocked -- the real OIDC round-trip is proven
  elsewhere, by `scripts/smoke_test_oidc.py` and `backend/tests/test_api.py`).
- `frontend/Dockerfile` + `nginx.conf`: two-stage build (`pnpm run build`
  then nginx serving the static bundle) added as docker-compose's fourth
  service, `VITE_*` config baked in at build time from the same `.env`
  ports every other service uses.
- `backend/app/main.py`: `CORSMiddleware`, scoped to exactly the
  frontend's origin(s) (`FRONTEND_ORIGINS`), `GET` only, `Authorization`
  header only -- verified with a real cross-origin preflight + GET against
  the live stack, not just unit-tested in isolation.
- `.github/workflows/tests.yml`: added a `frontend` job (lint, test,
  build) alongside the existing Python `pytest` job.

### Fixed

- Keycloak's `lineageweave-frontend` client (`docker/keycloak/realm-export.json`)
  now allows both the Vite dev-server origin (`:5173`) and the
  docker-compose-served frontend's origin (`:15173`) as redirect URIs and
  web origins -- the login redirect only worked from one of the two
  before this.

## [0.6.0] - 2026-08-13

### Added

- `backend/`: a FastAPI app connecting directly to PostgreSQL (`asyncpg`,
  no ORM, no file-backed DB). OIDC bearer-token login verified against a
  live Keycloak JWKS (`backend/app/auth.py`, fetched via
  `lineageweave.http_client` rather than PyJWKClient/`urllib`); RBAC
  (`post_read` permission via role membership) plus row-level ABAC
  (private `source_post` rows scoped to the requesting account's
  affiliated corporate entity) enforced on `GET /api/posts` and
  `GET /api/posts/{post_id}` (`backend/app/main.py`).
- `backend/tests/test_api.py`: real-integration tests -- a genuine access
  token from a live Keycloak, verified against a throwaway migrated
  Postgres database. Proves both the allow and the deny path: a private
  post scoped to a *different* corporate entity is excluded from the list
  and 403s on direct fetch; a forged token is rejected; a missing token is
  401. Skipped unless both a local PostgreSQL and Keycloak are reachable.
- `scripts/seed_demo_data.py` (`make seed`): seeds synthetic corp/PU/
  account/`source_post` rows keyed to the *real* subject ids Keycloak's
  admin REST API reports for the two demo users -- not a locally-fabricated
  guess at what those ids might be. Talks to Keycloak through
  `lineageweave.http_client` (`post_form` / `get_json_list`), never
  `urllib.request.urlopen`.
- `backend/Dockerfile`: `python:3.12-slim` pinned by digest, runtime
  `USER appuser` (DS-0002).
- `migrations/0001_initial_schema.sql`: added `corporate_entity.
  corporate_entity_code` (unique short code, e.g. `DEMO-CORP-01`) -- the
  column the login-time `corp_code` claim actually maps to; the original
  Phase 1 migration (still unmerged) only had the human-readable
  `entity_name`. Postgres's app database is now auto-migrated with this
  exact file on first `docker compose up` (`docker/postgres-init/Dockerfile`),
  so what's tested and what ships never drift apart.
- docker-compose.yml's default host ports moved off Postgres/Redis/common
  local-dev ports entirely (15432, 16379, 18080, 18420) -- found during
  this work that a colliding already-running service on a container's
  published port can silently answer curl/psql requests instead of the
  container, with no error; picking non-default ports avoids that
  ambiguity outright rather than relying on operators noticing.

### Fixed

- JWKS fetch and the demo seeder go through `lineageweave.http_client`
  instead of `PyJWKClient` / `urllib.request.urlopen`.

## [0.5.0] - 2026-08-13

### Added

- `docker-compose.yml`: PostgreSQL, Valkey, and a real Keycloak OIDC
  provider, genuinely functional (not a stub/mocked adapter). `make up`
  brings up all three from a clean checkout; `make smoke` runs
  `scripts/smoke_test_oidc.py`, which logs in as a synthetic demo user
  seeded by `docker/keycloak/realm-export.json`, fetches Keycloak's live
  JWKS, and cryptographically verifies the returned JWT's RS256 signature,
  issuer, and `corp_code`/`pu_code` custom claims -- a real round-trip
  proof, not a "the container started" check.
- `docker/postgres-init/` and `docker/keycloak/`: both services are `build:`
  targets (Dockerfiles that `COPY` in the keycloak-db init script and the
  realm seed) rather than bind mounts, so the images are self-contained and
  reproducible on any Docker host or CI runner.
- Keycloak stores its own state in a second database (`keycloak`) on the
  same PostgreSQL instance -- one running database service for the whole
  stack, no second file-backed store.
- `.env.example` documents the (already-defaulted) compose variables,
  including how to remap host ports if 5432/6379/8080 are already taken
  locally.

### Fixed

- Dockerfiles declare an explicit non-root `USER` (DS-0002) and pin
  `postgres:16-alpine`, `quay.io/keycloak/keycloak:26.0`, and
  `valkey/valkey:8-alpine` by digest.
- `scripts/smoke_test_oidc.py` talks to Keycloak through
  `lineageweave.http_client` (`get_json` / `post_form`) instead of
  `urllib.request.urlopen`, so the same `file://` allowlist used by the
  library clients applies to the OIDC smoke path.

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
