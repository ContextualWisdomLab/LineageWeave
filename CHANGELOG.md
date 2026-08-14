# Changelog

## Unreleased
- Extended the issuer-free Compose live-model proxy to the full product-task
  contract used by customer-master, role, appointment, issue-work, ontology,
  factor-item, and report enrichment. Product transport now prefers the direct
  gateway and otherwise starts/reuses Compose; missing live model configuration
  remains an explicit unavailable/503 state and never becomes a recorded answer.
- Made the customer-master projection snapshot-replace on every explicit
  analysis result, including an LLM empty/abstain result, so stale customer
  relationships cannot remain visible after reanalysis. Reader surfaces now
  use business vocabulary for evidence and visibility instead of raw model,
  heuristic, or storage-code labels.
- Kept the reader-facing business screens separate from the administrator
  console in the ADR and runtime contract: ordinary users receive `업무 홈`,
  `업무공간`, and evidence-backed `고객 화면`, while policy, review, and
  account-directory controls remain server-gated administrator capabilities.
- Filtered stale persisted shared-thread edges at response time by checking
  both current document endpoints, so old relatedness records cannot reappear
  as false Lineage after a document's thread membership changes.
- Corrected a current product-runtime issuer-boundary recurrence: the
  `/oidc/*` discovery, authorization, token, and introspection aliases now
  reject before the single-page-app fallback, matching the worker's strict
  boundary. The direct-PostgreSQL rebuild returned `404` for all 32
  product-and-worker `GET`/`POST` probes without starting or using an issuer.
- Rechecked the direct-PostgreSQL relationship projections without exposing
  source content: one stale historical shared-thread row remains in each audit
  projection, while 3,020 current matching pairs per projection remain
  visible as non-temporal relatedness and the 107 observed row-successors are
  the only chronological links.
- The current source gate passes 350 tests plus one expected connector skip
  (351 when the optional fast-mlsirm interpreter is installed) and 100%
  line-and-branch coverage for 7,587 shipped-runtime statements and 2,964
  branches; the React V8 gate
  and production build pass as well.
- Added an isolated PostgreSQL service to the product test workflow and
  non-root users to shipped/test container images; the explicit static-scan
  exceptions document their validated URL and SQL trust boundaries.
- Reclassified a common thread identifier from a claimed document revision to
  reviewable inferred relatedness. Only direct same-document row succession
  can now render as chronological Lineage; shared-thread documents are paired
  canonically, labeled as a clue, and never numbered as an event sequence.
  Startup performs a narrow direct-PostgreSQL correction of matching legacy
  Lineage and Knowledge Graph edges without deleting documents or source data.
- Rechecked the supplied Figma file through the current connector session.
  The available metadata exposes only the cover page, so the previous claim of
  a readable event-intelligence target is withdrawn pending a reproducible
  node-specific reference and a paired user-chosen-browser capture.
- Improved administrator degradation behavior: a missing reviewed Keyverse
  account-directory configuration now appears as a Korean availability message
  rather than a raw configuration error or a false zero-account state. Server-
  enforced 게시글 권한 통제 and Lineage review remain usable, and no local
  issuer or synthetic account is introduced.
- Hardened the Keyverse-only relying-party boundary so common bare
  authorization, token, and introspection aliases are rejected before the
  single-page-app fallback. The canonical issuer-shaped routes remain
  rejected by both the product and the Compose model worker; neither process
  becomes an identity authority.
- Rebuilt the current `product` Compose profile against direct PostgreSQL with
  development identity disabled and no Keyverse/OIDC environment interpolation.
  The fresh container reached database health while anonymous sessions stayed
  Keyverse-gated and malformed email input failed locally. This is runtime
  configuration evidence, not real-account acceptance.
- Tightened organization-alias resolution at the shared inference boundary:
  an LLM canonical-name candidate is promoted by automatic R&R expansion only
  when organization-only SearXNG evidence contains both the alias and that
  canonical name. The administrator alias route now also rejects a `verified`
  verdict when the same cited evidence text does not contain both the queried
  alias and the exact proposed canonical organization; unresolved or
  conflicting labels remain visible as unresolved instead of entering the KG.
- Issue To Do/calendar enrichment now preserves the distinction between an
  explicit due date and an unscheduled follow-up. Missing or invalid model
  dates no longer become today's date; pending rows are migrated to a nullable
  `occurred_on` value and render as `일정 미정`. A bounded direct-PostgreSQL
  operator batch sends only title plus a capped Korean summary, persists only
  complete LLM work pairs, and delivers only its matching Valkey outbox batch.
  One 8-ticket live-HTTP run completed 3 LLM pairs, retained 5 fallback rows,
  and delivered all 3 scoped events with none pending.
- Added a first-class general-user product shell: the default authenticated
  entry is 업무 홈, with separate 업무공간 and 고객 화면 navigation. Reader
  actors see business summaries, evidence-backed customer relationships,
  reports, source drawers, and Knowledge Graph detail without the operator KPI
  strip, Lineage override controls, LLM queue controls, TEPP controls, or
  Keyverse account administration. The server remains the authorization
  boundary; navigation visibility is not treated as access control.
- Added an evidence-bound factor-item catalog task. The live LLM derived five
  candidate items from multiple writings, each with persisted report/document
  evidence. PostgreSQL now keeps ten fixed anchor items, five LLM candidates,
  ten candidate evidence links, and fifteen Rust fast-mlsirm calibration rows
  in separate normalized relations. All fifteen items reached `calibrated` in
  the current run; 58 report slices received five linked scores each and 22
  slices remain explicitly unlinked because their item responses were
  insufficient.
- Issue tickets now use the shared `open`, `in_progress`, and `resolved`
  lifecycle. An authorized status change updates the direct-PostgreSQL ticket
  and its linked To Do rows together, then emits the existing Valkey outbox
  event; readers cannot mutate ticket state.
- Customer commitments now have a bounded operator-only LLM refresh. Each
  committed appointment batch carries an internal batch marker, and only its
  matching committed outbox rows may be delivered to Valkey. A non-LLM or
  malformed model result leaves existing extracted appointments intact. One
  16-document live-HTTP batch produced 14 LLM-derived rows, preserved two
  fallback cases, and delivered its 14 scoped events with zero pending.
- Customer searches now keep the matching account selected while returning its
  persisted, authorized ancestors and affiliate edges. A subsidiary search no
  longer turns an otherwise evidenced customer tree into an unconnected root.
