# Product & Technical Gap Baseline

> Audit scope: the current `fix/uiux-standard-guide-v3-postmerge` worktree,
> compared with `origin/main`, the UI/UX Standard Guide v3.0 supplied for this
> product, ADR 0118, the accepted TEPP PRD/contracts, and the
> contextual-orchestrator architecture. Real source identifiers are deliberately
> replaced with case labels; they must not enter repository artifacts.

## 1. Exact-head evidence

### 1.1 Current continuation head

The current buyer-surface/source-context continuation is PR #384 at exact head
`f688f0e4e2946ea86aed65311558923211a23aa7`, observed at
`2026-08-21T15:13:45Z` (`2026-08-22` KST). Its base is
`d5495162fbf4950ca180d43d5c13a636f1889e0c` (`docs/customer-master-scope-adr`).
GitHub reports `MERGEABLE` with `mergeable_state=unstable`; the two required
hosted workflows are queued for this exact head. No merge or approval is
claimed from that state.

The historical evidence below remains valid only at the exact heads and dates
stated in each entry. It must not be used as proof that the current continuation
head has passed the same checks.

### 1.2 Historical audit anchor

Audit anchor: the exact source state carried by this commit at 2026-08-21;
record the final PR head with `git rev-parse HEAD` during acceptance.

Current source/test exact head observed before this documentation update:
`8bed77e7e7b91b633bb92d3a82d0187c387206af`, the squash merge of PR #364
(docs-only) on top of PR #350. The runtime source was last tested at
`0e63ba0a2e23949630f8997cbe001b6e13b2d274`; this ADR/docs update creates the
next exact head and therefore requires the protected checks to rerun.

- **Implemented in source:** PostgreSQL-backed API boundaries, Keyverse/OIDC
  identity boundary, workspace navigation, post popup, ABAC/RBAC surfaces, Korean
  summary, 5W1H, R&R/Keyman, customer hierarchy, tickets/calendar, chat,
  provenance/evidence, and reconstructed lineage API/DAG layout.
- **Implemented in source, runtime evidence still required:** TEPP import/API
  transport, contextual-orchestrator processing of the authorized corpus,
  SearXNG corroboration, Local Zotero ingestion, real PostgreSQL import, and
  complete accessibility/edge-case browser workflows. Synthetic routes and
  health checks are recorded separately and are not corpus proof.
- **Implemented in source:** an explicit body-column or hash-verified
  `multipart/related` MHTML artifact resolver now gives the private importer a
  fail-closed path for exports whose PostgreSQL rows contain artifact
  provenance but no body column. The operator artifact root and raw artifacts
  remain outside the repository.
- **Figma reference:** ADR 0118 records file `1Su3lDRmiZdcUs47t1QwIX`; the
  inspected Event Lineage frames are desktop `5:14` and mobile `5:15`.
- **Local quality evidence at the source/test head:** backend `uv run pytest -q`
  passed `786` tests with `16` skips; frontend Vitest passed `174` tests in `19`
  files, frontend lint/build passed, and Storybook build completed. These are
  local checks, not hosted protected-gate or independent-review evidence.
- **Current PR gate:** PR #350 merged at
  `0e63ba0a2e23949630f8997cbe001b6e13b2d274` after its source head
  `819ef876270212305c89743e5443b3ce0b871e66` was reviewed and squashed into
  `feat/lineage-dag-regression`; PR #364 then merged the evidence-only
  baseline at `8bed77e7e7b91b633bb92d3a82d0187c387206af`. This ADR/docs
  follow-up requires its own protected checks and independent approval;
  neither is claimed yet. The prior PR #347 merged at
  `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`.
- **Historical parsing PR:** PR #367 subsequently merged at
  `7a0d025215fbd9f6510727c7139885b561296149` after exact head
  `5194d267b90430d7a27a9752a49d73617cb5756c`, based on
  `docs/customer-master-scope-adr` at `f66991699506ef14607de5946da1efcfd20ae6da`.
  It preserves numbered footnotes and empty-cell positions, avoids short-id
  collisions, and drops table rows made only of empty cells. The focused
  parser gate is `47 passed`; `compileall` and `git diff --check` passed.
  Hosted Checks remain queued and no approval or merge is claimed.

