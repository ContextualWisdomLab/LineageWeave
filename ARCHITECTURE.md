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

ADR 0208 fixes the end state: LineageWeave retains wire validation,
authorization, provenance persistence, and UI projection only. The current
Python IRT/report, residual-map, similarity, graph-ranking, and fusion paths
are explicitly inventoried migration debt rather than evidence that this
repository owns their mathematics. They move by construct to TEPP,
fast-mlsirm, or RankWeave after versioned Rust CPU/GPU owner contracts pass
recovery/equivalence checks; affected product paths fail closed during each
cutover rather than substituting a local estimate. See
`docs/doctoring/python-mathematical-compute-boundary-audit.md`.

ADR 0237 also keeps accelerator deployment outside this repository. MLX runs
as a native Apple-silicon inference service behind contextual-orchestrator;
scientific CPU/CUDA/OpenCL profiles belong to TEPP or fast-mlsirm. RankWeave
remains the dependency-free Python retrieval-fusion/evaluation owner behind its
published contract. LineageWeave Compose therefore does not reserve devices or
mount host drivers; its provider-neutral connectors consume versioned results
and fail closed when an owning service is unavailable.
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
| `image_content.py` | Pluggable vision channel: OCR + object recognition/tagging for embedded images (`Null` default, `OpenAiCompatibleVisionClient` real impl). The product popup (`frontend/src/PostBody.tsx`) renders each `data:image` payload in document order so the buyer sees the picture, not the base64 string; GET does not call the vision client. |
| `tepp_client.py` | TEPP's published `AnalysisRunRequest` wire contract, pluggable transport |
| `rankweave_client.py` | Fail-closed RankWeave ranking port (`weighted_reciprocal_rank_fuse` in-process; never invent a fused score or a theta) |
| `reconstruct.py` | The pipeline: group → candidate window → score → fuse → thread |
| `lineage_persistence.py` | Flattens reconstruct trees into `post_lineage_edge` rows plus `post_lineage_edge_signal` channel evidence |
| `interval_relation.py` | Allen (1983) closed interval relations for those edges. Each post is a point interval on its observed UTC `created_at` day; mutable ticket dates are not Event Lineage evidence. |
| `knowledge_graph.py` | Random-walk-with-restart relevance + per-node adaptive related-node cutoff (Tong et al., 2006) -- pure graph math, no Postgres |
| `keyman_extraction.py` | Pluggable LLM extraction of two-sided (our-side/counterparty) person mentions + N:N org affiliations from a post |
| `entity_relationship_classification.py` | Pluggable LLM classification of a named organization's relationship to the post author (`rel_voc`/`rel_vom`/`rel_vop`/`rel_vocc`/`rel_voco`/`rel_vos`) |
| `corporate_hierarchy_resolution.py` | Similarity-based resolution of a free-text org name to an existing `corporate_entity` row (Bhattacharya & Getoor, 2007's candidate-generation stage) |
| `affiliate_tree.py` | Ancestor forest of the organizations a post's Keymen touch -- resolved rows walk `parent_entity_id`, unresolved names stay roots |
| `voc_evidence.py` | Extractive VOC excerpts: sentences that name a classified organization, or empty |
| `post_summary.py` | Pluggable LLM Korean summary + key events + R&R derivation for a post |
| `post_chat.py` | Pluggable in-popup chat's reason-and-cite step (retrieve step lives in `backend/app/post_chat_ingestion.py`) |
| `commitment_extraction.py` | Pluggable LLM derivation of a customer commitment (promise + deadline) from a post; `Null` default, `ContextualOrchestrator` real impl |
| `temporal_expressions.py` | Pure Korean relative-time resolver for Global Ask (ADR 0150) |
| `ask_time_axis.py` | Event-time vs ingestion-time clock choice for that window (ADR 0202) |
| `ontology.py` | Loads the governed Turtle source tree (`lineageweave-kg.ttl` plus generated fragments), the formal OWL 2/RDFS/SKOS vocabulary for the Knowledge Graph's node/edge types, source taxonomies, and published O*NET linkages (ADR 0004, ADR 0252, ADR 0255, ADR 0256) |
| `backend/app/occupation_rating_ingestion.py` | Projects authenticated occupation-rating evidence plus persisted source and represented-occupation catalogs (ADR 0258, ADR 0260, ADR 0261) |
| `frontend/src/components/OccupationRatingProfile.tsx` | Selects an imported source, filters stored occupation titles without ranking, and reads exact Dashboard evidence while preserving absence, uncertainty, and warning semantics (ADR 0259–0262) |
| `ontology_neighborhood.py` | Bounded typed ontology/provenance neighborhood (ADR 0184); PostgreSQL stays authoritative, OWL subclass is not an instance edge |
| `occupational_construct_catalog.py` | Official O*NET 31.0 construct catalog sync (ADR 0250); no ratings or invented IRIs |
| `backend/app/occupational_construct_search.py` | Authorized catalog-label search over assertion-backed constructs (ADR 0257); hidden Posts never mint a hit |
| `ontology_source_cursor.py` | Opaque HMAC source-window continuation (ADR 0124); keyset pagination, never OFFSET |
| `period_report.py` | Fit GRM/GPCM on persisted IRT rows, FIPC-select, EAP-score a period (ADR 0003 slice 3; Bock & Mislevy, 1982) |
| `fixtures.py` | Synthetic demo dataset -- no real data ships in this repo |
| `server.py` | Legacy stdlib HTTP server for the library-level synthetic fixture demo; production uses FastAPI/PostgreSQL |
| `web/index.html` | Legacy self-contained SVG DAG viewer; production UI is the React/Vite frontend |

> **Known local-test-environment limitation:** `adjudication_client.py`'s
> `mode="verify"` call depends on contextual-orchestrator's
> `TaskOrchestrator.route_and_verify`, which as of this writing is still
> an open, unmerged upstream PR
> (`ContextualWisdomLab/contextual-orchestrator#149`). Until it merges,
> the four adjudication/chat tests that exercise `mode="verify"` against
> a real orchestrator fail with `invalid_mode` (the deployed `main` only
> accepts `auto`/`route`/`conduct`) -- confirmed by reproducing the same
> `400` directly against the orchestrator's own `/v1/chat/completions`,
> not caused by anything in this repo. `mode="route"` (every other
> pluggable client) is unaffected.

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
- **RankWeave is an in-process library, not an HTTP host.**
  `rankweave_client.py`'s default transport raises
  `RankWeaveNotAvailable`. `GET /api/rankings` then returns
  `rankweave_not_available` and an empty ranking list. Hidden posts
  are omitted from every channel. Accepted hits include
  `channel_evidence` computed from owned temporal/lexical ranks
  (Cormack weighted RRF contribution); RankWeave extra fields are
  ignored and no theta is invented. See ADR 0024 and ADR 0167.

## Standards and citations

See [ADR 0084](docs/adr/0084-lineage-research-grounding.md) for the normative
research-grounding policy and [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md)
for the full APA 7th reference list and supporting aggregate evidence.

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

Keyman and R&R person mentions are separate replaceable projections (`post_person_mention` and `post_summary_person_mention`). The read-only `combined_post_person_mention` view feeds lineage discovery. Materialized KG edges are unique and carry normalized `knowledge_graph_edge_evidence`; only evidence from an ABAC-visible post participates in RWR.
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
token is rejected. Its dev-only FastAPI `TestClient` uses Starlette's
supported `httpx2` transport alongside the project's official `httpx`
dependency. The transport package is dev-only and exists solely for the
current Starlette integration contract; production runtime dependencies remain
unchanged. `scripts/seed_demo_data.py` populates the docker-compose
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
(`{nodes, edges, truncated, reconstruction}`) from persisted `post_lineage_edge`
rows. Each edge includes additive `channel_evidence` from
`post_lineage_edge_signal`. Evidence for an endpoint the account cannot
see is omitted. Each node includes `group` from the same
`reconstruct_group_key()` rebuild uses (persisted `thread_group_key`,
else process unit, else corp).
Each direct edge includes `interval_relation_code` /
`interval_relation_label` computed from the posts' observed windows.
Global Ask merges cited threads from one post/edge fetch pair and
caps the payload at the landing node bound, keeping cited posts first
(ADR 0169). Optional `knowledge_cutoff` on `POST /api/ask` selects the
covering `source_post_revision` and never substitutes a live body
(ADR 0216). Open a cited post to read the focused thread.
`POST /api/lineage/rebuild` (`post_admin`) re-runs `reconstruct()` over
every `source_post` and atomically rewrites edges, channel signals, and
Allen interval relations. Reconstruct grouping is
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
same entity as "Acme Electronics Korea." A resolved name on
`GET /counterparties` carries `corporate_entity_id` so the popup can
open `GET /api/corporate-entities/{id}/related`; an unresolved name
stays `null`.

Phase 4 adds `GET /api/posts/{post_id}/lineage` (direct `post_lineage_edge`
links and indirect Knowledge-Graph links, kept as two separate lists --
`backend/app/post_chat_ingestion.py::find_linked_post_ids`),
`GET /api/posts/{post_id}/summary` (`lineageweave/post_summary.py`,
persisted in `post_summary_result` so a seeded demo -- including
A-100/B-200 Event Lineage nodes and the calendar commitment -- is
not empty without a live LLM; A-100/B-200 casts also persist R&R so
the popup list is not empty, and a matching Keyman name starts the
same related-node walk), and
`GET`/`POST /api/posts/{post_id}/chat` (`lineageweave/post_chat.py`'s
reason-and-cite step over `gather_chat_sources`' retrieve step -- both
Event-Lineage link kinds feed the chat's context, ABAC-rechecked per
candidate post). Seeded fixture answers live in `post_chat_result` so
Ask is useful without a live LLM -- each fixture stores "What
happened between these events?", "Who is involved?" (Keymen, or
an explicit no-Keyman sentence), and "What is the next commitment?"
(the seeded Calendar ticket title plus due date, or an explicit
no-commitment sentence on rec-006). A missing orchestrator and no stored
match is 503; the popup shows
`Chat unavailable (LLM orchestrator not configured)` rather than a
raw HTTP status. After that 503 the free-text Ask box is hidden and
only seeded question chips remain -- never a fabricated answer. Evaluate, Extract
Keymen, Derive commitment, and Verify use the same 503 empty-state
pattern and then hide the action button so it cannot 503 again.
`find_linked_post_ids` first expands to every post
sharing a mentioned person before calling
`backend/app/knowledge_graph.py::load_visible_subgraph` -- that function
only loads edges among an *already-known* post set (its other callers,
`related_for_person` / `related_for_entity` / `related_for_team`,
pre-resolve the full set themselves), it does not discover new posts on
its own; a real bug from calling it with only the single starting post
was caught while building this and is now regression-tested
(`test_post_chat_cites_a_post_linked_only_via_a_shared_keyman`).
Person, team, and organization mention channels load independently
(ADR 0018): a team-only or organization-only post still walks.