- Keyman Knowledge Graph popups now show every valid server-bounded node and
  directed relationship as `source → target`, including entity types,
  customer-readable relation labels, relation codes, and evidence status.
  Orphaned or malformed edge endpoints are not rendered as graph links.
- Clarified the operator environment example as a local product configuration
  only: it requires an externally operated Keyverse issuer and cannot be used
  to configure a loopback, Keycloak, or Keyverse imitation.
- Rechecked the external TEPP gate: the product has no configured TEPP service
  or credential, and TEPP's current HTTP contract is not a live server. The
  explicit unavailable state remains; no mock or local substitute is presented
  as integration or release evidence.
- Event cards now form only evidence-backed, contiguous numbered Lineage
  segments. Events outside a direct `row_successor` segment are unnumbered,
  independent observations with an explicit explanation; search ordering and
  semantic relatedness cannot create a successor presentation.
- Corrected historic protocol-fixture wording: retained issuer-shaped material
  is an unresolved ownership/audit finding, not a supported local login test,
  Keyverse substitute, or release-evidence source. Product acceptance still
  requires configured production Keyverse and a real business-account journey.
- Added four normalized RAGAS-aligned report metrics (faithfulness, answer
  relevancy, context precision, and context recall). Each report/metric row
  stores the live Judge source, verdict, score, and rationale; source-evidence
  references are stored in the separate `analysis_report_metric_evidence`
  relation, and unsupported metrics abstain without a fabricated numeric value.
- Re-evaluated all 80 persisted weekly/monthly report slices through the live
  LLM Judge: 320 metric rows (80 per metric) are now in PostgreSQL, all scores
  are within `[0, 1]`, and the existing 400 fast-mlsirm linked scores remain.
- Added parser, persistence, legacy-read, and malformed-model contracts for
  the normalized evaluation-metric boundary.
- Exposed persisted RAGAS/LLM-Judge report metrics in the general-user report
  detail, including pass/fail/abstain state, rationale, score, and bounded
  evidence-document links. A data-bearing browser run rendered four metrics
  and 32 authorized evidence links.
- Extended the data-bearing browser contract to select an actual Keyman in the
  document popup, open the authorized Knowledge Graph, and verify that typed
  relationship direction is rendered.
- Removed the dormant product-side Keyverse enrollment implementation,
  including account provisioning, local email capture, and browser-passkey
  challenge/attestation relay. Keyverse alone owns those responsibilities.
- Retired registration URLs now return `404` for both `GET` and `POST` before
  session authorization, so neither route can be mistaken for an authentication
  failure or reintroduced as an enrollment surface.
- The current complete source gate passes 350 tests with 7,569 statements and
  2,954 branches at 100 percent line-and-branch coverage.
- Added a V8-covered React presentation model for email validation, Keyman
  normalization, safe asset previews, semantic values, directed KG
  relationships, and customer trees. Its current 103 statements, 196
  branches, 28 functions, and 88 lines are all covered at 100 percent; the
  scheduled verifier and container web build run this gate before the React
  build.
- Excluded generated React coverage reports and build output from version
  control and container build context so local absolute paths and transient
  bundles cannot enter a public repository or image build.
- Added a reproducible Playwright login-gate E2E that exercises empty,
  malformed, and unavailable-configuration input without contacting or
  emulating an identity authority.
- The no-issuer login gate is explicitly local UX evidence only: it never
  starts, contacts, or represents Keyverse, and it cannot satisfy the real
  business-account login/callback/session/logout release acceptance.
- The currently accessible Figma file contains an event-intelligence target
  frame, but Product/Figma parity remains blocked until it is compared with a
  matching user-chosen-browser capture. The synthetic email UX check supplies
  neither visual nor identity acceptance.
- Corrected the evidence register: the product has no in-process psychometric
  fallback, and Figma structural QA is distinct from the still-blocked
  release-level product/Figma parity acceptance.
- Unified customer-visible lineage terminology as `글 자체의 Lineage`; the
  event-lineage API contract and observed-versus-relatedness separation remain
  unchanged.
- Optional persisted evaluation-metric reads no longer hide otherwise valid
  weekly/monthly reports and their linked scores when that separate query is
  unavailable.
- Direct-PostgreSQL batch commands now keep JSON, analytics, and DOT exports
  disabled by default. Operators can still create a detached file only by
  providing an explicit output path, while the canonical analysis state remains
  PostgreSQL.
- Added a minute-17 hourly product-gap proposal workflow. OpenCode receives
  only NVIDIA_NIM_API_KEY; an immutable patch is independently verified before
  a separate publisher can open one PR, while review, Checks, approval, merge,
  release, and deployment remain outside model authority.
- The product Compose profile now forwards the direct PostgreSQL DSN and source
  table only from operator-provided environment interpolation. This fixes a
  product-profile startup failure without committing either runtime value or
  adding a database proxy or local identity service.
- Reader detail and KG requests now calculate predicted relatedness without
  mutating PostgreSQL. Only the bounded administrator enrichment path can
  materialize that non-transition relatedness for review.
- Removed the in-process FIPC/CAT/EAP score fallback. Report linking now
  persists scores only when the separate Rust-backed `fast-mlsirm` HTTP/local
  connector returns package-produced scores; missing, malformed, diagnostic-
  only, or recorded-response bodies remain `unavailable` with no score rows.
- Replayed the persisted Judge item responses through the local package
  connector and reconciled the derived PostgreSQL report tables: 80 reports
  now retain 400 package-produced `fast_mlsirm` scores, with zero orphan,
  missing-score, or legacy fallback payload rows.
- Corrected an earlier changelog wording that described an isolated external
  identity run. It is not current identity evidence and must not be run, used,
  or cited as Keyverse or release acceptance; only a configured production
  Keyverse journey with a real business account can satisfy that gate.

## 0.2.18 - 2026-08-15
- HTTP response writes now treat a browser cancellation or connection reset as
  a normal disconnected client, preventing a second error write and noisy
  server traceback while large authorized surfaces are being delivered.
- The current product-runtime gate passes 333 tests with 7,358 statements and
  2,838 branches at 100 percent line-and-branch coverage.
- A fresh Edge reader E2E completed the authenticated development-session flow
  through 업무 홈, 업무공간, 고객 화면, document popup, source drawer, and
  Knowledge Graph; no administrator navigation or diagnostic KPI was exposed.