### 1.3 Current related PR queue

The following exact-head states were observed during this continuation and are
part of the acceptance queue, not completion evidence:

| Repository | PR | Exact head | State | Remaining gate |
| --- | ---: | --- | --- | --- |
| LineageWeave | #384 | `f688f0e4e2946ea86aed65311558923211a23aa7` | open, mergeable, unstable | hosted checks and review |
| LineageWeave | #383 | `720004942dd155a85020af32da402d320038f46a` | open, blocked | required checks and review |
| LineageWeave | #355 | `b606c2553f877fa85968d90dc46598ce16897fbf` | open, coverage pending | coverage gate and review |
| contextual-orchestrator | #765 | `d19e3492192e21e4a040fa3fc13a0793443731bf` | open, blocked | required checks and review |
| governance-risk-compliance | #50 | `ba78e4790f3e361826991455ce83634004f2875d` | open, mergeable, unstable | central OSV provenance gate |
| ContextualWisdomLab/.github | #1158 | `6e93fd0b65c159c7b168d83579e5b8282096480e` | open, behind | required checks and review |

GRC stack PRs #20 and #21 were merged in order before #50. These merge SHAs do
not make #50 or the other listed PRs merged; each remains subject to its own
exact-head protected gate.

## 2. UI/UX Standard Guide v3.0 comparison

### 2.1 Satisfied or substantially present

- Desktop shell has a sticky header, top-right user/logout controls, GNB,
  footer with brand/copyright, standard breakpoints, 1920px maximum layout,
  Noto Sans family, CI/BI palette tokens, table alignment tokens, focus styles,
  required-field marker, and 50% modal backdrop.
- GNB active state is exposed with `aria-current`; the lineage DAG has keyboard
  activation and branch/root/current visual states.
- PostgreSQL, orchestrator, TEPP, provenance, and synthetic-fixture boundaries
  are documented in `ARCHITECTURE.md` and the applicable ADRs.

### 2.2 Gaps and status

- **Mobile drawer — fixed in this worktree:** CSS referenced a drawer trigger but
  the authenticated shell rendered no trigger or drawer. The shell now renders
  an accessible hamburger button, close action, overlay, and reusable WorkspaceNav.
- **Event Lineage Figma parity — fixed in this worktree:** the DAG now includes
  lineage-evidence context, legend, horizontal overflow on phones, inference
  boundary, direction markers, and an evidence trail table/cards treatment.
- **Approved CI/BI asset — open:** the header/footer currently render the
  tenant brand name as text. Do not invent or alter a corporate logo; add the
  approved asset only after the tenant CI/BI source and usage permission are
  available.
- **Header utilities/search — partial:** the authenticated header now exposes a
  global Search action that focuses the existing board search, and its pending
  focus request is cleared when navigation leaves the board. A desktop site-map
  utility now reuses `WorkspaceNav`, closes on Escape or destination selection,
  and is omitted on phones where the drawer owns navigation; approved CI/BI
  assets and a no-JavaScript fallback remain open.
- **Header top-menu language placement — fixed in this worktree:** UI/UX
  Standard Guide v3.0 §2.2.2 assigns 언어설정 (language setting) to the header
  top menu alongside user info, login/logout, search, and utility items.
  `LanguageSwitcher` now renders inside `.app-header-top-menu` (`App.tsx`)
  instead of the GNB row; the now-unused `WorkspaceNav` `tools` prop and
  `.workspace-gnb-tools` CSS were removed.
- **Authorized corp/PU scope — fixed in this worktree:** `/api/me` remains the
  only source for GNB scope values, and that response is built from the
  authenticated account's DB-backed `account_affiliation` rows. The header now
  presents a compact code summary with a keyboard-operable disclosure for the
  complete corporation/business-unit list, keeps corporation-only affiliations,
  and omits the scope when no affiliation is authorized. Desktop and 390px
  mobile Playwright checks cover the disclosure, no-unassigned-code behavior,
  and no horizontal overflow; the external Keyverse/OIDC runtime gate remains
  open below.
