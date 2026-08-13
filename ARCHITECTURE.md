# Architecture

## Scope and non-scope

LineageWeave reconstructs a plausible thread structure over records that
already exist somewhere else. It does not ingest, own, or persist any
source-of-truth data, and it does not perform calibrated statistical
estimation. Both of those are explicitly out of scope and pushed to other
repos in the ecosystem:

- **Ingestion** of raw exports into governed tables is
  [mhtml-etl-gateway](https://github.com/ContextualWisdomLab/mhtml-etl-gateway)'s
  job.
- **Calibrated psychometric/temporal measurement** (latent trait scores,
  trajectories, uncertainty-quantified estimates) is
  [TEPP](https://github.com/ContextualWisdomLab/TEPP)'s job.

This is why the org-wide rule that mathematical/psychometrics computation
layers must be Rust with GPU + CPU multithreading does not apply to this
repo: LineageWeave does no such computation. Its heaviest per-request work
is fusing a handful of `[0, 1]` channel scores over a bounded candidate
window (`reconstruct.DEFAULT_CANDIDATE_WINDOW`, default 50) -- a scheduling
and orchestration problem, not a numerical-estimation one. If a future
version added real statistical inference (e.g. estimating thread-assignment
uncertainty), that layer would move into TEPP rather than being built here,
consistent with the dependency direction the ecosystem's own architecture
docs already establish (`psychometrics-commons`'s TRD explicitly forbids a
downstream product from reimplementing a measurement engine's model).

## Data flow

```mermaid
flowchart LR
    subgraph Source
        R[Records<br/>id, group_key, label,<br/>occurred_at, secondary_key]
    end

    subgraph LineageWeave
        G[Group by group_key]
        C[Candidate window<br/>most recent N priors]
        CH[Channels<br/>temporal · secondary_key · text · llm]
        F[RankWeave<br/>weighted_convex_fuse]
        T[ThreadWeave<br/>thread_messages]
    end

    subgraph External services, all optional
        EMB[Embedding provider<br/>swap in for the text channel]
        ORC[contextual-orchestrator<br/>mode=verify, llm channel]
        TEPP[TEPP<br/>AnalysisRunRequest v1,<br/>calibrated measurement]
    end

    R --> G --> C --> CH --> F --> T --> OUT[Tree per group:<br/>roots, edges, branch points]
    CH -.text channel.-> EMB
    CH -.llm channel.-> ORC
    OUT -.optional export.-> TEPP
```

## Module map

| Module | Responsibility |
|---|---|
| `models.py` | `Record`, `Edge`, `Tree` -- source-agnostic data shapes |
| `channels.py` | Independent `[0, 1]` scoring functions |
| `chunking.py` | Splits a document into meaning-identifiable units (paragraph, sentence, DOM, conversation-turn) plus embedded-image extraction, in document order |
| `embedding_client.py` | Pluggable text-embedding channel (`Null` default, `OpenAiCompatible` real impl) + `chunked_max_similarity` |
| `adjudication_client.py` | Pluggable LLM-judgment channel (`Null` default, `ContextualOrchestrator` real impl) |
| `image_content.py` | Pluggable vision channel: OCR + object recognition/tagging for embedded images (`Null` default, `OpenAiCompatibleVisionClient` real impl) |
| `tepp_client.py` | TEPP's published `AnalysisRunRequest` wire contract, pluggable transport |
| `reconstruct.py` | The pipeline: group → candidate window → score → fuse → thread |
| `lineage_persistence.py` | Flattens reconstruct trees into `post_lineage_edge` row specs (parent, child, fused_score) |
| `knowledge_graph.py` | Random-walk-with-restart relevance + per-node adaptive related-node cutoff (Tong et al., 2006) -- pure graph math, no Postgres |
| `keyman_extraction.py` | Pluggable LLM extraction of two-sided (our-side/counterparty) person mentions + N:N org affiliations from a post |
| `entity_relationship_classification.py` | Pluggable LLM classification of a named organization's relationship to the post author (`rel_voc`/`rel_vom`/`rel_vop`/`rel_vocc`/`rel_voco`/`rel_vos`) |
| `corporate_hierarchy_resolution.py` | Similarity-based resolution of a free-text org name to an existing `corporate_entity` row (Bhattacharya & Getoor, 2007's candidate-generation stage) |
| `post_summary.py` | Pluggable LLM Korean summary + key events + R&R derivation for a post |
| `post_chat.py` | Pluggable in-popup chat's reason-and-cite step (retrieve step lives in `backend/app/post_chat_ingestion.py`) |
| `fixtures.py` | Synthetic demo dataset -- no real data ships in this repo |
| `server.py` | Stdlib HTTP server: `GET /api/lineage` (JSON graph) + static viewer |
| `web/index.html` | Self-contained SVG DAG viewer, no build step, no external script dependency |

## Design decisions worth naming

- **Pluggable, never faked, channels.** `NullEmbeddingClient` and
  `NullAdjudicationClient` make a channel *unavailable* (dropped and
  renormalized in `active_weights()`), never silently scored as 0. A
  missing signal and a confidently-negative signal are different things and
  must not be conflated.
- **A minimum fused-score floor** (`DEFAULT_MIN_FUSED_SCORE`). Without it,
  every record after the first in a group gets *some* parent even when
  every candidate is a weak match -- wrong more often than useful. See
  `fixtures.sample_records()`'s intentionally-unrelated `rec-006` and its
  test in `tests/test_reconstruct.py`.
- **A bounded candidate window** (`DEFAULT_CANDIDATE_WINDOW`, default 50).
  `ponytail`-tagged in `reconstruct.py`: keeps per-group cost `O(n * window)`
  instead of `O(n^2)` for large groups; raise it if recall against a labeled
  set ever shows true parents falling outside the window.
- **TEPP is a wire contract, not an import.** `tepp_client.py`'s default
  transport raises `TeppNotAvailable` rather than silently no-op'ing,
  because TEPP has no live HTTP endpoint yet; the shape is validated
  (`AnalysisRunRequest.to_json()` mirrors TEPP's published JSON Schema
  exactly, `additionalProperties: false` and all) so wiring in a real
  transport is additive, not a rewrite.

## Standards and citations

See [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md)
for the full APA 7th reference list this design is grounded in.

## Product schema (Phase 1 of a larger roadmap)

`lineageweave`'s reconstruction pipeline above is being wrapped in a real
product: corp/PU-code accounts, ABAC/RBAC, posts, Keyman extraction, a
Knowledge Graph, corporate hierarchy, and issue tickets. See
[`docs/adr/0001-demo-identity-and-data-boundary.md`](docs/adr/0001-demo-identity-and-data-boundary.md)
for the identity/data scope decision (real infrastructure, synthetic
identities and content) and `migrations/0001_initial_schema.sql` for the
3NF PostgreSQL schema (`common_lookup_value`, `corporate_entity`,
`process_unit`, `user_account`, `account_affiliation`, `access_role` /
`role_permission` / `account_role_assignment`, `abac_policy`, `post` /
`post_counterparty_entity`, `person` / `person_affiliation` /
`post_person_mention`, `knowledge_graph_edge`, `issue_ticket`,
`post_lineage_edge`). Real-database tests: `tests/test_schema.py`
(skipped without a reachable PostgreSQL server, same pattern as the
real-provider LLM tests).

### Local infrastructure (Docker Compose)

`docker-compose.yml` runs PostgreSQL, Valkey, and a real Keycloak OIDC
provider (`docker/keycloak/realm-export.json` seeds a `lineageweave-demo`
realm with synthetic demo accounts carrying `corp_code` / `pu_code` as
custom token claims -- see [README](README.md#local-product-stack-docker-compose)).
`scripts/smoke_test_oidc.py` proves the round-trip is real: it logs in as
the synthetic demo user, fetches Keycloak's live JWKS, and cryptographically
verifies the returned JWT's RS256 signature rather than just checking for an
HTTP 200. Both Postgres (`docker/postgres-init/`) and Keycloak
(`docker/keycloak/`) are `build:` targets that `COPY` their seed files in,
not bind mounts -- self-contained images that don't depend on any particular
host filesystem layout being reachable from the Docker daemon, which also
makes them reproducible in CI. Valkey is the Phase 2+ event queue (not a
traditional MQ) for asynchronous work like Keyman/Knowledge-Graph
recomputation once posts change. Postgres's app database is auto-migrated
on first boot from the same `migrations/0001_initial_schema.sql` file
`tests/test_schema.py` applies -- one schema file, no drift between what's
tested and what ships.

### Backend (`backend/`)

A FastAPI app (`backend/app/main.py`) over a direct `asyncpg` connection
pool (`backend/app/db.py`) -- no ORM, no file-backed database. Login is
OIDC bearer-token verification against Keycloak's live JWKS
(`backend/app/auth.py`): the token's `sub` resolves to a `user_account`
row, and `corp_code`/`pu_code` are read back from that account's
`account_affiliation` rows in Postgres, never trusted directly off the
token, matching the schema's design intent. Two authorization layers
compose per request:

- **RBAC** (coarse): the account's roles must grant the `post_read`
  permission at all, via `account_role_assignment` -> `role_permission`.
- **ABAC** (row-level, on top of RBAC): a post is visible if it is public,
  or if it is private and the account is affiliated with the post's
  `corporate_entity_id`. `abac_policy.condition_expression` is reserved for
  a richer per-policy DSL later; Phase 1 implements exactly this one fixed
  rule directly in Python (`backend/app/main.py::_can_see_post`) since it
  is the only rule the product currently needs -- documented there rather
  than over-built as a generic evaluator nothing yet exercises differently.

`backend/tests/test_api.py` is a real-integration test, not a mocked one:
it fetches a genuine access token from a live Keycloak, verifies the
allow/deny ABAC boundary against a throwaway migrated Postgres database
(a private post scoped to a *different* corporate entity is proven
excluded from the list and 403s on direct fetch), and proves a forged
token is rejected. `scripts/seed_demo_data.py` populates the docker-compose
stack itself with the same shape of synthetic data for manual/frontend use.
`CORSMiddleware` (`backend/app/main.py`) allows exactly the frontend's
origin(s) (`FRONTEND_ORIGINS`), `GET` and `POST` (the extract-keymen
write), `Authorization` header only.

Phase 2 adds two more GET endpoints on the same RBAC+ABAC gate plus one
write: `GET /api/posts/{post_id}/keymen` (people extracted or seeded for
that post, with N:N affiliations), `GET /api/keymen/{person_id}/related`
(RWR from that person over `knowledge_graph_edge` rows, adaptive
relevance cutoff, never a fixed hop count), and
`POST /api/posts/{post_id}/extract-keymen` (`post_admin` only -- a write
with a real LLM-call cost). A Keyman who is only mentioned on a post the
account cannot see is 403, matching the post deny path. Extraction
lives in `lineageweave/keyman_extraction.py` and talks to
contextual-orchestrator; persist is `backend/app/keyman_ingestion.py`.

`GET /api/lineage` returns the ABAC-filtered reconstruct graph
(`{nodes, edges}`) from persisted `post_lineage_edge` rows.
`POST /api/lineage/rebuild` (`post_admin`) re-runs `reconstruct()` over
every `source_post` and rewrites those edges. Reconstruct grouping is
stored on the post as `thread_group_key` / `secondary_grouping_key`
(not derived from process unit or voc type).

Phase 3 adds `GET /api/posts/{post_id}/counterparties` (same RBAC+ABAC
gate) and extends `POST /api/posts/{post_id}/extract-keymen` to also
classify each extracted Keyman's affiliated organizations' relationship
to the post author's org (`lineageweave/entity_relationship_classification.py`,
persisted via `backend/app/entity_relationship_ingestion.py` into
`post_counterparty_entity`). Organization-name resolution into a real
`corporate_entity` row (both for Keyman affiliations and for the
relationship classifier's candidates) goes through
`lineageweave/corporate_hierarchy_resolution.py` instead of an exact
string match, so "Acme Electronics Korea Ltd." still resolves to the
same entity as "Acme Electronics Korea."

Phase 4 adds `GET /api/posts/{post_id}/lineage` (direct `post_lineage_edge`
links and indirect Knowledge-Graph links, kept as two separate lists --
`backend/app/post_chat_ingestion.py::find_linked_post_ids`),
`GET /api/posts/{post_id}/summary` (`lineageweave/post_summary.py`,
computed fresh per request, not persisted), and
`POST /api/posts/{post_id}/chat` (`lineageweave/post_chat.py`'s
reason-and-cite step over `gather_chat_sources`' retrieve step -- both
Event-Lineage link kinds feed the chat's context, ABAC-rechecked per
candidate post). `find_linked_post_ids` first expands to every post
sharing a mentioned person before calling
`backend/app/knowledge_graph.py::load_visible_subgraph` -- that function
only loads edges among an *already-known* post set (its other caller,
`related_for_person`, pre-resolves the full set itself), it does not
discover new posts on its own; a real bug from calling it with only the
single starting post was caught while building this and is now
regression-tested (`test_post_chat_cites_a_post_linked_only_via_a_shared_keyman`).

### Frontend (`frontend/`)

React + Vite + TypeScript, pinned Node via `mise.toml`, pnpm via Corepack.
`react-oidc-context` drives a real Authorization Code redirect through
Keycloak (`src/main.tsx`'s `AuthProvider`) -- no mocked auth, no static
HTML. `src/api.ts` calls the FastAPI backend directly with the token
Keycloak issued; `src/App.tsx` renders the post list and a full detail
popup: Korean summary/key-events/R&R, an Event Lineage panel
(direct vs. indirect links, visually distinguished per
`tests/test_indirect_lineage_linking.py`'s distinction), Keyman +
counterparty panels, and an in-popup chat whose cited sources open a
sliding evidence panel (`EvidencePanel`, CSS `slide-in-from-right`)
showing that source post's actual content. Built from the product
brief's text, not the referenced Figma frame's pixel layout -- see
[ADR 0002](docs/adr/0002-figma-access-boundary.md) for why. Served in
`docker compose` via a two-stage build (`frontend/Dockerfile`):
`pnpm run build` then `nginx` serving the static bundle, with `VITE_*`
config baked in at build time from the same `.env` ports every other
service uses (Vite embeds `import.meta.env.VITE_*` at build time, not
runtime, so these are Docker build args, not container env vars).
`src/App.test.tsx` mocks `react-oidc-context`'s `useAuth` to test the
component's own render logic (login button -> `signinRedirect()`; fetch
posts with the token -> render list -> click -> popup shows the fetched
body and every panel; ask a chat question -> click a citation -> the
evidence panel shows exactly that source post's content) -- the real
OIDC cryptography and the real LLM calls are proven elsewhere
(`scripts/smoke_test_oidc.py`, `backend/tests/test_api.py`), so this test
isn't re-proving that, only that the UI wires the pieces together
correctly. `src/setupTests.ts` registers `@testing-library/react`'s
`cleanup` explicitly in an `afterEach` -- this project's `vite.config.ts`
deliberately runs without `test.globals`, which is also why RTL's own
auto-cleanup (which only self-registers when `afterEach` is already a
global) silently never ran before this; a real bug this phase's larger
test file surfaced (stale DOM from one test bleeding into the next).