## 0.2.17 - 2026-08-15
- The customer-master screen now renders the evidence-backed affiliate
  hierarchy as an accessible, selectable tree with depth-aware indentation;
  selecting a tree node focuses the same customer detail and source documents.

## 0.2.16 - 2026-08-15
- The general-user customer screen now keeps customer counts, list state,
  account detail, and affiliate-tree state explicitly pending while its
  authorized PostgreSQL request is in flight; a settled empty customer master
  is no longer confused with a loading delay.

## 0.2.15 - 2026-08-15
- Task-aware LLM calls now allocate simple work to single-model routing and
  enrichment, multimodal inspection, verification, and report work to bounded
  deep orchestration through the HTTP-only contextual-orchestrator boundary.
- Direct model gateways receive only portable prompt metadata; route/conduct
  controls are sent only to an explicitly configured orchestrator endpoint.
- Multimodal inspection preserves the image part and its document-scoped
  semantic context while the upstream multimodal message contract remains an
  independent review and merge gate.
- Local validation passed 332 tests and 100 percent line-and-branch coverage
  for the product runtime.

## 0.2.14 - 2026-08-15
- Reader-facing home metrics now show an explicit loading state until the
  authorized PostgreSQL surfaces arrive, so an initial network delay cannot
  look like an empty workspace.
- The browser OIDC conformance runner is directly executable and tears down
  only its separate IdP/RP Compose projects on exit, including assertion
  failures, without removing volumes or touching the product stack.
- A real external-IdP browser run completed email login, callback/session
  establishment, reader-safe home navigation, customer screen, document
  popup, evidence drawer, and semantic KG checks against the direct database.
- Re-evaluated all persisted weekly/monthly slices through the live judge
  gateway in bounded maintenance batches: 80 `llm_judge` reports (`pass=50`,
  `fail=30`), 400 linked scores, zero missing-score reports, and zero orphan
  scores remain in PostgreSQL.

## 0.2.13 - 2026-08-15
- When a direct LLM or orchestrator URL is absent, Keyman extraction now starts
  and uses the Compose live-model proxy through the same HTTP contract. If the
  proxy cannot start or its gateway is unavailable, the product reports an
  explicit unavailable state; it never records a response or creates an actor.

## 0.2.12 - 2026-08-15
- Confirmed the reader-facing product entry point as `업무 홈`, with separate
  `업무공간` and evidence-bound `고객 화면` navigation. General users no longer
  start in operator diagnostics; KPI, queue, access-policy, Lineage-review,
  enrichment, and TEPP controls remain administrator-only.
- Recorded the customer-master semantic boundary: normalized customer and
  affiliate rows are exposed only after actor-scoped account-to-document
  evidence survives ABAC/RBAC, and the KG uses the persisted
  `schema:Organization`, `schema:subOrganization`, and `schema:about` terms.
- Reused the single PostgreSQL TEPP run-table DDL helper in the full snapshot
  writer so the direct database boundary has one schema definition.

## 0.2.11 - 2026-08-15
- Added the separate TEPP v1 analysis-run HTTP port. Administrator requests
  validate contract version, bounded snapshot/cutoff/model/output fields,
  HTTPS configuration, idempotency, and same-corp authorization before calling
  `POST /v1/analysis-runs`; missing TEPP service configuration remains an
  explicit unavailable state with no recorded-result fallback.
- Added normalized PostgreSQL TEPP run metadata and Valkey outbox events, plus
  administrator status/refresh endpoints and a real React TEPP request panel.
- The current complete source gate passes 329 tests, 7,313 statements, and
  2,838 branches at 100% line-and-branch coverage; React production build
  remains green.

## 0.2.10 - 2026-08-14
- Rate-limited live model calls now become explicit abstentions instead of
  aborting a PostgreSQL analysis run; report judge rows are never persisted
  with a NULL verdict, and `judge_verdict` is seeded in the shared ENUM table.
- The complete Python source gate now includes the retained offline OIDC
  utility: 323 tests, 7,147 statements, and 2,780 branches pass at 100%.
- The isolated OIDC browser fixture accepts runtime-only corp/PU scope claims
  and fails data-bearing acceptance when an authenticated scope returns no
  documents. The real direct-PostgreSQL reader flow completed login, customer
  screen, popup, evidence drawer, and KG checks.
- Added the role-separated browser acceptance record: reader navigation hides
  administrator diagnostics, while an administrator actor reaches access-policy
  and Lineage review screens and restores a relatedness visibility override
  after private/public HTTP 200 mutations. Customer-master accounts remain
  Ontology/Semantic-Layer evidence-bound.

## Unreleased
- Removed the customer-facing product-side first-use/passkey registration flow.
  The login gate now has one email-first `계속하기` action; configured Keyverse
  owns account setup and passkey policy after the redirect.
- Retired the unauthenticated product registration API: `POST /api/register`
  and `POST /api/register/complete` now return `404` and cannot provision or
  relay a passkey ceremony.
- Raised the authorized inline-image inspection ceiling from 6 MiB to 50 MiB so
  large source cells that are data-URI images remain OCR/object-analysis
  candidates without entering the graph or browser payload. Persisted metadata
  is recalculated on read; unconfigured or rejecting model gateways still fail
  explicitly and create no synthetic inspection.
- Automatic issue To Do/calendar rows now upsert their 3NF ticket parent before
  the work rows. Snapshot reconciliation owns only pipeline-created parents; a
  metadata-only direct-PostgreSQL repair inserted 28,211 missing parents while
  preserving two non-automatic tickets.
- Re-ran the complete product-runtime gate after the boundary change: 332 tests,
  7,354 statements, and 2,836 branches pass at 100% line-and-branch coverage.
- Improved unavailable-login guidance: a valid-format address now receives a
  plain retry-or-contact-administrator message without exposing identity
  implementation details.
- Rechecked the rebuilt Compose product boundary. Direct-PostgreSQL runtime
  inputs remain deployment-supplied and fail closed when absent; the retained
  issuer-shaped test utility is not a product identity authority or acceptance
  substitute.
- Rechecked the active direct-PostgreSQL snapshot and deployed React bundle:
  all 107 observed row-successor edges join source rows from the same document,
  while the Event Lineage UI creates a connector only from that explicit marker.
  Search-result order cannot create a chronological chain.
