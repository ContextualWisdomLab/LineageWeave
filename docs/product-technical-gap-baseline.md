# Product & Technical Gap Baseline

> Audit scope: the current LineageWeave reader/source-context worktree and all
> 56 open PRs, compared with protected `main`, the UI/UX Standard Guide v3.0,
> ADR 0118, the accepted TEPP contracts, and contextual-orchestrator. Real
> source identifiers are deliberately replaced with case labels; they must not
> enter repository artifacts.

## 1. Exact-head evidence

### 1.1 Current continuation head

Observed at `2026-08-24T06:45:00+09:00`: protected `main` and `origin/main`
remain `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`. This loop's continuation
head is PR #490 `feat/board-source-detail-state-filter` at
`154a13ef180a5f5e859c52fe056f4925c7fe2757` (docs refresh follows). The live queue has 56 open PRs,
all targeting protected `main` and GitHub-`MERGEABLE`. Protected merge stays
blocked by ruleset `18156473` (two approvals and approval-after-last-push)
and ruleset `21065108` (no force-push). This loop closed leftover-pair
next-action jargon on that head (ADR 0049: `Open {post}, then read Post
quality criterion {criterion}.`) and kept saved evaluation scores when the
evaluation channel is down. Worker factory review threads
`PRRT_kwDOT22WIM6biC_J` / `_K` / `_L` are resolved. Leftover-map PRs
#533 `ef38a8473bcf`, #532 `53f84127cd2a`, #531 `e359dcd28e5c`, #530
`2ca0974625e8`, and #529 `54f3f69fb3f7` had the inherited unauthenticated
AdminPanel TypeScript break repaired in source. Those leftover-map PRs still fork `ef6f5a5f`
independently rather than stacking on #426/#490. Local evidence on the
continuation head: worker pytest `20` passed twice, frontend Vitest `358`
passed twice, oxlint 0, Storybook static build completed. No real
organization or person names are used in this receipt.

Earlier observed at `2026-08-23T10:31:20Z`: protected `main` and `origin/main` are both
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`. The dirty continuation worktree is
based on `65f0a412c18286434c272eb8c4b38efeb2cd45c0`; relative to `origin/main`
it is `821` commits ahead and `0` behind, so this checkout is not a
merge-ready PR head and its local changes must not be attributed to any open
PR without a fresh branch/commit comparison.

Conversation-history review (example: a sidebar with New conversation and
selectable saved conversations): Ask Agent already ships list/select/new on
this checkout (ADR 0126, migration `0105`, `AskAgentPanel`, Vitest
`restores saved Ask Agent history and can start a new conversation`). Open
PRs in the current queue, including #484, #482, #258, #481, #468, #421, and
#418, do not add the same account-owned history to each post's
Ask-about-this-lineage surface. That gap is closed here as ADR 0136:
`post_ask_session` / `post_ask_turn` stay account-owned and post-scoped,
`post_chat_result` remains the seeded/cache store, and the popup starts a
new conversation so the seeded dump stays until the reader selects a saved
thread. TEPP topic modeling of how many posts can connect, and how many
lineages form under temporal precedence, remains deferred. No real
organization or person names are used in this receipt.

Current local changes close evidence-backed defects without weakening trust
boundaries: Global Ask now keeps question retrieval when a selected post is an
anchor, filters candidates before limits through the same reader-eligibility
and corporate-visibility boundary, bounds both chat request bodies at 4,000
characters, and preserves formal Korean `-니다` endings. The reader can open
Ask from a post, see and clear the starting evidence, switch saved
conversations without a stale anchor, navigate browser history without stale
state, confirm CJK IME composition without accidental submission, and use a
native modal mobile navigation drawer. Reader-facing failures now share the
token-backed `ExceptionAlert` / `SummaryStatus` surface (ADR 0134): text
identifies the failure, next-action copy is present, recovery controls meet
`--size-control-min`, light/dark `--color-exception-*` tokens replace
color-only red paragraphs, and raw exception types, stacks, OIDC diagnostics,
and 5xx provider payloads stay hidden (ADR 0123 / CWE-209). The bounded Python
unit partition passed `750` tests with `11` skips; backend integration
contracts passed `21` tests and skipped `115` live-stack cases. After leftover criterion landing and catalog-unbound / dropped-channel /
confident-negative next-action copy (ADR 0049 / ADR 0135),
`cd frontend && pnpm run test` passed all `255` tests,
leftover landing ran twice, `pnpm run build-storybook` completed, lint
was clean, leftover/Null-channel pytest passed `4` focused cases, and
Playwright loaded the Running Lineage Queued Storybook scene twice with
kind-exact next-action text, a Refresh control, no Start reconstruction
control, and zero page errors. After the
exception-message UI (ADR 0134) and analysis-result next-action flow
(ADR 0135), an earlier `cd frontend && pnpm run test` passed all `238` tests,
`pnpm run build-storybook` completed, and Playwright loaded the running
lineage queued scene twice with kind-exact next-action text, a Refresh
control, no Start reconstruction control, and zero page errors. Pinned
Corepack frontend lint and the production build pass on the current source. The production chunk warning, skipped live-stack cases,
repository-wide coverage, exact-source authenticated browser run, and hosted
gates remain open.

Subsequent source-reference research changes are not covered by those partition
totals. The focused research/security/KG partition passed `36` tests at 100%
branch coverage for `source_research.py` and `source_research_ingestion.py`; the
broader research, migration-replay, and shared HTTP-client partition passed
`69` tests. The source-research panel passed all `3` focused tests, and its
locale partition passed `28` tests. These checks do not prove a live PostgreSQL
migration, external SearXNG/orchestrator calls, or an authenticated API/browser
path.

The current ADR 0137 change closes the per-post customer-identity gap in
source: `(source_system_code, source_customer_code)` now requires at least two
authorized eligible posts, contextual-orchestrator candidate resolution, a
versioned fast-mlsirm Judge result with persisted IRT categories, external
corroboration, and a unique catalog outcome before promotion. Migration `0137`
keeps the judgment, exact post evidence, stable binding, and preferred/former/
alternate names in normalized tables. Promoted observations project as the
distinct `edge_customer_identity_observation` ontology/KG relation; source-post
authorization scope is not rewritten. The PostgreSQL importer automatically
reconciles only changed customer keys and reports unavailable providers without
rolling back imported source records. The identity/ingestion partition passed
`19` tests at 100% statement and branch coverage (`201` statements, `46`
branches); schema/replay checks passed `23`, focused UI/i18n checks passed `6`,
and the production frontend build passed. The exact-current authorized catalog
and corroborated-promotion API contracts passed against fresh migrated
PostgreSQL databases after Keycloak recovered. A live external
orchestrator/SearXNG/TEPP import, authenticated rendered review, hosted checks,
and independent review are not yet claimed.

The current temporal-relation correction makes explicit chronology an
OWL-Time `time:before` edge from the earlier release/introduction milestone to
the later milestone. Post-summary contract v19 separates the focused
`RELATIONS:` extraction from the larger evidence response, requires every
explicit pair, and rejects replacing a named base-to-variant pair with another
nearby product enumeration. A persisted older summary now returns immediately
as explicitly stale instead of blocking the reader on sequential orchestrator
calls; durable regeneration remains the operator backfill path.

Authorized, non-identifying runtime verification processed exactly one target
with no failure and persisted v19 as current. The authenticated API returned
one requested earlier-to-later edge, distinct temporal-entity endpoints, the
OWL-Time IRI/label, evidence, and confidence. The summary and focused Knowledge
Graph calls completed in approximately 0.23 and 0.19 seconds. The graph exposes
source, relation, target, evidence, and confidence without requiring SVG hover;
the served production asset contains the directed-graph name, visible direction
instruction, and evidence-table contract. Browser-rendered visual comparison
remains open and is not claimed.

Two Compose bottlenecks found during this verification are fixed at their
shared boundaries. `backend/Dockerfile` now caches the locked Rust/Python
dependency environment before copying application source: the clean dependency
layer compiled in 4 minutes 47 seconds, an unchanged rebuild completed in 2.2
seconds, and a later Python-source rebuild completed in 27 seconds without
recompiling `fast-mlsirm`. ADR 0144 and migration 0035 now skip legacy body
search indexes when migration 0036's normalized successors exist; a complete
existing-volume replay completed in 7 seconds with zero active or legacy index
builds. Focused backend/migration checks passed `102` tests with one optional
orchestrator integration skip, and frontend Knowledge Graph/i18n checks passed
`30`. The latest complete coverage-instrumented full Python suite, at
`e4ce49d1`, passed `987` tests with `17` skips; production Python source measured `87%` branch-aware
coverage across `8,071` statements and `2,506` branches, with `790` missed
statements and `397` partial branches. The current composition then passed
`90` focused Python tests with one optional integration skip. The temporal Python delta itself has
`7/7` changed executable statements and `2/2` changed branches covered.
The full frontend suite passed `354` tests, and frontend lint/build plus
`git diff --check` passed. The new official Vitest V8 production-source
measurement reports `95.73%` statements, `87.04%` branches, `94.57%`
functions, and `97.37%` lines; tests, Storybook scenes, and test setup are the
only excluded non-production files. Repository-wide 100% coverage and visual
browser acceptance remain separate open gates.

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

Live queue at `2026-08-24T06:50:00+09:00` is 56 open PRs, all based on
protected `main` `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`. Continuation
head is #490 `884edcd65e68`. Leftover-map family still forks `main`
independently: #533 length, #532 cosine, #531 inner product, #530 residual, #529 rank,
#527 observed/expected, #522 two-axis distance, #521 comparison strip,
#519 axis share, #518 complete-case, #485 criterion landing, #481
interaction-map. Hosted Checks on the heads repaired this loop are queued,
not a stop. Independent leftover-map PRs should stack onto #426/#490 rather
than keep inheriting the unauthenticated AdminPanel TypeScript break.

Ruleset `18156473` requires two approvals, an approval after the last push,
resolved conversations, dismissal of stale approvals, and seven central
workflows. Ruleset `21065108` prohibits force-pushes with no bypass. No
protected merge is claimed from this listing.

```text
#533 ef38a8473bcf  #532 53f84127cd2a  #531 e359dcd28e5c
#530 2ca0974625e8  #529 54f3f69fb3f7  #527 df18ed69ad43
#525 e4d6717c147c
#524 4b1691b4be7d  #522 2ab96809c374  #521 d9d2207360ea
#519 29bff9270764  #518 3117823ffc34  #496 288125acb1e6
#493 499c8b1bc4cd  #490 884edcd65e68  #485 f17a116dd60d
#484 c5c9911c102c  #482 c38c08d6f464  #481 329449790cc6
#480 f18b421d8522  #479 f8bb4102719e  #474 025bb3df4e5a
#468 228f13dd5e32  #463 3773d40c74df  #455 dab57fcadb3c
#454 f30e2523e9c3  #453 98fcf052b883  #452 09e0ec034ca1
#451 e84fa8d20c7d  #450 c624e919d880  #449 0cc40bc75a80
#448 3c1506a30101  #447 af6317237bc5  #446 8f9698993077
#445 160ca908fce1  #444 4af7d4b79689  #443 11fc2af36960
#442 8e6f24df1827  #441 5e59e7d1a0a3  #434 9f506a962f73
#426 3b7c3e29d608  #422 c54b172e439c  #421 2fc08835485d
#419 b51b97be0746  #418 ed99c40a22cc  #417 c5c0929c68ab
#415 d8590f1f81db  #405 0b1b1fcfed87  #394 cf9505b75948
#393 4ddd3a83aaa7  #387 6bcd52f1d8b1  #383 ab5d4c272532
#368 0f61d66ed1a8  #355 6fc22a9471bf  #349 bef4a858b2f0
#258 f0b5234db6d3
```

Historical snapshot retained below. Earlier in-scope leftover/workspace heads
included leftover-map locale follow-up `#489` `7f0368ec7d04`, leftover
landing `#485` `c2102f932e06`, leftover map `#481` `d192e8f40fff`, Event
Lineage interval `#484` `0d8187a5d529`, channel evidence `#387`
`c34681fdc692`, org-chip `#482` `42f7c4e81289`, image-region `#405`
`0b1b1fcfed87`, Ask citation `#419` `b51b97be0746` / `#418`
`ed99c40a22cc`, workspace board `#258` `ea143748cdda`. The following
open-PR heads were refreshed at `2026-08-23T12:02:11Z`. Newer PRs in the
live listing above supersede that snapshot.

Bounded gate evidence: PR #394's earlier Corepack/Undici pnpm-download failure
is superseded by terminal checks on unchanged head `cf9505b75948`; it still has
no independent approval. PRs #349/#355/#383/#417 have exact-head coverage
change requests, and #387/#405 remain blocked by older change-request decisions.
The earlier `2026-08-23T10:52:15Z` refresh of #258
found head `bcfb67f9b88dd62af6b6886dac4b846b6cbd0ce4` green with all 88
threads resolved, but it is now historical. Current head
`ea143748cdda9aa8be24f7ee8f282e56d6fc7adb` uses `math.isfinite` for
lineage-score validation and preserves early project-key validation; its `26`
focused project-history tests pass and all current threads are resolved. At
`2026-08-23T12:03:02Z`, Strix had failed closed after NVIDIA rate limiting
and a provider-less LiteLLM fallback; its completed report and SARIF contained
zero source findings. The active OpenCode change request is on historical head
`6dc040c6b3ea`; the current OpenCode workflow is green but does not provide a
current-head approval, and exact-head approvals remain zero. Active ruleset
`18156473` still requires two approvals and approval after the last push with
no bypass actor, so #258 remains blocked. The other
thread/check observations remain bounded to the earlier audit and are not
restated as current. PR #481's prior exact head `732f2b25f8ce` had one Strix
failure that explicitly reported provider/infrastructure errors; its two cited
source locations did not contain the claimed AWS credential or syntax error,
so no scanner-driven source patch was justified. Prior head
`7ff509e545fa8cdcba91acaeca25e46e40bab44e` also makes pair selection and
distance match the persisted two-axis map, preserves simultaneous
closest/farthest emphasis, exposes nested SVG buttons to assistive technology,
and applies migration 0104 in the real API fixture. Local evidence is backend
`661 passed, 114 skipped`, frontend `144 passed`, lint, TypeScript, and
production build success; all review threads are resolved. Hosted Strix later
failed closed after Nvidia returned 429, the first fallback ended without an
authoritative lifecycle report, and the `openai-direct` fallback reached
LiteLLM without a recognized provider prefix. The scan logged zero
vulnerabilities before those provider failures, but produced no authoritative
report; this is infrastructure evidence, not a source finding. Intermediate head
`94dc79ae6c7f40118c922c4e0042fad2b93daf85` additionally contains the merged
#488 criterion-node interaction. Current head
`d192e8f40fffd237525bf3b62583c36b2941a89a` removes redundant empty/rank guards
and adds shape, disconnected-observation, and overflow regressions without
inventing map coordinates. The leftover-map and period-report partition passes
`24` tests and all review threads are resolved. The exact-head full suite and
Strix are still running; qualifying approvals remain absent, so it is still
`BLOCKED`.
PR #482 head `42f7c4e812899131e255f117512e7a7081e7dec5` removes the unused VOC
alias query, preserves the direct Keyman companion-label read, keeps legal
suffixes distinct during companion matching, and includes the related-chip
caption in its accessible name. Its parent `116af49f403d` passed `25` focused
Python tests with 100% branch coverage for `organization_alias.py`; frontend
chip tests and lint passed. On the current child head, both focused related-chip
regressions, lint, and TypeScript no-emit checking pass. All review threads are
resolved. Hosted Strix failed after three Nvidia 429s and the same unrecognized
LiteLLM fallback provider; it reported zero vulnerabilities before failing
closed without an authoritative report. Exact-head approvals remain zero, so
it is still `BLOCKED`. PR #429 is also `BLOCKED` for
independent review; a later Strix run succeeded on the same exact head at
`2026-08-22T13:32:42Z`, superseding the earlier failed run. Auto-merge state is
intentionally not used as merge evidence.