- **Locale document metadata — substantially present:** `i18n.ts` synchronizes
  `document.documentElement.lang` after locale selection and `i18n.test.ts`
  covers the supported locales. `frontend/index.html` remains an English
  pre-JavaScript fallback, so a no-JavaScript locale check is still open.
- **Event Lineage locale parity — fixed in this worktree:** the PR review
  exposed ten Event Lineage, graph-evidence, navigation, and authorization
  labels translated only for Korean while Chinese, Japanese, and Vietnamese
  fell back to English. The three locale maps now contain those translations,
  and the i18n test rejects raw-key fallback for every supported non-English
  locale. This does not close the separate no-JavaScript fallback gap.
- **Phone content affordance — fixed and covered:** the authenticated 390px
  browser sweep had a scrollable page and rendered the post list below the
  sticky shell. A duplicate phone `.app-header` rule that overrode the required
  vertical padding was removed; `mobileHeaderCss.test.ts` now enforces one
  phone rule with `0.6rem 1rem` padding. The current exact-head frontend image
  was rebuilt and the authenticated 390px sweep reconfirmed the header and
  below-the-fold content affordance.
- **Large-body search migration — fixed in this worktree:** current PostgreSQL
  migration replay initially exhausted the 58.8 GB container overlay while
  building a raw HTML/Base64 body FTS index. The normalized search function and
  intermediate FTS index now bound indexed rendered text to 16,384 characters;
  the raw indexes are dropped by migration 0036. After reclaiming only Docker
  build cache (never the PostgreSQL volume), the live migration completed with
  exit 0 and the bounded function/index aggregate was verified.
- **Tenant settings replay — fixed in this worktree:** the idempotent migration
  runner stopped at `0102`, so existing volumes returned a misleading CORS
  symptom for `/api/settings` while the table was absent. The allowlist now
  replays `0103_tenant_settings.sql`; the existing PostgreSQL volume applied it
  with exit 0 and contains one tenant-settings row. Migration `0104` now
  preserves the canonical `tenant_settings_id` column during replay.
- **Database identifier contract — fixed in this worktree:** the live public
  schema audit found one single-token table and nine single-token persistent
  columns, including the legacy bookmark, status, content, report, and tenant
  settings fields. ADR 0120 and migration `0104_two_word_database_identifiers`
  rename them to two-word snake_case names, retain stable API JSON names, and
  recreate the current-status view. The replayed live schema now reports zero
  single-token table/view/column violations and zero invalid indexes. 3NF,
  hot-partition, lock, and read/write contention evidence remains open.
- **Metric superscript/subscript display — partially fixed in this worktree:**
  bounded metric markup such as `m<sup>3</sup>` and `m<sub>3</sub>` is now
  normalized consistently in the backend semantic parser and React renderer,
  with focused tests. Arbitrary mathematical formula semantics remain open.

### 2.3 Authenticated runtime evidence

The local Compose stack accepted the synthetic Keycloak OIDC account and the
real React client rendered the protected board. Aggregate evidence only:

- `/api/me` returned two authorized corporate entities and eight account
  affiliations, with corporate and process-unit code/name fields.
- At a 390×958 viewport, logout, scope display, language control, 50 visible
  posts, drawer open/close, and global-search-to-input focus all worked.
- On the rebuilt authenticated frontend, switching the header language to
  Chinese set `html[lang]` to `zh`, localized the drawer, authorized-scope,
  logout, summary, and Event Lineage labels, opened a post popup, and produced
  zero popup errors.
- The authorized PostgreSQL export relation contained 43,814 rows with
  complete title, source-key, and artifact-path metadata, but its schema had
  no body/content/HTML column. The importer now accepts an explicit
  body-column mapping or a path-column plus SHA-256-column mapping beneath an
  operator-supplied artifact root; this is source and synthetic-fixture
  evidence only because the authorized raw artifacts were not present in the
  repository runtime. No real-corpus import or multimodal backfill is claimed
  from this relation.
- After replaying the tenant-settings migration on the existing PostgreSQL
  volume, authenticated `/api/settings` returned HTTP 200 and the fresh React
  browser session recorded zero console errors and zero warnings. At 390×958,
  the document had no horizontal overflow (`scrollWidth=390`) and the protected
  board rendered the authenticated content surface.