- The reader home and document rail now distinguish initial loading, a
  completed empty authorization scope, and a request failure. A user with no
  authorized records no longer sees a perpetual loading message.
- Added a reproducible, separate OIDC conformance fixture for browser
  acceptance without a business account: a test-only Keycloak realm and Valkey
  Compose project provision the callback, `org`/`workspace`/`role` claims, and
  reserved `.test` reader account used by the direct-PostgreSQL relying-party
  runner. It remains outside the product profile and does not use or emulate a
  production Keyverse deployment.
- Added the temporal report-state boundary: weekly/monthly report observations
  carry stable slice identity and exact period ordering, and a configured
  fast-mlsirm longitudinal export is persisted into normalized state-spec,
  state-run, and state-observation tables. Missing connector capabilities stay
  explicitly unavailable; no Python or recorded psychometric fallback is used.
- Added `tests/compose.oidc-e2e.yml`, a test-only direct-PostgreSQL OIDC
  relying-party runner. It consumes a separately provisioned conformance IdP;
  it neither adds an issuer to the product Compose profile nor makes the worker
  serve identity routes. A selected-browser run completed email-first sign-in,
  reader workspace access, and product logout. Temporary test-realm callback
  and claim mapping changes were restored. This is not production Keyverse,
  business-account, passkey, or Figma-parity release acceptance.
- Semantic document search now preserves its relatedness threshold. When no
  authorized semantic result qualifies, it returns an explicitly labelled
  `keyword_fallback` from the same direct-PostgreSQL ABAC query instead of an
  empty list or an invented Lineage relation. The reader sees that the results
  are title/document matches, not semantic transitions.
- Product and worker containers now explicitly reject discovery,
  authorization, token, and introspection-shaped issuer paths with the shared
  404 JSON contract. This prevents the product's React fallback or generic
  request authentication from making the relying party look issuer-capable.
  The product Compose service also preserves operator-supplied direct database
  settings from its env file instead of overwriting them with empty values.
- Product Compose preflight now resolves the effective env-file configuration
  and rejects missing direct PostgreSQL or external OIDC settings before
  startup, naming missing keys but never their values.
- Verified the bounded live Event Lineage chat in the selected browser against
  direct PostgreSQL data. A reader-scoped document returned a non-empty answer
  with five citations, including one VOC source citation; opening that citation
  rendered the authenticated source drawer. The temporary isolated-realm scope
  mapping was restored and the browser session was logged out afterward.
- Corrected typed Keyman identity handling at the shared normalization boundary:
  LLM or administrator-supplied institutions remain `organization` actors and
  meso units remain `team` actors instead of being written as `person_name`.
  Their affiliation and Node/Entity/Relationship/Direction qualifiers survive
  PostgreSQL persistence, normalized ontology/semantic indexing, adaptive KG
  lookup, and the administrator editor. Legacy four-column person input remains
  compatible. Added organization/team KG regression coverage.
- Added a real admin browser mutation regression: an explicit organization
  Keyman can be entered and saved from the React administrator popup, returns
  HTTP 200 without `person_name` coercion, and the test restores the original
  persisted state.
- Completed a selected-browser, direct-PostgreSQL local replay with an
  isolated reader-only Keyverse test configuration. The workspace exposed 100
  authorized document choices; one opened nine-bead detail rendered zero
  observed connectors and zero relatedness entries, so returned-item order did
  not create a history line. The local session was logged out and the isolated
  realm's temporary scope mapping was restored. This is not production
  Keyverse, a business account, passkey, or Figma-parity release acceptance.
- Corrected the remaining Event Lineage ambiguity: inferred/predicted
  relatedness is no longer appended to the observed event bead chain. The API
  exposes it as `event_lineage.relatedness`, and the React popup presents it in
  a separately labelled panel. A chronological connector now requires an
  explicit observed `row_successor` marker, never adjacent returned cards.
- Reconciled the general-user/customer product-surface ADR and design QA with
  the now-readable Figma MU-02 semantic-search and MU-14 document-detail
  frames. The live React surface retains authorized API data, customer-master
  evidence, and Lineage semantics while adopting the target card/canvas/
  selection language; pixel parity is deliberately not claimed for dynamic
  data or the required extended detail panels.
- Extended boundary tests to reuse compose-guard script path constants (`COMPOSE_YAML_PATH`, `WORKER_PATH`, `WORKER_DOCKERFILE_PATH`) so identity checks are robust regardless of pytest working directory.

- Composer identity boundary assertions now load `compose_identity_boundary_contract.json`
  from repository resources so `compose.yaml` hardening, worker hardening, and
  contract tests share one source of truth. This keeps forbidden key fragments,
  boundary key prefixes, and worker hardening lines from drifting between
  script and test surfaces.
- Fixed boundary script bug by reading forbidden key prefixes from the product
  contract section; identity guard now runs cleanly from repository root with the
  same contract payload.
- Made compose boundary guard deterministic across working directories by loading
  `compose.yaml` and worker files from script location (`COMPOSE_ROOT`) rather
  than process CWD; the guard now passes both `python scripts/check...` and
  `cd scripts && python check...`.
- Hardened boundary regression tests to validate the CWD-independent guard path
  and explicit product-block plain-value boundary failure path by targeting the
  script's `COMPOSE_YAML_PATH` directly.
- Fixed the false Lineage projection caused by admitting every inferred or
  predicted edge into the selected document's bead chain. A relatedness bead
  now requires the selected document to be an endpoint, while chronological
  connectors remain limited to adjacent observed events.
- Fixed full analysis replacement so it merges durable, verified organization
  aliases before replacing KG and semantic rows. Interactive alias verification
  now survives both direct KG rebuilds and complete source reanalysis.
- Added an administrator-only `게시글 권한 통제` screen and a durable
  `Lineage 검토` screen. Administrators can review same-corp inferred or
  predicted candidates, exclude or restore a relation, and record a reason;
  observed transitions remain immutable. Decisions are stored in the
  normalized `analysis_lineage_edge_overrides` table, applied to both Lineage
  and document KG responses, and emitted through the PostgreSQL outbox.
- Added the bounded `entity_role_classification` product task. Selected
  documents can have their partner/competitor/customer/end-customer/market
  subject classified by the general LLM contract; only common ENUM roles or
  allowlisted English aliases are accepted, and model abstention falls back to
  the observed title classifier without creating Lineage transitions.
