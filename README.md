# LineageWeave

Reconstructs git-branch-style lineage DAGs from scattered short records --
turns a flat pile of loosely-grouped, timestamped items into a browsable set
of branching threads, without any explicit "this follows from that" link
existing in the source data.

```
group A-100
  rec-001  Initial site visit and project scope discussion
      └─ rec-002  Pricing renegotiation follow-up
           ├─ rec-003  Pricing renegotiation: revised quote sent
           └─ rec-004  Delivery schedule question raised
                └─ rec-005  Delivery schedule confirmed with logistics
  rec-006  Unrelated: annual account review   (own root -- no forced match)
```

This is a **demo prototype**: it ships with synthetic sample data only
(`lineageweave/fixtures.py`) and no connection to any real dataset or
organization.

The supporting [product requirements](docs/product-requirements.md) define
the product outcomes, non-goals, ecosystem boundaries, and release evidence;
ADRs remain normative for architecture and policy.

## Why

Given a pile of records with no native cross-record link, no single cheap
signal reliably tells you which record continues which -- see
[`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md) for
the validation numbers and the literature this design follows. LineageWeave
fuses several independent, individually-weak signals (temporal proximity, a
shared grouping key, text similarity, and an optional LLM judgment) instead
of trusting any one of them alone. The normative research-grounding policy is
[ADR 0084](docs/adr/0084-lineage-research-grounding.md); the linked notes
retain the supporting bibliography and aggregate evidence.

## How it fits with the rest of the ecosystem

LineageWeave is a thin orchestration/BI layer. It does not do its own
psychometric or statistical estimation -- that stays inside
[TEPP](https://github.com/ContextualWisdomLab/TEPP) (Rust), consumed here
purely through TEPP's own published wire contract
(`lineageweave/tepp_client.py`, `AnalysisRunRequest` v1), never by reading
TEPP's tables or reimplementing TEPP's model. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why the "computation layer must be
Rust + GPU/CPU multithreaded" rule that applies to TEPP does not apply to
this repo.

The optional LLM-adjudication channel calls
[contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
(`lineageweave/adjudication_client.py`). Tree assembly reuses
[ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave) (JWZ
message threading) and channel fusion reuses
[RankWeave](https://github.com/ContextualWisdomLab/RankWeave) (weighted
score fusion for reconstruction and the fail-closed Rankings port) -- both real dependencies, not reimplemented here.

## Run it

```bash
pip install -e .
python -m lineageweave.server
# -> http://127.0.0.1:8420
```

Or use the library directly:

```python
from lineageweave import reconstruct
from lineageweave.fixtures import sample_records

trees = reconstruct(sample_records())
for tree in trees:
    print(tree.group_key, "branch points:", tree.branch_points())
```

## Bring your own data

Map your records into `lineageweave.Record` (see `lineageweave/models.py`
for the field docs) and call `reconstruct()` directly -- nothing in this
package assumes any particular source schema.

To turn on the embedding or LLM channels, pass a real client instead of the
`Null*` defaults:

```python
from lineageweave import reconstruct
from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient

llm = ContextualOrchestratorAdjudicationClient(base_url="http://localhost:8000", api_key="...")
trees = reconstruct(my_records, llm=llm)
```

## Test

```bash
pip install -e ".[dev]"
pytest
```

## Local product stack (Docker Compose)

The reconstruction library above is being wrapped in a real product (see
[ARCHITECTURE.md](ARCHITECTURE.md#product-schema-phase-1-of-a-larger-roadmap)
and [ADR 0001](docs/adr/0001-demo-identity-and-data-boundary.md)). Phase 1's
infrastructure -- PostgreSQL, Valkey, and a real Keycloak OIDC realm seeded
with synthetic demo accounts -- runs via Docker Compose:

```bash
make up      # docker compose up -d: postgres, valkey, keycloak
make smoke   # real login as the synthetic demo user + JWT signature
             # verification against Keycloak's live JWKS -- proves the
             # OIDC round-trip actually works, not just that containers
             # started
make down
```

Outside GitHub, `make up` reads `~/.env` through Compose's `--env-file`.
Configure the contextual-orchestrator provider there with
`LLM_GATEWAY_API_URL` and `LLM_GATEWAY_API_KEY`; the key is never committed or
printed. `LLM_GATEWAY_URL`, `LLM_API_GATEWAY`, and `LLM_API_KEY` remain
compatibility aliases only. `ORCHESTRATOR_BASE_URL` and
`ORCHESTRATOR_API_KEY` are separate, internal
LineageWeave-to-orchestrator settings.

The Compose file declares `lineageweave` as its canonical default project, so
the same eight-service synthetic stack is addressed from the repository and
temporary worktrees. Isolated tests may override it explicitly with `-p`; use
`docker compose down` without `-v` when retiring such a project so its named
volumes remain recoverable (ADR 0224).
The bundled Keycloak realm is the standalone/local/dev/test fallback only.
Setting `KEYVERSE_ISSUER` selects central Keyverse for both backend and
frontend and activates the fail-closed claim binding in ADR 0156; the two
issuers are never combined as authorization authorities.

Postgres and Keycloak are built (`docker/postgres-init/`, `docker/keycloak/`)
rather than bind-mounted, so the keycloak database's init script and the
realm seed ship inside the images themselves -- portable to any Docker host
or CI runner, no assumption about a shared local filesystem layout.

Demo accounts (`docker/keycloak/realm-export.json`) are synthetic:
`demo.analyst` / `demo.admin`, password `lineageweave-demo-only`, each
carrying `corp_code` / `pu_code` as token claims -- these are throwaway
local-dev credentials in a locally-run realm, never the org's real Keyverse
tenant (see ADR 0001 for why).

Host ports (15432, 16379, 18080, 18001, 18420) deliberately avoid each service's
own default -- a dev machine commonly already runs its own
Postgres/Redis/local server on those. Override via `.env` (copy
`.env.example`) or inline if even those collide, e.g.
`KEYCLOAK_PORT=28080 make up`.

Postgres's `POSTGRES_DB` (the "app" database) is migrated automatically on
first boot -- `docker/postgres-init/Dockerfile` bakes in the exact same
`migrations/0001_initial_schema.sql` file `tests/test_schema.py` applies,
no re-typed copy.

`backend/` is a FastAPI app talking directly to that database (`asyncpg`,
no ORM, no file DB) and to Keycloak's live JWKS for OIDC verification:

The API does not consume durable jobs. Canonical Compose makes `backend`
depend on the progress-healthy `backend-worker`, so `docker compose up backend`
starts both. Any non-Compose deployment must co-deploy
`python -m backend.app.worker` and gate API readiness on that worker service;
`/healthz` is process liveness only.

```bash
make up
make seed   # scripts/seed_demo_data.py: inserts synthetic corp/account/post
            # rows keyed to the *real* Keycloak demo users' subject ids,
            # plus Valkey ticket_created events so Activity is not empty
curl http://localhost:18420/healthz
```

The optional authenticated MCP resource server submits and reads the same
durable Global Ask jobs as REST. Enable it only with quota values established
by the deployment's k6 capacity evidence; the service intentionally has no
guessed request/window defaults:

```bash
MCP_RATE_LIMIT_REQUESTS=<measured-count> \
MCP_RATE_LIMIT_WINDOW_SECONDS=<measured-window> \
docker compose --profile mcp up mcp
# Streamable HTTP resource: http://localhost:18001/mcp
```

`GET /api/posts`, `GET /api/posts/{post_id}`,
`GET /api/posts/{post_id}/keymen`, `GET /api/keymen/{person_id}/related`,
`GET /api/posts/{post_id}/affiliate-tree`,
`GET /api/posts/{post_id}/voc-evidence`,
and `POST /api/posts/{post_id}/extract-keymen`
require a real bearer token (RBAC: the account's role must grant
`post_read`; ABAC: a private post is only visible to accounts affiliated
with its owning corporate entity -- `backend/app/main.py`). A Keyman who
is only mentioned on a post the account cannot see is 403, same deny
path. `backend/tests/test_api.py` proves both the allow and the deny
path against a live Keycloak + throwaway Postgres database, including
that a private post scoped to a *different* corporate entity is excluded
from the list and 403s on direct fetch.

`frontend/` (React + Vite + TypeScript, `docker compose`'s fourth service)
is a real client, not mocked or static: `react-oidc-context` drives an
actual Authorization Code redirect through Keycloak, the home page
draws the reconstructed lineage as a git-branch SVG (`GET /api/lineage`;
`post_admin` can rebuild), and the post list / detail popup call the
FastAPI backend over real `fetch()` with the token Keycloak issued.

```bash
make up
make seed
cd frontend && cp .env.example .env.local && pnpm install && pnpm run dev
# Repeated chip/close controls: pnpm run storybook
# (Node 24 via frontend/mise.toml; pnpm only)
# Empty a run-bearing registry: insert analysis_run_retention_grant
# for session_user, GRANT analysis_run_retention_admin, then
# select purge_analysis_run_registry('approved-retention-purge').
# The published token is not a grant (ADR 0020).
# -> http://localhost:5173, click "Log in", redirects through the real
#    Keycloak login page for demo.analyst / lineageweave-demo-only
```

`docker compose up` also builds and serves the frontend itself (nginx,
`frontend/Dockerfile`) at `http://localhost:15173` -- the `VITE_*` build
args are wired from the same `.env` ports as every other service.
`frontend/src/App.test.tsx` covers the login-redirect and
fetch-then-render-popup paths (`react-oidc-context`'s `useAuth` mocked --
the *real* OIDC round-trip is what `scripts/smoke_test_oidc.py` and
`backend/tests/test_api.py` already prove against a live Keycloak).

## Modular / standalone

This repo runs standalone (own server, own tests, own CI) and is equally
usable as a library module (`import lineageweave`) inside a larger service
-- no global state, no required environment variables, every external
dependency (embeddings, LLM adjudication, TEPP) is injected, not hardcoded.

## License

MIT -- see [LICENSE](LICENSE).