- All 11 supplied post cases opened a popup with a loaded title and zero popup
  error elements. The footnote case rendered one footnote, the table case one
  semantic table, the known lineage case one DAG, and the image-table case
  rendered five images but zero persisted image-region panels.
- The full lineage endpoint returned 500 bounded nodes and one edge; the focused
  isolated case correctly returned an empty graph. PostgreSQL aggregates were
  43,839 source posts, 54 knowledge-graph edges, 65 edge-evidence rows, 1,308
  persisted post-lineage edges, and 1,929 posts participating in those edges.
  This is evidence of a sparse current relationship projection, not evidence
  that the Event Lineage product goal is complete.
- After the health-probe correction, the rebuilt backend returned unauthenticated
  `/healthz` HTTP 200. The focused representative case in the later mixed
  workspace image returned no DAG, so the earlier single-case DAG observation
  must not be generalized to corpus coverage.

## 3. Requirement traceability

Status is intentionally evidence-specific: `source` means the implementation
boundary exists; `unit` means synthetic automated coverage exists;
`local-integration` means the local PostgreSQL/Keycloak/Valkey stack exercised
the path; `live-external` means the requested external service or authorized
corpus was exercised; `open` means the requirement is not yet proven. A source
adapter, fixture, or HTTP-shaped test double never upgrades a row to
`live-external`.