- The current full suite passes 317 tests. The explicitly shipped product
  source gate is 100% line-and-branch covered (6,986 statements / 2,732
  branches), while the whole-tree report is 98% because it also counts the
  retained unshipped issuer-shaped audit artifact, the guard script, and test
  modules. The browser build is verified from the actual `web/` project with
  `npm run build`.
- Added a reader-friendly `업무 홈` as the default authenticated React
  surface. It summarizes recent work, evidence-backed customer relationships,
  reports, and the actor's effective scope; operator KPI and event-queue
  diagnostics are now limited to the administrator workspace.
- Browser acceptance now captures the authenticated home surface and checks
  the reader contract explicitly: a non-admin actor sees only 업무 홈,
  업무공간, and 고객 화면, with no administrator navigation or diagnostic
  KPI strip. The real-data detail wait was extended to cover slow PostgreSQL
  responses, so lineage assertions use the response for the selected document
  rather than an empty timeout fallback.
- Added the ADR and traceability contract for customer-master semantics:
  customer accounts, affiliate edges, and account-to-document evidence remain
  normalized PostgreSQL data, then enter the actor-filtered KG through
  `schema:Organization`, `schema:subOrganization`, and `schema:about` terms.
- Document-detail issue work is now queued through the PostgreSQL outbox and
  enriched off the HTTP response path, so a general user can open a document
  while LLM-authored To Do and calendar content is still pending.
- Added administrator-only bounded LLM enrichment controls. The React operator
  surface can queue `keyman`, product, appointment, or combined work for at
  most 64 documents; PostgreSQL outbox state and aggregate status make the run
  auditable. Existing user Keyman overrides are preserved, and an empty live
  model response is stored as an explicit abstention instead of fabricated
  people. A direct PostgreSQL one-document smoke completed with zero failures.
- Added the full TEPP APA 7th research register to `docs/doctoring` and added
  four open document-understanding papers to the Local Zotero provenance set.
  The current Connector/PostgreSQL verification stores 12 parents and 12
  original attachments with digests; the attachment ceiling is 32 MiB so the
  larger open multimodal paper is retained without disabling bounded transfer.
- Expanded the TEPP doctoring register with the task-level event/TimeML,
  temporal-reasoning, cross-classified/multiple-membership, recovery,
  reproducibility, concurrency, GraphML/API, and privacy/security references
  cited by the current TEPP research notes, all in APA 7th form. This records
  the research basis without claiming that LineageWeave owns TEPP's future Rust
  estimator.

- Added separate authenticated customer and administrator screens to the React
  product. `/api/customers` filters normalized customer-master accounts and
  affiliate edges by actor-visible document evidence. The admin mode uses a
  server-only Keyverse Admin REST adapter to list same-corp/unassigned accounts
  and update only the verified corp, PU, and `lineageweave-web` client roles;
  cross-corp targets, missing roles, malformed claims, credentials, and tokens
  are rejected or withheld.
- Added the customer/admin HTTP contracts and a fresh source-scoped run passed
  291 tests with 100% line-and-branch coverage (6,497 statements / 2,522
  branches). React production build verification remains part of the gate.
- Production `product` Compose profile now hard-fixes Keyverse OIDC variables to
  empty strings (`KEYVERSE_ISSUER`, `LINEAGEWEAVE_OIDC_CLIENT_ID`,
  `LINEAGEWEAVE_OIDC_CLIENT_SECRET`, `LINEAGEWEAVE_OIDC_REDIRECT_URI`,
  `KEYVERSE_CA_BUNDLE`) and keeps the model proxy 404-ing OIDC discovery,
  auth, and token routes. New boundary tests assert the compose profile and
  worker contract remain strict at runtime.
- Added `scripts/preflight_product_compose.sh` to make product compose startup
  fail fast when Keyverse identity hardening is not in place and when the
  compose configuration itself is invalid.
- Added an explicit integrated semantic-search action for the document list.
  It derives a bounded live query embedding, ranks only direct-PostgreSQL
  vectors from documents authorized for the current actor, and never presents
  lexical fallback results as semantic evidence. The in-process candidate scan
  reports its ceiling instead of silently claiming corpus completeness.
- Repeated content reads now compare the normalized DOM/format/asset rows and
  leave unchanged rows in place, preserving their source-linked embeddings;
  an actual content change still invalidates stale vectors through the existing
  foreign-key cascade. Semantic-related retrieval now reads the same bounded,
  actor-authorized PostgreSQL candidate set as semantic search instead of
  materializing the full KG. A live content-view round trip retained all 29
  indexed chunks and returned an inferred neighbor in 0.19 seconds.
- Full KG replacement now carries forward only persisted, verified
  `organization_alias` additions and regenerates their semantic assertions.
  Metadata-only method-paper refreshes also retain a prior Zotero attachment
  key, status, and digest instead of downgrading a stored original to
  `not_attempted`.
- Search results no longer appear as a fabricated Event Lineage. The workspace
  now renders only the selected document's evidence-bound event beads, and it
  draws connectors only between consecutive observed events. Inferred and
  predicted relatedness remains visibly separate rather than becoming a
  sequence claim. A focused UI contract, browser-script syntax check, and the
  React production build pass; the managed-browser matched-content flow is
  accepted with the divergences recorded in `design-qa.md`.
- The selected-document guard now suppresses stale event beads while a new
  search result is loading, and persisted predicted neighbors are ranked by
  title-token overlap before the stable document-number fallback. This keeps
  list order and coarse entity-role matches from masquerading as chronology;
  the direct detail path is covered by the same full test gate.
- The login gate now presents Keyverse-first, organization-policy registration
  guidance and no longer directs end users to a hard-coded local endpoint. The
  passwordless registration API remains fail-closed without a configured
  Keyverse registration service.
- A fresh current-tree run passed all 287 tests at 100% line-and-branch
  coverage (6,434 statements and 2,498 branches). When no explicit
  `LINEAGEWEAVE_TEST_DSN` is supplied, pytest uses a validated
  process-owned PostgreSQL test database so database-scoped locks and analysis
  tables cannot contaminate the suite. This is local source evidence, not
  production or release acceptance.
- The target-Figma paired managed-browser comparison is accepted with
  documented divergence. A configured production Keyverse real-account
  login, callback, session, logout, and matched content parity remain required
  release gates; `design-qa.md` keeps that distinction explicit.
