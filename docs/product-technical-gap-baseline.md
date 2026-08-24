# Product & Technical Gap Baseline

> Audit scope: the current LineageWeave buyer-surface/source-context worktree
> and open PR #384, compared with its exact base and the UI/UX Standard Guide v3.0 supplied for this
> product, ADR 0118, the accepted TEPP PRD/contracts, and the
> contextual-orchestrator architecture. Real source identifiers are deliberately
> replaced with case labels; they must not enter repository artifacts.

## 1. Exact-head evidence

### 1.1 Current continuation head

The current buyer-surface/source-context implementation head for PR #384 is
`d2d4b9209caed81cf4506908207e7b03142a1af6` (the exact head pushed after the
remote fixture cleanup and vendor-skill revert), observed at `2026-08-21T15:35:55Z`
(`2026-08-22` KST). Its base is
`83ace331edc982208c290763cb0d389c1884e21b` (`docs/customer-master-scope-adr`).
The repaired implementation includes the customer-master scope-facet base
and preserves the source-detail-state fixes. Local acceptance evidence is
backend `127 passed, 6 skipped`, frontend `199 passed`, lint, TypeScript, and
production build success. The baseline update itself follows this code
commit; hosted checks, formal review, and merge remain unclaimed until the
remote PR is queried at its newly pushed exact head.

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
  passed `788` tests with `17` skips; frontend Vitest passed `177` tests in `19`
  files, frontend lint/build passed, and Storybook build completed. These are
  local checks, not hosted protected-gate or independent-review evidence.
- **Current PR gate:** PR #350 merged at
  `0e63ba0a2e23949630f8997cbe001b6e13b2d274` after its source head
  `819ef876270212305c89743e5443b3ce0b871e66` was reviewed and squashed into
  `feat/lineage-dag-regression`; PR #364 then merged the evidence-only
  baseline at `8bed77e7e7b91b633bb92d3a82d0187c387206af`. This ADR/docs
  follow-up requires its own protected checks and independent approval;
  neither is claimed yet. PR #366 remains open at code head
  `a5aa0daa`; its hosted Tests run is queued,
  Devin Review is pending, and no independent approval or merge is claimed.
  The prior PR #347 merged at
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
| LineageWeave | #384 | `d2d4b9209caed81cf4506908207e7b03142a1af6` | open, mergeable, unstable | hosted checks and review |
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
- **Post detail modal keyboard access — fixed in this worktree:** the existing
  50% backdrop now exposes a named modal dialog with `aria-modal`, moves focus
  into the panel, closes on Escape, contains Tab focus, and restores focus to
  the opener. Native interactive controls also share the token-based
  `:focus-visible` ring. The behavior is covered by the authenticated React
  and CSS tests. `frontend/e2e/post-detail-modal.spec.ts` (real Chromium,
  real Keycloak login, dialog role/aria-modal/Tab-cycle/Escape/focus-restore
  all asserted against the live authenticated stack) passed cleanly on its
  own run 2026-08-23. Honest caveat: this shared dev machine was under
  sustained heavy concurrent load (uptime load averages 24-56 across many
  simultaneous sessions) while gathering this evidence, which caused
  network-step timeouts in *other* runs and in unrelated existing specs
  (`customer-master.spec.ts`, `knowledge-graph.spec.ts`) -- never a failed
  assertion inside this spec's own logic. A from-a-quiet-machine confirmation
  is still open; do not read the one clean run as proof of zero flakiness
  under contention. That browser run predates browser-assertion head `161f4eb80c75`,
  whose modal assertion requires the same opener element; an
  exact-head browser rerun remains open.
- **Approved CI/BI asset — open:** the header/footer currently render the
  tenant brand name as text. Do not invent or alter a corporate logo; add the
  approved asset only after the tenant CI/BI source and usage permission are
  available.