| Requirement | Evidence at this audit | Status |
| --- | --- | --- |
| 1024/1280/1920 layout and three responsive tiers | ADR 0118, `App.css`, responsive popup width/secondary evidence grid, frontend build/tests | source + unit |
| Sticky header, footer, GNB, active state, phone drawer | `App.tsx`, `WorkspaceNav.tsx`, `App.test.tsx` | source + unit |
| Approved CI/BI logo asset | Tenant text is present; approved asset and permission are absent | open |
| User/logout/language/global search header actions | `App.tsx`, `i18n.ts`, handled/pending search-focus tests | source + unit |
| Site map / utility menu | `SiteMapUtility`, accessible toggle/region, Escape and destination-close behavior, responsive CSS contract, locale coverage | source + unit; authenticated browser evidence open |
| Noto Sans, palette, table/form/button conventions, modal 50% mask | ADR 0118, token CSS, component tests | source + unit |
| Keyverse/OIDC login with real account | `auth.py`, OIDC discovery/JWKS boundary, local redirect check | source + local-integration; Keyverse open |
| Authenticated corp/PU attributes | `/api/me` returns DB-backed codes; backend integration test covers `TEST-CORP`/`TEST-PU`, the GNB disclosure is covered by `App.test.tsx`, and desktop/390px Playwright QA verifies the rendered scope | source + unit + local-integration + browser-mocked |
| RBAC/ABAC, public/private visibility, tenant isolation | `_can_see_post` plus W author/admin raw-source exception, analysis eligibility excluding W, API authorization tests, aggregate-only runtime checks | source + local-integration |
| React product surface and PostgreSQL boundary | React routes/components, asyncpg API, Compose stack | source + local-integration |
| Authorized PostgreSQL export import mapping | `scripts/import_postgresql_posts.py`, ADR 0121, hash-verified RFC 2557 MHTML resolver, and synthetic preflight/import tests; authorized relation has artifact-path metadata but no body/content/HTML field | source + unit + local-integration partial; operator artifact files and authorized live import open |
| Bounded large-body search migration | `0035_body_search_prefix.sql`, `0036_normalized_body_search.sql`; live replay completed after bounded rendered-text indexing | source + local-integration |
| Public Compose liveness and tenant settings boundary | health-probe regression test, `0103_tenant_settings.sql`, replayed existing volume, one tenant-settings row, canonical `tenant_settings_id` after `0104`, rebuilt backend `/healthz` and authenticated `/api/settings` HTTP 200 | source + unit + local-integration |
| Two-word snake_case database identifiers | ADR 0120, idempotent migration `0104`, live public-schema audit, zero invalid indexes | source + unit + local-integration |
| Post list/detail popup, Korean summary, 5W1H, R&R, tickets/calendar | API routes, popup panels, backend/frontend tests; W is raw-source-only for author/admin and is excluded from summary and derived analysis targets | source + unit |
| Keyman on both sides, titles, affiliations, related KG nodes | Keyman/affiliate-tree/related-node routes and popup | source + unit; live extraction open |
| Ontology, semantic layer, provenance, W3C PROV-O projection | normalized schema, SKOS operational vocabulary concepts, `ontology_annotations` label fallback, ADR 0124, provenance modules, ADRs, evidence UI | source + unit; corpus verification open |
| Branching Event Lineage DAG with evidence trail | `LineageDag.tsx`, Storybook story, Figma frames, accessible node-kind names for screen readers/tooltips, frontend tests; runtime cases include both a rendered DAG and honest empty states, while current corpus coverage remains sparse | source + unit + local-integration partial |
| Customer master and hierarchy tree | `/api/customer-master`, affiliate tree, catalog migrations | source + unit; scoped to `account_affiliation` only, no own-company/customer distinction — see §5 |
| VOC/VOM/VOP/VOCC/VOCO/VOS role classification | common lookup values and relationship APIs | source + unit; live classification open |
| Evidence-grounded chat and source navigation | `/chat`, `/ask`, citation/evidence UI | source + unit; synthetic orchestrator judge route verified, corpus chat/runtime evidence open |
| OpenTelemetry across LineageWeave, contextual-orchestrator, Valkey, and GRC | LineageWeave PR #383 adds API/Valkey/session spans; contextual-orchestrator PR #765 carries session/provider telemetry; governance-risk-compliance PR #50 adds request telemetry, W3C trace context, OTLP export, and ADR 0009 | source + PR; protected merge and end-to-end collector evidence open |
| PU/team/project weekly/monthly reports | report API/UI and grouping controls | source + unit; TEPP-backed live report open |
| TEPP calibrated measurement, dichotomous items, multilevel/MMM/time model | published import/REST boundary and TEPP ADR/PRD references | boundary-only; live-external open |
| contextual-orchestrator routing, VISION, embedding, schema repair | clients and provenance/session boundary; synthetic authenticated route returned a judge score of `0.98`, OCR succeeded, and region location returned five regions | source + local-integration partial; corpus backfill, capability/readiness evidence, and schema-repair workflow open |
| HTML semantic units, tables, indentation, footnotes, formulas | parser modules and synthetic tests; 11-case authenticated popup sweep had no popup errors and rendered the supplied footnote/table cases; bounded metric superscript/subscript normalization has backend/frontend focused coverage | source + unit + local-integration partial; arbitrary formula/semantic correctness open |
| Base64/file image regions and multimodal evidence | image-region schema and VISION client boundary; live aggregate has 12,823 images, 22 described images/regions, and 422 failed images; current synthetic VISION route returned five regions | source + local-integration partial; supplied image-table case re-backfill and complete corpus coverage open |
| Abbreviation/multilingual alias/entity disambiguation | catalog hints and resolver boundary | source; live corroboration open |
| SearXNG/internal relation fact check | verification endpoint and unavailable handling; local SearXNG health and JSON query both returned HTTP 200, while some upstream engines reported rate-limit/CAPTCHA results | source + local-integration partial; corroboration policy and reliable external coverage open |
| Valkey event queue and cloud-native Compose stack | queue modules, Compose services, health checks | source + local-integration; delivery stress open |
| 3NF, hot partitions, locks, read/write contention | canonical identifier migration plus existing migrations | source; operational evidence open |
| Rust/GPU/CPU psychometric computation | delegated to TEPP, not reimplemented here | boundary accepted; live TEPP evidence open |
| APA 7 doctoring and Zotero OA records | baseline bibliography, local Zotero API reachable, known metadata found | source + local-integration; OA attachment audit open |
| Browser E2E from login through evidence | authenticated local OIDC login, protected list, drawer/search, popup sweep, and aggregate evidence checks at 390x958; post-migration fresh session had `htmlLang=zh`, localized protected shell, zero console errors/warnings, no horizontal overflow, popup, summary, and Event Lineage | source + local-integration; external provider/runtime evidence remains open |
| Storybook scenes/edge events and design-token coverage | `LineageDag.stories.tsx`, inventory, Storybook build | source + unit |
| External email/project lineage package boundary | PR #343 merged at `125a8069a1554874d8067a15047e19d780ea6b7b` with strict v1.0.0 bounded request/result types, available-time cutoff handling, observed/inferred/proposed truth states, pair-budget enforcement, and no source/provider access | source + focused unit; immutable release open |
| Naruon calendar projection boundary | PR #337 is closed as superseded; PR #355 carries the strict read projection contract without making LineageWeave a CalDAV provider | source + focused unit; Naruon endpoint, runtime wiring, and provider conformance remain open |
| Hourly PR review/repair/merge loop | Central `ContextualWisdomLab/.github` scheduler owns `*/15 * * * *` sweep and `0 * * * *` heartbeat; no duplicate repo-local scheduler is required | boundary accepted; current-head runtime open |
| 100% coverage/docstrings/edge-case/release gates | current checks and coverage evidence are not complete on PR #350 | open |