- Document search now queries the complete PostgreSQL-backed, ABAC-filtered
  corpus and keeps pagination server-side instead of filtering only the first
  100 browser rows.
- Verified organization aliases now persist through a two-node/one-edge
  incremental KG transaction mapped to SKOS `exactMatch`; the request no
  longer loads or rewrites the complete graph. The Compose SearXNG service and
  live product LLM produced and stored a cited `verified` decision in the
  normalized inference tables.
- Historical loopback Keyverse ceremony records are retained as development
  evidence only. They do not satisfy the current production HTTPS, real-account
  browser login/callback/session/logout acceptance gate.
- Live multimodal inspection evidence now contains seven non-empty OCR/model
  results across three source documents, with no placeholder result; labels
  remain normalized per asset relation.
- Report calibration now uses the report ID as the psychometric observation
  unit, so the same PU/team/project label cannot mix weekly and monthly
  responses. A live reanalysis of all 80 persisted slices completed all 80
  LLM-as-a-Judge labels and 400 package-produced fast-mlsirm linked scores;
  the local connector exercised the installed Rust-backed EAP path.
- Report judging now retries each slice independently up to three times. A
  transient gateway failure can no longer trip a global circuit that marks
  every later report unavailable; the live reanalysis completed 80 of 80
  Judge decisions after this repair.
- Report persistence now removes score rows whose report no longer exists,
  preventing stale FIPC/CAT artifacts from surviving a changed report window.
  The real PostgreSQL recheck ended with 80 reports, 400 scores across 80
  report observations, zero orphan scores, and zero reports without scores.
- Compose now owns its SearXNG settings in a small pinned custom image and
  seeds the upstream image's declared config volume through an entrypoint;
  `docker compose up --remove-orphans --wait` passed Valkey, stand-in, and
  SearXNG health checks without leaving a duplicate project name.
- The document index now returns authorized corp/PU metadata so the bundled
  browser acceptance flow selects a manageable document before exercising
  visibility mutation; the updated click-by-click run restored visibility to
  public with two HTTP 200 responses.
- Compose product and worker services now optionally load the operator
  `${LINEAGEWEAVE_ENV_FILE:-$HOME/.env}` file, preventing a configured live
  model gateway from appearing unset inside the container while keeping the
  secret file outside the image and repository.
- Added bounded DOM-semantic embedding indexing and actor-filtered relatedness.
  The index uses verified HTTPS, source-linked chunks, normalized PostgreSQL
  model/vector relations, metadata-only outbox events, and inferred
  `semantic_related` results that never become document succession. The new
  module has eight focused contracts and 100% line-and-branch coverage. A
  bounded direct-PostgreSQL check retained a high known-thread match and now
  suppresses low-score retrieval with a multilingual-calibrated 0.40 floor, using
  aggregate-only evidence. The current source-hash runtime coverage run passed;
  real-Keyverse route acceptance and labeled retrieval evaluation remain
  release evidence.
- R&R model output now keeps organizations as PROV agents and represents each
  document/agent/role direction with PROV qualified attribution. Person
  affiliations use ORG Membership, while supported organization, rank, and
  title qualifiers prevent same-name people from collapsing into one KG node.
- R&R attribution metadata now keeps the model-supplied `node`, `entity`,
  `relationship`, and `direction` values in persisted KG attribution metadata
  instead of reducing them to a display label. Cold visibility, Keyman, ticket,
  and LLM-Keyman mutations also avoid rebuilding the full snapshot before
  returning.
- Full snapshot replacement now uses MVCC-friendly transactional `DELETE`
  ordering, so long analysis writes do not take an `AccessExclusiveLock` that
  freezes live document reads; a versioned staging table remains the upgrade
  path if delete/vacuum cost becomes material.
- Production snapshot writers now release schema-migration locks before the
  long data transaction, then reacquire the transaction-scoped KG lock. Test
  and library callers retain their existing transaction ownership.
- Keyman normalization and its React editor preserve optional rank/title
  qualifiers (`person | organization | rank | title`) for the same identity
  boundary.
- Local Zotero storage reuses an exact title/source parent and verifies its
  matching attachment URL and SHA-256 before writing, preventing repeated
  analysis runs from creating another copy of the same method paper.
- OA downloads now send an identifying User-Agent and the Connector attachment
  metadata carries its `sessionID`; this preserves NIST-hosted originals that
  reject Python's default client and completes eight verified parent/original pairs.
- Historical bundled-browser runs exercised full-corpus search, detail, cited
  organization-alias verification, evidence drawer, persisted OCR image search,
  and a WCAG 2 A/AA scan with zero violations and zero incomplete results. The
  current local run uses an explicit development actor; these artifacts are
  not user-selected-browser, production-Keyverse, or Figma acceptance evidence.
- Historical source-hash-guarded release-gate rechecks reached 100% coverage
  for all four shipped Python modules. The latest independently captured
  isolated snapshot passed 258 tests and one intentional skip at 100% (5,952
  statements and 2,316 branches). After the closed-claim and public-origin
  Keyverse repairs, a new direct-PostgreSQL run waited on a database lock after
  213 passes and one skip. That interrupted run is now superseded by the fresh
  263-test source-hash snapshot above. Python compilation and the React build
  remain required companion checks; this does not claim a real end-user
  Keyverse login.
- Document detail uses a native modal dialog, including focus containment,
  Escape close, backdrop close, and an in-dialog error surface.
- Earlier release-gate recheck: 235 tests passed, the React production build
  and Python compilation succeeded, and the prior source-scoped
  branch-coverage command reported 100% for `lineageweave.py`,
  `lineageweave_server.py`, and the Compose worker without exclusions.
  Bundled-browser E2E artifact also exercised the React login redirect,
  document popup, evidence drawer close, KG lookup, and admin visibility
  mutation against PostgreSQL. It is historical local evidence only and does
  not replace current user-selected-browser production acceptance.
- Made the existing weekly/monthly report API usable as a report drilldown:
  operators can inspect the bounded judge rationale and linked factor scores,
  then open one included document. The authenticated workspace also shows the
  existing Valkey outbox health signal instead of leaving it API-only.
- The login gate now starts Keyverse passkey enrollment from the product
  (`POST /api/register`). The IdP has no signup form; the product requests a
  password-free enrollment challenge and finishes WebAuthn in the LineageWeave
  page (`POST /api/register/complete`) before Keyverse SSO.
