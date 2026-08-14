# Testing

## Required verification

- `uv run pytest -q`
- `uv run python -m py_compile lineageweave.py lineageweave_embeddings.py lineageweave_server.py compose/http_standin.py compose/keyverse_oidc.py`
- `cd web && npm run build`
- `docker compose config --quiet`
- Verify Compose hardens the product profile IdP boundary and that the effective
  operator env file has non-empty direct PostgreSQL and external OIDC settings:
  - `LINEAGEWEAVE_ENV_FILE=/path/to/operator.env ./scripts/preflight_product_compose.sh`
- branch coverage for `lineageweave.py`, `lineageweave_embeddings.py`, `lineageweave_server.py`, `compose/http_standin.py`, and the retained offline OIDC utility `compose/keyverse_oidc.py` with `--fail-under=100`
- `bash -n scripts/run_real_lineageweave.sh`
- `bash -n scripts/run_oidc_conformance_e2e.sh` (retained-fixture syntax audit only; do not start it)

## Real-source execution check (operator DSN required)

With `LINEAGEWEAVE_DSN` and `LINEAGE_SOURCE_TABLE` configured for the private
runtime table, run:

```bash
./scripts/run_real_lineageweave.sh
```

## Retained local OIDC fixture — audit only

Do **not** start `scripts/run_oidc_conformance_e2e.sh` or either associated
OIDC Compose file. The retained fixture is neither Keyverse nor a supported
login test or acceptance path. It stays in the source tree solely as an
ownership/audit finding; its syntax and source boundary may be inspected, but
it must not produce release or browser-login evidence.

The only current local browser check is `npm run e2e:login-gate`: it validates
email UX and the generic unavailable state without starting or contacting an
identity authority. Real browser acceptance requires an operator-configured
production Keyverse service and a real business account for login, callback,
session, and logout.

For a bounded smoke check, set `LINEAGEWEAVE_LIMIT=1` (or another small
positive integer) and verify the command exits successfully.

For a bounded content inspection pass, set:

```bash
export LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS=1
export LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT=2
./scripts/run_real_lineageweave.sh
```

## Current evidence

A fresh current-tree isolated-PostgreSQL snapshot completed all 350 tests (with
 one expected skip when the sibling `fast-mlsirm` package is not installed) and
100% line-and-branch coverage for `lineageweave.py`,
`lineageweave_embeddings.py`, `lineageweave_server.py`, `compose/http_standin.py`,
and `compose/keyverse_oidc.py` (7,587 statements and 2,964 branches); no
coverage exclusion was added. The sibling `fast-mlsirm` interpreter check passed
in this workspace.
Production snapshot writers also release short schema-migration locks before
the long data transaction. The React production build and Python compilation
remain companion gates. Unless `LINEAGEWEAVE_TEST_DSN` is explicit, pytest
creates one process-owned PostgreSQL database before test imports and
force-drops that exact database at teardown. This isolates database-scoped
advisory locks and analysis-table replacement from the real runtime database.

A bounded direct-PostgreSQL backend run now holds 29 source-linked embedding
chunks across three documents at 3,072 dimensions. A live labeled multilingual
query retained its intended 0.440 match, and a generic 0.25 score is suppressed
by the bounded 0.40 floor. Opening the matched document's content retained all
29 chunks, while the relatedness route returned an inferred neighbor in 0.19
seconds without materializing the full KG. It recorded aggregate counts only.
This proves the direct data path, not the still-required real-Keyverse browser
authorization or production delivery path.

The real-data report reanalysis used a live factor-item catalog task, called the
local Rust-backed fast-mlsirm connector, and wrote 80 report slices. The current
bank has ten fixed anchor items and five evidence-bound LLM candidates; all
fifteen items have finite calibration rows. Fifty-eight slices received five
package-produced linked scores each (290 total); 22 slices remain explicitly
unlinked because their item responses were insufficient. The connector smoke
confirmed the Rust-backed path, and a missing connector remains an explicit
degraded mode rather than a false score.