### Frontend (`frontend/`)

React + Vite + TypeScript, pinned Node via `mise.toml`, pnpm via Corepack.
`react-oidc-context` drives a real Authorization Code redirect through
Keycloak (`src/main.tsx`'s `AuthProvider`) -- no mocked auth, no static
HTML. `src/api.ts` calls the FastAPI backend directly with the token
Keycloak issued; `src/App.tsx` renders a git-branch SVG of
`GET /api/lineage` (click a node to open that post; `post_admin` can
rebuild), the post list, and a full detail popup: Korean
summary/key-events/R&R, VOC evidence excerpts, an Event Lineage panel
(direct vs. indirect links; a link opens that post), the Keyman
affiliate tree (resolved ancestors plus unresolved org roots), Keyman +
counterparty panels (a Keyman click loads RWR related nodes;
a related corporate-entity node, a resolved Keyman affiliation,
a classified name that resolves to a cataloged org, or an R&R team
continues the same walk via `GET /api/corporate-entities/{id}/related`
or `GET /api/teams/{id}/related`;
`post_admin` can extract),
and an in-popup chat whose cited sources
open a sliding evidence panel (`EvidencePanel`, CSS
`slide-in-from-right`) showing that source post's actual content. Built from the product
brief's text, not the referenced Figma frame's pixel layout -- see
[ADR 0002](docs/adr/0002-figma-access-boundary.md) for why. Served in
`docker compose` via a two-stage build (`frontend/Dockerfile`):
`pnpm run build` then `nginx` serving the static bundle, with `VITE_*`
config baked in at build time from the same `.env` ports every other
service uses (Vite embeds `import.meta.env.VITE_*` at build time, not
runtime, so these are Docker build args, not container env vars).
`src/App.test.tsx` mocks `react-oidc-context`'s `useAuth` to test the
component's own render logic (login button -> `signinRedirect()`; the
A-100 fork DAG shows a branch point and rec-006 as its own root;
`post_admin` can rebuild; fetch posts with the token -> render list ->
click -> popup shows the fetched body and every panel; ask a chat
question -> click a citation -> the evidence panel shows exactly that
source post's content) -- the real
OIDC cryptography and the real LLM calls are proven elsewhere
(`scripts/smoke_test_oidc.py`, `backend/tests/test_api.py`), so this test
isn't re-proving that, only that the UI wires the pieces together
correctly. `src/setupTests.ts` registers `@testing-library/react`'s
`cleanup` explicitly in an `afterEach` -- this project's `vite.config.ts`
deliberately runs without `test.globals`, which is also why RTL's own
auto-cleanup (which only self-registers when `afterEach` is already a
global) silently never ran before this; a real bug this phase's larger
test file surfaced (stale DOM from one test bleeding into the next).

## Phase 6: affiliate tree and VOC evidence

`GET /api/posts/{post_id}/affiliate-tree` walks
`corporate_entity.parent_entity_id` for every organization a post's
Keymen are affiliated with (`lineageweave/affiliate_tree.py`, loaded by
`backend/app/affiliate_tree_ingestion.py`). The forest is the ancestor
set of those leaves, not the whole company directory -- a sibling the
post never mentions is omitted. People on the tree are buttons that
reuse `GET /api/keymen/{person_id}/related` so the popup Keyman walk
starts from the affiliation the buyer clicked. A resolved organization
is the same walk via `GET /api/corporate-entities/{id}/related`. An affiliation that did not resolve to
a `corporate_entity` row stays as its own root (`resolved=false`); that
is the same never-guess-a-parent rule
`corporate_hierarchy_resolution` already applies. Entity levels and
Keyman sides are labeled from `common_lookup_value` (`Our side`,
`Plant`, `Company`) so the popup never shows raw `our_side` / `plant`
codes when a label exists. Related-node person chips use the same
side lookup label (for example, `Our side` or `Counterparty`) rather
than exposing the generic PROV-O `Person` class as business context.

`GET /api/posts` and `GET /api/posts/{post_id}` include
`voc_type_label` / `visibility_label` from `common_lookup_value` so
the list badge and popup meta show `Voice of Customer` / `Public`
instead of raw codes.

`POST /api/posts/{post_id}/voice-assignments` lets a `post_admin` add one
governed atomic Voice with an explicit truth state and an ABAC-visible evidence
Post. The server creates the normalized PROV-O derivation and assignment in one
transaction; clients never submit an internal assertion id, and this route
cannot replace the imported primary Voice.
The bounded ontology response carries a visible Voice assignment's evidence
Post id alongside its exact-value row. The exact-value table therefore offers
separate carrying-Post and derivation-evidence actions; hidden evidence removes
the additional assignment before serialization rather than leaking its id or
showing a fabricated count.
The live Post popup exposes the route only to its existing `post_admin`
permission result and only outside knowledge-cutoff views. Its form excludes
already assigned catalog options, requires an explicit truth state, and uses
the open Post as evidence so the UI never asks for an internal Post id.

`GET /api/posts/{post_id}/voc-evidence` returns the
`common_lookup_value` label for the post's `voc_type_code` plus the
sentences in the post body that name a counterparty or affiliated
organization (`lineageweave/voc_evidence.py`). A name that does not
appear yields no excerpt. Each counterparty also carries
`verification_status_code` / `verification_evidence_url` so the VOC
panel shows the same Searxng badge as Counterparties. A counterparty
name that already sits on the affiliate tree is a button that starts
the same Keyman related-node walk (Northridge Grid -> Priya Nair).
`make seed` writes Ada West / Priya Nair /
Northridge Grid onto A-100 proj-alpha Event Lineage posts, Jordan Hale
/ Westfield Power onto B-200, and Riverbend onto the calendar
commitment so those panels are not empty without a live extractor.
rec-006 stays uncast. The popup also wires
the already-shipped `GET /api/keymen/{person_id}/related` (click a
Keyman) and `POST /api/posts/{post_id}/extract-keymen` (`post_admin`).

## Phase 5: issue ticket management

`backend/app/issue_ticket_ingestion.py` + three endpoints
(`GET`/`POST /api/posts/{post_id}/tickets`, `PATCH /api/tickets/{id}`)
close the one product-brief item with a schema table (`issue_ticket`)
but no implementation through Phase 4. Deliberately plain CRUD, not a
pluggable-LLM channel like `keyman_ingestion.py` -- ticket status is a
closed enum in `common_lookup_value`, and opening or updating a ticket
is a direct user action, not something extracted from text.
`frontend/src/App.tsx`'s `IssueTicketPanel` is the popup's real
list/create/status-update UI for it. Status options show
`common_lookup_value` labels (`Open` / `In progress` / `Closed`)
instead of raw codes. `make seed` opens tickets on the
A-100 follow-up and delivery fixtures and the B-200 specification
revision so a report-member click is not "No tickets yet."

Found and fixed a real deployment bug while verifying this end to end
against the actual Docker-built stack: `frontend/Dockerfile`'s earlier
non-root-`USER` hardening sed-replaced `/var/run/nginx.pid`, but the
real `nginx:1.27-alpine` base image's config uses `/run/nginx.pid` (no
`/var` prefix) -- the sed silently matched nothing, so the frontend
container never actually started. `pytest` alone would never have
caught this, since nothing in the Python test suite exercises the built
Docker image; this is why this project's discipline of also curling the
real Docker-built stack, not just running tests, keeps mattering.