PR #468 head `228f13dd5e32b5b0ee72d5ba7cfcd26f17c7a1c4` has all review threads
resolved. Its affiliation lookup cardinality is already bounded by database
uniqueness constraints, so an application-side multi-row check would duplicate
the native invariant. Strix failed with the same provider chain as #481 and no
authoritative source finding; exact-head approvals remain zero. PR #484 head
`0d8187a5d5298489444e1734412be277ea584b5e` now normalizes aware `created_at`
values to their UTC day in both the shared interval helper and migration 0105
backfill. The +09:00 near-midnight regression failed before the repair; the
interval, ingestion, replay, and live-schema partition now passes `29` tests.
All review threads are resolved; the full backend/frontend gates are green,
Strix failed closed through the same provider-infrastructure chain, and no
approval is claimed. PR #485 head
`c2102f932e0674175387726e0467f730c3c8af36` restores the existing OIDC return
URL flow and removes an unreachable unauthenticated AdminPanel render that made
the frontend TypeScript build fail, and now retains a regression for the
session-storage fallback. Production build, lint, the focused login and
leftover-pair landing tests, and the hosted frontend job pass on this head; all
review threads are resolved. The hosted full suite is also green; Strix failed
closed through the same provider-infrastructure chain, and exact-head approvals
remain zero.

PR #486 head `841f02418a9f109cd8d58894470c6b3a5fe5db3f` strengthens the
authenticated modal test to require focus restoration to the same opener and
forces the site-map test to navigate to Calendar and verify the URL, persistent
navigation state, and destination heading. Its 120-second test budget covers
the bounded serial fixture waits while retaining shorter step limits. Lint and
TypeScript pass. It merged at exact head
`841f02418a9f109cd8d58894470c6b3a5fe5db3f` as merge commit
`f11a2cb546792622932011587fe6f6aa54c79948`, but only into the historical
`docs/customer-master-scope-adr` branch. The earlier Chromium run predates the
strengthened assertions, so an exact-head browser rerun and eventual
protected-main gate remain open; this merge is not protected-main evidence.

PR #488 merged old exact head
`46434836e9b06453dabf6f3bfd72bbc19b3199cd` as
`94dc79ae6c7f40118c922c4e0042fad2b93daf85`, only into #481's feature branch.
That head makes only leftover-pair criterion nodes interactive; non-pair
criteria remain honest visual context. The locale repair was pushed after the
merge and therefore is not part of #488's merge evidence. PR #489 isolates that
single repair at `7f0368ec7d043a33197f6198b2b38a7560610fc5`: connector tooltips
use the existing i18n catalog and the displaced Event Lineage multi-locale
assertion is restored. Its exact three-file diff passes `154` frontend tests,
lint with only the existing Fast Refresh warnings, and forced TypeScript build;
both hosted test jobs are green, while qualifying independent approval remains
absent. Both branches remain stacked behind blocked #481, so neither merge is
protected-main evidence.

