# Product & Technical Gap Baseline

> Audit scope: the current LineageWeave TEPP terminal-result continuation and
> all 9 open PRs, compared with protected `main`, the UI/UX Standard Guide v3.0,
> ADR 0118, the accepted TEPP contracts, and contextual-orchestrator. Real
> source identifiers are deliberately replaced with case labels; they must not
> enter repository artifacts.

## 1. Exact-head evidence

### 1.0 Current TEPP continuation

Observed at `2026-08-26`: protected `main` is
`04e6b610655d0db91d5f7ba9486bdda1440e0b19`. Nine PRs target `main`:
#644 `c1018a0a`, #643 `041ec13b`, #640 `2fad1fe6`, #639 `aee02dca`,
#636 `f7b9a65f`, #632 `3e3f0ead`, #631 `c0022c97`, #629 `4b4d6707`, and
#579 `689a21b6`. All have auto-merge armed and zero unresolved review threads;
none has the independent exact-head approval required by protected rules, so
no protected merge is claimed. The older snapshots below remain historical.

TEPP PR #157 merged as `7ce87c305981819f5333c7eb90ea0feafc0f7bf6`
and closed TEPP issue #156 by publishing `AnalysisRunStatus` and
`AnalysisRunTerminalResult` v1. The provider explicitly did not deploy a
production HTTP status service. This continuation therefore consumes the
strict contract through a pluggable status-read port, retains accepted/running
as transport evidence, persists only fully request-bound terminal results,
and rejects changed digests. It does not guess a provider URL, polling cadence,
backoff coefficient, theta, or score. Focused exact-source evidence is
`64 passed`; the full Python suite passed `1087` with `16` live-stack skips.
TEPP issue #249 now owns the executable HTTP status-service gap. The unrelated
Starlette `httpx2` migration and short synthetic JWT-test key warnings remain
pre-existing dependency/test-fixture gaps and are not suppressed in this
TEPP-scoped continuation. Protected checks and independent review remain
required.

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
| Ontology, semantic layer, provenance, W3C PROV-O projection | normalized schema, SKOS operational vocabulary concepts, `ontology_annotations` label fallback, OWL-Time canonical earlier-to-later relations, ADR 0124/0129, provenance modules, directed evidence table, ADRs | source + unit; corpus verification open |
| Branching Event Lineage DAG with evidence trail | `LineageDag.tsx`, Storybook story, Figma frames, accessible node-kind names for screen readers/tooltips, frontend tests; runtime cases include both a rendered DAG and honest empty states, while current corpus coverage remains sparse | source + unit + local-integration partial |
| Customer master, cross-post identity, name history, and hierarchy tree | `/api/customer-master`, ADR 0125/0137, migrations `0105`/`0137`, source-system-qualified stable binding, fast-mlsirm Judge/IRT evidence, optional TEPP ordering, `edge_customer_identity_observation`, importer reconciliation, visible preferred/former/alternate names, scope filter | source + focused unit + local-integration partial; live external provider/import and broader authoritative hierarchy evidence remain open |
| VOC/VOM/VOP/VOCC/VOCO/VOS role classification | common lookup values and relationship APIs | source + unit; live classification open |
| Evidence-grounded chat and source navigation | `/chat`, `/ask`, citation/evidence UI | source + unit; synthetic orchestrator judge route verified, corpus chat/runtime evidence open |
| OpenTelemetry across LineageWeave, contextual-orchestrator, Valkey, and GRC | LineageWeave PR #383 adds API/Valkey/session spans; contextual-orchestrator PR #818 carries session/provider telemetry; governance-risk-compliance PR #51 adds request telemetry, W3C trace context, OTLP export, and ADR 0009 | source + PR; protected merge and end-to-end collector evidence open |
| PU/team/project weekly/monthly reports | report API/UI and grouping controls | source + unit; TEPP-backed live report open |
| TEPP calibrated measurement, dichotomous items, multilevel/MMM/time model | accepted receipt parent #496 plus TEPP terminal-result v1 consumer (ADR 0178); arithmetic remains TEPP-owned | strict contract consumer source + focused unit; provider HTTP status service and live-external evidence open |
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
  v19 with one requested pair; browser confirmation remains open. Chronology
  alone does not assert revision, specialization, causation, or a private
  product-succession predicate.

These are not “resolved” merely because a prompt or heuristic was changed.
Each requires synthetic unit coverage plus an authorized runtime reproduction
or an explicit unavailable result.

## 5. Product and technical gaps

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
- **TEPP measurement — terminal consumer implemented, runtime open:** LineageWeave must
  call TEPP through its published import/REST contract and must not implement a
  local theta, psychometric calibration, CAT, or judge score. TEPP owns the
  Rust numerical/psychometric layer and its multilevel/multiple-membership/time
  model. Live inspection on 2026-08-23 found that the upstream TEPP repository
  now publishes strict `AnalysisRunRequest`, `AnalysisRunAccepted`,
  `AnalysisRunStatus`, and `AnalysisRunTerminalResult` v1 DTOs and outbound HTTP
  exchange builders, but no production HTTP status server, snapshot-evidence
  ingest, or production
  estimator entrypoint. The current request carries only a snapshot digest, so
  a service cannot calibrate the underlying observations without a new
  purpose-bound evidence artifact/API. `TEPP_TRANSPORT_URL` alone therefore
  cannot make measurement available. Close this in TEPP first with an ADR and
  PRD update covering authorized evidence transfer, Rust estimator authority,
  durable lifecycle/idempotency, provider HTTP status route, and CPU/GPU parity;
  then pin that service in Compose and prove a persisted
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
- **Provider-boundary exception diagnosability — partially closed
  (2026-08-25, issue #361):** the 10 fail-closed `except Exception`
  catch-alls across `backend/app/main.py` (Global Ask, per-post chat,
  keymen extraction, entity-relationship verification, evaluation,
  summary regeneration, commitment derivation) now log the exception
  server-side (`logger.exception`, stdlib `logging`) before returning
  the same stable customer-facing 503; a caplog-based test proves an
  unexpected defect (not a classified provider error) reaches the logs
  with a traceback. Not yet done: OpenTelemetry metrics distinguishing
  known-provider-unavailable from internal-defect, correlation/request
  IDs, and bounded-cardinality alerting -- those need a new-dependency
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
- **Leftover pair next-action jargon — closed (2026-08-24, PR #490
  `154a13ef`):** ADR 0049 already names `Open {post}, then read Post quality
  criterion {criterion}.` Origin leftover copy still appended `This pair sat
  closest/farthest after main effects.` `leftoverPairNextAction` now matches
  the ADR sentence only. Evaluation keeps saved IRT scores when the
  orchestrator or evaluation channel is down, instead of hiding them behind
  the dropped-channel diagnosis. Vitest leftover-pair and evaluation-503
  tests cover both; leftover Storybook scenes read the same next-action
  helper.
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
