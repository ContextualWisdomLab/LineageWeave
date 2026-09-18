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

The supporting [product requirements](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/docs/product-requirements.md) define
the product outcomes, non-goals, ecosystem boundaries, and release evidence;
ADRs remain normative for architecture and policy.

## Why

Given a pile of records with no native cross-record link, no single cheap
signal reliably tells you which record continues which -- see
[`docs/lineage-bi-research-notes.md`](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/docs/lineage-bi-research-notes.md) for
the validation numbers and the literature this design follows. LineageWeave
fuses several independent, individually-weak signals (temporal proximity, a
shared grouping key, text similarity, and an optional LLM judgment) instead
of trusting any one of them alone. The normative research-grounding policy is
[ADR 0084](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/docs/adr/0084-lineage-research-grounding.md); the linked notes
retain the supporting bibliography and aggregate evidence.

## How it fits with the rest of the ecosystem

LineageWeave owns lineage product policy, source-evidence binding, instrument
and rubric administration, pilot lifecycle, interpretation, and audit. It does
not own reusable model routing or reusable psychometric numerical kernels.

Every production LLM-backed capability calls
[contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
through its published consumer contract. Provider/model discovery, routing,
fallback, structured-output compatibility, multi-agent orchestration,
reasoning-effort allocation, usage/cost provenance, and provider credentials
stay in contextual-orchestrator. LineageWeave receives versioned observations
and provenance; it never treats an LLM judgment as truth and never falls back
to a provider endpoint directly. See [ADR 0300](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/docs/adr/0300-contextual-orchestrator-owner-boundary.md).

Reusable psychometric numerical/statistical kernels and their recovery
evidence belong to
[fast-mlsirm](https://github.com/ContextualWisdomLab/fast-mlsirm). Temporal,
event, multilevel, cross-classified, and multiple-membership measurement
semantics belong to [TEPP](https://github.com/ContextualWisdomLab/TEPP),
consumed through TEPP's published wire contract
(`lineageweave/tepp_client.py`, `AnalysisRunRequest` v1). LineageWeave does
not read either owner's tables or copy their model implementations.

Tree assembly reuses
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

To turn on the embedding or LLM channels, use clients backed by a running
contextual-orchestrator. A provider endpoint or provider credential is not a
LineageWeave integration contract:

```python
from lineageweave import reconstruct
from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient

llm = ContextualOrchestratorAdjudicationClient(base_url="https://orchestrator.example", api_key="...")
trees = reconstruct(my_records, llm=llm)
```

## Test

```bash
pip install -e ".[dev]"
pytest
```

## Local product stack (Docker Compose)

The reconstruction library above is being wrapped in a real product (see
[ARCHITECTURE.md](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/ARCHITECTURE.md#product-schema-phase-1-of-a-larger-roadmap)
and [ADR 0001](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/docs/adr/0001-demo-identity-and-data-boundary.md)). Phase 1's
infrastructure -- PostgreSQL, Valkey, and a real Keycloak OIDC realm seeded
with synthetic demo accounts -- runs via Docker Compose:

```bash
make up      # docker compose up -d: postgres, valkey, keycloak, backend, frontend
KEYCLOAK_CLIENT_SECRET=lineageweave_test_automation_dev_only make smoke
             # machine client-credentials token/JWKS/API-audience check;
             # not browser Authorization Code/OIDC acceptance
make down
```

`make smoke` is deliberately a machine-to-machine compatibility probe. It
uses the synthetic confidential `lineageweave-test-automation` client and the
OAuth Client Credentials grant, requires the client secret explicitly at the
operator boundary, verifies the token against the live realm JWKS, and checks
the backend API audience. It does not impersonate `demo.analyst` and is not
evidence for redirect/PKCE, state/nonce, SSO, MFA, or browser-session behavior.
Those product-login properties require the rendered Authorization Code path.

The public `lineageweave-frontend` client is configured for S256 PKCE. The
ongoing #1119/#1120 migration has **not** yet reached its final security state:
`backend/tests/test_api.py` and `scripts/seed_demo_data.py` still contain local
password-grant test/bootstrap paths, so public direct grants remain enabled
until those callers are migrated atomically. Do not treat the machine smoke as
proof that Resource Owner Password Credentials have been fully removed. OAuth
2.0 Security BCP [RFC 9700 §2.4](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4)
forbids that grant, and browser applications must use a redirect-based flow
under [RFC 10017 §7.3](https://www.rfc-editor.org/rfc/rfc10017.html#section-7.3).

The local stack does not build or start contextual-orchestrator and does not
load provider credentials. If model-backed channels are required, deploy or
reach contextual-orchestrator through its canonical owner path and set only
`ORCHESTRATOR_BASE_URL` and `ORCHESTRATOR_API_KEY` in LineageWeave's local
`.env`. Leaving either empty keeps model-backed channels unavailable/fail-closed;
there is no direct-provider fallback.

Postgres and Keycloak are built (`docker/postgres-init/`, `docker/keycloak/`)
rather than bind-mounted, so the keycloak database's init script and the
realm seed ship inside the images themselves -- portable to any Docker host
or CI runner, no assumption about a shared local filesystem layout.

Demo accounts (`docker/keycloak/realm-export.json`) are synthetic:
`demo.analyst` / `demo.admin`. The default browser-fixture password and the
default machine-client secret are declared in `.env.example` as disposable
local-only values and are passed into realm import through environment
placeholders; neither is a production or Keyverse credential. Override both
for a shared development environment.

Keycloak's startup realm import does not overwrite an already-existing realm.
A changed realm seed therefore takes effect automatically in a fresh stack,
but not in a previously persisted Keycloak database. If the local environment
is disposable, `docker compose down -v` followed by `make up` recreates all
Compose volumes and re-imports the realm; that command also deletes the local
PostgreSQL and Valkey data, so do not use it as a general upgrade step.

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

```bash
make up
KEYCLOAK_ADMIN_PASSWORD=admin_dev_only make seed
            # scripts/seed_demo_data.py: inserts synthetic corp/account/post
            # rows plus Valkey ticket_created events; the admin/bootstrap path
            # is still part of the open #1119 migration
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
from the list and 403s on direct fetch. Its local token fixture is still a
known password-grant migration item under #1119/#1120 and is not a production
authentication recommendation.

`frontend/` (React + Vite + TypeScript, `docker compose`'s frontend service)
is a real client, not mocked or static: `react-oidc-context` drives an
actual Authorization Code redirect through Keycloak, the home page
draws the reconstructed lineage as a git-branch SVG (`GET /api/lineage`;
`post_admin` can rebuild), and the post list / detail popup call the
FastAPI backend over real `fetch()` with the token Keycloak issued.

```bash
make up
KEYCLOAK_ADMIN_PASSWORD=admin_dev_only make seed
cd frontend && cp .env.example .env.local && pnpm install && pnpm run dev
# Repeated chip/close controls: pnpm run storybook
# (Node 24 via frontend/mise.toml; pnpm only)
# Empty a run-bearing registry: insert analysis_run_retention_grant
# for session_user, GRANT analysis_run_retention_admin, then
# select purge_analysis_run_registry('approved-retention-purge').
# The published token is not a grant (ADR 0020).
# -> http://localhost:5173, click "Log in", redirects through the real
#    Keycloak login page for demo.analyst / the configured synthetic password
```

`docker compose up` also builds and serves the frontend itself (nginx,
`frontend/Dockerfile`) at `http://localhost:15173` -- the `VITE_*` build
args are wired from the same `.env` ports as every other service.
`frontend/src/App.test.tsx` covers the login-redirect and
fetch-then-render-popup paths (`react-oidc-context`'s `useAuth` mocked). Run
`make smoke` only for the local machine token/JWKS/resource-audience check;
browser Authorization Code acceptance requires the rendered frontend E2E path.

## Modular / standalone

This repo runs standalone (own server, own tests, own CI) and is equally
usable as a library module (`import lineageweave`) inside a larger service.
Deterministic reconstruction remains available without any model service;
model-backed channels are injected through contextual-orchestrator's consumer
contract and fail closed when that contract is unavailable.

## License

MIT -- see [LICENSE](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/LICENSE).