- Limited CLI persist (`--limit`) upserts the incoming subset and durable
  Keyman only. It no longer replaces the live document snapshot, so a
  `--limit 20` smoke writer cannot wipe a prior full-table LLM Keyman.
- Local Keyverse passkey pages are opened on `localhost`. Browsers reject
  `127.0.0.1` as a WebAuthn RP ID (`SecurityError: invalid domain`).
- Local Zotero loopback HTTP is accepted without `LINEAGEWEAVE_DEV_MODE`.
  CLI persist no longer records every OA paper as `invalid_url`.
- R&R parse treats meso labels such as 설계팀 as `org:OrganizationalUnit`
  with `affiliated_organization_name`, expands abbreviated organization
  names from Searxng evidence, and rejects `[image: content unavailable]`
  as a vision result.
- Added durable LLM/user Keyman provenance and a bounded Local Zotero original
  attachment path. Eight method-paper parents and eight OA originals were stored
  in the live verification run with SHA-256 digests.
- Removed the personal local DSN from public defaults and fixtures; source
  access now uses runtime `LINEAGEWEAVE_DSN`/`LINEAGE_SOURCE_TABLE` settings.
- Historical runtime verification expanded to 209 collected tests with 100%
  line and branch coverage across the then-validated shipped Python product and
  Compose worker modules; the current release-gate recheck above supersedes it
  for present-tense readiness.
- Serialized full knowledge-graph replacements with a transaction-scoped
  PostgreSQL advisory lock, replaced reader-blocking KG truncation with
  transaction-atomic node-then-edge deletes, and check edge schema columns
  before issuing a legacy migration DDL statement.
- Added partial direct-PostgreSQL lineage-edge indexes for inferred/predicted
  document ordering. A cold, actor-filtered document list no longer performs a
  full edge scan for every visible document.
- Hardened Keyverse claim projection so a malformed account-attribute envelope
  is rejected as unauthenticated rather than reaching attribute parsing.
- Added a normalized PostgreSQL ontology and semantic layer for KG namespaces,
  terms, domain/range rules, RDF type assignments, and evidence-preserving
  predicate assertions. Event chat now reads only the actor-filtered semantic
  subgraph and fails closed when that grounding is unavailable.
- Customer-master account-to-document evidence links now scope customer KG
  nodes, affiliate relations, and browser responses; unscoped model output is
  retained out of the visible KG.
- Separated the two-sided Keyman adapter from general product enrichment.
  Appointment extraction, customer-master updates, issue-work content, and
  report judgement now use an allowlisted structured Chat Completions contract
  instead of the Keyman endpoint or prompt.
- Product login is authorization-code PKCE against the configured Keyverse
  issuer; corp and PU remain verified session attributes. When live Keyverse
  is unset, login fails closed; the shipped Compose worker has no issuer
  contract and returns 404 for identity-shaped routes.
- CLI persist merges existing predicted `entity_role_affinity` edges back
  after a structure rebuild so popup-written relatedness is not truncated.
- Keyman click loads a bounded persisted KG neighborhood (people, companies,
  events, posts, adaptive per-node depth) instead of the single-document VOC
  snippet from a cold API start.
- KG neighborhood `depths` maps stringify node identifiers so HTTP JSON
  cannot fail on tuple keys.
- Added a bounded ontology-relation verifier: observed internal KG evidence
  and optional SearXNG evidence are supplied to the product LLM, which can
  only return verified, rejected, or insufficient without promoting an
  inferred relation automatically.
- Persist now truncates `analysis_customer_document_links` together with
  `analysis_customer_accounts` so a second analyzer run does not fail the
  PostgreSQL parent-FK TRUNCATE rule.
- Meeting titles without an in-text date now take the document-number date
  (or first event timestamp) as the 고객 약속 date. The document popup
  overlays persisted appointment rows so the 약속 list is not empty.
- Two-sided Keyman no longer keeps the same person/org on 사측 and 상대측.
  Title-bracket organizations stay on the counterpart; the author fills 사측
  when that split would otherwise leave it empty.
- Opening a post with pending To Do/calendar stubs asks the product LLM for
  authored bodies and upserts those rows so the popup is not a template stub.
- Customer-master persist rejects entity-role labels used as account names and
  keeps only group/national/HQ/plant organizations with parent-child edges
  that the semantic layer maps as schema.org/subOrganization lineage clues.
- `/api/analytics`, `/api/reports`, and the document list/popup no longer
  rebuild or serialize the full persisted graph on a cold API start. Workspace
  metrics, period reports, and a single post load from bounded PostgreSQL
  queries so recapture does not time out.
- Event Lineage now renders a beads-on-a-string DAG of observed events plus
  persisted inferred/predicted relatedness. Predicted entity-role affinity is
  stored as a non-transition. Popup chat cites ontology/semantic-layer URIs
  and still slides VOC evidence into the source drawer.
- Weekly/monthly report slices expose FIPC/CAT linked-score families
  (일반 경영 / 산업별 / 영업 Lead) in the workspace so every emitted slice
  shows its judged verdict and linked factor coverage.
- The report judge now receives the slice body and source-document writings.
  Factor-item responses come from that LLM verdict, not title-token
  heuristics. Local fast-mlsirm persists package EAP scores only; otherwise
  the report remains explicitly unlinked.
- Event-lineage chat citations carry a VOC `evidence_id`. Clicking a
  non-ontology citation opens the sliding source drawer; the evidence
  lookup falls back to the document's observed row when the cited handle is
  not a source guid.
- Customer-master persist completes a group → national → HQ → plant
  affiliate ladder. The workspace tree and Keyman KG walk attach those
  parent/child clues instead of a single parent→plant hop.
- OA method papers used by mixed-body extract and inferred-relation
  verification are posted to the operator-managed Local Zotero Connector when
  that API is reachable; an unreachable or rejected write is persisted as that
  outcome and is never labeled stored.
- When `LINEAGEWEAVE_MLSIRM_URL` is unset, report linking uses a sibling
  ContextualWisdomLab/fast-mlsirm install as an owned local connector if that
  interpreter is present.
- Added a milestone-2 real-data execution run: `lineageweave.py --table
  $LINEAGE_SOURCE_TABLE --write-reports` now builds the configured-source
  payload with weekly/monthly report slices and persisted linked scores.
