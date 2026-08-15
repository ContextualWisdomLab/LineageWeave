# Architecture

```text
verified Keyverse actor
          |
          v
React -> LineageWeave HTTP API -> PostgreSQL
          |                         |
          |                         +-- normalized documents/events/KG/semantic tables
          |                         +-- transactional event outbox
          v
   TEPP/orchestrator-compatible HTTP workers
          |
          +-- live LLM extraction, inspection, report judging, verification

PostgreSQL outbox -> Valkey Stream
```

The browser never reads the database or a JSON export. Access decisions are made on the server from the verified actor's account, legal-company, PU, and roles. Large source content and image bytes remain behind document-scoped routes. KG neighborhoods are bounded and evidence-filtered; inferred or predicted relations are not chronological transitions.

The ordinary-user entry point is the reader shell (`업무 홈`, `업무공간`,
`고객 화면`). The administrator shell is a separate, server-authorized
surface for access policy, Lineage review, enrichment, and external account
directory operations. The customer screen is not a free-standing label tree:
`analysis_customer_accounts`, `analysis_customer_affiliates`, and
`analysis_customer_document_links` project `schema:Organization`,
`schema:subOrganization`, and `schema:about` facts only after the same actor
scope predicate used for source documents succeeds. Source-document links in
the customer detail reopen the authorized evidence route.

At response time, persisted shared-thread edges are rechecked against both
current document endpoints. A stale edge can remain as audit history but is
not returned to reader Lineage, administrator review, or a KG neighborhood;
same-document row succession is the only chronological presentation edge.

The current implementation loads persisted analysis before rebuilding. This makes the product restartable without silently re-running expensive model calls. A missing persisted snapshot triggers the direct source query and live worker path.

Task-aware model calls carry a bounded Fugu/Conductor/TRINITY policy envelope.
The envelope selects single-model routing for simple work and deep
thinker/worker/verifier/synthesizer composition for high-risk enrichment,
verification, reports, and multimodal inspection. The envelope is nested in
the user request for every OpenAI-compatible gateway; top-level `route` or
`conduct` controls are added only for an explicitly configured
contextual-orchestrator endpoint. This keeps direct providers portable and
keeps orchestration an HTTP boundary.

Weekly and monthly report slices are evaluated by the live report-judge task.
Its factor-item observations remain separate from four RAGAS-aligned metrics.
`analysis_evaluation_metrics` stores the reusable metric catalog, while
`analysis_report_metric_scores` stores one report/metric observation with its
score, dichotomous verdict, model source, and rationale. The separate
`analysis_report_metric_evidence` relation stores one evidence reference per
row, keeping the report metric contract in third normal form. A metric without
sufficient source support is `abstain` with no fabricated numeric score.
The React report detail renders these observations only after the actor-filtered
`/api/reports` response and reuses the authorized document-selection path for
each evidence link; it never exposes the metric tables directly to the browser.

Factor-item calibration is a separate normalized lifecycle. The fixed item bank
and live-LLM candidate catalog live in `analysis_factor_items`; candidate
support is stored in `analysis_factor_item_evidence`, and connector-produced
discrimination/difficulty estimates live in
`analysis_factor_item_calibrations`. An item is promoted to `calibrated` only
after the separate fast-mlsirm connector returns finite calibration output.
Missing item responses leave a report slice unlinked. The general-user report
surface may display the resulting score or explicit unlinked state, but never
edits the item bank or calibration rows.

The authenticated React shell is role-shaped: every actor enters 업무 홈 and
can navigate to the actor-filtered 업무공간 and 고객 화면. Only an `admin`
actor receives the 관리자 모드 navigation and its diagnostics, policy,
Lineage-review, enrichment, TEPP, and Keyverse-account controls. The server
rechecks the same actor on every route, so the reader UI is a product surface,
not a client-side security boundary.

The administrator screen separates the Keyverse account-directory dependency
from local policy operations. If the reviewed Keyverse Admin endpoint is not
configured, the browser shows a Korean availability message and leaves account
claim editing unavailable; server-enforced 게시글 권한 통제 and Lineage review
remain usable. The UI never replaces that missing directory with a local issuer
or a fake account record.

Organization aliases use the same evidence boundary: the LLM supplies a
contextual canonical-name candidate, while organization-only SearXNG evidence
must contain both the source alias and that canonical name before the inferred
SKOS exact-match assertion can enter the normalized KG. A mismatch remains a
reviewable unresolved result and cannot alter chronological Lineage.

Customer-master persistence is snapshot-replacement semantics. A payload that
contains `customer_master` clears document links, affiliate facts, and account
facts in that order before inserting the new normalized projection, including
when the live LLM abstains. A payload without that boundary does not alter the
customer projection. Reader vocabulary hides raw implementation provenance and
uses business terms for evidence and visibility; administrator/audit routes
retain source fields for operational diagnosis.

## Container and workflow supply-chain boundary

All shipped product, Compose worker, SearXNG, and isolated OIDC-conformance
base images are referenced by immutable registry digest. The React build stage
uses the non-root `node` account, and runtime stages retain their explicit
non-root users. GitHub workflow bootstrap installation uses `pip` hash
verification for the pinned Linux `uv` wheel in both the scheduled verifier
and the normal test workflow. These controls make image and CI dependency
replacement detectable without changing the PostgreSQL, Keyverse, Valkey, or
HTTP-only integration boundaries.

## Evidence

- `lineageweave.py`
- `lineageweave_server.py`
- `web/src/App.jsx`
- `compose.yaml`
- `docs/planning/adrs/0001-lineageweave-runtime-and-governance.md`