## 4. Supplied parsing and semantic cases

The following user-reported cases remain tracked without storing real post IDs:

- `case-footnote-01`: footnote/list `li`/`ol` boundary is misclassified.
- `case-table-01`: HTML table parsing fails.
- `case-indent-01` and `case-indent-02`: semantic indentation is wrong.
- `case-multi-project-01`: two projects must produce separate event streams;
  internal facilities must not be guessed as Partner/Supplier.
- `case-image-table-01`: image tables need region-aware OCR/description and
  rendered Markdown/table support.
- `case-summary-affiliation-01`: a role such as PM needs person, title, and
  organization evidence rather than an unqualified collective label.
- `case-r-and-r-01`: requester, assignee, action, and cost/payment owner must
  remain explicit in R&R evidence.
- `case-math-01`: bounded metric units such as m³ now have
  superscript/subscript-preserving source/semantic normalization in backend and
  frontend tests; arbitrary formula parsing, ontology-safe formula semantics,
  and the authorized runtime case remain open.

These are not “resolved” merely because a prompt or heuristic was changed.
Each requires synthetic unit coverage plus an authorized runtime reproduction
or an explicit unavailable result.

## 5. Product and technical gaps

- **R&R role/relationship conflation and catalog-linking boundary — evidence-backed (2026-08-21):**
  Live UI/UX feedback on a real R&R extraction surfaced three related gaps,
  root-caused against source rather than assumed:
  1. **"카탈로그 미연결" is the designed fail-closed behavior, not a bug, but
     is undiagnosable from the UI.** `_resolve_existing_cataloged_person_id`
     (`backend/app/post_summary_ingestion.py`) is documented as never
     inserting a `cataloged_person` row (ADR 0009 — "a missing catalog row
     stays unbound rather than inventing a person"). Organization actors do
     go through `get_or_create_corporate_entity` (ADR 0010), but that
     function's `hierarchy_inference_client`/`verification_client` default to
     Null clients whenever no live orchestrator/SearXNG corroboration is
     wired — in that state it can only match an *already-cataloged* entity,
     never create one, so an organization actor stays unlinked too. The
     resulting "카탈로그 미연결" label is a correct, honest reflection of
     missing live infrastructure, not a code defect — but it gives the
     reader no way to tell "not yet processed" from "no live orchestrator in
     this environment" from "verification declined to corroborate."
  2. **Job title and relationship type are conflated into one free-text
     field.** `RoleResponsibility.responsibility` (`lineageweave/post_summary.py`)
     is documented as "what they are responsible for or did" — a single
     string. An observed extraction produced `"상담고객 연구원"` in that one
     field, gluing a *relationship-type* signal ("상담 고객", i.e. a
     consulting/customer relationship — the same concept already modeled
     elsewhere as `post_counterparty_entity.relationship_type_code`, e.g.
     `rel_voc`) together with a *job title* ("연구원") that has no home of
     its own on `RoleResponsibility` the way `last_known_job_title` does on
     `Keyman`. Fixing this needs a new field plus an
     `POST_SUMMARY_CONTRACT_VERSION` bump (currently `12`) and an extraction-
     prompt change — not a display-layer patch, and not something to
     implement without review given every future extraction depends on the
     contract version.
  3. **Planned-facility events don't become project/entity evidence, and no
     operator inference exists.** A key event whose text names a specific
     planned facility (e.g. "X 충전소 구축 계획") produces `key_events`/
     `key_event_details` prose only — it is never checked against
     `post_project_mention`/`ProjectEvidence`, so the facility itself is
     not recognized as an entity, and no relationship is inferred between it
     and the organization the post's own R&R evidence says would operate it.
     This is a deliberate ontology-design question, not a quick fix:
     inferring an "operates" relationship from event-adjacent context risks
     inventing a fact the source text does not state, which is exactly what
     ADR 0010's fail-closed design exists to prevent. Needs its own ADR
     (a new PROV-O/SKOS relationship class and a conservative admission
     rule) before any inference code is written.
  Two related, safely-scoped UI fixes shipped alongside this finding: R&R
  rows now nest under their affiliated organization's row instead of each
  repeating "· 소속: X" as flat text (`buildRoleTree`, `frontend/src/App.tsx`),
  and `key_events` sharing the same `project_name` now nest under one
  heading instead of repeating the project name as a flat prefix
  (`groupKeyEventsByProject`). Neither fix touches extraction, the summary
  contract, or catalog creation.
- **Customer master "customer tree" — scope gap, evidence-backed (2026-08-21):**
  `/api/customer-master`'s `corporate_entities` list (`backend/app/main.py`
  `read_customer_master`, `entity_rows` query) is scoped to
  `account.corporate_entity_ids`, which comes only from `account_affiliation`
  rows (`backend/app/auth.py` `get_current_account`) — the account's own
  employer plus any explicitly granted entities. A live query against the
  seeded stack confirms the Demo Corp account's `account_affiliation` grants
  exactly one entity (Demo Corp itself) with zero `source_customer_code`/
  `source_customer_name` hints on its posts, so `buildCustomerEntityTree`
  (`frontend/src/App.tsx`) renders a single un-nested node, not the "Harbor
  Group -> Harbor Devices Korea" customer-affiliate tree ADR 0004 and ADR 0010
  describe as a standing requirement. Counterparty `corporate_entity` rows
  that ADR 0010's `get_or_create_corporate_entity` auto-creates are never
  linked via `account_affiliation`, so they cannot reach this endpoint no
  matter how well-populated the corpus becomes — the tree needs to traverse
  observed post/VOC/affiliate-tree evidence, not `account_affiliation` alone.
  Separately, there is no schema signal distinguishing "own company" from
  "granted customer entity" inside `account_affiliation`: both use the same
  `process_unit_id`-bearing row shape (the Demo Analyst account's grants into
  "Source company H504"/"H904" carry `process_unit_id` exactly like Demo
  Corp's own grant does), so a same-screen filter separating 자사(own
  company) attributes from customer attributes has no field to filter on
  yet. Needs an ADR before implementation: either an explicit
  `account_affiliation`/`corporate_entity` scope flag, or a customer-tree
  query redesign: guessing at either without a reviewed decision risks an
  ABAC-adjacent regression.