- Added product transport availability mode metadata: when LLM gateways are
  unavailable, analysis still completes with deterministic fallback and all
  unfulfilled tasks marked `unavailable` rather than blocking snapshot writes.

## 0.2.9 - 2026-08-13

- Issue tickets persist a To Do and a calendar item with LLM-authored content.
  Appointment extract, LLM customer-master / affiliate-tree lineage clues, and
  weekly/monthly PU·팀·프로젝트 reports with dichotomous LLM-as-a-Judge
  scores plus owned FIPC/CAT linking over 3NF 일반 경영 / 산업별 / 영업 Lead
  factors are shipped. Inferred edges stay non-transitions.
- The source line retains no Compose OIDC fallback: the worker is model-task
  only, while Keyverse remains the sole identity provider for the product.

## 0.2.8 - 2026-08-13

- Removed the mistakenly restored Compose OIDC issuer from the release worker.
  The worker now exposes only health and live-model task routes; Keyverse is
  the sole identity provider and the product remains its relying party.
- Added a direct-PostgreSQL inline-image/markup marker to the bounded source
  projection. It detects a data URI or SVG even when it appears after the
  short metadata prefix, while the graph and browser continue to receive only
  byte length, prefix, and classification metadata.
- Re-persisted the direct-source snapshot without exporting source content;
  the release evidence now records the marker-aware classification path.

## 0.2.7 - 2026-08-13

- Removed the invalid local OIDC fallback from the Compose worker. A missing
  Keyverse issuer now fails the product login start closed; the worker exposes
  only health and live-model task routes.
- Worker tests assert that discovery, authorization, token, and introspection
  return `404` rather than completing a local PKCE exchange.

## 0.2.6 - 2026-08-13

- Added a KG-scope regression that removes hidden evidence and document
  metadata from shared graph entities.
- Kept the Keyverse boundary external even in local development: an
  operator-provisioned development issuer is required for login and is never
  substituted by the model worker.

## 0.2.5 - 2026-08-13

- The Compose HTTP worker forwards model tasks only. It has no local account,
  client, token, tenant claim, discovery, authorization, token, or
  introspection implementation; an unconfigured Keyverse issuer fails closed.

## 0.2.4 - 2026-08-13

- Closed a shared-KG authorization disclosure path: retained shared nodes now
  expose only actor-visible document scope, and KG relations whose evidence is
  outside the actor-visible document, row, or thread scope are suppressed.
- Added direct product-flow, Keyverse relying-party, PostgreSQL persistence,
  Valkey protocol, worker, and HTTP failure-contract tests. The measured
  branch-coverage baseline is 90%; this is reported as measured, not rounded
  up to a 100% claim.

## 0.2.3 - 2026-08-13

- Removed the local OIDC issuer from the Compose worker. It now forwards live
  model tasks only; it cannot create an account, client, token, or tenant
  claim. Browser authentication remains with the configured Keyverse issuer.
- Hardened the explicit local Keyverse HTTP exception: both development
  switches and an allowlisted loopback or Docker host-bridge origin are
  required. Production remains HTTPS-only.
- Added the Docker host-gateway mapping for a direct host-local PostgreSQL
  connection, a product health check, and loopback-only published service
  ports by default.
- Removed the synthesized worker bearer token; an operator-supplied worker
  token is forwarded only when one is actually configured.
- Added application-level direct-database and worker HTTP contract tests, plus
  a rebuilt-container acceptance check for PostgreSQL, authorized inline
  assets, Valkey, and the worker's no-identity boundary.

## 0.2.2 - 2026-08-13

- Replaced the product password/session relay with Keyverse authorization-code
  OIDC using S256 PKCE, confidential-client exchange, verified discovery and
  introspection, exact issuer/audience/client/expiry enforcement, and opaque
  token-bounded local sessions. `org` and `workspace` now map to corp and PU
  only after token validation; only an explicitly enabled local development
  actor can bypass the external identity boundary.
- Added on-demand, document-authorized inline-image OCR/object inspection with
  strict raster signatures, base64 validation, and a 6 MiB decoded-size limit.
  A real direct-PostgreSQL image completed a verified live-model OCR call.
- Added `truststore` platform TLS verification with an optional
  `LLM_GATEWAY_CA_BUNDLE`; insecure certificate contexts are removed.
- Normalized inspection persistence: label names are catalogued once and
  image-specific descriptions live on the inspection-label relation. Added
  tenant-scoped OCR/object search and metadata-only outbox events.
- Added ADR-0002 and ADR-0003, and corrected the worker documentation: Keyman requires the
  direct gateway, while Compose is a no-identity live-model proxy for supported
  event-chat and image-inspection paths.
- Added a multi-stage product container and opt-in Compose profile. The container
  serves the compiled React app, connects directly to PostgreSQL, and reaches
  Valkey and the worker through service DNS.

## 0.2.1 - 2026-08-13

- Product API loads the persisted PostgreSQL snapshot before rebuilding so a
  restart does not wipe LLM Keyman rows. Structure-only CLI rebuilds keep
  existing LLM/user Keyman instead of truncating them away.
- React login reads the form fields instead of a shadowed `document`
  binding, and the Vite proxy targets the product API on port 18082.
- The document popup loads even when `/content` fails, and the content
  manifest no longer 500s the whole detail view.
- Workspace KPIs reuse persisted run counts when row nodes are not in
  memory. Keyman clicks synthesize a neighborhood when the stored KG has
  no person node. Event chat uses persisted document events and opens
  the cited source row.
- Affiliate clues are company/PU hierarchies persisted in
  `analysis_affiliate_edges`, not title-split fragments. Structure rebuilds
  persist the live-row knowledge graph without wiping LLM Keyman.

## 0.2.0 - 2026-08-13

- Replaced the static viewer path with a compiled React workspace served by the
  direct-PostgreSQL HTTP service.
- Added Keyverse session gating, document-scoped evidence/content routes,
  event-lineage chat, ticket/visibility/Keyman mutations, and paged document
  browsing.
- Added persisted people/organization/PU/event/document KG nodes and explicit
  cross-PU, cross-company, and same-PU cross-company relations.
- Added KG scope filtering, inline-image metadata handling, Compose worker
  contract, ADR, architecture, and traceability documentation.
- Added adaptive per-node KG depth, a real model-gateway Compose proxy with no
  sample identity/recorded answer, and a PostgreSQL outbox to Valkey Stream
  event queue.
