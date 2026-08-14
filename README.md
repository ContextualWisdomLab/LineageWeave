# LineageWeave

LineageWeave is a runnable React product backed by direct PostgreSQL access.
It reads the runtime source table, persists a bounded lineage and Knowledge
Graph snapshot, and serves it through a Keyverse-gated API. It is separate from
TEPP; any orchestration integration is an HTTP worker boundary.

## Product behavior

- Keyverse supplies the authenticated account, legal company, PU, and roles.
  Corp/PU are never typed into a browser login form.
- ABAC/RBAC is enforced before document, row, evidence, content, KG, chat, or
  mutation responses leave the server.
- The precomputed KG contains people, organizations, PUs, events, and posts.
  It includes same-company/different-PU, different-company, and
  same-PU/different-company links with evidence IDs.
- The KG has a normalized PostgreSQL ontology and semantic layer: versioned
  namespaces, reusable terms, domain/range rules, RDF type assignments, and
  evidence-preserving predicate assertions. Event chat reads only the
  already-authorized semantic subgraph and fails closed when it is absent.
- Authorized users can run a bounded relationship-verification Agent over
  inferred/predicted KG edges. It uses observed internal evidence and optional
  organization-only SearXNG results to obtain a live LLM verdict of `verified`,
  `rejected`, or `insufficient`; the verdict never promotes the original edge.
- The document list searches the complete server-authorized corpus. Verified
  organization aliases are stored directionally as inferred SKOS exact-match
  assertions without rebuilding the complete KG. A new alias is accepted only
  when the cited organization-only SearXNG result contains both the source
  label and the LLM-proposed canonical organization; disagreement remains
  unresolved.
- Customer-master hierarchy is a KG consumer only when an LLM response names
  its source documents; account-to-document links enforce the same ABAC/RBAC
  scope as the document graph.
- The document popup provides Korean summary, event timeline, R&R, observed
  글 자체의 Lineage, a separately labelled inferred/predicted relatedness view,
  two-sided LLM Keyman, Keyman neighborhood, issue tickets, visibility, event
  chat, and AJAX source citations.
- Content cells are classified from byte length, a short prefix, and a
  database-side inline-image/markup marker that scans the source cell without
  returning its bytes. Inline images, markup, and binary cells remain in
  PostgreSQL and are fetched through an authorized asset endpoint; bytes are
  not written into the KG.
- Authors, editors, and admins can request OCR/object inspection for a bounded
  PNG, JPEG, GIF, or WebP inline image. OCR and image-specific object
  descriptions are persisted in normalized PostgreSQL relations and searched
  only within the caller's visible documents.
- Managers can index one authorized document's DOM semantic text through the
  verified embedding gateway. The browser receives only inferred relatedness
  metadata for already-visible documents with a provisional 0.40 relevance
  floor; vectors, markup, inline bytes, and source text do not leave the
  server through that surface.
- Weekly/monthly PU, team, and project reports use the report ID as the
  temporal psychometric observation unit and delegate FIPC/CAT linking to the
  separate fast-mlsirm HTTP or local connector. The verified local path uses
  its Rust-backed EAP implementation and returns package-produced scores; if
  the connector is absent or does not return linked scores, the report remains
  explicitly unlinked rather than using an in-process estimate.
- The same live report Judge persists four RAGAS-aligned metrics per slice in
  normalized PostgreSQL tables. Each metric keeps its evaluator source,
  dichotomous verdict, score, and rationale; evidence references live in a
  separate child relation, and unsupported metrics abstain instead of receiving
  an invented score.
- Report factor items are also normalized. A live catalog task can derive
  candidate dichotomous items only from supplied writings and persists their
  report/document evidence separately. The calibrated item bank is sent to the
  separate Rust-backed fast-mlsirm connector; a slice with insufficient item
  responses remains explicitly unlinked rather than receiving a local estimate.
- The authenticated product opens on a reader-friendly 업무 홈 with recent
  work, evidence-backed customer relationships, and reports. The navigation
  then separates the evidence workspace from a customer screen. The customer
  screen reads only customer-master accounts and affiliate edges linked to
  documents visible to the current actor, then opens those source documents
  from the same API boundary. Operator KPI and queue diagnostics stay in the
  administrator workspace.
- Administrators receive a server-authorized Keyverse account screen. It lists
  same-corp or unassigned accounts, keeps the corp claim fixed to the verified
  administrator, edits the PU claim, and reconciles only roles on the
  configured `lineageweave-web` client. Keyverse admin credentials and tokens
  never enter React or API responses.