- **Entity and abbreviation resolution — open:** canonical names, aliases,
  multilingual labels, team-vs-organization typing, title-aware person
  disambiguation, and SearXNG/internal corroboration need end-to-end evidence.
- **Image/HTML semantic units — partially implemented:** source DOM, layout
  metadata, region evidence, and provenance must remain separate from embedding
  text; transparent/unsupported image conversion and multimodal processing need
  live verification.
- **Metric/formula semantics — partially fixed:** bounded metric markup is now
  preserved across the backend parser and React renderer. Full formula AST,
  units, exponents, and ontology mapping remain an evidence-backed follow-up,
  not a claim of mathematical completeness.
- **Authorized source mapping — partially implemented:** the inspected export
  relation exposes metadata and artifact paths but no body/content/HTML field.
  ADR 0121 and the importer now connect a path plus SHA-256 mapping to an
  operator-local MHTML root, while rejecting traversal, missing files, and
  digest mismatches before writes. The remaining acceptance work is to mount
  the authorized raw artifacts and run the real import/backfill; do not map an
  unrelated metadata column as body.
- **TEPP measurement — boundary accepted, runtime open:** LineageWeave must
  call TEPP through its published import/REST contract and must not implement a
  local theta, psychometric calibration, CAT, or judge score. TEPP owns the
  Rust numerical/psychometric layer and its multilevel/multiple-membership/time
  model.