## Phase 5b: Valkey as a real event queue

`docker-compose.yml` has run a `valkey` service since Phase 1 -- the
brief explicitly asked for an event queue on Valkey rather than a
traditional MQ -- but nothing in the codebase ever published or
consumed an event through it; it was dead infrastructure until this
phase. `backend/app/activity_stream.py` closes that gap with the
smallest slice that makes Valkey load-bearing: `publish_activity_event`
`XADD`s onto a per-post stream key (`activity:{post_id}`, approximately
trimmed to the most recent 1000 entries so one very active post can't
grow the stream without bound), and `read_activity_events` reads it
straight back with `XREVRANGE`. Deliberately no consumer group and no
background worker -- the read path (`GET /api/posts/{post_id}/activity`)
queries the stream directly, which is the smaller real design for a
single reader; a consumer group is the natural next step if a second,
independent reader (e.g. a notification worker) is ever needed.

Wired into the two ticket-mutation endpoints (`ticket_created` on
create, `ticket_status_changed` on a status-changing `PATCH`) as the
first real producer, and surfaced in the popup as an `ActivityPanel`
(list + manual refresh) as the first real consumer. `make seed` XADDs
`ticket_created` for the seeded A-100 and calendar tickets so Activity
is not empty after a report-member click. Verified against
the actual Docker Compose network, not just `pytest`: created and
patched a ticket through the real `backend` container talking to the
real `valkey` container over the internal `redis://valkey:6379/0` DNS
name, confirmed the events on the activity endpoint, and independently
confirmed the stream's existence and length with `valkey-cli` directly
against the `valkey` container.

## Phase 5c: customer commitment derivation and the calendar

The brief asked for two separate-sounding things: issues auto-registered
as a to-do/calendar entry with LLM-authored content, and an LLM that
derives customer commitments from a post's text. Treated as one design,
not two: a derived commitment *is* the ticket that appears on the
calendar (`issue_ticket.due_date` + `commitment_summary`), reusing the
Phase 5 ticket infrastructure rather than inventing a parallel "to-do"
concept (ponytail: extend, don't duplicate).

`lineageweave/commitment_extraction.py` is the pluggable channel --
same discipline as `keyman_extraction.py`/`post_summary.py`:
`NullCommitmentExtractionClient` makes the channel unavailable, never
invents a commitment. A commitment specifically needs a resolved
deadline, so the prompt is given a reference date and asked to resolve
relative phrases ("by next Friday") against it -- closer to
temporal-expression normalization (Chambers & Jurafsky, 2008) than to
ACE-style key-event extraction (Doddington et al., 2004), which is why
it is its own client rather than a field bolted onto `post_summary`'s
key events. `has_commitment: false` is a legitimate result, not a parse
failure, the same missing-vs-empty discipline every parser in this repo
already keeps.

`POST /api/posts/{post_id}/derive-commitment` (`post_admin`, a real
LLM-call write action) persists the result as an `issue_ticket`. The
reference date handed to the client is the post's `created_at` (TimeML
document creation time), not wall-clock now -- otherwise a January
post's "by next Friday" lands on the Friday after the operator clicked
Derive. Re-deriving the same post updates the existing open commitment
ticket instead of stacking a duplicate calendar row. `GET /api/calendar`
lists every dated, not-closed ticket the account may see across all
posts, soonest first, ABAC-filtered per row the same way
`read_post_lineage` filters cross-post candidates. `due_date` is a
calendar `date`, not a `timestamptz`: a "by Friday" commitment is a
day, and binding a Python `date` into timestamptz midnight is an
off-by-one in any session whose TZ is not UTC. A malformed
`YYYY-MM-DD` is a 422, not a 500.

## Phase 5c follow-up: seeded calendar row

`scripts/seed_demo_data.py` inserts `fixtures.ambiguous_commitment_post`
(created_at 2026-01-05) and one open `issue_ticket` due 2026-01-09 so
`GET /api/calendar` is not empty on a freshly seeded stack. The same
seed writes the A-100 pricing ticket (`Send Northridge Grid the revised
quote`, due 2026-01-12) and the B-200 revision ticket (`Send Westfield
Power the revised specification`, due 2026-01-14) so home Calendar
lists the same dated tickets the period-report members already show.
Re-seed is idempotent. The empty-state copy is only for accounts that
truly have no dated open tickets.

## Phase 6-M2: authorized analysis-run evidence (read projection)

Issue #79's first buyer-visible Milestone 2 slice is a source-redacting
read of the #89 registry. `GET /api/analysis-runs` and
`GET /api/analysis-runs/{id}` require `post_read` and apply the scope
in SQL: the requester always sees their own run; a corporate-entity or
process-unit scope is visible only to affiliated accounts; a
thread-group scope is visible only when the account can already see a
post in that group; `all_visible` is requester-only. Hidden runs 404. Detail also lists ABAC-visible post titles in the
run's scope whose `created_at` is at or before `knowledge_cutoff`
(ADR 0016) so a buyer can open a post the run was allowed to know
without seeing later live rows or hidden bodies. Detail also returns
revision and configuration digest prefixes.
`POST /api/analysis-runs` records a Pending lineage run on a new
authorized cutoff capture (ADR 0017): snapshot, counts, frozen
membership, run, scope, and the first status in one transaction. TEPP
and period-report kinds are 422. Request a lineage reconstruction from
the home list after affiliated corps load (choose a corp if you walk
more than one), then open the Pending row to confirm the cutoff corpus.
`POST /api/analysis-runs/{id}/start` then commits Running plus a
durable outbox row, wakes Valkey, and delivers ThreadWeave on that
frozen bag (ADR 0021 / ADR 0023) or submits TEPP through
`tepp_client` (ADR 0022). It does not invent a TEPP score.
Request a lineage reconstruction from the home list, open the Pending
row, then start reconstruction. A Pending TEPP row starts a
measurement; a missing transport stays Failed /
`tepp_not_available`. Hover the Result digest
prefix, then confirm the designed A-100 fork before treating the live
Event Lineage panel as that run's tree.
`make seed` also records a TEPP measurement run through
`tepp_client` on that same snapshot; the default transport is
unavailable, so that run is Failed rather than a fabricated score.
The home list is clickable: `GET /api/analysis-runs/{id}` fills a
labeled detail (cutoff, requested date, 12-character digest prefixes
with full digests on hover, counts, status history)
without exposing a DSN or raw record. Opening a cutoff title still
shows the live body and names both clocks when the title was
rewritten after the run. A marked title also shows the body that
run knew (`GET /api/posts/{id}?as_of=`) so the operator can compare
two texts, not two clocks. Status history is detail-only
and uses lookup labels plus occurrence times; a failure event keeps
its machine `failure_code` rather than an invented caption. Failed
TEPP list rows add a next-action line (open the run, then connect the
measurement service) so `tepp_not_available` is not mistaken for a
calibrated negative result. A failed lineage row tells the operator
to retry reconstruction, not to connect TEPP. A failed period-report
row tells the operator to rebuild the report. A pending TEPP row
does not claim a calibrated measurement. A pending lineage row
says reconstruction has not started yet; open it and start
reconstruction. The
payload is lookup labels plus non-negative aggregate counts -- never
source SQL, a DSN, a raw record, or a provider body. After `make seed`,
Demo Analyst and Demo Admin see "Lineage reconstruction · Succeeded ·
Demo Corp" with "3 documents" and Pending / Running / Succeeded times,
the designed A-100 fork as clickable reconstructed edges, Claimed
then Delivered outbox times, and "TEPP measurement · Failed · Demo
Corp" whose detail history ends in Failed / `tepp_not_available`.
Seed also records "Period report · Succeeded · Demo Corp" on that
same snapshot after the calibrated report tables are written
(ADR 0024). Open that row to confirm the cutoff posts; mean θ stays
on the period-report panel. Start stays 422.
A run-bearing registry is emptied only after an unrevoked
`analysis_run_retention_grant` and `GRANT analysis_run_retention_admin`,
then `purge_analysis_run_registry('approved-retention-purge')`
(ADR 0020); a raw `DELETE` and a runtime role that only knows the
public phrase stay rejected. Repeated chip and close controls use
`frontend/src/styles/tokens.css` and the Storybook inventory.

