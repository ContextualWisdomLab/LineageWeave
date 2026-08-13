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
| `affiliate_tree.py` | Ancestor forest of the organizations a post's Keymen touch -- resolved rows walk `parent_entity_id`, unresolved names stay roots |
| `voc_evidence.py` | Extractive VOC excerpts: sentences that name a classified organization, or empty |
| `post_summary.py` | Pluggable LLM Korean summary + key events + R&R derivation for a post |
| `post_chat.py` | Pluggable in-popup chat's reason-and-cite step (retrieve step lives in `backend/app/post_chat_ingestion.py`) |
| `commitment_extraction.py` | Pluggable LLM derivation of a customer commitment (promise + deadline) from a post; `Null` default, `ContextualOrchestrator` real impl |
| `ontology.py` | Loads `docs/ontology/lineageweave-kg.ttl`, the formal OWL 2/RDFS/SKOS vocabulary for the Knowledge Graph's node/edge types (ADR 0004) |
| `period_report.py` | Fit GRM/GPCM on persisted IRT rows, FIPC-select, EAP-score a period (ADR 0003 slice 3; Bock & Mislevy, 1982) |
| `fixtures.py` | Synthetic demo dataset -- no real data ships in this repo |
| `server.py` | Stdlib HTTP server: `GET /api/lineage` (JSON graph) + static viewer |
| `web/index.html` | Self-contained SVG DAG viewer, no build step, no external script dependency |

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
(`{nodes, edges}`) from persisted `post_lineage_edge` rows. Each node
includes `group` from the same `reconstruct_group_key()` rebuild uses
(persisted `thread_group_key`, else process unit, else corp).
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
persisted in `post_summary_result` so a seeded demo -- including
A-100/B-200 Event Lineage nodes and the calendar commitment -- is
not empty without a live LLM), and
`POST /api/posts/{post_id}/chat` (`lineageweave/post_chat.py`'s
reason-and-cite step over `gather_chat_sources`' retrieve step -- both
Event-Lineage link kinds feed the chat's context, ABAC-rechecked per
candidate post). A missing orchestrator is 503; the popup shows
`Chat unavailable (LLM orchestrator not configured)` rather than a
raw HTTP status -- never a fabricated answer. Evaluate, Extract
Keymen, Derive commitment, and Verify use the same 503 empty-state
pattern for a missing orchestrator or search service. `find_linked_post_ids` first expands to every post
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
Keycloak issued; `src/App.tsx` renders a git-branch SVG of
`GET /api/lineage` (click a node to open that post; `post_admin` can
rebuild), the post list, and a full detail popup: Korean
summary/key-events/R&R, VOC evidence excerpts, an Event Lineage panel
(direct vs. indirect links; a link opens that post), the Keyman
affiliate tree (resolved ancestors plus unresolved org roots), Keyman +
counterparty panels (a Keyman click loads RWR related nodes;
`post_admin` can extract), and an in-popup chat whose cited sources
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
starts from the affiliation the buyer clicked. An affiliation that did not resolve to
a `corporate_entity` row stays as its own root (`resolved=false`); that
is the same never-guess-a-parent rule
`corporate_hierarchy_resolution` already applies. Entity levels and
Keyman sides are labeled from `common_lookup_value` (`Our side`,
`Plant`, `Company`) so the popup never shows raw `our_side` / `plant`
codes when a label exists.

`GET /api/posts` and `GET /api/posts/{post_id}` include
`voc_type_label` / `visibility_label` from `common_lookup_value` so
the list badge and popup meta show `Voice of Customer` / `Public`
instead of raw codes.

`GET /api/posts/{post_id}/voc-evidence` returns the
`common_lookup_value` label for the post's `voc_type_code` plus the
sentences in the post body that name a counterparty or affiliated
organization (`lineageweave/voc_evidence.py`). A name that does not
appear yields no excerpt. Each counterparty also carries
`verification_status_code` / `verification_evidence_url` so the VOC
panel shows the same Searxng badge as Counterparties. `make seed` writes Ada West / Priya Nair /
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
list/create/status-update UI for it. `make seed` opens tickets on the
A-100 follow-up and delivery fixtures so a report-member click is not
"No tickets yet."

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
`GET /api/calendar` is not empty on a freshly seeded stack. Re-seed
is idempotent. The empty-state copy is only for accounts that truly
have no dated open tickets.

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
persist to `report_item_information`. Results persist to
`report_period_score` / `report_member_score`.
`GET /api/reports/{grouping}` lists the trend;
`GET /api/reports/{grouping}/{period}` is ABAC-filtered;
`GET /api/reports/compare/{period}` is the home-page grouping strip;
`POST .../rebuild` scores every grouping kind (post_admin). `make seed`
folds A-100/B-200 Event Lineage fixtures (and the Riverbend calendar
post) that already have constructed IRT cells into the same shared
bank as the dummy high/low band rows, so comparison-strip click
through opens those DAG posts. The home page renders the actual mean
θ, the FIPC delta, the CAT-selected item, and the PU / corp / thread
comparison -- never a placeholder. TEPP is unchanged.

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

`docs/ontology/lineageweave-kg.ttl` is a real OWL 2 / RDFS / SKOS
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

`lineageweave/ontology.py` parses the Turtle file once with `rdflib`
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

Wiring: `backend/app/config.py` gained `Settings.vision_model` (env
`VISION_MODEL`) -- empty means the vision channel is unavailable, the
same "no fake channel" discipline as every other pluggable client, not a
guessed default model. `backend/app/main.py`'s `_vision_client()` factory
returns a real `OpenAiCompatibleVisionClient` (via
`orchestrator_vision_client`, which appends `/v1` so the same
`ORCHESTRATOR_BASE_URL` other channels use lands on
`/v1/chat/completions`) only when base URL, API key, and model are all
set, else `NullImageContentClient()`; it is
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