- **Orchestration — boundary accepted, runtime open:** all LLM/VISION/embedding
  work must cross contextual-orchestrator with provenance, session, cost, schema
  validation, synthesis/repair, and capability discovery. No provider key or
  model selector belongs here.
- **Authorization — runtime open:** verify actual Keyverse/OIDC login, corp/PU
  attributes, post visibility, ABAC/RBAC denials, and no cross-tenant evidence
  leakage using aggregate, non-identifying results.
- **Database/operations — audit open:** verify 3NF constraints, hot-partition
  behavior, lock boundaries, Valkey event delivery, multithreaded server
  behavior, retention grants, and read/write contention on the local Compose
  stack.
- **Lineage coverage — open:** the persisted graph has 1,308 post-lineage edges
  across 1,929 participating posts, while the bounded current view exposed one
  edge and some focused posts had no component. Add a rebuild/coverage gate that
  distinguishes genuinely isolated posts from missing extraction or grouping
  evidence before presenting a reader-facing branching DAG as complete.
- **Cross-repository email/project lineage — provider boundary implemented,
  consumer open:** PR #343 merged at
  `125a8069a1554874d8067a15047e19d780ea6b7b`, but the contract remains
  unreleased. Naruon issue #1437 still needs a disabled-by-
  default admission policy, durable idempotent analysis job, immutable artifact
  pin, result projection, accept/correct/reject audit, and integration into the
  existing email/thread/project surfaces. No draft branch, direct SQL, shared ORM,
  credential forwarding, or automatic promotion of inferred facts is allowed.
- **Calendar interoperability — contract-only:** PR #337 defines the LineageWeave
  consumer contract. Naruon must still publish the provider-side read endpoint,
  service audience, provider conformance fixtures, sync/revision semantics, and
  failure/reconciliation behavior before fail-closed runtime wiring is enabled.
- **Literature/Zotero — open:** record APA 7 references and verify Local Zotero
  API availability before claiming synchronization. The repository must retain
  only metadata/citations appropriate for public artifacts.
- **Release/quality gates — open:** current PR checks and required reviews must
  complete on the exact current head; frontend, backend, browser, accessibility,
  Storybook, security, and coverage evidence must be collected before release.

## 6. Next acceptance loop

1. Re-fetch the exact PR head and required reviews/checks for the workspace UI stack,
   PR #343, and the superseding calendar contract PR #355.
2. Run frontend lint, tests, build, Storybook, backend tests, and authenticated
   browser checks when the local stack is available.
3. Reproduce each case label using synthetic fixtures or authorized runtime
   aggregates, preserving `unavailable` as an explicit result.
4. Complete exact-head review and immutable release of the LineageWeave provider
   contract before creating the Naruon consumer implementation; do not import a
   draft branch or share application database state.
5. Fix only evidence-backed failures, then repeat the exact-head protected merge
   gate. Do not self-approve, bypass protection, or claim a PR is merged without
   a merge SHA.

## 7. References (APA 7th)

ContextualWisdomLab. (2026). *TEPP* [Computer software]. GitHub.
https://github.com/ContextualWisdomLab/TEPP

ContextualWisdomLab. (2026). *contextual-orchestrator architecture notes*
[Computer software]. GitHub.
https://github.com/ContextualWisdomLab/contextual-orchestrator/blob/main/docs/architecture.md

Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2025).
*Learning to orchestrate agents in natural language with the Conductor*.
arXiv. https://doi.org/10.48550/arXiv.2512.04388

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H.,
Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., & Kuroki, S.
(2026). *Sakana Fugu technical report*. arXiv.
https://arxiv.org/abs/2606.21228

Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2025).
*TRINITY: An evolved LLM coordinator*. arXiv.
https://doi.org/10.48550/arXiv.2512.04695

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
 (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