## Phase 6a: fast-mlsirm dependency + Rust toolchain (infra only)

First of three staged slices toward the brief's weekly/monthly
PU/team/project reports (see
[ADR 0003](docs/adr/0003-fast-mlsirm-report-integration.md) for the
full reasoning). `fast-mlsirm` already implements the LLM-as-a-Judge
-> IRT-row -> Fixed-Item Parameter Calibration pipeline the brief asks
for, provider-neutrally against contextual-orchestrator -- this slice
makes it buildable and importable in this repo, with zero product
behavior change yet.

Pinned as a git dependency (`pyproject.toml`, same commit-pin pattern
as `rankweave`). It ships a PyO3/maturin Rust core with no PyPI wheel,
so `requires-python` moved from `>=3.10` to `>=3.12` (its own floor)
and `backend/Dockerfile`'s build stage gained a pinned, non-interactive
`rustup` install (`build-essential` for the C linker maturin needs,
`--profile minimal` since the build image needs `rustc`/`cargo` only,
not docs or clippy). The same pin is installed in the pytest CI job,
or `pip install -e ".[backend]"` cannot compile the extension. This
is the IRT compute library the brief names -- not a second TEPP, and
not a fork of TEPP's temporal engine (`tepp_client.py` is unchanged).
Verified both locally (`import fast_mlsirm._core` resolves to the
compiled extension, not the NumPy parity fallback) and against a
freshly built `backend` Docker image.

## Phase 6d: post evaluation IRT row (ADR 0003 slice 2)

Slice 2 of the report pipeline: a pluggable `PostEvaluationClient`
(`Null` / `ContextualOrchestrator` wrapping
`fast_mlsirm.ContextualOrchestratorJudge`) scores a post against a
versioned three-criterion rubric (constructive stance, negative
stance, sales-lead specificity). The only persist path is
`LLMJudgeResult.to_irt_row()` into `post_evaluation_response` (one
row per post per criterion, `common_lookup_value`-backed codes).
`POST /api/posts/{id}/evaluate` is an explicit post_admin action;
`GET /api/posts/{id}/evaluation` is the read. The post popup shows
the persisted categories and an "Evaluate post" button. `make seed`
writes constructed (not judged) rubric cells for the demo public
post and A-100/B-200 fixtures so the panel is not empty without an
LLM. Thetas still come only from `calibrate_period_report`.

## Phase 6e: calibrated period reports (ADR 0003 slice 3)