- **Header utilities/search — partial:** the authenticated header now exposes a
  global Search action that focuses the existing board search, and its pending
  focus request is cleared when navigation leaves the board. A desktop site-map
  utility now reuses `WorkspaceNav`, closes on Escape or destination selection,
  and is omitted on phones where the drawer owns navigation; approved CI/BI
  assets and a no-JavaScript fallback remain open. Current head `161f4eb80c75`
  also requires the site-map E2E to select Calendar from the default board and
  verify the URL, persistent navigation state, and destination heading; its
  browser rerun remains open.
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
| Site map / utility menu | `SiteMapUtility`, accessible toggle/region, Escape and destination-close behavior, responsive CSS contract, locale coverage | source + unit; `frontend/e2e/site-map-utility.spec.ts` (real Chromium/Keycloak) passed both cases cleanly on one run 2026-08-23, but not yet confirmed on a quiet machine -- this shared dev machine was under sustained heavy concurrent load (uptime load averages 24-56) during evidence-gathering, which caused unrelated network-step flakiness in other runs. Responsive CSS contract still open. |
| Noto Sans, palette, table/form/button conventions, modal 50% mask and keyboard semantics | ADR 0118, token CSS, popup dialog implementation, frontend tests | source + unit |
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
| Customer master and hierarchy tree | `/api/customer-master`, `scope_facets`, visible `post_organization_mention` enrichment (directly-observed entities need no affiliation row), affiliate tree, migration `0105`, scope filter, in-place related-post popup, hierarchy-aware `resolve_customer_hint`, `scripts/backfill_customer_hints.py`, Storybook coverage, ADR 0144 (reviewed decision, not yet implemented) | source + unit + local-integration partial; authorized own/granted/unclassified facets, directly-observed organizations (with zero affiliation row), admitted observed hierarchy facets, in-place post viewing, and hierarchy-aware customer-hint resolution are implemented, while authoritative scope backfill and surfacing an *ancestor* entity never itself directly named in any visible post (ADR 0144's scope) remain open |
| VOC/VOM/VOP/VOCC/VOCO/VOS role classification | common lookup values and relationship APIs | source + unit; live classification open |
| Evidence-grounded chat and source navigation | `/chat`, `/ask`, citation/evidence UI | source + unit; synthetic orchestrator judge route verified, corpus chat/runtime evidence open |
| OpenTelemetry across LineageWeave, contextual-orchestrator, Valkey, and GRC | LineageWeave PR #383 adds API/Valkey/session spans; contextual-orchestrator PR #765 carries session/provider telemetry; governance-risk-compliance PR #50 adds request telemetry, W3C trace context, OTLP export, and ADR 0009 | source + PR; protected merge and end-to-end collector evidence open |
| PU/team/project weekly/monthly reports | report API/UI and grouping controls | source + unit; TEPP-backed live report open |
| TEPP calibrated measurement, dichotomous items, multilevel/MMM/time model | published import/REST boundary and TEPP ADR/PRD references | boundary-only; live-external open |
| contextual-orchestrator routing, VISION, embedding, schema repair | clients and provenance/session boundary; synthetic authenticated route returned a judge score of `0.98`, OCR succeeded, and region location returned five regions | source + local-integration partial; corpus backfill, capability/readiness evidence, and schema-repair workflow open |
| HTML semantic units, tables, indentation, footnotes, formulas | parser modules and synthetic tests; adjacent open PR #367 at exact head `b628722cb000717b0198e4337d12306d4306922d` adds numbered-footnote, leading-empty-cell, and short-ID regressions; 11-case authenticated popup sweep had no popup errors and rendered the supplied footnote/table cases; bounded metric superscript/subscript normalization has backend/frontend focused coverage | source + unit + local-integration partial; PR #367 protected checks, arbitrary formula/semantic correctness, and corpus re-backfill remain open |
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
| 100% coverage/docstrings/edge-case/release gates | current local checks pass, but repository-wide coverage/docstring reports, hosted checks, independent review, and release evidence are not complete on PR #366 | open |

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
     **Update (2026-08-22):** the resolution path for an uncataloged person
     already exists and is a defined action, not a missing feature —
     `POST /api/posts/{id}/extract-keymen` ("Extract Keymen" in the Keymen
     panel's "Evidence operations"), gated `post_admin`, runs Keyman
     extraction and populates `cataloged_person` for names the extractor
     finds. It had simply never been run for the specific post that
     surfaced this finding. Live-verified the mechanism up through the
     LLM extraction step itself (see "Orchestrator client timeouts" below);
     confirming the catalog row and R&R link actually land is currently
     blocked by unrelated environment schema drift, not this design.
  2. **RESOLVED (2026-08-22, PR #407): job title and responsibility were
     conflated into one free-text field.** `RoleResponsibility.responsibility`
     (`lineageweave/post_summary.py`) was documented as "what they are
     responsible for or did" — a single string. A live extraction on a real
     post produced a bare job title (e.g. a person's title alone, such as
     "PM") standing in for their entire responsibility, with no separate
     field to distinguish the two. Fixed: `POST_SUMMARY_CONTRACT_VERSION`
     bumped `13` -> `14`; the ROLES extraction contract gained a 5th column
     (job title or NONE) with an explicit prompt rule against copying the
     title into the responsibility column; `RoleResponsibility.job_title`
     threads through the parser, `post_summary_role.job_title_text`
     (migration 0131), persistence, and the frontend (`RoleEvidence`'s new
     job-title badge). Also fixed in the same PR: `buildRoleTree` now groups
     2+ people/teams sharing an affiliated organization that has no ROLES
     row of its own under a synthetic organization-anchor node (fail-closed
     — the heading only repeats an already-stated name, it does not invent
     an org-level responsibility), so a host organization with only named
     attendees and no org-level action still renders as a real tree instead
     of flat, disconnected roots.
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
  **Update (2026-08-23, PRs #458/#461/#462):** three related, user-reported
  Customer Master defects fixed and merged into this branch, narrowing but
  not closing the standing gap above. (a) Clicking a customer's related
  post called `changeDestination("board")`, unmounting Customer Master
  entirely instead of showing the post in the existing right-docked
  `PostDetailPopup` -- fixed by giving `CustomerMasterPanel` its own
  `selectedPostId` state; the popup now opens in place. (b)
  `resolve_customer_hint` (`backend/app/customer_hint_ingestion.py`)
  previously created every newly resolved SAP customer code as a flat,
  unparented `corporate_entity` via a bare INSERT; it now routes through
  `get_or_create_corporate_entity` first (ADR 0010's hierarchy-inference
  pipeline, same one `keyman_ingestion.py` already used), respecting ADR
  0026's tie-must-stay-unbound rule, so a configured hierarchy channel
  gives the entity a real parent chain at resolution time. (c) Hint
  resolution was reachable only one `source_customer_code` at a time via
  the admin "Resolve" button in the UI; `scripts/backfill_customer_hints.py`
  now resolves a bounded batch through the same pipeline, closing the "no
  bulk/automatic backfill" gap for a SAP export whose only customer field
  (`zcrht811_export_rows.kunnr_field`) is an opaque number with no name at
  all. **Correction (2026-08-23):** the original bullet's framing above --
  "counterparty `corporate_entity` rows... are never linked via
  `account_affiliation`, so they cannot reach this endpoint no matter how
  well-populated the corpus becomes" -- is no longer accurate and should not
  be read as still-current: ADR 0125 (merged after the original 2026-08-21
  finding, before this checkpoint even started) already added an `observed`
  path to `entity_rows` (`backend/app/main.py`, joining
  `post_organization_mention`) that surfaces an ADR-0010-created entity with
  zero affiliation row, the moment it is directly named in any post the
  account is authorized to read. Verified by reading the current query
  directly, not assumed. **The real remaining gap is narrower:** `entity_rows`
  never adds a row for an ancestor that is itself *not* directly named in any
  visible post -- only inferred as a parent by ADR 0010's hierarchy pipeline.
  `_observed_hierarchy_ids` (`backend/app/main.py`) only *facet-marks* an
  ancestor already present in the result set; it cannot add one that
  is missing. So a real, verified "그룹 -> 본사 -> 공장" chain still renders
  with a missing top link whenever that top entity was inferred but never
  itself named in text. (b)/(c) above only improve the *creation* path, not
  this visibility gap. **ADR 0144** (`docs/adr/0144-customer-master-observed-entity-link.md`)
  now records a reviewed decision for closing it: a write-time normalized
  `account_observed_entity` evidence table keyed by account, observed entity,
  granting entity, and source post, not a
  read-time catalog traversal -- the traversal alternative was evaluated and
  rejected after an adversarial security review found a concrete cross-account
  leak (`corporate_entity` is one catalog shared across every account; a
  reused/fuzzy-matched ancestor row's data can trace entirely to a different
  account's private post evidence, and a public-verification-only gate
  cannot tell the difference). Implementation itself is not started -- ADR
  0144 is Proposed status, this checkpoint's deliverable was the reviewed
  decision, not the code. Storybook coverage for
  `CustomerEntityTreeRow`/`CustomerRelatedPostCard` (default/loading/empty/
  interactive states, reviewed against this repo's `ui-ux-pro-max` +
  `Anti-Slop-UI` skills) and two accessibility fixes (WCAG 2.5.5 touch
  target size on `.customer-entity-button`/`.related-post-card`; a
  per-hint `aria-label` on the "Resolve" button so screen-reader users can
  distinguish it from others in the same list) shipped in the same PR
  series. A Playwright e2e spec (`frontend/e2e/customer-master.spec.ts`)
  covers the (a) fix end-to-end -- same "runs only against a live
  authenticated stack, not CI" convention as the existing
  `knowledge-graph.spec.ts` -- but was not executed in this environment (no
  local stack was up at the time; the operator should run it against
  `make up && make seed` or a real import to confirm).
- **Event Lineage thread grouping — systemic mismapping, evidence-backed
  (2026-08-22):** `reconstruct_group_key` (`backend/app/lineage_ingestion.py`)
  uses `source_post.thread_group_key` first when non-empty, falling back to
  `process_unit_id`/`corporate_entity_id`. A live query found 43,814 of
  43,839 `source_post` rows (99.94%) have `thread_group_key` equal to that
  same row's own `source_record_key` — not a genuine thread/story
  identifier — so `reconstruct()`'s `_group_by` treats nearly every real
  imported post as its own singleton group and never even considers it as a
  lineage candidate against anything else, regardless of scoring. This
  explains reports of "day 3 has no visible day 1/day 2" for records that
  share an obvious project code: they were never compared, not scored low.
  Traced to `scripts/import_postgresql_posts.py`'s `mapping.thread_group`
  column resolution defaulting to a record-unique source column for this
  import; `source_order_pool_code` is reliably captured on the same rows
  and is the best available real thread signal for records that carry a
  project/order-pool code, but not every row has one, so the correct
  fallback chain needs design (this is not solvable by a blind
  find-and-replace across the dataset). A minimal, targeted fix shipped for
  this baseline's two named posts only (`thread_group_key` corrected to the
  shared project code for one 3-post family, verified via a rebuilt
  `post_lineage_edge` chain with fused scores above the 0.3 floor); the
  dataset-wide backfill and import-script fix remain open and need their
  own reviewed checkpoint before running against the full corpus.
  **Update (2026-08-24, PR #499 + executed operator run):** substantially
  closed. The reviewed checkpoint this bullet asked for landed as ADR
  0145's grouping-evidence restoration plus psychometric weight
  estimation, and the operator sequence has now actually run against the
  dev corpus with an explicit user go: (1)
  `scripts/backfill_thread_group_keys.py` cleared 43,811
  placeholder-signature rows (thread key = own record GUID) to migration
  0002's designed empty-string no-signal value and routed
  `source_project_code` into `secondary_grouping_key` -- the
  secondary-key channel's own documented signal -- as fused *evidence*,
  never a hard partition; a fail-closed guard refuses the rewrite if any
  `analysis_scope_thread_group` run's live scope match would be orphaned
  (none existed). (2) `scripts/estimate_channel_weights.py` fitted
  fast-mlsirm's multilevel 2PL over 244,921 real candidate pairs and
  persisted grounded fusion weights (temporal 0.868 / secondary_key
  0.121 / text 0.011 -- the hand-picked 0.30 text weight was ~26x off
  what the data supports) with provenance into `lineage_channel_weight`
  (migration 0135). (3) The weighted rebuild took `post_lineage_edge`
  from 943 to 41,257 edges; 41,698/43,839 posts (95.1%) now participate
  in the lineage graph, min fused score exactly at the 0.3 floor.
  The import-script fix also landed: `_validate_thread_group_mapping`
  preflight rejects a mapped thread-group column that is >=95% distinct
  (per-row identity, not a thread key) unless
  `--allow-unique-thread-group` is passed explicitly. **Update
  (2026-08-24, fail-closed amendment):** per the operator directive that
  weights are treated only via TEPP/fast-mlsirm, the hand-picked
  constant fallback was removed from every product reconstruction path:
  `rebuild_lineage`, `POST /api/lineage/rebuild` (503 with the
  estimate-first next action), and the analysis-run start delivery all
  fail closed until a persisted set exactly matching the active
  channels exists (migration 0136 keys sets by `channel_set_code`, so
  the 3-channel deterministic and 4-channel llm-inclusive combinations
  never regress each other). `DEFAULT_CHANNEL_WEIGHTS` is relabeled
  library-demo/test-only. **Still open from this finding:** the llm
  adjudication channel joining the weight estimate (ADR 0145 SS5 —
  4-channel estimation run in progress against the dev corpus), and
  re-verifying the named 3-post family's chain under the new
  corpus-wide graph.
- **Entity and abbreviation resolution — source-stated case fixed
  (2026-08-22), inferred case open:** an organization's former/alternate
  name (e.g. "X(구 Y)") the post text itself states was dropped entirely
  during extraction, even though `prov_alternate_of` was already a fully
  declared predicate end-to-end (ontology term, allowlist, frontend label)
  with nothing extracting it. Fixed with a RELATIONS prompt rule
  requiring the post text to state the name change directly -- never
  inferred from context, similarity, or outside knowledge. The
  SearXNG-verified INFERRED-alias path (for a relationship the source
  text does not state, e.g. an unstated real-world merger/acquisition)
  remains open and needs its own resolution/verification client wiring
  analogous to `organization_name_resolution.py`, plus a dedicated ADR --
  not implemented here to avoid silent unverified inference. Canonical
  names, multilingual labels, team-vs-organization typing, and
  title-aware person disambiguation beyond this specific case still need
  end-to-end evidence.
- **Search ranking for structured field matches — fixed (2026-08-22):** a
  search matching a post's own `source_order_pool_code` (project/order-pool
  code) exactly fell into the same generic relevance tier as any unrelated
  post that merely mentioned the code string in free-text body prose,
  scattering a project's own records below loosely related noise for that
  exact search term. Promoted a structured field match to the same top
  priority tier as a title match.
- **Playwright E2E coverage — infrastructure added (2026-08-22), narrow
  scope:** Playwright was an unused devDependency with no config or `e2e/`
  directory. Added `playwright.config.ts`, a login fixture, and one
  regression spec covering the Knowledge-Graph black-node fix end-to-end
  against a live authenticated browser+backend+database, discovering a
  target post through the app's own API at runtime rather than a post id
  fixed in the file (this repository's synthetic-only-artifact rule
  forbids committing a specific private record's identifier). Broader
  E2E coverage (R&R job-title/org-anchor rendering, Event Lineage
  connection, search ranking) against seeded synthetic data with fresh
  LLM-populated content remains open; that logic is covered today at the
  unit/integration level (vitest, pytest) but not through a real browser.
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
- **Lineage coverage — open, root cause identified (2026-08-22):** superseded
  by the more precise "Event Lineage thread grouping" finding above -- the
  dataset-wide `thread_group_key` mismapping is the dominant reason most
  posts have no lineage component, not a genuine absence of a real thread.
  After the targeted single-family fix and a full rebuild (still LLM-free,
  see that entry), the persisted graph has 943 post-lineage edges (down
  from a stale pre-fix snapshot of 1,308 that predated the current
  `SOURCE_POST_ELIGIBILITY_SQL` filter -- not itself a regression). A
  rebuild/coverage gate distinguishing genuinely isolated posts from
  missing extraction/grouping evidence remains open pending the dataset-
  wide `thread_group_key` backfill and import-script fix.
- **Orchestrator client timeouts — fixed, evidence-backed (2026-08-22):**
  three separate `ContextualOrchestratorXClient` classes
  (`keyman_extraction.py`, `organization_name_resolution.py`,
  `corporate_hierarchy_inference.py`) defaulted to 30-180s timeouts too
  short for `mode="auto"`'s deep multi-agent orchestration; a live
  "Extract Keymen" call reproducibly hit `BrokenPipeError` in
  contextual-orchestrator's own logs (the request completed, but the
  client had already given up and closed the socket) and, once that was
  fixed, a `TimeoutError` one step further down the same call chain.
  Raised all three to 600-900s (this is a real user-triggered action, not
  a hot path). `relation_verification.py`'s SearXNG client (15s, a plain
  search HTTP call, not `mode="auto"`) was left unchanged since nothing
  reproduced a problem there. Contextual-orchestrator's own "agent pool"
  work (PR #795 merged, #804 open in that repo) may independently reduce
  how often the ceiling is needed; not duplicated here.
- **`organization_name_resolution` schema drift — open, environment-only:**
  the live shared dev database has a `context_sha256` column and a
  composite primary key on `organization_name_resolution` that exists in
  NO committed migration (0015 defines a plain `raw_organization_name`
  primary key, matching the current application code exactly). This is
  uncommitted, in-progress work from a different concurrent session
  applied directly to the shared database rather than through source
  control -- not a code defect. It currently blocks a live end-to-end
  verification that an uncataloged person becomes clickable after a
  fresh "Extract Keymen" run (the mechanism itself, and every timeout fix
  above it in the call chain, are confirmed correct up to this point).
  Resolves once that session's migration lands.
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

1. Re-fetch PR #366's exact head and required reviews/checks, then separately
   audit PR #343 and the superseding calendar contract PR #355.
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

## 6a. 2026-08-22 update: 5W1H/KG evidence-contract checkpoint (`docs/customer-master-scope-adr`)

Exact head after this update: `dbd8422c0ed094b94d1f778ffa70a2a6438a50e7`
(squash merge of PR #430 on top of #425, #424, #423, #416, #413, all merged
this session). Real post identifiers and business names are deliberately
excluded per this repo's de-identification discipline.

- **Closed this checkpoint:** a corpus-wide 5W1H `who`/`what` regression
  (stale-contract summaries silently emptied both slots regardless of
  whether the underlying evidence rows existed -- PR #413); relative "when"
  phrases (올해/내년-style) had no absolute-date resolution mechanism, now
  added via a `resolved_date_text` field anchored to the post's own
  authored date, never a guess (PR #416); the MEASUREMENTS unit registry
  had no volume unit at all (`unit_m3`/`unit_liter` added, PR #424) and the
  active extraction prompt never enumerated any valid unit code, not even
  the pre-existing three; a stripped inline HTML tag (`<span>` etc.) could
  fabricate a phantom indentation level indistinguishable from real nbsp
  indentation (PR #423); product/equipment RELATIONS extraction had zero
  prompt guidance despite the KG renderer already supporting the node type
  generically (PR #416); a details-response token budget shared with the
  short summary call silently truncated RELATIONS on content-rich posts
  (PR #416); the source detail-state W/D/A panel asserted an unverified
  LOVEM/SAP label as settled fact with no confidence signal at all (PR
  #425, now confirmed/unconfirmed throughout the UI, R added as a
  moderately-evidenced hypothesis via multivariate analysis of the raw
  export, not LOVEM-confirmed); a bare meeting clock-time with no date
  anywhere in the post had no resolution path (PR #430, the model now
  judges same-day-filing plausibility explicitly, never asserting the
  filing timestamp as the event's own time).
- **Investigated, no code defect found:** an embedded-image email's date
  clue not reaching 5W1H turned out to be a stale-contract artifact already
  fixed by PR #413's mechanism, confirmed via 4 live reproductions; a
  external supplier's product-announcement post's empty who/what/when was
  the same stale-contract pattern, confirmed already resolved live.
- **Investigated, genuine external blocker, not fixed:** "TEPP-based
  cross-post connection" -- TEPP is architecturally an analysis-run *kind*
  (psychometric theta measurement per corporate entity per period) with no
  code path anywhere linking posts to each other; building one would be a
  new feature, not a bug fix, and is separately blocked on TEPP's own
  production readiness (its most recent merged PR is explicitly scoped
  "not a production... service", loopback-only, non-durable; see
  `tepp_readiness_watch` session memory for the standing watch).
- **Not investigated this checkpoint:** the day1/2/3 post-family lineage
  connection and search-ranking complaint (carried over from a prior,
  already-closed goal); org→project→org KG structure, R&R
  job-title/catalog-link, a competitor's former-name alias resolution, black-KG rendering,
  and event-lineage tracing for the carried-over introduction-meeting post
  family (also carried over from that prior goal, already resolved per its
  own closure record) were not re-verified this checkpoint.
- **Local quality evidence at this exact head:** backend `pytest tests/ -q`
  722 passed / 11 skipped; frontend `npx vitest run` 200-203 passed across
  the individual PR heads; `npx tsc --noEmit` clean on each frontend PR.
  These are local checks at PR-branch heads, not independent-review or
  hosted-protected-gate evidence at the current merged head -- rerun after
  merge before treating this exact head as release-ready.

## 6b. 2026-08-23 update: Customer Master post-panel checkpoint (`docs/customer-master-scope-adr`)

Exact head after this update: `5458151f8702fe0444a45b38715216de7c29fa61`
(squash merge of PR #462 on top of #461, #458, all merged this session).
Detailed evidence for each item lives in section 5's "Customer master
'customer tree'" bullet, updated in this same checkpoint.

- **Closed this checkpoint:** clicking a customer's related post in
  Customer Master navigated the whole workspace to Board instead of
  showing the post in place (PR #458); `resolve_customer_hint` created
  every newly resolved SAP customer code as a flat, unparented entity
  instead of routing through the existing ADR 0010 hierarchy-inference
  pipeline (PR #458); hint resolution was reachable only one code at a
  time via the admin UI with no bulk path (`scripts/backfill_customer_hints.py`,
  PR #458, CLI-safety fix in PR #461); `CustomerEntityTreeRow`/
  `CustomerRelatedPostCard` had no Storybook coverage and two real
  accessibility gaps (WCAG 2.5.5 touch target size, screen-reader
  disambiguation of the "Resolve" button) went unreviewed against this
  repo's `ui-ux-pro-max`/`Anti-Slop-UI` skills (PR #462).
- **Learned this checkpoint, process-level:** this repository's
  stacked-branch workflow lets a PR merge into a branch another PR has
  already forward-merged past, orphaning the new commits even though
  GitHub reports `state: MERGED` -- happened twice in this checkpoint
  (PR #414's predecessor attempt, and the final commit of PR #458 itself).
  Verify a merge by reading the actual file content at the merge commit,
  not by trusting `state`/`mergeStateStatus`/commit-ancestry alone (a
  squash merge also makes `git merge-base --is-ancestor` an unreliable
  check on its own).
- **Not closed this checkpoint:** the standing gap section 5's bullet
  describes -- a counterparty `corporate_entity` ADR 0010 auto-creates is
  never linked via `account_affiliation`, so it cannot reach
  `/api/customer-master` regardless of corpus size -- remains open and
  still needs its own ADR before implementation.
- **Local quality evidence at this exact head:** frontend `pnpm exec tsc -b`
  clean, `pnpm run lint` clean, `pnpm test -- --run` 204/204 passed,
  `pnpm run build-storybook` succeeds; backend `pytest tests/ backend/tests/`
  860 passed / 17 skipped (one pre-existing, unrelated failure --
  `resolved_date_text` column missing -- confirmed absent from every file
  this checkpoint's diffs touch). The new Playwright e2e spec
  (`frontend/e2e/customer-master.spec.ts`) was not executed: no local
  stack was running in this environment at the time.

## 6c. 2026-08-23 update: ADR 0144 design panel and a self-correction

Ran a multi-agent design panel (2 independent design proposals + 2
adversarial ABAC-safety critiques + 1 synthesis) to resolve the "Customer
master 'customer tree'" bullet's open ADR requirement. Produced
`docs/adr/0144-customer-master-observed-entity-link.md` (Proposed status,
not yet implemented).

- **Self-correction, not just new work:** the design panel's first agent
  re-read `backend/app/main.py` before proposing anything and found that
  section 5's own "counterparty entities are never linked via
  `account_affiliation`, so they cannot reach this endpoint no matter how
  well-populated the corpus becomes" claim -- repeated without
  re-verification in this checkpoint's own earlier `## 6b` update -- is
  false as stated: ADR 0125 already added an `observed` path
  (`post_organization_mention`-joined) that surfaces a directly-named
  counterparty entity with zero affiliation row. Verified directly against
  the current query rather than trusting the agent's claim. Corrected
  section 5's bullet in place (see its "Correction (2026-08-23)"
  paragraph) rather than leaving the overbroad claim standing. The real,
  narrower gap: an ancestor entity never itself directly named in any
  visible post is still invisible, because `_observed_hierarchy_ids` only
  facet-marks rows already in the result set, it cannot add a missing one.
- **Adversarial review caught a real security defect before it shipped:**
  the panel's first design (bounded read-time traversal gated on the
  `AUTO-` entity-code prefix) was rejected after its critique constructed a
  concrete cross-account leak -- `corporate_entity` is one catalog shared
  across every account, and a fuzzy-matched/reused ancestor row's
  `entity_name`/`parent_entity_id` can trace entirely to a different
  account's private post evidence, which a public-verification-only gate
  cannot distinguish from evidence *this* account itself provided. The
  second design (write-time, per-source `account_observed_entity` evidence)
  survived
  its own critique with one required fix (synchronous reconciliation on
  post-mutation, not merely nightly) and was adopted with that fix folded
  into the decision as mandatory, not optional.
- **Not done this checkpoint:** implementation of ADR 0144 (new table,
  ingestion hook, reconciliation path, tests) -- intentionally scoped out;
  ADR-before-implementation discipline per this repo's own constraint on
  ABAC-adjacent changes. ADR number `0144` may need renumbering when this
  branch reconciles with others assigning numbers in parallel (see the
  numbering note at the top of the ADR file itself).

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