- Administrators also receive bounded `LLM 분석 작업` controls. They can queue
  Keyman, product work, appointment, or combined enrichment for at most 64
  documents; status is aggregate-only and comes from PostgreSQL outbox/work
  rows. Existing user Keyman overrides are protected, and an empty live model
  result is recorded as an explicit abstention.

## Run locally

The source table is runtime configuration and is intentionally absent from
tracked files. For a local session, enable the explicit development actor:

```bash
export LINEAGE_SOURCE_TABLE='schema.table'
export LINEAGEWEAVE_DSN='postgresql://user@localhost/database'
export LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT='30'
export LINEAGEWEAVE_KEYMAN_LLM_TIMEOUT='45'
export LINEAGEWEAVE_CONTENT_LLM_TIMEOUT='120'
export LINEAGEWEAVE_CHAT_LLM_TIMEOUT='60'
export LINEAGEWEAVE_EMBEDDING_TIMEOUT='60'
export LINEAGEWEAVE_REPORT_JUDGE_MAX_ATTEMPTS='3'
export LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS='0'
# Optional: otherwise the gateway's embedding-capable model is discovered.
export LINEAGEWEAVE_EMBEDDING_MODEL='operator-selected-embedding-model'
export LINEAGEWEAVE_COMPOSE_STANDIN_TIMEOUT='90'
export LINEAGEWEAVE_DEV_MODE=1
export LINEAGEWEAVE_DEV_ACTOR_JSON='{"account_id":"local-account","corp_code":"CORP_A","pu_code":"PU_A","roles":["reader","author"]}'
export LINEAGEWEAVE_VALKEY_URL='redis://127.0.0.1:6379/0'

docker compose up -d --wait
cd web
npm ci
npm run build
cd ..
uv run python lineageweave_server.py
```

Compose also reads the optional operator environment file at
`${LINEAGEWEAVE_ENV_FILE:-$HOME/.env}` for the live model gateway; set
`LINEAGEWEAVE_ENV_FILE` or use `docker compose --env-file` when deployment
secrets live elsewhere. The file is never copied into the image or repository.

The server serves the compiled React bundle and the `/api/*` contract from the
same configured origin.

## Container run

The `product` Compose profile builds the React bundle and product HTTP service.
It still connects directly to the configured PostgreSQL source; it does not add
a file database or a database proxy. Supply the source connection and table
through the deployment secret/configuration mechanism, then run:

```bash
docker compose --profile product up -d --build
```

For a controlled Compose deployment, copy this legacy-named ignored sample to
an operator-managed file and fill the direct PostgreSQL and approved **external
Keyverse** settings. The filename refers only to a local product configuration;
it does not imply or provision a local Keyverse service. `--env-file` supplies
Compose interpolation for the direct database settings, while
`LINEAGEWEAVE_ENV_FILE` passes the same operator-managed values into the product
container:

```bash
cp compose/local-keyverse.env.example .env.local
# Fill the direct PostgreSQL and approved Keyverse values.
# This project does not run a Keyverse identity container in compose.
LINEAGEWEAVE_ENV_FILE=.env.local \
docker compose --env-file .env.local --profile product up -d --build --wait
```

Run this once before startup in product environments:

```bash
LINEAGEWEAVE_ENV_FILE=.env.local ./scripts/preflight_product_compose.sh
```

Before production startup, harden-check the compose boundary:

```bash
python scripts/check_compose_identity_boundary.py
```

If the secret is unavailable, product startup will fail fast by contract in
`/api/login` path instead of silently using a fallback identity mode.

When the configured PostgreSQL server runs on the Docker host, use
`host.docker.internal` in `LINEAGEWEAVE_DSN`, not `localhost`; the profile adds
the standard host-gateway mapping without inserting a proxy. For example,
`postgresql://host.docker.internal/database`. A managed PostgreSQL
hostname remains unchanged.

Inside the Compose network, the product reaches Valkey and the live-worker
proxy by service name. The same stack provides SearXNG for bounded
organization-only corroboration; no person or raw document text is sent as its
query. Keyverse remains the external identity authority: deploy
an HTTPS issuer and the registered OIDC client settings described below rather
than adding a sample account to the product stack.

For production, leave `LINEAGEWEAVE_DEV_MODE` unset and register an HTTPS
redirect URI through Keyverse's reviewed `lineageweave-web` account-derived
profile. That profile obtains `org` and `workspace` from the real Keyverse
account and `role` from its same-client role assignment; none of those values
are static client configuration. Configure its OIDC settings:

```bash
export KEYVERSE_ISSUER='https://identity.example/realms/lineage'
export LINEAGEWEAVE_OIDC_CLIENT_ID='lineageweave-web'
export LINEAGEWEAVE_OIDC_CLIENT_SECRET='operator-provided confidential value'
export LINEAGEWEAVE_PUBLIC_ORIGIN='https://app.example'
export LINEAGEWEAVE_OIDC_REDIRECT_URI='{origin}/api/oidc/callback'
# Optional only for an operator-managed Keyverse CA:
export KEYVERSE_CA_BUNDLE='/run/secrets/keyverse-ca.pem'
# Optional server-only account-administration adapter for LineageWeave admins:
export KEYVERSE_ADMIN_TOKEN_URL='https://identity.example/realms/lineage/protocol/openid-connect/token'
export KEYVERSE_ADMIN_USERNAME='operator-managed-admin-account'
export KEYVERSE_ADMIN_PASSWORD='operator-managed-secret'
```

`{origin}` is expanded only from `LINEAGEWEAVE_PUBLIC_ORIGIN`; request `Host`
and forwarded headers never choose an OIDC callback origin. `/api/login` starts
Keyverse authorization code with S256 PKCE. The server
exchanges the callback code and validates the resulting token through Keyverse
introspection before it maps `org` → corp code, `workspace` → PU code, and
`role` → product role. It accepts no product password, browser-supplied
tenant claim, or fallback account. API bearer tokens use the same validation.
The administrator screen uses the separate server-only `KEYVERSE_ADMIN_*`
settings to obtain a short-lived Keyverse Admin REST token. A dedicated
operator account and secret manager are required; the browser can request only
the scoped account list or claim mutation endpoint. The server resolves the
configured realm and `lineageweave-web` client itself, rejects cross-corp
targets, and never accepts a browser-supplied admin token or client secret.
The first administrator still has to be provisioned in Keyverse with the
reviewed same-client `admin` role; the product does not create issuer roles.

The `product` Compose profile forces `LINEAGEWEAVE_DEV_MODE=0` and secure
cookies, then consumes only externally provisioned Keyverse settings. The model
worker may read the same file for model-gateway settings, but Compose clears the
known Keyverse and OIDC values there and the worker aborts if any nonempty
`KEYVERSE_*` or `LINEAGEWEAVE_OIDC_*` value reaches it. The worker is never an
IdP: it creates no account, client, token, or claim.

Do not configure a loopback, host-bridge, Keycloak, or Keyverse imitation as an
identity test path. Local browser work ends at the email UX and unavailable
configuration gate. Actual browser acceptance requires the operator-configured
production Keyverse service and a real business account for login, callback,
session, and logout.

The model client verifies HTTPS with the platform trust store. Set
`LLM_GATEWAY_CA_BUNDLE` only when the deployment requires an operator-managed
CA bundle; certificate verification is never disabled.

For optional external corroboration, configure a SearXNG endpoint on the
product service. Production requires HTTPS; a loopback or Docker host-bridge
HTTP endpoint is accepted only with explicit development mode:

```bash
export LINEAGEWEAVE_SEARXNG_URL='https://search.example'
# Optional only for an operator-managed SearXNG CA:
export SEARXNG_CA_BUNDLE='/run/secrets/searxng-ca.pem'
```

The verifier sends at most two organization labels derived from the already
authorized KG. It never sends people, raw source content, credentials, or a
browser-selected tenant value to SearXNG. Unavailable external evidence leaves
the LLM result insufficient; it does not expand the search scope.

### Direct batch analysis run (real source)

Run the real PostgreSQL source directly for a full database analysis run. The
analyzer starts from the contract query form `SELECT zer.*` against the
configured source table and persists normalized analysis state in PostgreSQL:

```bash
export LINEAGE_SOURCE_TABLE='your_schema.your_source_table'
uv run python lineageweave.py --table "$LINEAGE_SOURCE_TABLE" --write-reports
```

For repeatable operational use, execute:

```bash
export LINEAGE_SOURCE_TABLE='your_schema.your_source_table'
./scripts/run_real_lineageweave.sh
```

For long-running environments where LLM report scoring is not required yet, run with:

```bash
export LINEAGEWEAVE_WRITE_REPORTS=0
./scripts/run_real_lineageweave.sh
```

For one-command contract runs where you want explicit `--table`/`--dsn` control and the default DSN fallback, execute:

```bash
export LINEAGE_SOURCE_TABLE='your_schema.your_source_table'
./scripts/run_contract_lineageweave.sh
```

For bounded OCR/vision inspection only, set either script with:

```bash
export LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS=1
export LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT=3   # 0 means all matched documents
./scripts/run_real_lineageweave.sh
```

```bash
export LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS=1
export LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT=3   # 0 means all matched documents
export LINEAGE_SOURCE_TABLE='your_schema.your_source_table'
./scripts/run_contract_lineageweave.sh
```