`lineageweave/period_report.py` assembles the stored IRT matrix,
fits GRM and GPCM via `fast_mlsirm.fit_polytomous` (Rust EM),
EAP-scores with `score_polytomous` (Bock & Mislevy, 1982), and
selects the model with `fixed_item_calibration_diagnostics`.
The first period free-calibrates a **shared** item bank
(`shared_metric` / `all`) on the pooled posts; every process unit,
corporate entity, and thread group is then FIPC-scored on that bank
so PU/team/project thetas stay on one metric. Later periods EAP-score
on those same fixed parameters (Kim, 2006 FIPC). After scoring,
`information_polytomous` ranks the shared-bank items by Fisher
information at the group's mean θ (Lord, 1980 max-info CAT). Rankings
persist to `report_item_information`. After those IRT main effects,
residual SVD leftover pairs on two Gabriel axes (Jeon et al., 2021;
ADR 0017 / 0048 / 0049 / 0119 / 0148 / 0158 / 0162 / 0163 / 0164 / 0168 /
0182 / 0185 / 0201 / 0233 / 0266 / 0267 / 0268 / 0269 / 0270 / 0271 / 0272 / 0273 / 0274 / 0275 / 0276 / 0277 / 0278 / 0279 / 0280 / 0281 / 0282 / 0283 / 0284 / 0285 / 0286 / 0287 / 0288 / 0289 / 0290) persist to `report_leftover_pair` with signed residual `R`,
observed `Y`, expected `E[Y|θ, item]`, full leftover-map rank, unexplained
leftover, ADR 0201 reconstruction evidence, ADR 0185 cross-share evidence,
ADR 0233 unexplained leftover share `s`, ADR 0266 explained leftover
share `e`, and ADR 0267 leftover-map coordinates `ξ_{1:2}` / `ζ_{1:2}`.
ADR 0268 draws those persisted coordinates as the leftover-map graphic
display above the pair buttons. ADR 0269 captions leftover-map axes 1
and 2 with persisted leftover-map axis share. ADR 0270 ticks those
leftover-map axes at persisted `ξ` / `ζ` coordinates so the pair-row
badge matches the plot. ADR 0271 captions leftover-map pair segments
with persisted leftover-map distance `d`. ADR 0272 captions leftover-map
pair segments with persisted leftover-map reconstruction `R̂`. ADR 0273
captions leftover-map pair segments with persisted leftover-map
explained leftover share `e`. ADR 0274 captions leftover-map pair
segments with persisted leftover-map unexplained leftover share `s`.
ADR 0275 captions leftover-map pair segments with persisted leftover-map
cross share `x`. ADR 0276 captions leftover-map pair segments with persisted leftover-map
unexplained leftover `U`. ADR 0277 captions leftover-map pair segments with persisted leftover
residual `R`. ADR 0278 captions leftover-map pair segments with persisted leftover
observed `Y`. ADR 0279 captions leftover-map pair segments with persisted leftover
expected `E`. ADR 0280 captions leftover-map pair segments with persisted leftover-map
rank. ADR 0281 captions the leftover-map graphic display with persisted leftover-map
complete-case coverage. ADR 0282 captions the leftover-map graphic display with
persisted leftover-map item complete-case coverage. ADR 0283 captions the leftover-map
graphic display with persisted leftover-map incomplete post coverage. ADR 0284
captions the leftover-map graphic display with persisted leftover-map incomplete
item coverage. ADR 0285 captions the leftover pair list with persisted leftover-map
item complete-case coverage. ADR 0286 captions the leftover pair list with persisted leftover-map
incomplete post coverage. ADR 0287 captions the leftover pair list with persisted leftover-map
incomplete item coverage. ADR 0288 fail-closes leftover-map post complete-case coverage
on the leftover pair list through leftoverMapCoverageCounts. ADR 0289 captions the
grouping comparison strip with persisted leftover-map post complete-case coverage
through leftoverMapCoverageCounts. ADR 0290 captions the grouping comparison strip
with persisted leftover-map item complete-case coverage through leftoverMapItemCoverageCounts.
ADR 0291 captions the grouping comparison strip with persisted leftover-map incomplete
post coverage through leftoverMapIncompletePostCount.
ADR 0292 captions the grouping comparison strip with persisted leftover-map incomplete
item coverage through leftoverMapIncompleteItemCount.
ADR 0293 captions grouping comparison leftover-pair buttons with persisted leftover-map
reconstruction `R̂` through formatLeftoverMapReconstruction.
ADR 0294 captions grouping comparison leftover-pair buttons with persisted leftover-map
explained leftover share `e` through formatLeftoverMapExplainedShare.
ADR 0295 captions grouping comparison leftover-pair buttons with persisted leftover-map
unexplained leftover share `s` through formatLeftoverMapUnexplainedShare.
ADR 0296 captions grouping comparison leftover-pair buttons with persisted leftover-map
cross share `x` through formatLeftoverMapCrossShare.
ADR 0297 captions grouping comparison leftover-pair buttons with persisted leftover-map
unexplained leftover `U` through formatLeftoverMapUnexplained.
ADR 0298 captions grouping comparison leftover-pair buttons with persisted leftover
residual `R` through formatLeftoverMapResidual.
ADR 0299 captions grouping comparison leftover-pair buttons with persisted leftover
observed `Y` through formatLeftoverMapObserved.
ADR 0300 captions grouping comparison leftover-pair buttons with persisted leftover
expected `E` through formatLeftoverMapExpected.
ADR 0301 captions grouping comparison leftover-pair buttons with persisted leftover-map
rank through formatLeftoverMapRank.
ADR 0302 captions grouping comparison leftover-pair buttons with persisted leftover-map
coordinates `ξ` / `ζ` through formatLeftoverMapCoordinates.
ADR 0303 returns persisted leftover-map coordinates `ξ` / `ζ` on
`GET /api/reports/compare/{period}` leftover pairs.
ADR 0304 draws the leftover-map graphic display of those already-named
coordinates above grouping comparison leftover-pair buttons when four
leftover-map axes are finite.
ADR 0305 returns persisted leftover-map axes on
`GET /api/reports/compare/{period}` and captions leftover-map axis share
on that grouping comparison leftover-map graphic when the persisted share
is finite.
ADR 0306 captions leftover-map complete-case coverage on that grouping
comparison leftover-map graphic when leftoverMapCoverageCounts returns usable
complete-case integers.
ADR 0307 captions leftover-map item complete-case coverage on that grouping
comparison leftover-map graphic when leftoverMapItemCoverageCounts returns usable
complete-case integers.
ADR 0308 captions leftover-map incomplete post coverage on that grouping
comparison leftover-map graphic when leftoverMapIncompletePostCount returns a usable
dropped integer.
ADR 0309 captions leftover-map incomplete item coverage on that grouping
comparison leftover-map graphic when leftoverMapIncompleteItemCount returns a usable
dropped integer.
ADR 0310 captions leftover-map reconstruction on that grouping
comparison leftover-map graphic when formatLeftoverMapReconstruction returns a usable
signed badge.
ADR 0311 captions leftover-map explained leftover share on that grouping
comparison leftover-map graphic when formatLeftoverMapExplainedShare returns a usable
badge.
ADR 0312 captions leftover-map unexplained leftover share on that grouping
comparison leftover-map graphic when formatLeftoverMapUnexplainedShare returns a usable
badge.
ADR 0313 captions leftover-map cross share on that grouping
comparison leftover-map graphic when formatLeftoverMapCrossShare returns a usable
badge.
ADR 0314 captions leftover-map unexplained leftover on that grouping
comparison leftover-map graphic when formatLeftoverMapUnexplained returns a usable
badge.
ADR 0315 captions leftover residual on that grouping
comparison leftover-map graphic when formatLeftoverMapResidual returns a usable
badge.
ADR 0316 captions leftover observed on that grouping
comparison leftover-map graphic when formatLeftoverMapObserved returns a usable
badge.
ADR 0317 captions leftover expected on that grouping
comparison leftover-map graphic when formatLeftoverMapExpected returns a usable
badge.
ADR 0318 captions leftover-map rank on that grouping
comparison leftover-map graphic when formatLeftoverMapRank returns a usable
badge.
ADR 0319 captions leftover-map distance on that grouping
comparison leftover-map graphic when formatLeftoverMapDistance returns a usable
badge.
ADR 0320 captions leftover-map coordinate ticks on that grouping
comparison leftover-map graphic from already-named leftover-map coordinates.
ADR 0321 captions leftover-map singular values on that grouping
comparison leftover-map graphic from already-named leftover-map axes.
ADR 0322 captions leftover-axis report badges with persisted leftover-map
singular values `σ_k`.
ADR 0323 captions leftover-axis report badges on the grouping comparison strip
with persisted leftover-map singular values `σ_k`.
ADR 0324 captions leftover-map graphic-display axes with persisted leftover-map
singular values `σ_k`.
ADR 0325 captions leftover-axis report badges with persisted leftover-map
singular values `σ_k` independently of leftover-map axis share.
ADR 0326 captions leftover-map comparison graphic leftover-map axes with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotAxisBadge returns a usable leftover-map
axis caption.
ADR 0327 captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapPlotTickAxisBadge returns a usable leftover-map
axis tick caption independently of leftover-map axis share.
ADR 0328 captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map
axis tick caption independently of leftover-map axis share.
ADR 0329 captions leftover-map comparison leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapCompareAxisTickBadge returns a usable leftover-axis
tick caption independently of leftover-map axis share.
ADR 0330 captions leftover-axis ticks with persisted leftover-map
singular values `σ_k` when leftoverMapAxisTickBadge returns a usable leftover-axis
tick caption independently of leftover-map axis share.
ADR 0331 captions leftover-map comparison graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapComparePlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption independently of leftover-map singular values.
ADR 0332 captions leftover-map graphic leftover-map axis ticks with persisted leftover-map
axis share when leftoverMapPlotTickAxisBadge returns a usable leftover-map axis tick leftover-map
axis share caption independently of leftover-map singular values.
ADR 0333 captions leftover-map comparison leftover-axis ticks with persisted leftover-map
axis share when leftoverMapCompareAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption independently of leftover-map singular values.
ADR 0334 captions leftover-axis ticks with persisted leftover-map
axis share when leftoverMapAxisTickBadge returns a usable leftover-axis tick leftover-map
axis share caption independently of leftover-map singular values.
ADR 0335 captions leftover-map graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapPlotCriterionBadge returns a usable leftover-map criterion leftover-map
item coordinate caption independently of leftover-map post ξ markers.
ADR 0336 captions leftover-map comparison graphic leftover-map criterion markers with persisted leftover-map
item coordinates when leftoverMapComparePlotCriterionBadge returns a usable leftover-map comparison graphic leftover-map criterion leftover-map
item coordinate caption independently of leftover-map post ξ markers.
ADR 0337 captions leftover-map comparison graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapComparePlotPostBadge returns a usable leftover-map comparison graphic leftover-map post leftover-map
person coordinate caption independently of leftover-map criterion leftover-map item coordinates.
ADR 0338 captions leftover-map graphic leftover-map post markers with persisted leftover-map
person coordinates when leftoverMapPlotPostBadge returns a usable leftover-map graphic leftover-map post leftover-map
person coordinate caption independently of leftover-map comparison graphic leftover-map post markers.
ADR 0339 captions leftover-map pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapListPostBadge returns a usable leftover-map pair leftover-map post leftover-map
person coordinate caption independently of leftover-map pair leftover-map criterion leftover-map item coordinates.
ADR 0340 captions leftover-map pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapListCriterionBadge returns a usable leftover-map pair leftover-map criterion leftover-map
item coordinate caption independently of leftover-map pair leftover-map post leftover-map person coordinates.
ADR 0341 captions leftover-map comparison leftover-pair leftover-map post with persisted leftover-map
person coordinates when leftoverMapCompareListPostBadge returns a usable leftover-map comparison leftover-pair leftover-map post leftover-map
person coordinate caption independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates.
ADR 0342 captions leftover-map comparison leftover-pair leftover-map criterion with persisted leftover-map
item coordinates when leftoverMapCompareListCriterionBadge returns a usable leftover-map comparison leftover-pair leftover-map criterion leftover-map
item coordinate caption independently of leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates.
ADR 0343 captions leftover-map graphic leftover-map axis origin ticks when leftoverMapPlotTickAxisBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values.
ADR 0344 captions leftover-map comparison graphic leftover-map axis origin ticks when leftoverMapComparePlotTickAxisBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values.
ADR 0345 captions leftover-map comparison leftover-axis origin ticks when leftoverMapCompareAxisTickBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values.
ADR 0346 captions leftover-map leftover-axis origin ticks when leftoverMapAxisTickBadge
returns a leftover-map origin tick caption independently of leftover-map axis share and leftover-map singular values.
ADR 0347 captions leftover-map graphic leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapPlotCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map person coordinates.
ADR 0348 captions leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapPlotPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map criterion leftover-map item coordinates.
ADR 0349 captions leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapComparePlotPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map graphic leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0350 captions leftover-map comparison graphic leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapComparePlotCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0351 captions leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapListPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map comparison graphic leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0352 captions leftover-map pair leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapListCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0353 captions leftover-map comparison leftover-pair leftover-map post leftover-map origin leftover-map person coordinates when leftoverMapCompareListPostBadge
returns a leftover-map origin leftover-map person coordinate caption independently of leftover-map pair leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0354 captions leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates when leftoverMapCompareListCriterionBadge
returns a leftover-map origin leftover-map item coordinate caption independently of leftover-map comparison leftover-pair leftover-map post leftover-map origin leftover-map person coordinates.
ADR 0355 captions leftover-map graphic leftover-map origin when leftoverMapPlotOriginBadge
returns a leftover-map origin caption independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map singular values.
ADR 0356 captions leftover-map comparison graphic leftover-map origin when leftoverMapComparePlotOriginBadge
returns a leftover-map origin caption independently of leftover-map graphic leftover-map origin, leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map singular values.
Click a post marker or a pair button
opens that post. Those ADRs are the normative mathematical, storage, and
display contracts. Leftover-map axis share
(Gabriel inertia of residual SVD axes 1 and 2; ADR 0148) persists to
`report_leftover_map_axis`. Complete-case leftover-map coverage (ADR
0168) persists to `report_leftover_map_coverage` so readers see how
many scored posts entered the factorization, including on the graphic,
and how many scored criteria entered the factorization on the graphic
and on the pair list,
and how many scored posts stayed incomplete and out of the factorization,
including on the pair list,
and how many scored criteria stayed incomplete and out of the factorization,
including on the pair list. Results persist to
`report_period_score` / `report_member_score`.
`GET /api/reports/{grouping}` lists the trend;
`GET /api/reports/{grouping}/{period}` is ABAC-filtered;
`GET /api/reports/compare/{period}` is the home-page grouping strip
and carries the same ABAC-filtered leftover pairs (ADR 0149) plus persisted
leftover-map complete-case coverage (ADR 0289), leftover-map item complete-case
coverage (ADR 0290), leftover-map incomplete post coverage (ADR 0291), leftover-map
incomplete item coverage (ADR 0292), leftover-map reconstruction `R̂`
(ADR 0293), leftover-map explained leftover share `e`
(ADR 0294), leftover-map unexplained leftover share `s`
(ADR 0295), leftover-map cross share `x`
(ADR 0296), leftover-map unexplained leftover `U`
(ADR 0297), leftover residual `R`
(ADR 0298), leftover observed `Y`
(ADR 0299), leftover expected `E`
(ADR 0300), leftover-map rank
(ADR 0301), leftover-map coordinates `ξ` / `ζ`
(ADR 0302), leftover-map coordinates on the compare leftover-pair payload
(ADR 0303), leftover-map graphic display on the grouping comparison strip
(ADR 0304), leftover-map axis share on the grouping comparison leftover-map
graphic (ADR 0305), leftover-map complete-case coverage on the grouping
comparison leftover-map graphic (ADR 0306), leftover-map item complete-case
coverage on the grouping comparison leftover-map graphic (ADR 0307), leftover-map
incomplete post coverage on the grouping comparison leftover-map graphic (ADR 0308),
and leftover-map incomplete item coverage on the grouping comparison leftover-map
graphic (ADR 0309), leftover-map reconstruction on the grouping comparison leftover-map
graphic (ADR 0310), leftover-map explained leftover share on the grouping comparison leftover-map
graphic (ADR 0311), leftover-map unexplained leftover share on the grouping comparison leftover-map
graphic (ADR 0312), leftover-map cross share on the grouping comparison leftover-map
graphic (ADR 0313), leftover-map unexplained leftover on the grouping comparison leftover-map
graphic (ADR 0314), leftover residual on the grouping comparison leftover-map
graphic (ADR 0315), leftover observed on the grouping comparison leftover-map
graphic (ADR 0316), leftover expected on the grouping comparison leftover-map
graphic (ADR 0317), leftover-map rank on the grouping comparison leftover-map
graphic (ADR 0318), leftover-map distance on the grouping comparison leftover-map
graphic (ADR 0319), leftover-map coordinate ticks on the grouping comparison leftover-map
graphic (ADR 0320), leftover-map singular values on the grouping comparison leftover-map
graphic (ADR 0321), leftover-map singular values on leftover-axis report badges
(ADR 0322), leftover-map singular values on leftover-axis report badges on the
grouping comparison strip (ADR 0323), leftover-map singular values on leftover-map
graphic-display axes (ADR 0324), leftover-map singular values on leftover-axis
report badges independently of leftover-map axis share (ADR 0325), leftover-map
comparison graphic leftover-map axis leftover-map singular values as leftoverMapComparePlotAxisBadge
(ADR 0326), leftover-map graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0327), leftover-map comparison graphic leftover-map axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0328), leftover-map comparison leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0329), leftover-axis tick leftover-map singular values independently of leftover-map axis share
(ADR 0330), leftover-map comparison graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0331), leftover-map graphic leftover-map axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0332), leftover-map comparison leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0333), leftover-axis tick leftover-map axis share independently of leftover-map singular values
(ADR 0334), leftover-map graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(ADR 0335), leftover-map comparison graphic leftover-map criterion leftover-map item coordinates independently of leftover-map post ξ markers
(ADR 0336), leftover-map comparison graphic leftover-map post leftover-map person coordinates independently of leftover-map criterion leftover-map item coordinates
(ADR 0337), leftover-map graphic leftover-map post leftover-map person coordinates independently of leftover-map comparison graphic leftover-map post markers
(ADR 0338), leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates
(ADR 0339), leftover-map pair leftover-map criterion leftover-map item coordinates independently of leftover-map pair leftover-map post leftover-map person coordinates
(ADR 0340);
`POST .../rebuild` scores every grouping kind (post_admin). `make seed`
folds A-100/B-200 Event Lineage fixtures (and the Riverbend calendar
post) that already have constructed IRT cells into the same shared
bank as the dummy high/low band rows, so comparison-strip click
through opens those DAG posts. Report members include the earliest
open ticket title, status lookup label, and due date when one exists. The home page renders
the actual mean θ, the FIPC delta, the CAT-selected item, leftover
closest/farthest pairs (signed residual `R`, observed `Y`, expected
`E`, full rank, two-axis leftover-map distance `d`, and leftover-map
coordinates `ξ` / `ζ` after IRT main
effects) above the member list, leftover-map axis share for residual
SVD axes 1 and 2, and complete-case coverage captions (map used N of M
scored posts), plus the