After the RAGAS-aligned metric schema was added, a separate live report-judge
rerun completed all 80 persisted slices without failure. PostgreSQL now holds
320 report-metric observations (80 each for faithfulness, answer relevancy,
context precision, and context recall), all with `llm_judge` provenance and
scores within `[0, 1]`; their source-evidence references are persisted in the
normalized `analysis_report_metric_evidence` child relation; the 290 linked psychometric
scores and 15 calibration rows were persisted. A metric that lacks adequate evidence is designed to be
stored as `abstain` with a NULL score rather than a made-up zero.

`cd web && npm run e2e` runs bundled-browser interaction checks for product
surfaces. A development actor may exercise non-identity screen behavior, but
cannot prove authentication acceptance. Historical local-conformance records
are audit context only and are superseded as login evidence. The local product
browser gate remains limited to email UX and unavailable configuration; only
configured production Keyverse plus a real business account can prove hand-off,
callback, session, and logout.

For the reader product-surface check, run the same browser script against a
separate loopback product process whose development actor has only the
`reader` role. The script captures `home.png` and asserts that the session has
no administrator navigation and no technical KPI strip. Use an isolated port
for the second process so it cannot change the administrator browser session.

For the administrator product-surface check, run the script against an
isolated development actor carrying the administrator role. It must reach the
access-policy and Lineage-review screens, load non-empty review candidates,
open the customer/document surfaces, and restore any relatedness visibility
override after its private/public mutation check. A missing Keyverse Admin
account-list adapter may be reported as unavailable in this local-only smoke;
it must not create a local issuer or bypass server-side actor authorization.

The current data-bearing reader run also opened a persisted report detail with
four RAGAS metric cards and 32 authorized evidence-document links.
The popup path also selects an available LLM Keyman and verifies the
actor-authorized Knowledge Graph relationship-direction list.

The fresh post-fix reader run reported `preauthenticated_session: true`,
`reached_identity_authority: false`, 43,483 visible documents, 5 actor-scoped
customer rows and 3 customer-affiliate edges in the bounded `limit=3` probe,
4 report metrics, 32 report-evidence links, 0 observed chronological edges,
and 8 separate relatedness results. The current persisted customer snapshot
contains 22 accounts.
These are direct-PostgreSQL product-surface results; they are not Keyverse
login acceptance evidence.

The same read-only runtime aggregate contains 267 normalized content blocks,
299 HTML/DOM format hints, 7 asset profiles, 7 multimodal inspections with
non-empty OCR text, 3 persisted object labels, and 29 semantic chunk
embeddings. This confirms that the HTML/image path produced persisted analysis
artifacts; it does not claim that every future asset will be inspectable when a
configured multimodal provider is unavailable.

The normalized Ontology/Semantic Layer aggregate contains 8 namespaces, 46
ontology terms, 28 relation rules, 264,750 Knowledge Graph nodes, 838,550
Knowledge Graph edges, 836,794 semantic edge assertions, and 308,457 semantic
node assignments. These counts are database evidence only; the browser still
receives only the actor-authorized, document-evidence-scoped subgraph.

For the administrator LLM-control smoke, start the product against the
operator's configured direct PostgreSQL source and call the bounded route with
`{"task":"keyman","limit":1}`. Verify that the response is `queued`, then
poll `/api/admin/enrichment/status` until the durable completion event appears.
The current live smoke completed one document with zero failures and one
explicit abstention; it did not expose document content or model payloads.
Never run the batch without an explicit small limit during a test loop.

For the administrator TEPP port smoke, configure `TEPP_BASE_URL` and
`TEPP_API_TOKEN` for a deployed TEPP v1 service. The product calls only
`POST /v1/analysis-runs` and `GET /v1/analysis-runs/{run_id}` over the versioned
HTTP boundary, persists lifecycle metadata in PostgreSQL, and emits a Valkey
outbox event. Without the endpoint, the UI must show unavailable and must not
invent a completed run. The current TEPP protected main still labels its HTTP
service as an accepted target contract, so the passing loopback `accepted` →
`completed` wire smoke proves only request/response compatibility and is not
TEPP scientific-runtime evidence.

## Real-world cases covered

Tests cover visibility and role authorization, persisted PostgreSQL payloads, event succession, inferred/non-transition edges, inline image validation/inspection, Keyman split, worker identity-route denial, outbox behavior, API failure mapping, and React buildability.

## Evidence

- `tests/`
- `pyproject.toml`
- `web/package.json`
- `notes/lineageweave_milestone2_run_summary.md`