For dry-run verification without processing a full table, set
`LINEAGEWEAVE_LIMIT` to a positive integer (for example `1` or `100`) before
running the script.

If no local Keyverse is available, keep runtime auth in product mode only by
leaving production OIDC values unset; the server then starts in explicit
development actor mode only when requested through `LINEAGEWEAVE_DEV_MODE`.

By default the CLI and both batch wrappers write no JSON, analytics, or DOT
file. Use PostgreSQL as the canonical operational state. An operator may create
a detached export only by explicitly supplying its destination, for example:

```bash
export LINEAGEWEAVE_JSON_OUT='/operator-controlled/lineageweave.json'
export LINEAGEWEAVE_ANALYTICS_OUT='/operator-controlled/lineageweave-analytics.json'
./scripts/run_real_lineageweave.sh

uv run python lineageweave.py --table "$LINEAGE_SOURCE_TABLE" --dot-out /operator-controlled/lineageweave.dot
```

### Research provenance

The configured Local Zotero API can receive the method-paper metadata used by
the analysis. Set `LINEAGEWEAVE_ZOTERO_API` to the local API root; add
`LINEAGEWEAVE_ZOTERO_ATTACHMENTS=1` to fetch and store bounded OA originals as
Connector attachments. PostgreSQL records the parent/attachment outcome and
SHA-256; the current provenance set contains 12 stored parents and originals,
including four multimodal document-analysis papers. A failed or keyless
Connector response is not presented as stored. The full APA 7th research
register is in [`docs/doctoring/tepp-literature-review.md`](docs/doctoring/tepp-literature-review.md).

## Worker contract

Set the configured LLM gateway variables for direct Keyman extraction and
structured product enrichment. The Keyman adapter is deliberately limited to
two-sided people/organization extraction; bounded subject-role classification,
appointment extraction,
customer-master updates, issue work-item copy, and report judging use the
general OpenAI-compatible chat contract with an allowlisted task schema. The
local Compose worker is available as the same-contract proxy for event chat
and image inspection when separately configured with a live model gateway;
without one it returns an unavailable response rather than fabricating an
answer or identity:

```bash
docker compose up -d --wait
```

The Compose worker is not an authentication provider and contains no identity
implementation. The stack also provides Valkey. Inspection accepts only strict,
signature-matched raster data up to 50 MiB; unsupported and larger assets remain
available only through the authorized asset route. Mutations are first committed
to the PostgreSQL transactional outbox and then appended to the
`lineageweave_events` Valkey Stream with at-least-once delivery. Production
deployments must use the live Keyverse, worker, and managed Valkey URLs. The
Compose profile mounts Valkey's append-only data directory on `valkey_data` so
a routine container recreation does not discard queued Stream entries.

## Checks

```bash
uv run --group dev python -m pytest -q
uv run --group dev python -m py_compile lineageweave.py lineageweave_server.py compose/http_standin.py
uv run --group dev coverage run --branch --include='lineageweave.py,lineageweave_embeddings.py,lineageweave_server.py,compose/http_standin.py,compose/keyverse_oidc.py' -m pytest -q
uv run --group dev coverage report --fail-under=100
LINEAGEWEAVE_ENV_FILE=.env.local ./scripts/preflight_product_compose.sh
cd web && npm run coverage && npm run build
```

For the reproducible no-issuer browser check against a running local product:

```bash
cd web
LINEAGEWEAVE_E2E_LOGIN_BASE_URL=http://127.0.0.1:18100 \
LINEAGEWEAVE_E2E_LOGIN_EXPECT_UNAVAILABLE=1 \
npm run e2e:login-gate
```

This check uses only a synthetic address. It validates empty/malformed email
guidance and the configured-unavailable response; it never substitutes for a
real Keyverse login.

The ADR, architecture, traceability map, and operational decisions are in
[`docs/planning/adrs/0001-lineageweave-runtime-and-governance.md`](docs/planning/adrs/0001-lineageweave-runtime-and-governance.md),
[`docs/planning/adrs/0002-verified-inline-image-inspection.md`](docs/planning/adrs/0002-verified-inline-image-inspection.md),
[`docs/planning/adrs/0003-keyverse-authorization-code-pkce.md`](docs/planning/adrs/0003-keyverse-authorization-code-pkce.md),
[`docs/planning/adrs/0004-evidence-verified-ontology-inference.md`](docs/planning/adrs/0004-evidence-verified-ontology-inference.md),
[`docs/planning/adrs/0005-live-provenance-and-method-paper-attachments.md`](docs/planning/adrs/0005-live-provenance-and-method-paper-attachments.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), and [`TRACEABILITY.md`](TRACEABILITY.md).