closest/farthest pairs above the member list, leftover pairs on the
grouping comparison strip, and the
PU / corp / thread comparison -- never a placeholder. TEPP is unchanged.

## Phase 6b: Knowledge Graph as a real Ontology + Semantic Layer

The brief's latest revision marks every Knowledge Graph use (Keyman
traversal, the customer/corporate hierarchy tree, entity-relationship
classification, indirect lineage linking, in-popup chat evidence) as
requiring a real Ontology and Semantic Layer, "FULL 표준." See
[ADR 0004](docs/adr/0004-knowledge-graph-ontology.md) for the full
reasoning; in short: `knowledge_graph_edge` was already, structurally,
an RDF triple (subject/predicate/object) -- the gap was that its
vocabulary had never been published as a real, machine-checkable
ontology, so nothing could verify the relational schema's controlled
vocabulary (`node_type`, `edge_type`, `entity_relationship_type`,
`person_side`, `corporate_entity_level`) actually matches what the
Ontology/Semantic-Layer claim implies.

`docs/ontology/lineageweave-kg.ttl` and its deterministic governed fragments
are a real OWL 2 / RDFS / SKOS
ontology in Turtle syntax: classes for `Post`/`Person`/`CorporateEntity`
(with `OurSidePerson`/`CounterpartyPerson` subclasses), object
properties for each `edge_type_code` and `entity_relationship_type`
code with declared `rdfs:domain`/`rdfs:range`, and the corporate
hierarchy level ladder (Group -> Company -> Plant) as a proper SKOS
concept scheme with `skos:broader`/`skos:narrower` -- SKOS being the
W3C standard specifically for organizational/concept hierarchies, as
distinct from OWL class subsumption. PostgreSQL stays the source of
record for actual graph data; the ontology is the published semantic
specification over it, in the same sense W3C's own stack uses "semantic
layer" (RDFS/OWL as the governed conceptual layer over raw data), not a
separate BI-metrics product and not a parallel triple store.

`lineageweave/ontology.py` parses the Turtle source tree once with `rdflib`
(pure Python, no Rust toolchain, unlike `fast-mlsirm`) and exposes the
vocabulary as importable IRI constants, so application code has one
canonical name per class/property instead of re-typing lookup codes as
bare strings. `GET /api/keymen/{id}/related` spreads
`ontology_annotations(node_type_code)` onto each hydrated node so the
popup can render the class label (`Person`, `Post`, `Corporate entity`)
instead of the raw lookup code. `tests/test_ontology.py` is the real correctness check --
not just "does the file parse," but a round-trip against
`scripts/seed_demo_data.py`'s own committed SQL, in both directions:
every lookup code the seed script inserts (for the categories this
ontology covers) must have a matching ontology term, and the ontology
must not declare a term for a code nothing actually seeds. This is the
enforcement mechanism: a future PR that adds a new `edge_type` or
`entity_relationship_type` code without updating the ontology fails
this test, not just a docstring's word.

### Authorized job architecture snapshots

The public SOC/O*NET vocabulary and an employer's job architecture remain
different graphs. ADR 0263 adds an organization-scoped PostgreSQL source
boundary for private job-family/job-series snapshots: immutable source
metadata owns normalized nodes, source-declared broader/narrower edges, and
optional explicit bindings to a versioned external occupation scheme. An edge
table preserves multiple-family membership; the importer rejects cycles and
never derives a parent or binding from a label or code pattern. The snapshot
is source evidence only. It does not create a person, post, organizational
unit, competency, score, weight, or ontology assertion, and runtime rows never
enter repository artifacts.

## Phase 6c: post content normalization before any LLM/embedding call