The LineageWeave-specific central heartbeat is not yet deployed. Central
`.github` PR #1086 now has exact head
`aeb096a52c5f4c2647f05f54f0aa6b17200a350f` after a normal merge of protected
central `main`; it runs the existing repository-wide test suite and measures all
three modified scheduler modules at 100% statement and branch coverage. Local
exact-head evidence is `1426 passed, 1 skipped, 16 subtests`, `2159/2159`
statements, and `868/868` branches, with Actionlint, docstrings, compileall, and
diff checks green. All 19 review threads are resolved, but hosted checks are
running and historical change-request decisions have not been replaced by a
qualifying exact-head approval. The workflow inventory contains only
pull-request runs for this caller; no `schedule` run from protected central
`main` exists yet. The central generic scheduler on protected `main` does run
`*/30 * * * *` and `*/15 * * * *`, but that is not evidence that the proposed
minute-4 LineageWeave repair caller is operational.

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
  and CSS tests; fresh browser evidence remains open.
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
- **Locale document metadata — substantially present; no-JS fallback fixed
  in this worktree:** `i18n.ts` synchronizes `document.documentElement.lang`
  after locale selection and `i18n.test.ts` covers the supported locales.
  `frontend/index.html` now renders a visible `<noscript>` message
  (English + Korean, inline-styled so it doesn't depend on the JS-bundled
  CSS) instead of a silent blank page when JavaScript is disabled, covered
  by `indexHtml.test.ts`. A fully locale-aware no-JS message (matching the
  visitor's `Accept-Language`) remains open -- that needs server-side
  locale negotiation, not a client-only fix.
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
| Noto Sans, palette, table/form/button conventions, modal 50% mask and keyboard semantics | ADR 0118, token CSS, popup dialog implementation, frontend tests | source + unit |
| Keyverse/OIDC login with real account | `auth.py`, OIDC discovery/JWKS boundary, local redirect check | source + local-integration; Keyverse open |
| Authenticated corp/PU attributes | `/api/me` returns DB-backed codes; backend integration test covers `TEST-CORP`/`TEST-PU`, the GNB disclosure is covered by `App.test.tsx`, and desktop/390px Playwright QA verifies the rendered scope | source + unit + local-integration + browser-mocked |
| RBAC/ABAC, public/private visibility, tenant isolation | `_can_see_post` plus W author/admin raw-source exception, analysis eligibility excluding W, API authorization tests (extended in this worktree: `/content`, `/knowledge-graph`, `/evaluation`, `/five-w1h`, per-post `/lineage`, `/bookmark` each now have a dedicated other-corp-403 regression test -- all were already correctly gated via `_load_visible_post`, so this closes a test-coverage gap, not a bug), aggregate-only runtime checks | source + local-integration |
| React product surface and PostgreSQL boundary | React routes/components, asyncpg API, Compose stack | source + local-integration |
| Authorized PostgreSQL export import mapping | `scripts/import_postgresql_posts.py`, ADR 0121, hash-verified RFC 2557 MHTML resolver, and synthetic preflight/import tests; authorized relation has artifact-path metadata but no body/content/HTML field | source + unit + local-integration partial; operator artifact files and authorized live import open |
| Bounded large-body search migration | `0035_body_search_prefix.sql`, `0036_normalized_body_search.sql`; live replay completed after bounded rendered-text indexing | source + local-integration |
| Public Compose liveness and tenant settings boundary | health-probe regression test, `0103_tenant_settings.sql`, replayed existing volume, one tenant-settings row, canonical `tenant_settings_id` after `0104`, rebuilt backend `/healthz` and authenticated `/api/settings` HTTP 200 | source + unit + local-integration |
| Two-word snake_case database identifiers | ADR 0120, idempotent migration `0104`, live public-schema audit, zero invalid indexes | source + unit + local-integration |
| Post list/detail popup, Korean summary, 5W1H, R&R, tickets/calendar | API routes, popup panels, backend/frontend tests; W is raw-source-only for author/admin and is excluded from summary and derived analysis targets | source + unit |
| Keyman on both sides, titles, affiliations, related KG nodes | Keyman/affiliate-tree/related-node routes and popup | source + unit; live extraction open |
| Ontology, semantic layer, provenance, W3C PROV-O projection | normalized schema, SKOS operational vocabulary concepts, `ontology_annotations` label fallback, OWL-Time canonical earlier-to-later relations, ADR 0124/0129, provenance modules, directed evidence table, ADRs; the Knowledge Graph view now classifies every rendered/tabulated relation into Time order, Hierarchy, Cause and effect, or Other (a legend plus an evidence-table Category column) and lays out nodes by a topological sort over temporal/hierarchical/causal edges instead of raw payload order, so precedence and hierarchy read without hovering each arrow (`frontend/src/relationCategory.ts`, `frontend/src/KnowledgeGraph.tsx`) | source + unit; corpus verification and authenticated browser confirmation remain open |
| Branching Event Lineage DAG with evidence trail | `LineageDag.tsx`, Storybook story, Figma frames, accessible node-kind names for screen readers/tooltips, frontend tests; runtime cases include both a rendered DAG and honest empty states, while current corpus coverage remains sparse | source + unit + local-integration partial |
| Customer master, cross-post identity, name history, and hierarchy tree | `/api/customer-master`, ADR 0125/0137, migrations `0105`/`0137`, source-system-qualified stable binding, fast-mlsirm Judge/IRT evidence, optional TEPP ordering, `edge_customer_identity_observation`, importer reconciliation, visible preferred/former/alternate names, scope filter | source + focused unit + local-integration partial; live external provider/import and broader authoritative hierarchy evidence remain open |
| VOC/VOM/VOP/VOCC/VOCO/VOS role classification | common lookup values and relationship APIs | source + unit; live classification open |
| Evidence-grounded chat and source navigation | `/chat`, `/ask`, citation/evidence UI | source + unit; synthetic orchestrator judge route verified, corpus chat/runtime evidence open |
| OpenTelemetry across LineageWeave, contextual-orchestrator, Valkey, and GRC | LineageWeave PR #383 adds API/Valkey/session spans; contextual-orchestrator PR #818 carries session/provider telemetry; governance-risk-compliance PR #51 adds request telemetry, W3C trace context, OTLP export, and ADR 0009 | source + PR; protected merge and end-to-end collector evidence open |
| PU/team/project weekly/monthly reports | report API/UI and grouping controls | source + unit; TEPP-backed live report open |
| TEPP calibrated measurement, dichotomous items, multilevel/MMM/time model | published import/REST boundary and TEPP ADR/PRD references | boundary-only; live-external open |
| contextual-orchestrator routing, VISION, embedding, schema repair | clients and provenance/session boundary; synthetic authenticated route returned a judge score of `0.98`, OCR succeeded, and region location returned five regions | source + local-integration partial; corpus backfill, capability/readiness evidence, and schema-repair workflow open |
| HTML semantic units, tables, indentation, footnotes, formulas | parser modules and synthetic tests; adjacent open PR #367 at exact head `b628722cb000717b0198e4337d12306d4306922d` adds numbered-footnote, leading-empty-cell, and short-ID regressions; 11-case authenticated popup sweep had no popup errors and rendered the supplied footnote/table cases; bounded metric superscript/subscript normalization has backend/frontend focused coverage | source + unit + local-integration partial; PR #367 protected checks, arbitrary formula/semantic correctness, and corpus re-backfill remain open |
| Base64/file image regions and multimodal evidence | image-region schema and VISION client boundary; live aggregate has 12,823 images, 25 described images, 421 failed images, 12,377 unavailable images, and 19 persisted regions; the bounded real-data queue run published three Valkey wake-ups and the worker claimed one | source + local-integration partial; supplied image-table case re-backfill and complete corpus coverage open |
| Abbreviation/multilingual alias/entity disambiguation | catalog hints, ADR 0026/0137 tie boundary, alternate/former name history, source-system-qualified resolver | source + focused unit; multilingual and live corroboration evidence open |
| SearXNG/internal relation fact check | verification endpoint and unavailable handling; local SearXNG health and JSON query both returned HTTP 200, while some upstream engines reported rate-limit/CAPTCHA results | source + local-integration partial; corroboration policy and reliable external coverage open |
| Source-reference research agent | ADR 0133, URL/patent lead discovery, bounded public-target crawl guard, contextual-orchestrator Judge boundary, normalized provenance persistence, cited supported-actor KG/PROV-O projection, explicit admin POST/read-only GET, and reader panel; the focused research/security/KG partition passed `36` tests at 100% branch coverage for both source-research modules, the broader research/migration/HTTP partition passed `69`, and the panel passed `5` focused tests | source + focused unit; live external and authenticated API/browser validation and canonical/final URL capture remain open; TEPP calibration remains unavailable until TEPP publishes a response-event wire contract |
| Valkey event queue and cloud-native Compose stack | queue modules, Compose services, health checks | source + local-integration; delivery stress open |
| 3NF, hot partitions, locks, read/write contention | canonical identifier migration plus existing migrations | source; operational evidence open |
| Rust/GPU/CPU psychometric computation | delegated to TEPP, not reimplemented here | boundary accepted; live TEPP evidence open |
| APA 7 doctoring and Zotero OA records | baseline bibliography, local Zotero API reachable, known metadata found | source + local-integration; OA attachment audit open |
| Browser E2E from login through evidence | authenticated local OIDC login, protected list, drawer/search, popup sweep, and aggregate evidence checks at 390x958; post-migration fresh session had `htmlLang=zh`, localized protected shell, zero console errors/warnings, no horizontal overflow, popup, summary, and Event Lineage | source + local-integration; external provider/runtime evidence remains open |
| Storybook scenes/edge events and design-token coverage | `LineageDag.stories.tsx`, inventory, Storybook build | source + unit |
| External email/project lineage package boundary | PR #343 merged at `125a8069a1554874d8067a15047e19d780ea6b7b` with strict v1.0.0 bounded request/result types, available-time cutoff handling, observed/inferred/proposed truth states, pair-budget enforcement, and no source/provider access | source + focused unit; immutable release open |
| Naruon calendar projection boundary | PR #337 is closed as superseded; PR #355 carries the strict read projection contract without making LineageWeave a CalDAV provider | source + focused unit; Naruon endpoint, runtime wiring, and provider conformance remain open |
| Hourly PR review/repair/merge loop | Central protected `main` owns generic `*/30 * * * *` and `*/15 * * * *` sweeps; the LineageWeave-specific minute-4 hourly repair caller remains open in `ContextualWisdomLab/.github#1086` at `aeb096a52c5f`, so no duplicate repo-local scheduler is required | source + exact-head local gate; protected merge and first scheduled run open |
| 100% coverage/docstrings/edge-case/release gates | the public Python docstring AST contract is current-head green; the two source-research modules and PROV-O have exact focused 100% branch results; the latest complete coverage-instrumented full Python suite at `e4ce49d1` is green at `987` passed / `17` skipped but measures only `87%` across production Python source, while the subsequent exact composition passes `90` focused tests / `1` optional integration skip; official Vitest V8 measurement keeps all production TypeScript/TSX in scope and reports `95.73%` statements / `87.04%` branches / `94.57%` functions / `97.37%` lines with `354` tests green | open: current-head hosted full suite, 790 measured Python statements, 397 measured partial Python branches, 122 frontend statements, 337 frontend branches, 47 frontend functions, 69 frontend lines, independent review, and release evidence |

## 4. Supplied parsing and semantic cases

The following user-reported cases remain tracked without storing real post IDs:

- `case-footnote-01`: footnote/list `li`/`ol` boundary is misclassified.
- `case-table-01`: HTML table parsing fails.
- `case-indent-01` and `case-indent-02`: semantic indentation is wrong.
- `case-multi-project-01`: two projects must produce separate event streams
  (synthetic unit coverage added in this worktree --
  `tests/test_person_mention_projection.py`'s
  `test_two_projects_on_one_post_keep_separate_key_event_streams` persists a
  post with two declared `project_mentions` and confirms each `KeyEvent`
  keeps its own `project_key`, with an event naming no project staying
  unattached rather than guessed onto either); internal facilities must not
  be guessed as Partner/Supplier remains open -- a separate claim about
  entity role classification, not addressed by this event-stream test.
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
- `case-temporal-product-sequence-01`: explicit first/next product chronology
  now extracts the corresponding release/introduction milestones as one
  earlier-to-later OWL-Time relation and renders its direction and evidence in
  the Knowledge Graph. Authorized re-extraction now passes at summary contract
  v19 with one requested pair; the earlier milestone now also renders above
  the later one (topological layout, not array order) with a "Time order"
  legend swatch and evidence-table category instead of an unlabeled arrow,
  closing the readability half of this case; authenticated browser
  confirmation remains open. Chronology alone does not assert revision,
  specialization, causation, or a private product-succession predicate.

These are not “resolved” merely because a prompt or heuristic was changed.
Each requires synthetic unit coverage plus an authorized runtime reproduction
or an explicit unavailable result.

## 5. Product and technical gaps

- **10-dimension UI/UX audit (Accessibility, Touch & Interaction,
  Performance, Style Selection, Layout & Responsive, Typography & Color,
  Animation, Forms & Feedback, Navigation Patterns, Charts & Data) —
  26 verified real gaps found, 7 shipped as PRs, 1 investigated and
  correctly declined, 18 logged below for follow-up (2026-08-24):** each
  dimension was surveyed independently, every finding re-verified against
  the live source by a second, skeptical pass before being trusted, and
  the highest-severity 8 were implemented with tests and opened as their
  own small PRs (this repo's established convention) rather than bundled
  into one large change.
  - **Shipped:** `.post-meta` text failed WCAG 1.4.3 contrast in both
    themes (#553); footer text failed WCAG 1.4.3 in light theme (#552);
    ~15 bare loading-state paragraphs had no `role="status"` live region,
    including the app's first screen (#558); Event Lineage DAG node marks
    were 14–18px, below the 24px minimum touch target (#554); the
    analysis-run reproducibility digest was readable only via mouse-hover
    tooltip, no touch/keyboard path (#557); several `<details>`/`<summary>`
    disclosure toggles rendered under the 24px touch-target minimum, two
    with no CSS hook at all (#560); Ask/Chat citation chips rendered
    ~19px tall on mobile (#556). All 7 are open PRs against `main`,
    pending review -- not yet merged.
  - **Investigated, correctly declined:** a claimed AdminPanel breakpoint
    mismatch (640px/900px vs. the shell's 768px/1024px) turned out to be
    evidence from a large, unmerged admin-workspace feature branch --
    the CSS/markup in question does not exist on `main` at all. No PR was
    opened rather than importing an unrelated feature to align breakpoints
    that don't exist yet; this is deferred until that admin-workspace
    branch itself lands.
  - **Logged for follow-up (verified real, not yet implemented):**
    footer copyright/title text and the required-field asterisk both have
    contrast gaps in at least one theme (Typography & Color, medium);
    Ask/Chat composers have no client-side character limit and surface a
    raw internal API path when the backend's 4,000-char cap is hit, and
    AdminPanel's Tenant Settings form has zero inline per-field validation
    feedback with no `aria-invalid`/`aria-describedby` wiring (Forms &
    Feedback, medium); Board search/filter/sort/page state is invisible
    to the URL and browser back/forward unlike the rest of the app's
    navigation, and the Keymen related-node drill-down has no breadcrumb
    or back path (Navigation Patterns, medium); the Knowledge Graph panel
    silently renders nothing on fetch failure or while loading, and its
    node styling (focus/evidence-only/catalog-linked) has no legend or
    text/aria-label equivalent (Charts & Data, medium); Board list
    filtering/dropdown derivation and the Lineage DAG's layout algorithm
    both recompute on every unrelated App re-render with no memo boundary
    (Performance, low); five separate hardcoded-value-instead-of-token
    instances in App.css -- a dead `--accent-warning` reference, two
    `border-radius: 6px` inputs instead of `--radius-control`, two
    `*-chip` classes hardcoding `999px` instead of `--radius-chip`, a
    third monospace font-stack spelling duplicating `--mono`, and one
    44px icon button hardcoding its size instead of `--size-control-min`
    (Style Selection, low); `.admin-section-heading` and
    SourceResearchPanel's title row were left out of layout fixes applied
    to their siblings (Layout & Responsive, low); an admin deep-link
    smooth-scroll bypasses the app's own `prefers-reduced-motion` reset
    (Animation, low).
  - **Operational hazard surfaced during this audit, worth fixing
    process-wide:** this repo's many concurrent-agent git worktrees share
    one `.git` directory and therefore one shared `refs/stash` stack.
    Multiple independent implementing agents in this same audit run hit
    real collisions -- a blind `git stash pop` grabbing a *different*
    session's unrelated uncommitted work into the wrong tree. Every
    incident was caught and recovered without data loss (via `git stash
    store`/`git log -g refs/stash` to restore the other session's entry,
    then re-applying the agent's own intended diff from scratch), but
    this is a real, repeatable footgun for this multi-agent-swarm working
    style, not a one-off. Recommendation: avoid `git stash` in any shared
    worktree checkout of this repo; use a scratch commit instead (`git
    commit -m wip`, later `git reset HEAD~1` or amend), which is
    per-worktree by construction and cannot collide.
- **Fabricated citation in ADR 0024 — closed (2026-08-24):** ADR 0024
  attributed the RankWeave `temporal` 0.25 / `lexical` 0.75 channel-weight
  split to "Samuel, D., MacAvaney, S., Yates, A., Zhang, E., Zhang, S.,
  Macdonald, C., & Ounis, I. (2025). Weighted reciprocal rank fusion for
  multi-channel retrieval [Preprint]" -- a paper that does not exist. It
  combined real information-retrieval researchers' names into a title no
  search or bibliography lookup could confirm; the lack of a DOI/URL on a
  specific, multi-author, dated citation was the tell. This is precisely
  the "arbitrary weight dressed as research" failure this project's own
  standing instruction against unfounded weights exists to catch -- an
  invented citation is worse than an admitted default, because it looks
  verified when it is not. Corrected in place: the fabricated reference is
  removed, Cormack et al. (2009) remains correctly cited for the RRF
  mechanism and η = 60 (this part was always real), and the 0.25/0.75
  split is now honestly described as an engineering default consistent
  with Efron & Golovchinsky (2011)'s general finding that relevance should
  usually dominate raw recency for a non-time-sensitive query -- not a
  value taken from any paper's reported optimum. A visible
  "### Correction (2026-08-24)" section documents the fabrication and fix
  for audit-trail transparency (relevant given this project's SOC 2/CSAP
  posture). `tests/test_adr_citation_integrity.py` pins the correction so
  the fabricated string cannot silently reappear. A dedicated citation-
  integrity sweep across all 44 ADRs with a References section (149
  citations total) then ran to check whether this was an isolated
  incident or a systemic pattern: it was isolated -- 147 of 149
  citations verified real (W3C/IETF standards, ACM/IEEE/arXiv papers,
  and software-documentation links all checked out). Two more, lower-
  severity issues surfaced: ADR 0025 and ADR 0137 both cited the real
  W3C PROV-O document (correct title and URL) but attributed it to
  "Moreau, L., & Missier, P. (Eds.)" -- the real editors of the sibling
  same-day PROV-DM spec, not PROV-O itself (PROV-O's real editors are
  Lebo, Sahoo, & McGuinness, 2013). Both are corrected in place with the
  same visible-correction-note pattern; `tests/test_adr_citation_integrity.py`
  now pins all three fixes (ADR 0024, 0025, 0137). No further fabricated
  or misattributed citations remain in the ADR corpus as of this sweep;
  a future ADR should be checked the same way before its citations are
  trusted, since this sweep only covers ADRs that existed when it ran.
- **Technology-benefit relation (which partner technology, who adopted it,
  where it is applied) — locally implemented, acceptance open (2026-08-24):**
  source research (ADR 0133/0145) can resolve a partner organization a post
  names only indirectly (e.g. an address match), but until now the specific
  technology or capability that partner provided, which organization
  received it, and where the adopter intends to apply it had no structured
  representation -- a reviewer opening a post that named a technology
  partner had no answer to those three questions beyond whatever free-text
  evidence happened to be attached to an unrelated relation row. ADR 0146
  adds a `technology` semantic-relation node type and three predicates
  (`lw_technology_provided_by`, `lw_technology_adopted_by`,
  `lw_technology_applied_to`) that decompose one technology-transfer fact
  into up to three source-grounded rows sharing the same technology subject,
  reusing the existing `post_summary_semantic_relationship` channel (no new
  table, same pattern ADR 0142 used for the planned-facility predicate).
  `SemanticRelationship.__post_init__` rejects a technology predicate whose
  subject is not typed `technology`. Migration 0177 extends the write
  constraint and is registered for existing-volume replay
  (`docker/postgres-init/migrate.sh`); the ontology TTL declares the class,
  the three object properties, and their `SemanticPredicateMapping`
  entries so `semantic_predicate_annotations` resolves them; the extraction
  prompt documents when to emit each predicate with a fictional example.
  `POST_SUMMARY_CONTRACT_VERSION` bumped 20 -> 21. Verified: targeted
  `pytest` (post_summary, ontology, schema, migration-replay -- 154 passed,
  1 pre-existing skip, including a real-Postgres insert/constraint round
  trip), frontend `tsc -b` and `oxlint` clean. Not yet verified: the LLM
  extractor actually emitting these predicates against a real post (no
  provider call made in this pass) and an authenticated browser capture of
  the popup surfacing the three facts distinctly.
- **Global Ask anchored temporal retrieval — locally implemented, acceptance
  open (2026-08-23):** a post detail now has a direct Ask action and carries a
  visible, removable starting-evidence anchor into the global Ask request.
  Question terms remain active alongside the anchor, authorized/eligible rows
  are filtered before candidate limits, stale anchors are cleared for saved
  conversations and browser navigation, CJK composition Enter does not submit,
  and both chat request bodies are capped at 4,000 characters. ADR 0090 now
  records that one exact sales-order code is sufficient retrieval evidence;
  the query admits company-code candidates while broader hints still require
  corroboration. Focused source, API-model, i18n, React interaction, lint, and
  build checks passed. A live PostgreSQL regression remains required before
  acceptance.
- **Ask history N+1 reauthorization — closed (2026-08-24, issue #358):**
  `fetch_conversation` in both `global_ask_history.py` and
  `post_ask_history.py` reauthorized each turn's sources/citations (and,
  for Global Ask, evidence facts) with its own query per turn --
  `2N+3`/`3N+3` queries for an `N`-turn conversation. Replaced with
  `_visible_post_ids_batch` / `_turn_evidence_batch`: one query per
  relation type per page load, independent of turn count, verified by a
  fake-connection unit test asserting exactly one `fetch()` call across 50
  turns. `turn_limit` (already capped at 50 by the `/api/ask/conversations/{id}`
  route) is the existing bound on citations-per-page, so no new budget
  parameter was needed. Same fail-closed, per-turn authorization boundary
  as before -- a real-Postgres integration test proves a citation revoked
  after persistence is dropped from only its own turn, never a neighbor's.
  Explicit query-latency benchmarking (vs. only query-count) is not yet
  measured; the AST/unit evidence above is the current acceptance basis.
- **Ask evidence labels — locally implemented, acceptance open:** persisted
  event, event-clue, quantitative, source-fact, and semantic-relation facts now
  have distinct reader evidence kinds and localized labels instead of falling
  through to the raw `source_field` label. Backend evidence rendering and the
  Ask UI regression pass; exact-source authenticated browser evidence remains
  required.
- **Frontend delivery and scene QA — partial:** production build succeeds but
  the single JavaScript chunk is 574.31 kB minified (158.54 kB gzip) and exceeds
  Vite's 500 kB warning threshold. Storybook now covers unanchored, anchored,
  saved-history, unavailable, and phone Ask states, and its static build passes.
  Add route- or workspace-level native code splitting only after measuring the
  authenticated navigation path; current-source browser capture remains open.
- **Repository-wide gate stability — partial:** the latest complete
  coverage-instrumented Python run at `e4ce49d1` passes `987` tests with `17` skips and
  measures `87%` branch-aware production-source coverage; pinned Corepack Vitest
  passes all `354` tests, and the reproducible `test:coverage` command reports
  `95.73%` statements / `87.04%` branches / `94.57%` functions /
  `97.37%` lines. CI now provisions pinned Valkey and a synthetic
  imported Keycloak realm, removing the infrastructure
  reason that made all `115` live-stack API tests self-skip; `actionlint` passes,
  but the hosted run is not yet evidence. The subsequent current composition
  passes `90` focused tests with one optional integration skip; current-head
  hosted full-suite evidence remains open.
- **Coverage and docstring gates — docstrings closed, coverage enforcement
  open:** the exact-branch AST contract scans every non-private function,
  method, nested callback, and class under `lineageweave/` and `backend/app/`;
  all 51 definitions missing on this head are now documented and the contract
  plus documentation-hygiene tests pass `5/5`. The full Python and official
  Vitest V8 production-source measurements remain below 100%, so their exact
  uncovered statement and branch counts stay open above. Exact 100% branch
  evidence remains limited to the scoped PROV-O workflow, the two
  source-research modules, and this docstring contract does not substitute for
  executable coverage.
- **Central OpenCode coverage sandbox — owner repair pending protected main:**
  issue `ContextualWisdomLab/.github#1250` is tracked in Project #1 as
  Ops/In Progress. Owner PR #1052 at `d2629dc7d9634368f04025c570b6395a9e1413f5`
  exports locked Python optional extras and removes pnpm's unsupported
  `--trust-lockfile` option while retaining exact lock-blob validation,
  offline installation, and disabled lifecycle scripts. Every other
  current-head check was terminal-success, but Strix failed closed after Nvidia
  429s and both configured fallback paths failed to emit an authoritative
  report. Central owner PR #1213 at
  `a675daccb65ee582781690db1b0e9dd282b34af1` already owns normalization of the
  `openai-direct` selector to LiteLLM's provider prefix and the bounded
  capability-fallback contract; it is still under review with Strix and Devin
  pending, so this repository does not duplicate that repair. Neither #1052
  nor #1213 is on protected `main`; LineageWeave #405 therefore still needs a
  fresh unchanged downstream canary after both relevant central contracts
  land.
- **R&R role/relationship conflation and catalog-linking boundary — evidence-backed (2026-08-21):**
  Live UI/UX feedback on a real R&R extraction surfaced three related gaps,
  root-caused against source rather than assumed:
  1. **"카탈로그 미연결" is the designed fail-closed behavior, not a bug, but
     was undiagnosable from the UI — fixed in this worktree (ADR 0141).**
     `_resolve_existing_cataloged_person_id`
     (`backend/app/post_summary_ingestion.py`) is documented as never
     inserting a `cataloged_person` row (ADR 0009 — "a missing catalog row
     stays unbound rather than inventing a person"). Organization actors do
     go through `get_or_create_corporate_entity` (ADR 0010), but that
     function's `hierarchy_inference_client`/`verification_client` default to
     Null clients whenever no live orchestrator/SearXNG corroboration is
     wired — in that state it can only match an *already-cataloged* entity,
     never create one, so an organization actor stays unlinked too. The
     resulting "카탈로그 미연결" label is a correct, honest reflection of
     missing live infrastructure, not a code defect — but it gave the
     reader no way to tell "not yet processed" from "no live orchestrator in
     this environment" from "verification declined to corroborate." ADR 0141
     and migration `0134_catalog_unresolved_reason.sql` add a closed reason
     vocabulary (tied candidates / no live client / not corroborated / no
     catalog entry) captured at write time on `post_summary_role`, on both
     the primary actor link and the separate affiliated-organization link
     (the field the shipped label actually renders next to); the frontend
     (`RoleEvidence.tsx`, `App.tsx`) now shows the specific reason instead of
     the flat label, falling back to today's behavior on historical rows
     with no recorded reason. Covered by `RoleEvidence.test.tsx`,
     `App.test.tsx`, `tests/test_tied_organization_no_create.py`, and
     `tests/test_migration_replay.py`.
  2. **Job title and relationship type are conflated into one free-text
     field.** Remaining: `RoleResponsibility.responsibility` is still one
     source phrase. The reader now sees fail-closed next-action copy
     (`gluedRoleRelationshipNextAction`) instead of an inferred catalog
     relationship. Splitting job title from `relationship_type_code` still
     needs a reviewed `POST_SUMMARY_CONTRACT_VERSION` bump and is not done
     here.
  3. **Planned-facility events don't become project/entity evidence, and no
     operator inference exists — ADR drafted in this worktree, implementation
     still open by design.** A key event whose text names a specific planned
     facility (e.g. "X 충전소 구축 계획") produces `key_events`/
     `key_event_details` prose only — it is never checked against
     `post_project_mention`/`ProjectEvidence`, so the facility itself is
     not recognized as an entity, and no relationship is inferred between it
     and the organization the post's own R&R evidence says would operate it.
     This is a deliberate ontology-design question, not a quick fix:
     inferring an "operates" relationship from event-adjacent context risks
     inventing a fact the source text does not state, which is exactly what
     ADR 0010's fail-closed design exists to prevent. ADR 0142 proposes
     reusing the existing `post_summary_semantic_relationship` channel
     (rather than a new table) with one new closed predicate,
     `lw_plans_to_operate`, whose name itself carries the "announced intent,
     not standing fact" distinction, plus a conservative admission rule
     (source names both actor and facility in the same evidence span; the
     facility is independently backed by a `post_project_mention` row, not
     just event prose). Per its own text, ADR 0142 authorizes only the
     follow-up implementation shape; the `POST_SUMMARY_CONTRACT_VERSION`
     bump, prompt change, and fixture-backed tests remain separately
     reviewed work, not something this ADR performs itself.
  Two related, safely-scoped UI fixes shipped alongside this finding: R&R
  rows now nest under their affiliated organization's row instead of each
  repeating "· 소속: X" as flat text (`buildRoleTree`, `frontend/src/App.tsx`),
  and `key_events` sharing the same `project_name` now nest under one
  heading instead of repeating the project name as a flat prefix
  (`groupKeyEventsByProject`). Neither fix touches extraction, the summary
  contract, or catalog creation. Leftover closest/farthest clicks now land
  on the named Post quality criterion (`focusCriterionCode`, ADR 0049);
  kind×status next actions remain exact (ADR 0135). Missing leftover cells
  stay out of the Gabriel factorization (not treated as zero). The planned
  “operates” inference and R&R contract split remain open.
- **Customer master "customer tree" — source gap closed, runtime evidence open:**
  ADR 0125 added explicit own/granted/unclassified scope facets and admitted
  organizations observed through already-authorized posts without widening
  post access. ADR 0137 now promotes a repeated source customer key only after
  collective Judge, corroboration, and unique catalog evidence, then links the
  same customer across its supporting posts without changing the posts'
  authorization owner. The remaining gap is an authorized external import and
  rendered browser audit proving the resulting hierarchy, aliases/former names,
  and source-system collision behavior on non-identifying aggregate evidence.
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
  model. Live inspection on 2026-08-23 found that the upstream TEPP repository
  currently publishes strict `AnalysisRunRequest` / `AnalysisRunAccepted` DTOs
  and outbound HTTP exchange builders, but no executable HTTP server, completed
  measurement response contract, snapshot-evidence ingest, or production
  estimator entrypoint. The current request carries only a snapshot digest, so
  a service cannot calibrate the underlying observations without a new
  purpose-bound evidence artifact/API. `TEPP_TRANSPORT_URL` alone therefore
  cannot make measurement available. Close this in TEPP first with an ADR and
  PRD update covering authorized evidence transfer, Rust estimator authority,
  durable lifecycle/idempotency, completed-result provenance, and CPU/GPU
  parity; then pin that service in Compose and prove a persisted
  `analysis_run_tepp_result`. An accepted-envelope shim is explicitly not an
  acceptable substitute.
- **TEPP temporal context — source-connected, local runtime proven:** TEPP's
  LineageWeave consumer stack publishes `TemporalContextRequest` v1 and the
  executable loopback sidecar is proposed in upstream TEPP PR #186 at exact
  head `169faa164ee6418f5ccce45a4fa8b244df700af2`. The Compose sidecar and backend
  client were exercised locally with its wire-compatible predecessor
  `f22ac1b93c877312b827479c61d23b98d21d1903`:
  cutoff-safe opaque events returned deterministic `before` relations with the
  explicit `association_not_causal` boundary. Global Ask now consumes that
  exact wire contract, validates the complete response, and drops the channel
  on any transport or shape failure. Production remains open until PR #186 is
  protected-merged and a pinned release image replaces the sibling-source
  Compose build; this does not change the calibrated-measurement gap.
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
- **Lineage coverage — per-post reason (ADR 0143) and corpus-wide aggregate
  both fixed in this worktree:** the persisted graph has 1,308
  post-lineage edges across 1,929 participating posts, while the bounded
  current view exposed one edge and some focused posts had no component.
  `GET /api/lineage?post_id=...` now reports `isolation_reason` --
  `"no_relation_found"` when the post had other visible posts in its
  `reconstruct_group_key` group and reconstruct still produced no edge, or
  `"no_comparison_group"` when it was the only visible member of its group
  (`visible_lineage_graph`, `backend/app/lineage_ingestion.py`).
  `EventLineageSection` (`frontend/src/App.tsx`) shows the specific reason
  instead of one flat "No linked posts yet." Note that `thread_group_key`
  presence is not itself evidence of a real thread: `scripts/import_postgresql_posts.py`
  back-fills it from the import's own process-unit code whenever the source
  mapping has no explicit thread column, so group *size* (not key presence)
  is the signal this feature actually uses. Independent of, and does not
  duplicate, the separate open PR fixing `rebuild_lineage()`'s
  adjudication-client wiring (a different bug: the highest-weighted
  comparison channel not running during corpus-wide rebuild).
  `POST /api/lineage/rebuild` now also returns a `coverage` breakdown
  (`total_posts`, `posts_with_edges`, `posts_no_relation_found`,
  `posts_no_comparison_group`) computed by the same group-size logic,
  aggregated corpus-wide instead of per-post -- an operator running a
  rebuild gets an honest coverage summary instead of a bare edge count.
  No frontend display was added for this (the rebuild button today shows
  no result at all, not even the existing `edge_count`); building an
  operator-facing rebuild-health panel is separate UI/UX work, not part
  of this backend-aggregate fix.
- **Lineage hidden-sibling-edge leak — closed (2026-08-25):** a peer
  session's review of a divergent history line (PR #493) found that
  `visible_lineage_graph`'s connected-component BFS built its neighbor
  graph from every `post_lineage_edge` row before filtering by ABAC
  visibility, so an edge to a hidden sibling post could make an
  otherwise-isolated focused post look connected -- masking
  `isolation_reason` and leaking the existence of a hidden relationship
  through its absence. Both edge endpoints must now be visible before an
  edge counts toward the component. Ported the fix here (this branch's
  canonical `isolation_reason` implementation, ADR 0143) rather than
  merging #493's parallel reimplementation. Regression test proves RED
  (pre-fix: focused post renders as connected) to GREEN.
- **Event Lineage links topically/causally unrelated posts within a
  mega-group fallback — evidence-backed (2026-08-24), root-caused against
  a live corpus:** a reader-reported case (Event Lineage popup on a
  charging-station-construction post) showed a parent and a child edge to
  two posts about unrelated engineering topics (a volume-unit change
  request; an unrelated steering-mechanism note) with `fused_score` 0.40
  and 0.45 -- just above `DEFAULT_MIN_FUSED_SCORE` (0.3). Traced to two
  compounding causes, neither yet fixed:
  1. **Grouping fallback is too coarse.** `reconstruct_group_key`
     (`backend/app/lineage_ingestion.py`) falls back to `process_unit_id`
     when `thread_group_key` is empty (documented, intentional design --
     it must match what `GET /api/lineage`'s display grouping uses, per
     ADR 0143 above). For the reported post, that fallback groups it with
     21,670 other posts spanning three-plus years -- an entire team's
     inbox, not a thread -- so `reconstruct()`'s `DEFAULT_CANDIDATE_WINDOW`
     (50 temporally-preceding records) draws candidates from a
     topically unbounded pool.
  2. **The text channel is not semantic.** `text_similarity_score`
     (`lineageweave/channels.py`) is `difflib.SequenceMatcher` character-overlap
     ratio on raw titles, not embeddings -- its own docstring already
     names this as a stand-in pending a real embedding channel. With no
     `AdjudicationClient` configured for the rebuild path (the `llm`
     channel drops out and `temporal`/`secondary_key`/`text` renormalize
     to 0.25/0.25/0.50), two same-length Korean titles sharing common
     particles and a close timestamp can clear the 0.3 floor on
     temporal-proximity plus coincidental character overlap alone, with
     `secondary_key_match_score` contributing 0 (empty
     `secondary_grouping_key` on both posts in the reproduced case).
  Fix (1) is an architecture decision (grouping-key redesign) needing its
  own ADR before implementation, not appropriate to improvise solo --
  **remains open.**
  Fix (2) **implemented, open PR (2026-08-24, #538, ADR 0190), stacked on
  PR #434:** `reconstruct()` now batch-embeds every record's label once up
  front via `lineageweave/embedding_client.py` and scores the `text`
  channel with cosine similarity for any pair with vectors, falling back
  to the prior difflib ratio otherwise -- reusing the existing
  `_embedding_client()` factory already wired for post-content search
  embeddings. Threaded through the same call chain as PR #434's
  `adjudication_client` (`lineage_edge_specs` -> `rebuild_lineage` ->
  the analysis-run worker -> `main.py`'s three call sites ->
  `scripts/import_postgresql_posts.py`). A new regression test
  (`tests/test_reconstruct.py::test_embedding_channel_overrides_a_difflib_false_positive`)
  reproduces the reported false-positive synthetically. Independent of,
  and does not duplicate, PR #434 (restores the highest-weighted `llm`
  channel for the corpus-wide rebuild path) -- the two PRs fix different
  channels of the same fusion and compose without conflict; cause (1)
  remains open after both merge.

  **Post-review correction on PR #538 (2026-08-24):** the first
  implementation mapped `cosine_similarity`'s output via
  `(cosine + 1) / 2`, the textbook transform for a similarity spanning the
  full `[-1, 1]` range. Real sentence embeddings do not span it -- they
  occupy an anisotropic cone (Ethayarajh, 2019), so two genuinely unrelated
  texts from an actual provider score a modestly *positive* raw cosine in
  practice, essentially never near -1. The remap inflated that unrelated
  baseline to roughly 0.5-0.65, a "weak positive" that could still clear
  `DEFAULT_MIN_FUSED_SCORE` combined with temporal proximity -- silently
  reproducing this exact gap through the embedding channel instead of
  difflib. Fixed by clamping the raw cosine into `[0, 1]` instead of
  remapping it (matches the unremapped STS evaluation convention, Reimers &
  Gurevych, 2019). Caught by Devin Review before merge; the regression test
  was also strengthened to use a realistic low-positive cosine (0.05)
  rather than an unrealistic exact -1.0, since the old remap bug would not
  have failed the original -1.0 fixture.

  **New, still-open calibration observation surfaced by that review:** for
  two records roughly an hour apart, `temporal_score` alone
  (`1 / (1 + gap_days)`) already contributes close to
  `DEFAULT_MIN_FUSED_SCORE` once weights renormalize without an `llm`
  channel, so *any* weakly-positive text score -- clamped cosine included --
  can still tip a temporally-close, topically-unrelated pair over the
  floor. Changing `temporal_score`'s steepness or
  `DEFAULT_MIN_FUSED_SCORE` is a calibration decision, not something to
  fold into PR #538 -- **remains open**, tracked here for whoever picks up
  the reconstruction-fusion tuning work next.

  **Measured against the live corpus (2026-08-24), evidence for the
  calibration decision above:** of 41,257 persisted `post_lineage_edge`
  rows, 148 (0.36%) sit at `fused_score < 0.35`, i.e. within one difflib
  coincidence of the 0.3 floor. A spot sample of the lowest-scoring edges
  (case labels, not real source content) confirms the same failure shape
  as the originally reported bug -- pairs of business posts about clearly
  unrelated subjects (a sales-visit note paired with an unrelated dealer
  visit; a market-trend summary paired with an unrelated internal lecture
  summary; a quality-inspection note paired with an unrelated audit note)
  -- clustering at a 38-46 hour parent-child gap, not the ~1 hour used in
  PR #538's synthetic regression test. These 41,257 edges predate PR
  #538/#549's embedding channel (built under difflib-only or
  difflib-plus-clamped-embedding-not-yet-rebuilt); re-running
  `POST /api/lineage/rebuild` under the current code and re-measuring this
  148-edge population is the natural verification step for whoever picks
  up the calibration work, before deciding whether `temporal_score` or
  `DEFAULT_MIN_FUSED_SCORE` actually need to change.

  **Related, smaller diagnosability gap found while measuring this --
  closed (2026-08-24, ADR 0195, open PR):** `post_lineage_edge` persisted
  only `parent_post_id`, `child_post_id`, `fused_score`, `created_at` --
  `Edge.channel_scores` (the per-channel breakdown `reconstruct()` already
  computes) was dropped at `persist_lineage_edges`
  (`backend/app/lineage_ingestion.py`) and never written, so nothing --
  not even an operator with database access -- could tell *why* an edge
  formed without re-running reconstruction offline. Fixed: migration 0195
  adds a nullable `channel_scores jsonb` column;
  `persist_lineage_edges` and `scripts/seed_demo_data.py`'s parallel
  psycopg2 insert path both now write it. Covered by
  `tests/test_lineage_ingestion.py::test_persist_lineage_edges_writes_the_channel_score_breakdown`
  and its empty-object sibling. No API/UI surface added -- direct
  database inspection only, matching the scope of this gap.

  **Process note (2026-08-24): a stranded-fix incident, recovered.** PR
  #538 merged into PR #434's branch at `23:39:36Z`; the cosine-clamp fix
  above was pushed to #538's branch at `23:42:28Z`, three minutes after
  close, so it never reached #434's branch and looked like GitHub API lag
  for a time. Root cause: merges into a *non-default-branch* PR (a stacked
  PR merging into another PR's branch, not into `main`) are not gated by
  the org's 2-approving-review ruleset -- only `main` is -- so a fast
  merge-on-green-checks pass can land before a reviewer's last-minute fix
  commit arrives. Recovered by cherry-picking the stranded commit onto
  #434's post-merge tip as PR #549. No data or code was lost; flagging the
  pattern here since it can recur on any stacked PR in this repo.
- **Provider-boundary exception diagnosability — partially closed
  (2026-08-25, issue #361):** the 10 fail-closed `except Exception`
  catch-alls across `backend/app/main.py` (Global Ask, per-post chat,
  keymen extraction, entity-relationship verification, evaluation,
  summary regeneration, commitment derivation) now log the exception
  server-side (`logger.exception`, stdlib `logging`) before returning
  the same stable customer-facing 503; a caplog-based test proves an
  unexpected defect (not a classified provider error) reaches the logs
  with a traceback. **Correlation/request IDs closed in this worktree
  (2026-08-24):** a stdlib-only `contextvars.ContextVar` plus a
  `@app.middleware("http")` handler stamps a server-generated UUID4 onto
  every request (returned as the `X-Request-Id` response header, never
  echoing an inbound client-supplied value back into logs -- a
  log-injection vector this design does not need to accept); a
  `logging.LoggerAdapter` subclass wraps the module's one `_logger` so
  every one of the 10 call sites above picks up the active request ID
  automatically, without a per-site change.

  **Related finding, not fixed here (2026-08-24):** verifying the change
  against the full suite surfaced a pre-existing flake in
  `backend/tests/test_api.py`'s own token handling, unrelated to this
  correlation-ID work. `demo_analyst_token` is a `scope="module"`
  fixture (325 call sites across 378 tests in this one 6,228-line file)
  that mints one real Keycloak access token for the whole module; the
  realm's `accessTokenLifespan` (`docker/keycloak/realm-export.json`) is
  900s. A full-module run that takes longer than that -- observed at
  1435.9s (11 failures, all "invalid access token" or an auth-before-
  permission 401) under today's heavy multi-session machine load, versus
  43.5s for 4 of the same tests re-run in isolation with a fresh token --
  fails every test that happens to execute after the 15-minute mark, not
  because of what those tests exercise. Not fixed in this checkpoint:
  the fixture is shared by nearly the entire file and any change (scope,
  a lazy-refresh wrapper) needs its own careful design and coordination
  given how many concurrent sessions touch this file; a quick reduction
  to per-function scope would also add one Keycloak round trip per test.
  Flagging so a future "test X is flaky" report against this file checks
  elapsed wall-clock time before assuming a code regression.

  Not yet done on the diagnosability gap itself: OpenTelemetry metrics
  distinguishing known-provider-unavailable from internal-defect, and
  bounded-cardinality alerting -- those still need the new-dependency
  decision this checkpoint didn't force through.
- **Per-post Ask citation rollback — closed (2026-08-25, issue #362
  sibling gap):** `post_ask_history.py` (ADR 0136) was scaffolded from
  `global_ask_history.py` before the #362 atomic-reauthorization fix
  existed, and never received it: `persist_turn` had no citation
  reauthorization step at all, so a post that lost authorization between
  source-gathering and commit had its facts served in the
  `POST /api/posts/{post_id}/chat` answer and its citation row persisted
  regardless. Added the identical `_ensure_citations_visible` /
  `PostAskEvidenceChanged` -> 503 pattern already proven for Global Ask.
  Regression test confirmed RED (a revoked citation's facts served with
  a 200) before GREEN.
- **Indirect-relationship hidden-sibling bridge — closed (2026-08-25):**
  `find_linked_post_ids` (ADR 0018, used by `read_post_lineage`,
  `gather_chat_sources`, and `load_five_w1h_slots`) expands to every
  post mentioning the same person as the focus post before walking their
  shared org/team/customer entities via `load_visible_subgraph` -- but
  that sibling-post expansion was never ABAC-filtered. A hidden sibling's
  own entity mention could bridge to an unrelated visible post through
  shared entity membership, fabricating an "indirect" relationship (and
  a chat-source citation slot) whose only real basis was content the
  account cannot see; the hidden sibling itself was always correctly
  excluded from output, only its influence on other results leaked.
  Found by an Explore agent hunting for the "unfiltered-then-filtered"
  pattern after two earlier fixes this session had the same shape.
  Filtered siblings by `can_see_post` before they can seed the entity
  graph, at all three call sites. Regression test confirmed RED before
  GREEN.
- **Board pagination total_count overshoot — closed (2026-08-25):**
  `GET /api/posts`'s `total_count` came from `count(*) over()`, a window
  function that only rides along on rows surviving the query's own
  `OFFSET`/`LIMIT` -- an offset past the last matching row returned zero
  rows and silently reported `total_count=0` even though matches
  existed (a routine "user paged past the end" or "a filter change
  shrank the result set" scenario). Found by an Explore agent hunting
  for a different bug class after the ABAC-leak well ran dry.
  Extracted the query's predicate into a shared variable so a small
  fallback `count(*)` query (used only when the main page comes back
  empty) can reuse it without duplicating ~170 lines of SQL. Regression
  test confirmed RED (reported 0 instead of the real count) before
  GREEN.
- **Admin Panel i18n gap — partially closed, second slice
  (2026-08-25):** a key-set diff of `i18n.ts`'s four non-English locale
  blocks found 117 keys that exist only in `ko` (added for Korean,
  never mirrored to zh/ja/vi) -- `t()` silently falls back to the raw
  English key when a translation is missing, and no test catches it
  since the existing i18n test only checks curated key lists a
  component's keys must be manually added to. First checkpoint closed
  the 20 keys referenced as JSX `t("...")` literals. This checkpoint
  found and closed 33 more: AdminPanel.tsx's endpoint-catalog and
  nav-group metadata is defined as data (`ADMIN_LNB_GROUPS`,
  `ADMIN_OPERATIONS` label/description/note fields, plus two keys --
  `Rankings`, `Workspace` -- written as unquoted object keys) rendered
  via `t(item.label)`, so a literal-`t("...")` grep missed them
  entirely; found instead by grepping the component's own data arrays.
  Extended the `adminPanelLabels` parity test to all 53 of AdminPanel's
  live keys. The remaining ~64 keys (used by other, not-yet-audited
  components -- App.tsx alone accounts for most of them) are still
  ko-only and not claimed fixed -- tracked as the next slice, not
  attempted this checkpoint given the translation-quality risk of
  rushing many keys without a dedicated review pass.
- **Admin Panel i18n gap — third slice, closed (2026-08-24):** two
  concurrent sessions split the remaining ~68 ko-only keys by domain
  to avoid an `i18n.ts` merge collision. This checkpoint closed the 22
  Board/R&R keys: the Board hand-off prompt (`Open in Board`, `Board
  advanced review`, the existing-Board-owns-this-post explanation),
  the R&R semantic-relationship predicate labels (`Responsible for`,
  `Supports`, `Organization member/unit of`, `Sub-organization of`,
  `Explicit semantic relationships`), the evidence workspace, and
  AdminPanel's `Account`/`Permissions`/`routes` fields, verified with
  translations cross-checked against already-established terminology
  for `Board`/`Organization`/`Summary`/`Workspace` elsewhere in the
  file. A sibling session's concurrent slice closed the 30
  source-lineage-hints-panel keys (`sourceLineageHintLabels` in
  `i18n.test.ts`); both slices merged on `feat/board-source-detail-
  state-filter` (PR #490) with one duplicate key (`Lifecycle vector`,
  independently translated by both sessions) resolved in favor of the
  source-lineage-hints session's copy, since it is the key's actual
  domain (`post.source_lineage_hints.lifecycle_vector`,
  `App.tsx:3182`). Full frontend suite (369 tests), lint, and build
  pass after the merge. Any keys outside these two domains remain
  open.
- **Component/story/test triplet gap — closed for AdminPanel, FiveW1H,
  icons (2026-08-24):** a sweep of `frontend/src/components/` for the
  repo's component+story+test convention found three components
  shipped without a `.stories.tsx`: `AdminPanel.tsx`, `FiveW1H.tsx`,
  and `icons.tsx`. Added stories covering AdminPanel's overview,
  account-scope (with and without affiliations, with a still-loading
  `currentUser`), and tenant-settings sections, and FiveW1H's loading,
  populated-evidence, and all-dimensions-empty states, each with
  play-function assertions matching the repo's existing story
  pattern; AdminPanel's settings-save button is deliberately left
  unclicked in its story since it performs a real `updateTenantConfig`
  network call this story does not mock. `icons.tsx` is three
  prop-less SVG glyphs with no logic to assert on, so it gets one
  gallery story rather than a dedicated unit test.
  `SourceResearchPanel.tsx`'s missing story and
  `LeftoverPairButton.tsx`'s missing test are left open -- both files
  were mid-edit by concurrent sessions on this branch at the time of
  this checkpoint.
  **`SourceResearchPanel.tsx` closed (2026-08-24):** the peer session
  editing it finished and confirmed clear. The component fetches from
  `../api`'s module-level `fetch` on mount, not a prop, and this repo
  has no MSW addon -- rather than skip coverage or add MSW just for one
  story, stubbed `window.fetch` per story via Storybook `loaders`
  (restored after each story), which exercises the real component code
  path instead of faking it. Covers populated results (supported +
  not-enough-information leads), the empty "no persisted research yet"
  state, the read-only variant with the Research-sources button hidden,
  and the fail-closed 503 path rendering `role="alert"` with a Retry
  action. `LeftoverPairButton.tsx`'s missing test remains open -- still
  the leftover-map PR stack's territory, not touched here.
- **Leftover pair next-action jargon — closed (2026-08-24, PR #490
  `154a13ef`):** ADR 0049 already names `Open {post}, then read Post quality
  criterion {criterion}.` Origin leftover copy still appended `This pair sat
  closest/farthest after main effects.` `leftoverPairNextAction` now matches
  the ADR sentence only. Evaluation keeps saved IRT scores when the
  orchestrator or evaluation channel is down, instead of hiding them behind
  the dropped-channel diagnosis. Vitest leftover-pair and evaluation-503
  tests cover both; leftover Storybook scenes read the same next-action
  helper.
- **Customer Master relationship-network ABAC scope-widening leak —
  closed (2026-08-24):** a `lineageweave-bug-sweep` Workflow finder
  found that `read_customer_master` (`GET /api/customer-master`,
  ADR 0125) passed `entity_ids` -- the endpoint's broad Customer Master
  listing, which includes entities the account merely *observes*
  (mentioned in a visible post, never actually affiliated with) -- into
  `fetch_relationship_network` as its ABAC scope. That function's SQL
  treats its `corporate_entity_ids` parameter exactly like
  `_can_see_post`'s `post.corporate_entity_id = any($1)` clause, so the
  broader listing let a private post owned by an observed-only entity
  leak its counterparty classification into `relationship_network`. The
  pre-existing giant Customer Master contract test did not catch this:
  its `"Private Other Corp" not in network` assertion passed only
  incidentally, because the demo-vs-real-data source-context heuristic
  happened to exclude the relevant fixture post. Scoped the call to
  `account.corporate_entity_ids` (the account's own real affiliations),
  net of the same synthetic-only/stale-demo-grant exclusion the entity
  tree above it already applies once real source context exists -- an
  initial fix using the raw affiliation list still leaked a stale demo
  grant back in, caught by the existing giant test after the fix, and
  corrected before commit. A new focused regression test defeats the
  eligibility heuristic on purpose (giving both the mentioning and the
  mentioned posts real source context) to isolate the ABAC-scoping
  behavior; RED confirmed pre-fix, GREEN after, full suite (1032 passed,
  17 skipped) shows no regressions.
- **SourceResearchPanel stale-fetch race — closed (2026-08-24):** the
  same `lineageweave-bug-sweep` Workflow finder that found the Customer
  Master leak above also found `SourceResearchPanel.tsx`'s `load`
  callback had no request-id guard on its `fetchPostSourceResearch`
  call. A fast `postId` change (or the `runResearch` -> `load` refresh
  racing a still-in-flight initial load) could let an earlier post's
  response resolve after the panel had already moved to a newer post,
  rendering the wrong post's persisted evidence. Added the same
  `requestIdRef` counter/compare guard already used elsewhere in
  `App.tsx` (`historyRequestIdRef`, `relatedRequest`, `postsRequest`).
  Regression test confirmed RED (a stale response's lead rendered after
  the postId change) before GREEN; full frontend suite 361 passed, lint
  clean.
- **Source lineage combination i18n gap — closed (2026-08-24):** the
  Source Detail popup's "Source lineage combination" panel -- the badge,
  field-presence list, and the nine `commercial_context_code` labels
  plus four `SOURCE_LINEAGE_FIELDS` labels computed in
  `frontend/src/sourceLineageHints.ts` -- was ko-only across 29 keys;
  zh/ja/vi silently fell back to raw English. A per-locale re-run of
  the key-diff (per-locale missing-from-ko, not "missing from all
  three") found all three locales missing the identical 68-key set,
  confirming no asymmetry to track separately. Scoped this checkpoint
  to the 29 keys belonging to this one panel (the other ~39 are a
  separate Board/R&R/customer-identity-search slice). Added zh/ja/vi
  translations and a curated `sourceLineageHintLabels` parity test.
  Confirmed RED (all three locales fell back to English) before GREEN.
  Full frontend suite: 365 passed, lint clean, tsc clean.
- **i18n ko-only key backlog — closed (2026-08-24):** the remaining
  17 ko-only keys after this checkpoint's source-lineage-hints slice
  and a peer session's concurrent 21-key Board/R&R slice
  (`171c869b`/`f238ef49`/`b8d69320`) belonged to the role-evidence
  panel (quantitative/normalization evidence, connected/negated
  clues, subject/object type) and the Customer Master "find source
  customer code" search dialog. Verified via a per-locale key-diff
  (missing-from-ko independently for zh, ja, vi, not "missing from
  all three at once" -- the bug in an earlier version of this
  checkpoint's own diff script) that all three locales were missing
  the identical 17-key set. One additional key in that set,
  `"Present fields"`, was confirmed via grep to have no live
  `t("...")` call site anywhere in the frontend -- dead code, left
  untranslated since there is no reader-facing gap to close. Added
  zh/ja/vi translations for the other 17 and a new curated
  `roleEvidenceAndCustomerIdentitySearchLabels` parity test.
  Confirmed RED (all three locales fell back to English) before
  GREEN. Full frontend suite: 373 passed, lint clean, tsc clean. This
  closes the entire i18n ko-only backlog opened by the Admin Panel
  fix earlier in this document -- `t()` now has no live English
  fallback across zh/ja/vi.
- **Frontend stale-fetch-response races — 4 closed, 1 of 5 backend
  findings closed, 4 backend findings tracked open (2026-08-24):** a second `lineageweave-bug-sweep`
  Workflow run this hour (4 finders pointed at post_summary/keyman,
  evaluation/ticket, calendar/tenant-settings, and frontend
  AdminPanel/Board subsystems not yet audited) confirmed 9 real
  findings and correctly rejected 1 false positive (an
  ActivityPanel fetch the verifier traced back to already being
  guarded). Closed the 4 frontend findings this checkpoint, all the
  same "unfiltered-then-filtered"/stale-response shape already fixed
  in `SourceResearchPanel.tsx` earlier this session: the post detail
  popup's 8-fetch-plus-bookmark fan-out (`PostDetailPopup`, reused the
  effect's existing but inconsistently-applied `disposed` flag),
  `ReportsPanel`'s period/grouping fetch and rebuild action,
  `IssueTicketPanel`'s per-post ticket list, and `CustomerMasterPanel`'s
  hint-code search -- all via the same `disposed`/`requestIdRef` guard
  pattern established earlier. A new deferred-response test harness
  addition (`deferCustomerMasterHintCode`/`releaseCustomerMasterHint`
  in `App.test.tsx`'s `stubBackend`) proved the Customer Master fix
  RED-to-GREEN; RED initially passed for the wrong reason (awaiting
  only the raw mocked `fetch()` promise left `response.json()` and the
  component's own `setState` + re-render unobserved) until an explicit
  short delay was added before the final assertion. Full frontend
  suite: 374 passed, lint clean, tsc clean. The other 5 confirmed
  findings are backend and lower severity. **Closed at the next hourly
  checkpoint (2026-08-24):** `post_summary.py`'s
  `_parse_plain_summary_response` now returns the declared 3-tuple
  (`summary, key_events, key_event_details`) instead of a 2-tuple on
  its no-`KEY EVENTS:`-marker branch -- previously a provider response
  with real summary prose but no marker line crashed
  `summarize_with_hints`'s destructuring assignment with a generic
  `ValueError: not enough values to unpack` instead of the caller's own
  descriptive one (externally invisible today only because
  `read_post_summary` blanket-catches `ValueError`). Regression test
  confirmed RED (`not enough values to unpack (expected 3, got 2)`)
  before GREEN. **Remaining 4, not yet attempted:** (2) `_formalize_korean_summary`'s hardcoded Korean
  verb-ending ladder misses common past/perfective forms
  (`-았음/-었음/-였음`, contracted `됐다`, nominalized `됨`), producing
  grammatically broken doubled endings like "체결되지 않았음입니다." in
  persisted, reader-facing summaries; (3) `keyman_ingestion.py`'s
  `_upsert_person` lookup has no `ORDER BY`, so an untitled mention can
  bind to an arbitrary pre-existing same-name person when duplicates
  exist; (4) concurrent re-evaluation writes in
  `post_evaluation_ingestion.py` are not transactional, so
  `GET /api/posts/{id}/evaluation` can serve a torn mix of two
  different judge runs; (5) `issue_ticket_ingestion.py`'s
  `upsert_commitment_ticket` has an unguarded check-then-act race that
  can create duplicate open commitment tickets for the same post.
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
- **`main`'s frontend build was broken — fix in flight on PR #426
  (2026-08-24):** `frontend/src/App.tsx` fails `tsc -b` at `main`'s head (a
  dead import plus an unguarded `AdminPanel` render passing a
  `string | undefined` OIDC `accessToken` into a `string`-typed prop), so
  every PR branched from `main` inherits a spurious "Frontend lint, test,
  build" failure regardless of its own diff -- confirmed against PR #547
  (a `docker-compose.yml`-only change). Opened a fix as PR #550, then
  closed it: a peer session flagged that this exact root cause already had
  two prior fixes, PR #456 (closed as duplicate) and PR #426 (open,
  auto-merge armed). Comparing diffs, #426's fix is the correct one, not
  merely an earlier one -- it root-causes rather than symptom-patches:
  the dead import wasn't dead code to delete, it was the login button
  computing `window.location.pathname + window.location.search` inline
  instead of calling the already-imported `returnUrlFromLocation()` (which
  also preserves the URL fragment) and persisting it via
  `rememberOidcReturnUrl()` for the OIDC redirect round-trip -- #550's fix
  silenced the compiler error but left that return-URL-preservation
  feature broken. #426 also correctly deletes the `AdminPanel` render as
  unreachable dead code rather than merely guarding it. Any PR still
  failing "Frontend lint, test, build" with the same `TS6192`/`TS2322`
  errors needs a rebase onto `main` after #426 merges, not a code change.

### 5.z PR #463 audit port (2026-08-24) — items re-verified open on this branch

PR #463's 2026-08-23 audit targeted the pre-restructure version of this
document and could not merge; most of its findings are already fixed or
tracked above. These six were re-verified against this branch's current
head (`aab4a6eb`) and remain true and previously untracked here:

- **DAG keyboard focus ring is very weak**: `.lineage-dag-node:focus`
  strips the native outline (`App.css:2201-2203`, `outline: none`) and
  relies on a same-color stroke bump — insufficient focus indication
  (WCAG 2.4.7). Open.
- **Rendered post-body tables have no header semantics**: `PostBody.tsx`
  emits only `<td>` (zero `<th scope>` / `<caption>`); the `<th>` support
  merged in PR #303 was silently dropped by the `ef6f5a5f` whole-file
  rewrite. Open (regression).
- **Unregistered i18n aria-label key**: `tf("Affiliates of {name}")`
  (`App.tsx:5274`) has no entry in any ko/zh/ja/vi block of `i18n.ts`, so
  the customer-entity-tree label always renders in English. Open.
- **Drafted `CHANGELOG.d/` fragments (2.12.7 through 2.21.1) were never
  compiled** into `CHANGELOG.md` — the release prose exists; the compile
  step never ran. Open (mechanical).
- **The durable post-content ingestion queue (ADR 0098) shipped with no
  CHANGELOG entry** (no `CHANGELOG.md` line, no `CHANGELOG.d/` fragment) —
  dropped in the `ef6f5a5f` squash of PR #347. Open.
- **PR #460's fix is missing from `CHANGELOG.md` `[Unreleased]`.** Open;
  belongs with the fragment-compilation pass above.

## 6. Next acceptance loop

1. Isolate the dirty continuation on a current-main branch without overwriting
   concurrent work, then rerun unit/backend files with bounded diagnostics,
   full frontend checks, Storybook, and authenticated desktop/mobile Ask and
   drawer flows against images built from that exact source.
2. Land the central coverage-sandbox repair, rerun the four exact-head coverage
   change requests on #349/#355/#383/#417, and resolve only findings that remain
   valid on each current head.
3. Obtain two independent approvals including an approval after the final push.
   Stack leftover-map PRs #533/#532/#531/#530/#529/#527 onto #426/#490 rather than
   forking protected `main` independently. Refetch and revalidate every
   sibling after each protected merge. Do not claim a protected-main merge
   without the merge SHA.
4. Validate the ADR-backed anchor source-field policy on live PostgreSQL and
   add the missing Ask/mobile Storybook scenes. Reproduce private cases only as aggregate, non-identifying
   runtime evidence and preserve `unavailable` explicitly.
5. Continue issue work in evidence-integrity order: #362, #359/#358, #361,
   #372/#341, #336, then #274. Do not self-approve, bypass protection, force
   push, or claim a merge without the protected merge SHA.

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

---

## Appendix: independently-maintained snapshot from `main` (merged 2026-08-24)

The sections below accumulated on `main` while this branch's copy of
this file (above) was independently maintained -- `main` was frozen
for hundreds of commits and only just had a build-break fix merged
(PR #426), which is why the two copies diverged this far. Kept as a
distinct appendix rather than interleaved, since the two documents'
section numbering and gap-tracking conventions differ; reconciling
them into one running log is follow-up work, not done in this merge.

> Audit snapshot: 2026-08-24 03:09 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.
> Identifying post identifiers, organization names, and production record keys
> must never appear in this file.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 54 open PRs and 19 open issues. The audited open
delivery set (#426, #490, #496, #507, and #515) had zero approving reviews. Branch
protection / rulesets require two independent approvals, resolved review
threads, and last-push approval; the authenticated GitHub identity that authors
these PRs cannot self-approve.

Protected `main` currently has two defects that poison downstream work:

1. Unauthenticated login rendered `AdminPanel` with an undefined access token,
   so `tsc -b` failed on `main`. LineageWeave#426 owns the shared login repair
   (OIDC return-URL helpers; no admin settings before authentication) and the
   ontology Pages stack. #494's demonstrably unique optional-extra collection
   is merged into #426 only and remains dependent on that parent reaching
   protected `main`.
2. This file on `main` listed identifying post identifiers, which ADR 0001
   forbids. This head removes them from the current tree and binds gaps to the
   current PR/issue inventory. The identifiers remain reachable in protected
   Git history pending an approved incident/history-remediation process. It
   does not duplicate #426's login patch.

Recent protected-default-branch and org-control-plane evidence:

| PR | Exact observed head | Current gate evidence |
| ---: | --- | --- |
| #347 | merged as `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` | Korean UI standards on the current protected head |
| ContextualWisdomLab/.github #1248 | merged | central Strix scope repair is available to subsequent reruns |
| ContextualWisdomLab/.github #1245 | `92624300414b19dbed0f96a0295b1ac516181b4b`; auto-merge armed; blocked on independent review | retry/defer shared GitHub App installation rate limits so OpenCode dispatch is not starved |
| ContextualWisdomLab/.github #1258 | `9b5dba9f558d20dbb651b409ea9fa54a865e3405`; auto-merge armed; blocked on independent review | `--trust-lockfile` only on pnpm 11.3+; Jest keeps native `--coverage`; no invented Vitest instrumenter |
| ContextualWisdomLab/.github #1259 | `6041f2aa9e23af5850cd83fa838a3eb6c45d84b9`; auto-merge armed; blocked on independent review | thin LineageWeave hourly review-repair caller at minute 4; supersedes #1086 stack driver |
| LineageWeave #426 | `8948cdb036eb6f6a041ad97fe7e33b3043893028` (this stack) | open, mergeable but blocked, review required, auto-merge armed; zero approvals, core backend/frontend checks passing, and security/review checks still queued or running |
| LineageWeave #429 | `3763e1335cd3ac38b5e02b964ab49af34c8d73a0` | open, mergeable but blocked, review required, auto-merge armed |
| LineageWeave #494 | `5d9728a16051e7db453ca513cd5baa75be7450cc`; merged as `1ff0cd13b84d5c5f817706ef23dcbd5c3d67a510` into #426 only | unique diff is the four optional-extra collection files; this stack-only merge is not protected-`main` delivery |
| LineageWeave #497 | `07554b238a822e4423f8e6b4c000e5882fe49163`; merged as `250f20e8a6f830479ce904448cd29ab1a106aeef` into #426 only | ADR 0001 baseline is present on this hidden stack, not on protected `main` |
| LineageWeave #498 | `35823d889c5360ebf2152ed5679d7c22d6832545` | `/healthz` + docstring coverage; overlaps #429; blocked on independent review |
| LineageWeave #496 | `78287c08309f614ca1de04612c3e15c555bed1c6` | accepted TEPP receipts remain Running during an unavailable recheck; open and blocked with the exact-head Strix check failed and zero approvals |
| LineageWeave #499 | `a985f820af7a6552bcf32860b35b513e213a498c`; merged as `8f43d7fd17ae7ae9c197fe89ddb4beee82a2886a` into `docs/customer-master-scope-adr` only | channel-weight estimation remains hidden-stack evidence, not protected-`main` evidence; #507 is the clean protected-main restack of the fail-closed repair |
| LineageWeave #505 | `cbc6bd727d613216e8b0bf93b80d476205e2dd37`; merged as `c6d0ae57ca88684f3e7de992891adc2c208f06ed` into #490 only | merged into the non-default, unprotected parent branch rather than protected `main`; all 5 threads, including the 4 latest findings, are resolved; 4 checks passed and zero approvals |
| LineageWeave #506 | closed unmerged at `fd27f2d52766ac6cfe00e0713dcfc3fe938c6078` | its public PR head and pre-existing public history contain a real private runtime source-table identifier; this baseline intentionally neither names nor describes its value |
| LineageWeave #507 | `b8d9ce429f223d43a8639d0e2b2b0777e9105d2b` directly on protected `main` | exact remote tree matches the validated local tree; hosted Frontend, Full suite, and OpenCode are green, but Strix failed and zero approvals leave review required |
| LineageWeave #490 | `63f3231d249f20b0f34f7fc56fbd3f28f62f6d0c` directly on protected `main` | open, mergeable but blocked, review required; core and OpenCode checks pass, Strix is running, Devin failed, and approvals remain zero |
| LineageWeave #515 | `2d11b4b87beed3eaa7e452349a2daedb44cc32f7` stacked on exact #427 `446ceddd2a447a970cfaf2b6b858e79a0efe4b0d` | deterministic semantic row/cell, footnote, and encoded script normalization; local backend 51 and frontend 25 passed with independent adversarial review, while hosted checks are queued and no approval exists |
| LineageWeave #509 | `bba8a8ac43a43db70c563dd9612ab74c3fbe7930`; merged as `e4d692c6e5daede2af7c0e259d3fc5a4c1c7636a` into #490 only | all 4 hosted checks passed, its 1 thread is resolved, and approvals remain zero; unique diff was limited to the changelog, legacy-JSON fail-closed parser/test, and live PostgreSQL schema regression; local focused validation was 108 passed/1 skipped including 12 live PostgreSQL, migration vocabulary 54/55/54, compile and diff checks passing; this is not protected-`main` delivery |

This documentation is now owned by the open LineageWeave#426 stack because
#497 merged into that branch rather than protected `main`. #426 owns the login
`tsc` repair, ontology Pages, and this non-identifying baseline. #494 is the
login-only overlap and must not receive this file again. #505 is merged only
into #490's non-default branch; #509's isolated fixes also merged only into
#490 as `e4d692c6e5daede2af7c0e259d3fc5a4c1c7636a`, after which #490 advanced to
`63f3231d249f20b0f34f7fc56fbd3f28f62f6d0c`. That stack remains unprotected.
#499 remains hidden-stack evidence; #507 is the clean
protected-main delivery path for its fail-closed repair. Repeated concurrent
add/revert oscillation on #494 was not chased. Exact `5d9728a` changed stack
ownership and is now merged into #426 as `1ff0cd13`; #426 must still land for
that optional-extra collection work to reach protected `main`. If any exact head
changes, re-fetch and recheck the diff, checks, threads, and approvals before
making a lifecycle claim.

The current protected-`main` and exact #507 trees are clean of the private
runtime source-table identifier present in the closed #506 head and older
public history. Do not reproduce or hint at its value. Historical remediation
requires the ADR 0001 incident process and security/privacy-owner coordination;
never force-push or delete evidence ad hoc.

The Grok durable hourly loop and the central thin GitHub Actions caller
ContextualWisdomLab/.github#1259 (minute 4, `pr-review-fix-scheduler.yml`)
both target this repository. Do not add a LineageWeave-local duplicate
workflow. OpenCode coverage-evidence currently fails pnpm 9.15.9 heads on
`--trust-lockfile` (a pnpm 11.3 flag) and on a synthesized Vitest `--coverage`
flag; ContextualWisdomLab/.github#1258 (`9b5dba9`) is the exact-head repair
and has auto-merge armed pending independent OpenCode / Strix / Noema.

Figma design-system boundary (ADR 0002): File ID `1Su3lDRmiZdcUs47t1QwIX`.
The sanitized file now contains synthetic Event Lineage desktop (`5:14`) and
mobile (`5:15`) frames with graph direction, event dates, an inference
boundary, and exact fused-score evidence. Do not copy source-organization
content into this repository. Storybook remains the executable scene and
edge-case inventory for repeated web objects; rendered code-to-Figma parity
still requires same-viewport browser comparison on an exact candidate head.

## 2. User-visible capability baseline

Substantially present on protected `main`:

- PostgreSQL-backed import, normalized provenance, cutoff-aware analysis runs,
  source revisions, lineage reconstruction, and explicit unavailable states.
- Authenticated workspace navigation, post detail, localized summaries, 5W1H,
  R&R/Keyman, evidence citations, chat, organization hierarchy, and lineage DAG
  (`frontend/src/LineageDag.tsx` is on `main`; the old “DAG view missing”
  baseline entry is stale).
- Semantic paragraph/list/table/image-region units that preserve the source
  representation and provenance instead of flattening it into one body string.
- Contextual-orchestrator boundaries for adjudication, extraction, summaries,
  chat, embeddings, and VISION; null channels remain unavailable and are
  dropped from score fusion.
- W3C PROV-O projection through normalized provenance tables, with the
  knowledge graph retained as an explicit navigation projection.
- Keyverse/Keycloak OIDC, RankWeave fusion port, TEPP measurement client,
  ThreadWeave tree assembly.

These statements describe source capability, not authenticated production
corpus acceptance or protected release.

## 3. Snapshot open PR inventory

Heads below are queue evidence; explicitly marked merged rows are lifecycle
evidence and are not protected-main release evidence. Recheck
SHA, checks, unresolved threads, and independent approval immediately before
any merge claim. Do not self-approve, force-push, or transfer stale review
evidence across heads.

### 3.1 Merge-blocking and shared-gate repairs

| PR | Observed head | Intent | Gap it closes when merged |
| ---: | --- | --- | --- |
| #426 | `8948cdb036eb6f6a041ad97fe7e33b3043893028` | Login `tsc`, ontology Pages, namespace compatibility, optional-extra collection, and canonical baseline ownership | Shared frontend typecheck and public ontology publication on protected `main`; core checks pass, remaining security/review checks are unsettled, and no independent approval exists |
| #507 | `b8d9ce429f223d43a8639d0e2b2b0777e9105d2b` | Clean fail-closed weighting repair restacked directly on protected `main` | Local focused 41 and parent full 770 passed; hosted Frontend, Full suite, and OpenCode are green, but Strix failed and independent exact-head approval is absent |
| #494 | `5d9728a16051e7db453ca513cd5baa75be7450cc`; merged as `1ff0cd13b84d5c5f817706ef23dcbd5c3d67a510` into #426 only | Optional-extra collection only; four-file unique diff | Stack ownership preserves unique scope; land #426 to deliver it through protected `main` |
| #497 | `07554b238a822e4423f8e6b4c000e5882fe49163` | Non-identifying gap baseline (ADR 0001), merged only into #426 as `250f20e8a6f830479ce904448cd29ab1a106aeef` | Removes identifying post identifiers from the #426 tree; protected history still requires incident remediation and protected `main` has not received it |
| #498 | `35823d889c5360ebf2152ed5679d7c22d6832545` | `/healthz`, public docstring gate, and overlapping login repair | Preserve only value unique from #426 and #429 after their protected merge order is resolved |
| #429 | `3763e1335cd3ac38b5e02b964ab49af34c8d73a0` | `/healthz` routes to the liveness probe | Operability: liveness vs settings mix-up |
| #428 | Not captured | `migrate.sh` whitelist catch-up | Deploy: migrations silently skipped |
| #393 | Not captured | Detach provider parse error context | Honest orchestrator failure, not a poisoned parse |
| #383 | Not captured | Reader-safe OTel server diagnostics | Issue #361: generic 503 must still preserve diagnostics |
| #474 | Not captured | Rename operator-facing terminology + login return | Workspace copy; do not use “Buyer” for internal objects |
| #436 | Not captured | AdminPanel coverage | Frontend coverage 100% bar for admin settings |
| #439 | Not captured | LineageDag tests and stories | Storybook inventory for DAG edge cases |

### 3.2 User-visible product surfaces

| PR | Intent | Related issue / ADR |
| ---: | --- | --- |
| #258 | Workspace evidence board and source-grounded ontology | Critical; CHANGES_REQUESTED historically |
| #355 | Naruon event projection contract | Issues #336, #338 |
| #349 | Bounded ontology and provenance explorer | Issue #341 |
| #387 | Persist and explain Event Lineage channel evidence | Issue #274 |
| #484 | Allen interval relations on Event Lineage edges | Temporal modeling; Allen (1983) |
| #480 | Bind corroborated SKOS org aliases to one catalog row | SKOS exact-match / altLabel |
| #482 | SKOS companion caption on organization chips | Same SKOS catalog |
| #405 | Persisted image-region locations | VISION region provenance |
| #427 | Quantity superscripts in post bodies | Formula / unit display |
| #515 | Deterministic semantic rows/cells, safe encoded scripts, and literal escaped markup stacked on exact #427 | Source-unit reader parity; synthetic local tests pass, hosted checks and independent review remain open |
| #481 | Persist leftover LSIRM interaction-map coordinates | fast-mlsirm leftover pairs |
| #485 | Land leftover pair clicks on the named Post quality criterion | Same leftover surface |
| #490 | Wire remaining ADR 0133–0138 surfaces; exact head `63f3231d249f20b0f34f7fc56fbd3f28f62f6d0c` is still open against protected `main` | Consolidated product stack, including the Knowledge Graph token repair; #505/#509 merges here are not protected delivery, Strix is running, and Devin failed |
| #505 | Planned-facility relationship intent merged as `c6d0ae57ca88684f3e7de992891adc2c208f06ed` into #490 only | All review findings resolved, but the merge target is a non-default unprotected branch |
| #509 | Isolated #505 follow-up fixes at `bba8a8ac43a43db70c563dd9612ab74c3fbe7930`, merged as `e4d692c6e5daede2af7c0e259d3fc5a4c1c7636a` into #490 only | All 4 checks passed and 1/1 thread resolved with zero approvals; unique changelog/parser/test/live-schema diff and local validation remain non-protected stack evidence |
| #434 | Wire adjudication client into corpus-wide rebuild | Issue #289 |

### 3.3 Ask Agent stack (issues #358–#363, #269–#272)

| PR | Intent |
| ---: | --- |
| #415 | Korean relative-time expressions in Global Ask |
| #418 | Merged `lineage_graph` for every cited post |
| #419 | Cite persisted image evidence for cited posts |
| #421 | Playwright harness for Ask Agent capabilities |
| #422 | ADRs for Ask Agent temporal / lineage / evidence goal |

### 3.4 Scientific measurement recovery (must remain true-parameter tests)

| PR | Intent |
| ---: | --- |
| #451 | GRM parameter-recovery (RMSE vs true parameters) |
| #452 | GPCM parameter-recovery |
| #453 | CAT parameter-recovery |
| #454 | FIPC parameter-recovery |
| #468 | Bind fast-mlsirm, Keyverse, orchestrator, and TEPP |
| #417 | TEPP topic-lineage consumption boundary (TRSL-TM + CHRONOS/TDT) |
| #496 | Durable accepted TEPP receipts and recheck continuity; exact head `78287c08309f614ca1de04612c3e15c555bed1c6` |
| #499 | Psychometric channel-weight estimation merged only into a hidden docs stack; #507 is its clean fail-closed protected-main restack |

### 3.5 Gap-baseline documentation queue (superseded by this file)

PRs #440–#450, #455, and #463 rewrite documentation slices of this baseline.
PRs #368 and #479 also rewrite the baseline but are not docs-only: both modify
`frontend/src/App.tsx`. #479 carries the same login-fix blob as exact #426;
#368 carries the same login behavior with an indentation-only difference.
After #426 and this non-identifying inventory land on protected `main`, those
mixed and docs-only heads have no independently demonstrated source value and
should be closed as superseded rather than merged as conflicting rewrites. Do
not merge an identifying baseline over this file. #494 was limited to value
independently verified as unique from #426. Repeated concurrent add/revert
oscillation was not chased; exact `5d9728a` changed stack ownership before its
optional-only diff merged into #426 as `1ff0cd13`. #426 must land for that value
to reach protected `main`.

## 4. Open issues (product acceptance remaining on `main`)

| Issue | User-visible gap | Active PR |
| ---: | --- | --- |
| #79 | Milestone 2: port verified direct-PostgreSQL analysis into the protected architecture | analysis-run registry on `main`; remaining runtime bridge |
| #87 | Milestone 2.1 normalized runtime-analysis schema bridge | related analysis-run work |
| #269 | Authenticated Global Ask MCP browser-safe and admission-bounded | Ask stack |
| #271 | Evidence-honest knowledge-cutoff scope on Global Ask | Ask stack |
| #272 | Verify Global Ask KG/ontology/semantic claims with public SearXNG evidence | Ask stack |
| #274 | Persist and explain Event Lineage channel evidence | #387 |
| #277 | TEPP: persist accepted receipts, poll completed results, keep measurement authority distinct | #468, #417 |
| #280 | Full project-lifecycle history and handover intervals | Tracked with issue #284; no active delivery PR confirmed |
| #284 | Authoritative lifecycle ingestion and idempotent reconciliation | No active delivery PR confirmed |
| #289 | Activate the optional lineage LLM channel through a bounded asynchronous rebuild | #434 |
| #336 | Replace pseudo-CalDAV feed with a Naruon-owned calendar projection | #355 |
| #338 | Evidence-bounded email/project lineage contract for Naruon consumption | #355 |
| #341 | Heterogeneous ontology and provenance explorer separate from Event Lineage | #349 |
| #358 | Batch reauthorize persisted post-Ask evidence without N+1 queries | Ask stack |
| #359 | Centralize Global Ask session storage access | Ask stack |
| #361 | Preserve server diagnostics behind generic orchestrator 503 responses | #383 |
| #362 | Roll back rejected Global Ask turn atomically instead of poisoning the session | Ask stack |
| #363 | Continue ontology neighborhoods beyond the bounded source window | Ask / ontology |
| #372 | Reconcile lowercase and repository-case public namespace IRIs | #426 Pages stack; #492 is merged into that branch, not protected `main` |

## 5. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | 54 PRs open; the audited open #426/#490/#496/#507/#515 delivery set has no independent current-head approval; #496 and #507 have failed Strix checks while #426/#490/#515 remain unsettled | Terminal exact-head checks, no unresolved threads, independent exact-head approvals, protected squash-merge SHA |
| Shared frontend gate | Unauthenticated `AdminPanel` + unused OIDC helpers failed `tsc -b` on `main`; #494's four-file optional-extra diff is merged only into current #426 | Settle #426's exact-head checks and independent review, then land #426 without another add/revert cycle |
| Identifying baseline regression | `main` gap file listed real post identifiers; separately, closed #506 and pre-existing public history contain a private runtime source-table identifier, while current `main` and #507 trees are clean | Land this non-identifying rewrite, then coordinate ADR 0001 history remediation with security/privacy owners; do not reproduce the value, force-push, or delete evidence ad hoc |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419), but current runtime acceptance has not yet proved table-image structure, complete region coverage, or summary/image readiness together | Orchestrator-backed rendered workflow, original/derived asset provenance, region-before-OCR processing, and honest unsupported states; reconcile ADR 0052's image-bearing summary readiness with ADR 0098 before changing sequencing |
| Semantic source rendering | Paragraph, table, list, formula, and indentation work exists across stacks (#394, #427, #448–#450); #515 adds synthetic backend/frontend parity for deterministic rows/cells, footnote boundaries, and encoded scripts | Land the #427 → #515 stack, then gather authenticated browser evidence that list nesting, continuation alignment, and formula units render without authoring-layout artifacts |
| Event and project semantics | Multi-project mentions, project-bound actions, 5W1H, requester/processor, and semantic relations exist in ADR 0036/0052/0100/0111/0129 and active stacks | Aggregate authenticated evidence must show distinct projects and events, explicit requester/processor and real R&R, normalized relative time, and product/entity relations without promoting attendance or co-occurrence |
| Knowledge Graph readability | The black evidence-node root cause is an undefined-token fallback; the design-token repair and long-label/evidence-table coverage are present on #490, not protected `main` | Deliver the token repair through protected `main`, then verify light/dark contrast, keyboard graph navigation, full labels, and evidence tables in the authenticated rendered surface |
| Source-code lookup UX | Source state/detail codes remain evidence-bearing machine values and current detail presentation is dense | Catalog-backed display labels with raw-code provenance, compact 5W1H/source-detail hierarchy, keyboard access, and no unsupported customer/project binding |
| Calendar / Naruon | Pseudo-CalDAV remains on `main`; #355 carries the projection contract | Naruon-owned projection, issue #336/#338 acceptance, no invented events |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | #496 preserves an already accepted TEPP receipt across an unavailable recheck, but its exact-head Strix check failed and approvals remain zero; #499 is merged only into a hidden docs stack, while #507 is the clean protected-main restack with its own Strix failure | Repair exact-head Strix findings, then protect delivery of persisted accepted envelopes and fail-closed weighting; calibration/recovery RMSE; no invented theta |
| Planned-facility intent | #505 and its #509 follow-up are merged only into open #490's non-default branch; current #490 is `63f3231d249f20b0f34f7fc56fbd3f28f62f6d0c` with core/OpenCode checks passing, Strix running, Devin failed, and zero approvals | Settle #490's exact-head gate and obtain independent review, then deliver the stack through protected `main` before making a release claim |
| Accessibility and responsive UX | Unit coverage exists for major surfaces; Storybook inventory incomplete | Keyboard, screen-reader, mobile, and authenticated Playwright acceptance on the exact release head |
| Design tokens and repeated objects | Token extraction started; sanitized Figma Event Lineage desktop/mobile frames exist, while other repeated product surfaces remain incomplete | Tokens in CSS + Storybook stories for board, popup, DAG, Ask, calendar, forms, charts; same-viewport Figma/runtime visual comparison before release |
| External integrations | Search, Zotero, calendar, Keyverse, orchestrator, RankWeave, ThreadWeave, TEPP, disksage, wardnet | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| MSA / modular reuse | LineageWeave must run standalone and as a consumer of org packages | Do not reimplement RankWeave/TEPP/orchestrator/ThreadWeave/Keyverse; fix upstream and PR there |
| Release quality | Local focused/full suites have passed on individual PR heads | Repository-wide coverage, docstrings, Storybook, security, browser, and release evidence on one exact head |
| PII | Masking would paralyze the product; ADR 0001 forbids identifying artifacts in git | ABAC + authorized runtime; synthetic fixtures in git; no mask-in-place that drops names the operator must read |
| Database | PostgreSQL, 3NF, snake_case ≥ two words, hot-partition and lock policy | No file DBs; read/write split if lock management fails; whitelist every migration |

## 6. UI-UX acceptance inventory (must be defined, reviewed, applied, audited)

Each item needs a Storybook scene, an edge-case story, and an automated check
before a commercial release claim. Figma File ID `1Su3lDRmiZdcUs47t1QwIX`.

| Dimension | Current | Gap |
| --- | --- | --- |
| Accessibility | Partial labels/roles on board, popup, login | WCAG 2.2 AA on login, board, popup, Ask, calendar, admin; focus order; live regions |
| Touch & Interaction | Click-first popup and lists | 44px targets, swipe/escape to dismiss popup, no hover-only actions |
| Performance | Board caps and hint render limits exist | Interaction-to-next-paint on board search, DAG, Ask; no N+1 (#358) |
| Style Selection | Korean UI standards merged (#347) | Tokenized light/dark; Anti-Slop-UI density; no decorative noise |
| Layout & Responsive | Desktop popup shell | 402px-class phone layout; stacked GNB; readable DAG |
| Typography & Color | Badge tokens extracted | Contrast on badges, links, error/status; no raw hex in components |
| Animation | Minimal | Reduced-motion; no blocking animation on evidence open |
| Forms & Feedback | Login, Ask, tickets, admin brand | Inline validation, next-action copy, unavailable vs failed distinction |
| Navigation Patterns | Board / customers / calendar / Ask / admin | Deep-link post + OIDC return URL (#426); bookmarkable Ask |
| Charts & Data | Period reports, leftover pairs, Rankings, DAG | Honest empty/unavailable; no invented theta; Storybook chart states |

## 7. Ecosystem leverage order

Reuse before rebuild. Consume these ContextualWisdomLab packages in this order
of leverage; open connector PRs there when the defect is upstream:

1. **contextual-orchestrator** — every LLM/VISION/embedding call (Fugu / Conductor / TRINITY routing). Never a raw provider SDK.
2. **Keyverse** — OIDC issuer, JWKS, tenant principals.
3. **RankWeave** — fused scores and rankings; never invent a fused score or theta.
4. **TEPP** — calibrated measurement; persist receipts; no local reimplementation.
5. **fast-mlsirm** — GRM/GPCM/CAT/FIPC recovery tests (#451–#454) must stay true-parameter RMSE.
6. **ThreadWeave** — tree assembly.
7. **Naruon** — calendar and email/project lineage projection (#336, #338, #355).
8. **disksage / wardnet** — storage and network policy as needed.
9. **ContextualWisdomLab/.github** — required review workflows (OpenCode, Strix, Noema) and the LineageWeave hourly caller (#1259). If stacked PRs miss central review or coverage-evidence fails on pnpm 9 (`--trust-lockfile` is pnpm 11.3) or a missing Vitest coverage provider, fix the org workflow (#1258), not a local bypass.

## 8. Public ontology publication boundary

- PR #426 publishes fragment-addressable HTML, byte-identical Turtle,
  isomorphic JSON-LD and N-Triples, the PROV-O support profile, and a
  source-digest manifest from the authoritative ontology.
- Pull requests validate only. Only protected `main` may publish, and the
  generated-directory marker, linked-IRI, duplicate-fragment, symlink, and
  source-overlap checks fail closed.
- The lowercase knowledge-graph namespace and repository-case support-profile
  namespace remain distinct until issue #372 delivers a versioned migration
  and compatibility decision; this publication PR rewrites neither identity.
- Until the protected deployment and exact URL checks succeed, the public
  ontology endpoint remains unavailable and must not be represented as live.

## 9. Evidence boundaries

- Never add a real record, title, name, identifier, screenshot, log, benchmark
  artifact, or documentation example to this repository.
- Attendance or co-occurrence is not responsibility, project, customer, or
  affiliation evidence. Preserve uncertainty and provenance.
- Missing transport, model capability, accepted envelope, or persistence is
  unavailable or failed evidence, never a placeholder result.
- Local green tests, bot statuses, auto-merge, and warning-only checks do not
  prove a protected merge.
- Re-fetch base/head SHAs, checks, review threads, approvals, rulesets, and the
  merge SHA immediately before any lifecycle claim.
- Do not self-approve. Independent OpenCode / Strix / Noema review is required.
- Do not force-push. Do not treat GitHub Checks duration as a blocker; repair
  the failing check instead.
- `COPILOT_GITHUB_TOKEN` is not used.

## 10. Next acceptance loop

1. Let #426's remaining exact-head security/review checks settle; partial green
   checks are not a terminal protected gate even though its threads are resolved.
2. Obtain two independent exact-head approvals for #426 and land that stack on
   protected `main`; auto-merge being armed does not itself satisfy the gate.
3. Repair #496's failed Strix finding and obtain independent exact-head review
   while preserving the durable accepted-receipt behavior across unavailable
   rechecks.
4. Treat #505 and #509 merge commits as #490-only evidence. Settle Strix and
   repair Devin findings on exact #490 head `63f3231d249f20b0f34f7fc56fbd3f28f62f6d0c`, obtain independent review, and
   deliver the resulting stack through protected `main` before a release claim.
5. Repair #507's failed Strix finding, then obtain independent exact-head
   approval for `b8d9ce429f223d43a8639d0e2b2b0777e9105d2b`; its 12 threads,
   Frontend, Full suite, and OpenCode are green, but zero approvals still block
   the clean protected-main path. Do not credit #499's hidden-stack merge as
   protected delivery.
6. Coordinate the ADR 0001 history incident with security/privacy owners. Keep
   current `main` and #507 clean, never reproduce the private identifier, and
   do not force-push or delete public-history evidence ad hoc.
7. After ContextualWisdomLab/.github#1259 is on protected `.github` main, the
   minute-4 caller owns the GitHub Actions heartbeat. Close superseded baseline
   PRs (#368, #440–#450, #455, #463, #479) once #426 is on
   `main`; #368 and #479 also carry already-covered login changes.
8. #494 is already merged only into #426 as `1ff0cd13`; settle #426's exact-head
   checks and independent approvals so that four-file optional-extra diff can
   reach protected `main` without another add/revert oscillation.
9. Merge smallest shared-gate repairs next (#429, #428, #393, #436, #439)
   when independently approved.
10. Advance user-visible gaps in leverage order: Event Lineage evidence (#387 /
   #274), Naruon calendar (#355 / #336), SKOS aliases (#480 / #482), ontology
   explorer (#349 / #341), Ask Agent (#415–#422 / #358–#363).
11. Keep psychometric tests as true-parameter recovery (RMSE), never fixture
   tautologies.
12. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
13. Fix only evidence-backed failures and repeat the protected merge gate.

## 11. Spec pointers (derive, do not fork)

- Product/architecture: `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`
- Research grounding: ADR 0084, `docs/lineage-bi-research-notes.md`
- Demo identity: ADR 0001
- Figma boundary: ADR 0002 (File ID `1Su3lDRmiZdcUs47t1QwIX`)
- Orchestrator / paper-grounded models: ADR 0015, ADR 0076 (Fugu, TRINITY, Conductor)
- Ontology / PROV-O / SKOS: ADR 0004, ADR 0011, issue #372
- Analysis runs / TEPP: ADR 0013–0023, issue #79 / #277
- Calendar / Naruon: issues #336 / #338, PR #355
- Ask Agent: issues #269–#272, #358–#363

Citations in doctoring and ADRs use APA 7th. Do not invent a heuristic where
the papers leave the decision undecided.