The brief's latest revision calls out, explicitly, that a post body mixing
HTML tags and base64-embedded images needs care before Knowledge Graph
derivation: raw tags degrade an embedding model (Cai, Yu, Wen, & Ma,
2003 -- VIPS's premise that a DOM's visual/structural cues, e.g. a
block's tag and inline style, carry real segmentation signal and should
be extracted as *metadata*, not left inline to dilute the text an
embedding or LLM call actually reads), and font color/alignment/bullet/size
information needs to be stored separately rather than dropped. Auditing
every backend endpoint that reads `source_post.post_body` found this gap
was real, not hypothetical: `chunking.py` (DOM-aware chunking) and
`image_content.py` (vision-model description of embedded images) already
existed and were already tested, but no `backend/app/*.py` endpoint
imported either one -- `extract-keymen`, the summary endpoint, commitment
derivation, and chat source retrieval all sent the raw `post_body` column
straight to an LLM call, HTML tags, base64 image payloads, and all.

`lineageweave/post_content_normalization.py` closes that gap with one
function, `normalize_post_body(body, vision_client=None)`. For a body
that isn't HTML (`_looks_like_html` -- a real tag such as `<p>`/`<img>`,
not a comparison like `qty < 50 and price > 10`), it is returned
unchanged; there is no cost to imposing DOM parsing on a plain-text VOC
record. For HTML, it reuses `chunk_by_dom` and, per chunk: text
becomes a `text_parts` entry (with its `style` attribute, if any,
recorded as a separate `FormattingHint(chunk_index, tag, style)` --
never appended into the text a model reads); an image chunk is described
through `vision_client.describe()` and replaced in-place with
`[image: <caption> | text: <ocr>]` at its original document position
(OCR text is kept -- it is what the vision call paid for, and a name
or figure in a screenshot is otherwise lost). Position matters: an
image before or after a given paragraph changes what it is evidence
for. A vision-provider exception is caught per-image so one bad
call degrades to `[image: content unavailable]` instead of losing the
rest of the post; `vision_client=None` behaves the same way by default
(`NullImageContentClient`, `available=False`), so the function is always
safe to call without a live provider configured.

`chunking.py` gained the actual DOM-level capture this depends on:
`_DOM_BLOCK_TAGS` now includes `h1`-`h6` (a heading's tag name is itself
a VIPS-style importance cue, not just more paragraph text), and
`Chunk.style` carries a block's `style` attribute (`None`, not `""`,
when absent) alongside its text -- `_BlockTextExtractor` tracks it
through the existing start/end-tag stack rather than adding a second
pass over the document.

Wiring: `backend/app/main.py`'s `_vision_client()` factory
returns a real `OpenAiCompatibleVisionClient` (via
`orchestrator_vision_client`, which appends `/v1` so the same
`ORCHESTRATOR_BASE_URL` other channels use lands on
`/v1/chat/completions`) when base URL and API key are set, else
`NullImageContentClient()`. The request omits `model`; contextual-orchestrator
selects the registered vision-capable agent. It is
called at all three raw-`post_body`-reading endpoints (`extract-keymen`,
post summary, commitment derivation) and threaded through
`post_chat_ingestion.gather_chat_sources()` so every RAG source document
in a chat answer -- not just the post the popup is currently open on --
is normalized before the reason-and-cite LLM call sees it.
`GET /api/posts/{id}` (the plain post-detail read) is deliberately left
untouched: the frontend renders the post as-authored, and normalizing
that response would mean users never see their own formatting.

Proven against a real orchestrator instance, not just unit tests: an
HTML-wrapped, base64-image-embedded version of the existing
`ambiguous_keyman_post()` fixture still correctly extracts the same real
people through the live `/extract-keymen` endpoint
(`test_extract_keymen_normalizes_html_and_embedded_image_content`).

## Phase 6d: external search verification for Ontology relation inferences

The brief requires an external web/internal search agent to check the
truthfulness of Knowledge Graph relation inferences (Searxng named as an
acceptable implementation) -- see
[ADR 0005](docs/adr/0005-relation-verification-agent.md) for the full
reasoning. `entity_relationship_classification.py`'s LLM output (an
organization name plus a VOC/VOM/VOP/VOCC/VOCO/VOS relationship) is the
concrete target: both the organization and the relationship are the
model's inference, and nothing previously checked whether the named
organization has any real-world footprint at all.

`lineageweave/relation_verification.py` is grounded in FEVER-style
open-domain claim verification (Thorne, Vlachos, Christodoulopoulos, &
Mittal, 2018): retrieve external evidence, then classify the claim
against it. The implemented subset is deliberately coarse --
presence/absence of any search result (`verify_corroborated` /
`verify_uncorroborated`), catching the failure mode actually observed
(a hallucinated organization with zero web footprint), not full
NLI-based entailment scoring against retrieved passages. The real
client, `SearxngRelationVerificationClient`, queries a **self-hosted**
Searxng instance (`docker/searxng/`, a new Docker Compose service on a
non-default host port like every other service here) -- never a
third-party hosted search API requiring its own key, and never a
"channel unavailable" report where Docker Compose can instead genuinely
run the dependency.

`post_counterparty_entity` gained `verification_status_code`
(`common_lookup_value` category `relation_verification_status`),
`verification_evidence_url`, and `verification_checked_at`
(`migrations/0001_initial_schema.sql`, with `0004_relation_verification.sql`
as the idempotent upgrade path). A re-classification resets these back
to `verify_pending` -- a prior verification was checked against the OLD
relationship label. Trigger: a separate, explicitly-invoked
`POST /api/posts/{id}/verify-relations`, matching this repo's existing
pattern for real-cost actions (summary, commitment derivation) that the
user triggers rather than a hidden side effect of extraction. The
post-detail popup's Counterparties section (new `CounterpartyPanel`
component, `frontend/src/App.tsx`) renders a status badge per row --
linked to the evidence URL when corroborated -- with a "Verify against
web search" action while any row is still pending.

Proven against a real, self-hosted Searxng instance, not a mocked
search client: `test_verify_relations_persists_real_search_outcomes`
checks a well-known public foundation name ("Mozilla Foundation")
against a deliberately fabricated one in the same request, asserting
the former comes back `verify_corroborated` with a real evidence URL
and the latter `verify_uncorroborated` with none.

## Phase 7: R&R's named actor is a PROV-O Agent, not always a person

`post_summary.py`'s R&R extraction forced every named actor into a
person slot, but business correspondence routinely names an
organization acting in its own name ("당사" [our company],
"Demo Corp"), not an individual. See
[ADR 0006](docs/adr/0006-role-responsibility-agent-ontology.md).

Grounded in W3C PROV-O (Lebo, Sahoo, & McGuinness, 2013):
`RoleResponsibility` (renamed field `actor_name`, was `person_name` --
the field can hold an organization's name now, so "person" in the name
would be wrong) gains `actor_type_code` (`prov_person` /
`prov_organization`, defaulting to person when the model omits it) and
`affiliated_organization_name` (an LLM-inferred affiliation for a
person actor, since a bare name without an employer is hard to place).
The ontology gains `:RoleActorPerson rdfs:subClassOf prov:Person` and
`:RoleActorOrganization rdfs:subClassOf prov:Organization` -- genuine
subclasses of the real external PROV-O classes (imported via the
`prov:` namespace), kept distinct from the ontology's existing `:Person`
(node_type's cataloged Keyman with a stable `person_id`) since an R&R
actor is a free-text name with no cataloged identity of its own.
`migrations/0060_role_responsibility_agent_type.sql` renames the
`post_summary_role` column via `RENAME COLUMN` (preserves existing
rows) rather than a drop/recreate. The popup's R&R list shows a
Person/Organization badge and the inferred affiliation; only a person
actor still links to the Keyman panel.

## Phase 8: same-name Keymen are not silently merged; titles are captured

Two different real people can share a name -- `keyman_extraction.py`
never captured a stated job title/position, so nothing distinguished
"Kim Cheolsu, sales manager" from an unrelated "Kim Cheolsu, purchasing
lead" beyond the bare name. `PersonMention` gains `job_title: str |
None`, and the extraction prompt now explicitly asks for one when the
text states it (never left out as a same-name disambiguation signal).

Persistence, in two places for a reason: `person_affiliation.role_title`
(a schema column that already existed, previously never populated) for
a title tied to a specific organization, and a new
`cataloged_person.last_known_job_title` (`migrations/0013_person_job_title.sql`)
for a title stated without a named organization to attach it to (e.g.
"our legal counsel, Sam Okonkwo" -- `fixtures.ambiguous_keyman_post()`'s
own real example, which has zero affiliated organizations for Sam).
Both feed `_upsert_person`'s disambiguation check
(`backend/app/keyman_ingestion.py`): a same person_name+person_side_code
match is only reused when the new mention's stated title, if any, does
not conflict with a title already on file -- a genuine stated conflict
creates a fresh `cataloged_person` row instead of merging two different
people. A missing title on either side is not treated as a conflict
(titles legitimately change -- a promotion -- and most mentions state no
title at all), so this only splits on an actual stated disagreement,
verified by a real test that two posts naming the same name with
genuinely different stated titles produce two distinct person rows.

## Phase 9: an R&R actor can be a team, meso-level between person and organization

Real post text named "설계팀" (design team) -- neither a person nor the
company itself, but a sub-unit of one. See
[ADR 0007](docs/adr/0007-team-actor-type.md). `actor_type_code` gains a
third value, `prov_team`, grounded in the W3C Organization Ontology's
`org:OrganizationalUnit` (Reynolds, 2014) -- a different, complementary
W3C vocabulary from PROV-O (which models "who acted," not "how a
company is internally structured"). The prompt now offers three actor
types and requires `affiliated_organization_name` for a team actor too
(not just a person): a team's own name never answers "which company,"
unlike an organization actor's. `migrations/0014_role_responsibility_team_actor_type.sql`
adds the lookup row -- purely additive, no schema change, since
`actor_type_code` already stores an arbitrary FK'd code.

## Phase 10: an abbreviated organization name is resolved and search-verified, not left opaque

Real post text names organizations by abbreviation ("AGP" for
"Aurora Grid Power") that character-similarity matching
(`corporate_hierarchy_resolution`) structurally cannot bridge -- an
initialism shares almost no substring with its expansion. See
[ADR 0008](docs/adr/0008-organization-abbreviation-resolution.md).

New module `lineageweave/organization_name_resolution.py`: an LLM
proposes the full name from context (or declines with `UNKNOWN`), then
the *existing* `relation_verification` Searxng client cross-verifies
the specific raw/resolved pairing (no second web-search integration
built). Only a search-corroborated resolution is ever substituted in
for `resolve_corporate_entity` -- an unresolved or unverified name
still flows through unchanged. Cached in a new
`organization_name_resolution` table
(`migrations/0015_organization_name_resolution.sql`) keyed by the raw
name, so the same abbreviation across many posts is resolved once.
Grounded in SKOS `skos:altLabel`/`skos:prefLabel` (Miles & Bechhofer,
2009). After a pair is search-corroborated, both labels compete as
virtual candidates for the **same** `corporate_entity_id`, so a later
mention of `AGP` or `Aurora Grid Power` reuses one catalog row instead
of inserting a second `AUTO-` identity (ADR 0160). Wired into
`backend/app/keyman_ingestion.py`'s affiliation loop
and the offline synthetic-batch script's paced re-implementation of it
(the batch script's own copy was also missing `role_title` persistence
entirely -- fixed alongside this).

Buyer-facing organization chips (affiliate tree, Keyman affiliation,
counterparty, related corporate node) project the *other* corroborated
label as `organization_alias` only when the pair resolves to the same unique
catalog id already carried by the chip, and render `Demo Corp (DC)` (ADR 0170).
A miss, pending row, same-name catalog tie, id mismatch, or identical labels
stays unlabeled. The mapping is not copied onto affiliation rows; it is read
from `organization_name_resolution` at hydrate time. Seed
writes the synthetic `DC` / `Demo Corp` pair so the walk is clickable
after `make seed`.

Also fixed while running this against synthetic embedded-image fixtures:
`image_content.py`'s `_parse_description` required an exact single-pass
`TEXT:`/`CAPTION:`/`TAGS:` match, which was rejecting real vision
responses whose formatting was close but not exact (markdown-bolded
labels, reordered labels, a missing TAGS line) -- silently producing
the same "content unavailable" placeholder as a genuinely unconfigured
vision channel. Fields are now recovered independently per label line;
only a response with neither TEXT nor CAPTION is treated as unusable.

## Phase 11: R&R team/organization actors get a shared cross-post identity

Extraction runs per-post; a team's or organization's identity did not
survive across posts the way a Keyman's already did via
`cataloged_person`. See
[ADR 0009](docs/adr/0009-cross-post-actor-identity.md). New
`cataloged_team` catalog (`migrations/0016_cross_post_actor_identity.sql`,
identity key `(team_name, affiliated_organization_name)` -- a bare team
name like "설계팀" is not by itself identifying) plus two mention join
tables (`post_team_mention`, `post_organization_mention`); an
organization actor reuses the existing `corporate_entity` catalog, no
new table needed. `lineageweave/knowledge_graph.py`'s
`knowledge_graph_edges_for_post` extended with three new edge kinds
(`edge_mention_team`, `edge_team_affiliation`, `edge_mention_organization`);
`backend/app/post_summary_ingestion.py`'s `persist_post_summary` now
resolves each R&R actor's identity, stores that id on
`post_summary_role` (ADR 0019 — `entity_name` is not unique), and calls
the same `persist_edges_for_post` Keyman ingestion already uses. A person R&R
actor is opportunistically joined to an existing `cataloged_person` row
by name (never originated by R&R itself -- documented gap in the ADR:
`cataloged_person` needs `person_side_code`, which R&R's prompt does
not currently capture). ADR 0019 stores that resolved catalog id on
`post_summary_role` (`cataloged_team_id` /
`cataloged_corporate_entity_id` / `cataloged_person_id`, ADR 0019 /
0027) so a later read does not rejoin `corporate_entity` by
`entity_name`. Fetch returns the person foreign key as
`catalog_node_id` the same way. Historical backfill leaves a role
unbound when two same-named mentions already exist on the post.
Open a post whose R&R names an organization that shares a display name
with another catalog row: the chip keeps the id persist stored. Click
it to walk that organization, not the homonym. Click a person chip to
walk the stored person even when Keyman was not extracted on that post.

## Phase 12: a real counterparty organization is auto-created, not left permanently unresolved

`corporate_hierarchy_resolution`'s similarity matching only ever finds
an ALREADY-cataloged entity. Real Milestone 2 data confirmed the actual
gap: 0 of 4,154 person affiliations and 0 of 9,852 R&R organization
mentions ever resolved -- the standing "통합 고객사 계열 tree AI"
requirement was never actually populated. See
[ADR 0010](docs/adr/0010-corporate-hierarchy-auto-creation.md).

New `lineageweave/corporate_hierarchy_inference.py` proposes a
Group/Company/Plant placement from context; new
`backend/app/corporate_entity_ingestion.py`'s
`get_or_create_corporate_entity` tries similarity matching first, then
creates a real new `corporate_entity` row once the proposal is
Searxng-corroborated (reusing `relation_verification`, no new search
integration), recursing up a bounded parent chain so the whole
hierarchy gets real links. Auto-created rows get a deterministic
`AUTO-`-prefixed code so they can never collide with a real login corp
code. Wired into both `keyman_ingestion.py`'s affiliation loop and
`post_summary_ingestion.py`'s R&R organization-actor loop.
## Standards-complete W3C PROV-O provenance layer

ADR 0011 separates standards-complete provenance from the compact
buyer-facing navigation graph. `lineageweave/prov_o.py` validates
and materializes all 50 normative PROV-O properties, including
literal-valued times/values and qualified Influence resources.
`migrations/0017_prov_o_standard_relations.sql` stores definitions,
class/property hierarchies, domains, ranges, qualification maps,
inverse names, typed resources, literals, assertions, and inference
premises in third normal form. Existing product nodes cross the
boundary only through `provenance_resource_binding`; projection to
`knowledge_graph_edge` is explicit and reversible.

See `docs/PROV_O_IMPLEMENTATION.md`, the complete implementation
matrix, and `docs/adr/0011-prov-o-standard-relations.md`.

## Phase 13: corporate-entity creation is serialized against a real observed deadlock

Phase 12's creation path made real concurrent writes for the first
time. A synthetic regression corpus batch run under real concurrency surfaced a
genuine `DeadlockDetectedError`: two concurrent transactions each
creating a different new entity, mentioned in opposite order across
two different posts, took row-level locks in opposite order and
deadlocked. See [ADR 0012](docs/adr/0012-corporate-entity-creation-lock.md).

`get_or_create_corporate_entity` now takes a single named Postgres
advisory transaction lock (`pg_advisory_xact_lock`) immediately before
the write -- never held across the slow LLM inference/Searxng
verification calls that precede it -- and re-checks candidates fresh
under the lock before inserting. The lock key is fixed, not per-name,
so it also covers the multi-entity opposite-order case a per-name lock
would still deadlock on. Every already-cataloged entity still resolves
through the unchanged, lock-free similarity-matching fast path; only
the rare creation branch serializes.
