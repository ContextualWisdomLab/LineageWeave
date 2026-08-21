# Product & Technical Gap Baseline

> Repository artifacts contain synthetic fixtures and derived, non-identifying
> evidence only. Real PostgreSQL rows, source payloads, images, names, and
> identifiers remain in a protected external runtime and are never copied into
> this repository, screenshots, tests, logs, or buyer evidence.

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: synthetic case `case-footnote-01` exercises numbered footnote recognition; PR #367 merged semantic-chunker coverage, and stacked PR #388 adds browser fallback recognition for HTML, Word, and OOXML footnotes. Authorized production/browser corpus evidence remains pending.
- **Table Parsing**: synthetic case `case-table-01` exercises malformed row boundaries and empty cells; PR #389 now covers ordinary Markdown rendering, while region-aware image tables and protected-corpus evidence remain open.
- **Indentation**: synthetic cases `case-indent-01` and `case-indent-02` retain
  corpus coverage gaps; PR #391 adds the common nested HTML-list depth fix and
  regression coverage, while authorized production/browser evidence remains open.
- **Image/Table OCR**: synthetic case `case-image-table-01` now has region-aware table OCR, markdown rendering, and buyer-visible normalized region locations through stacked PR #395; authorized production/browser evidence and complete image-region coverage remain open.
- **Math/Superscripts**: synthetic case `case-math-01` covers bounded metric normalization such as m³; arbitrary formula semantics and authorized runtime verification remain open after PR #344.
- **Missing UI Elements**: synthetic case `case-dag-01` tracks the Event Lineage DAG surface; current source includes the DAG, but corpus coverage and browser evidence remain open.

## 1.1 UI/UX Standard Guide v3.0 audit

- **Present in source and unit coverage:** the React shell has a sticky header,
  top-right account/logout/language/search utilities, GNB and phone drawer,
  footer/copyright, Noto Sans and tokenized palette, 1024/1280/1920 layout
  bounds, three responsive tiers, table/form alignment rules, required-field
  markers, focus states, and a 50% modal mask. The Event Lineage DAG has
  keyboard activation, branch/root/current states, evidence context, and
  Storybook scenes.
- **Figma reference:** ADR 0118 records File ID `1Su3lDRmiZdcUs47t1QwIX`;
  Event Lineage desktop/mobile frames remain the normative visual reference.
- **Open buyer or governance gaps:** approved tenant CI/BI assets and usage
  permission are not present; no-JavaScript fallback is not proven; phone and
  site-map behavior need protected runtime evidence; and Figma parity does not
  prove complete authorized-corpus image/table evidence.
- **Historical exact-source UI audit at PR #392 ancestor `a046da4e`:** the
  header and footer rendered one configured `brandName` and the footer used
  the browser's current year. This observation remains historical and is not
  a claim about the current stacked head.
- **Current exact-source mitigation at the merged stack change `2e51a777`:**
  `tenant_settings` now persists separate `brandName`, `systemName`,
  `copyrightYear`, and `copyrightHolder` values. The header renders brand and
  system name separately, the footer uses the persisted year and rights
  holder, and the admin form validates the four-field contract through the
  `post_admin` boundary. The migration is replayable through Compose and the
  old brand-only PATCH shape remains compatible. The merged change also fixed
  the asynchronous draft synchronization race and the Korean operation-note
  translation key, with the same operation note covered across all five
  product locales. PR #397 merged into the non-main stack branch; the
  protected `main` branch still depends on the separate parent PR #392.
- **Current follow-up at PR #398 head `f101ab93`:** the settings upsert now
  refreshes `tenant_settings.updated_at`, and clearing the numeric copyright
  year stays visibly blank and blocks submission instead of coercing the
  draft to a valid-looking value. Local backend and frontend evidence is
  recorded below; hosted Checks and independent approval remain required.
- **Remaining UI governance gap:** no approved CI/BI image asset or usage
  permission was supplied, so the implementation deliberately remains text
  based. Production release still requires the approved asset and legal
  metadata; no asset or real organization identity is invented in this repo.
  The React-only entry point also has no proven no-JavaScript fallback.

### 1.1.1 Exact implementation evidence for tenant identity metadata

Observed at `2026-08-21T20:17:13Z` from the GitHub API and local worktree
`/private/tmp/lineageweave-identity-restack`:

This subsection is a historical checkpoint. The current exact-head state is
recorded in Section 4.7; the older PR #397 open-state wording below is not a
current merge claim.

- PR [#397](https://github.com/ContextualWisdomLab/LineageWeave/pull/397) is
  open and ready at head `8988fe7175c8b03e27c9ea6fe3a554955eb350a4`, based on
  exact stack branch head `259ce60abdb8e0d0993635facd8c987a2999cd58`; it is
  `UNSTABLE` while hosted Checks and automated reviews run and has no formal
  review decision yet.
- Local verification at the latest restacked head passed the focused settings
  API suite (`4 passed`), migration replay (`8 passed`), frontend `203 passed`,
  lint, and production build. The earlier source-compatible head also passed
  the full backend suite (`850 passed, 17 skipped`) and Storybook build.
  The focused API tests cover authentication, full metadata, legacy
  brand-only PATCH compatibility, blank values, and copyright-year bounds.
- PR #392 remains open at head `259ce60abdb8e0d0993635facd8c987a2999cd58`,
  targets `main`, and is `BLOCKED` with `REVIEW_REQUIRED`; #397 is a stacked
  follow-up and must not be described as a protected-main merge.

## 2. LLM Extraction & Knowledge Graph Gaps
- **Multiple Project Extraction**: A structured `key_events.project_name` implementation exists, but separate-event behavior still requires protected authorized-corpus evidence.
- **5W1H Missing**: A structured 5W1H evidence-item implementation exists, but completeness and provenance still require protected authorized-corpus evidence.
- **R&R and Keyman Missing**: Prompt and persistence paths exist, but actual-side/other-side affiliation, requester, assignee, and provenance still require protected authorized-corpus evidence.
- **Entity Resolution / Searxng**: Abbreviations like "한전" and "한국전력" are not mapped properly using Searxng and KG corroboration. 
- **Meso-level Team Mapping**: `team` mapping logic is present; affiliation and same-entity resolution still require ontology-backed runtime evidence rather than prompt-only confirmation.
- **Base64 Image Omni-modal**: Current text-only embedding fails on images. Omni-modal LLM processing is required for images to capture layout, font size, colors, and spatial meaning.

## 3. General Architecture Gaps
- **DB Architecture**: Ensure PostgreSQL is strictly used (no file DBs), 3rd normal form is maintained, and Hot Partitions are handled. DB locks must be managed (or use read/write replicas).
- **Zotero Integration**: Papers and standards referenced by TEPP must be synced via Local Zotero API (http://localhost:23119/api/) and cited using APA 7th edition in docstrings.
- **Testing**: We need actual testing of Psychometrics (Fast-MLSIRM parameter calibration, RMSE of estimates, Fixed-Item Parameter Calibration, CAT) against synthetic/demo data.
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

### 2.1 Requirement traceability matrix

The status vocabulary is evidence-bound: **verified** means the current source
and a scoped test prove the contract; **partial** means local or synthetic
evidence exists but the requested authorized-corpus or production proof is
absent; **open** means implementation or governance work is still required.
An open PR never counts as a protected-main merge.

| Requested capability | Current evidence | Status and remaining proof |
| --- | --- | --- |
| UI shell, responsive tiers, Figma and Storybook | React shell, token tests, viewport/browser checks, Storybook scenes, ADR 0118 Figma File ID `1Su3lDRmiZdcUs47t1QwIX` | **Partial** — approved CI/BI asset, legal usage permission, no-JavaScript fallback, and protected runtime parity remain unproven. |
| Corporate-code/PU login, logout, ABAC/RBAC and visibility | OIDC browser run, account affiliations, permission checks, post visibility predicates and API tests | **Partial** — authorized production identity and complete role/policy matrix remain unverified. |
| Event DAG, branching and channel evidence | `LineageDag`, keyboard selection, branch/root/current states, persisted channel evidence and synthetic tests | **Partial** — current protected-corpus rendering and lineage quality remain unproven; PR #387 is open. |
| TEPP import/REST boundary and PostgreSQL source | TEPP client contract, PostgreSQL migrations, import boundary and no-file-DB tests | **Partial** — the requested real `zcrht811_export_rows` analysis cannot be committed or claimed without protected authorized runtime evidence. |
| Keyman, R&R, 5W1H, multi-project events and commitments | Orchestrator clients, persistence schemas, popup routes and synthetic/API coverage | **Partial** — affiliation, requester/assignee, counterparty-side identity, provenance and corpus completeness remain unverified. |
| Ontology, semantic layer, KG depth and customer master | normalized entity/relation/provenance schema, ABAC filters and customer/ontology routes | **Partial** — Searxng corroboration, abbreviation resolution, multi-company/team identity and per-node depth need live evidence. |
| HTML/CSS structure, Base64 image and multimodal analysis | semantic units, region persistence, OCR/caption rendering and bounded VISION boundary | **Partial** — image-heavy summaries still return processing/unavailable states; complete region/OCR/embedding quality is not proven. |
| Weekly/monthly reports and psychometric linking | report routes, TEPP/fast-mlsirm contracts and synthetic measurement tests | **Open** — authorized corpus calibration, RMSE/linking evidence, CAT/Fixed-Item calibration and buyer report acceptance are missing. |
| Valkey event queue, retries, concurrency and operations | queue migrations, worker supervision tests, replay-safe migrations and lock-aware settings update | **Partial** — production throughput, hot-partition behavior, lock contention and recovery SLO evidence remain open. |
| Orchestrator auto-discovery, VISION, embeddings and OTEL | provider-neutral gateway boundary, bounded provenance/session metadata and open upstream PR evidence | **Partial** — live model completion, collector delivery, retention/access review and downstream central workflow repair are not yet accepted. |
| Security, CSAP/SOC 2 and PII-preserving controls | ABAC/authorization tests, redaction-safe telemetry contract and repository no-real-data rule | **Partial** — control-owner evidence, audit artifacts, key management and operational access reviews remain outside this repository. |

## 4. Current Checkpoint Evidence

The following states are evidence-bound and must not be changed to `merged` or
`resolved` from intent alone. Observed at `2026-08-21T18:56:50Z` from the
GitHub API. Checkpoint types are `merge_commit`, `head`, and
`closed_without_merge`; the latter records a closed PR's exact `head` when
`merged_at` and `merge_commit_sha` are both absent. A merged commit is
identified by `merge_commit`; an open PR is identified by its exact `head` and
`base`.

Recently merged into the protected repository:

- PR #385: `merge_commit` `8b356a8399d40bcecc68a07bcfacab78eef303a0`.
- PR #366: `merge_commit` `ec6a829c88f9d2fdb6c34d2d089945aefb59c7a4`.
- PR #374: `merge_commit` `79c40bc8c25050084e5bbed62b8f145f6fa47775`.
- PR #375: `merge_commit` `fb0d185a2da707e57d2ed10900b06707126d8300`.
- PR #379: `merge_commit` `b606c2553f877fa85968d90dc46598ce16897fbf`.
- PR #370: `merge_commit` `aa38b29a95eed24de8073753552befc2e8cfaaae`.
- PR #369: `merge_commit` `6e591f4b7ec4da6acf768298d8d06f841e3a2372`.
- PR #287: `merge_commit` `bc8bcbee45c050cbd6775ca4f8455c00c25cc77d`.
- PR #262: `merge_commit` `6bf75991b04601483d48384045e314db2a928e30`.

Recently merged into an open stack base (not main):

- PR #382: `merge_commit` `43e24783ae38d65d03df7cb901f93b8ac8731b9b`, merged
  into PR #373's `ci/publish-ontology-pages-clean` base.
- PR #388: `merge_commit` `068ed6a44a7235e2f996450f0d6a7948bdd8732a`, merged
  into PR #387's `feat/event-lineage-channel-evidence` base.
- PR #389: `merge_commit` `778c5df1223ed60a6494e8896079b3ece97669f4`, merged
  into PR #388's `feat/post-body-footnote-display` base.
- PR #390: `merge_commit` `b020378710a0e405974538d80f7ef68ae3badd7c`, merged
  into PR #389's `feat/markdown-table-display` base.
- PR #391: `merge_commit` `16f2b13caad10f4d999293d623405aefadeda52e`, merged
  into PR #387's `feat/event-lineage-channel-evidence` base.
- PR #367: `merge_commit` `7a0d025215fbd9f6510727c7139885b561296149`, merged
  into `docs/customer-master-scope-adr`, not protected `main`. Its historical
  Full test run failed because that temporary base lacked migration `0105` and
  had one stale SQL-suppression count; the current #392/#397 stack contains the
  migration and must be judged by its own exact-head Checks.

Open PRs at the same observation:

- PR #258: `head` `6621eb116a4e92eb33eeae989c70fbc602450c51`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #349: `head` `202194a2d9ba6da49a011ca6127a00f6bf5394ba`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #355: `head` `b606c2553f877fa85968d90dc46598ce16897fbf`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`). The overlap with PR #379's
  merge commit is intentional: #355 is the open successor from the same
  feature branch, now pointing at that merged branch tip, and is not itself
  merged.
- PR #368: `head` `7855f2af0c516a0a4f6228e0b9230e6062d326be` (the exact current
  documentation checkpoint), base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #373: `head` `151fe6e177416a5d83b5539a73d97737c12d1ce4`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #383: `head` `b1d32a93632164cf1379f24fc9aca71c5d29b746`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #387: `head` `eaea56d3b2f07f89a5dfcc7d81b032148048982d`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #392: `head` `a046da4e52c484807fc28111bd813d1acbc00816`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #388, #389, #390, and #391 are closed after the stack merges recorded above;
  they are not open PRs at this checkpoint.

The open queue remains subject to exact-current-head Checks, formal independent
approval, and protected mergeability. Green Checks alone do not prove that a
merge is authorized. PRs #388, #389, and #390 were merged into non-main stack
bases through normal merge commits; PR #387 remains the open main-targeting
parent carrying those changes. PR #258 still targets `main` at base
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` and remains open; PR #385's merge
commit is later repository history, not PR #258's original base or a merge of
PR #258. PR #386 is closed as a duplicate of the safer #373 login fix. PR #382's
stack merge is not a main merge; #373 must still pass its own current-head
gates.

Queue refresh at `2026-08-21T18:56:50Z`: PRs #258, #355, and #373 had
terminal successful Checks but no independent `APPROVED` review, so none was
authorized to merge. PRs #349, #368, #383, #387, and #392 had no failed
Checks observed at their exact heads but retained non-terminal Checks and no
independent approval. PR #355 also retained a `CHANGES_REQUESTED` review
decision from the earlier stale coverage verdict; it remains unmergeable until
the current-head review is refreshed. PRs #388, #389, #390, and #391 were
merged into stack bases only; their merge commits are not protected-main merges.
Re-read the exact current HEAD, review, and terminal-check gates before every
future merge.

Queue refresh at `2026-08-21T19:00:00Z`: PR #391 is recorded as merged into the open
#387 stack parent with merge commit
`16f2b13caad10f4d999293d623405aefadeda52e`; this is not a protected-main
merge. PR #392 is open at exact head
`a046da4e52c484807fc28111bd813d1acbc00816` with one passing and twelve pending
non-skipped Checks and no independent approval. The remaining open PRs were
not authorized to merge from this observation because approval and/or terminal
Checks were still absent.

Queue refresh at `2026-08-21T19:07:01Z`: exact-current inspection found no
failed Checks on the listed main-targeting open LineageWeave PRs. PR #387 advanced to
`eaea56d3b2f07f89a5dfcc7d81b032148048982d`; PR #392 remains at
`a046da4e52c484807fc28111bd813d1acbc00816`; the baseline PR itself is at
`7855f2af0c516a0a4f6228e0b9230e6062d326be`. All had no independent approval;
the green-only PRs remain unmerged under the protected-main policy.

Queue refresh at `2026-08-21T19:16:15Z`: the open queue changed after the
previous checkpoint. PR #393 is open at exact head
`859e03674cd65f790594cffe8cd19f4de443ba0c`; #392 remains at
`a046da4e52c484807fc28111bd813d1acbc00816`; #387 at
`eaea56d3b2f07f89a5dfcc7d81b032148048982d`; #383 at
`b1d32a93632164cf1379f24fc9aca71c5d29b746`; #373 at
`151fe6e177416a5d83b5539a73d97737c12d1ce4`; #368 at
`0e807d0b95fb3658c512793090de8828a43849fa`; #355 at
`b606c2553f877fa85968d90dc46598ce16897fbf`; #349 at
`bfb3760403f6d6af22db3950f3d4d472a97edd4e`; and #258 at
`6621eb116a4e92eb33eeae989c70fbc602450c51`. All target `main` and are
blocked by the protected merge gates. Checks had no failures for #393, #392,
#387, #373, #368, #355, #349, or #258; #383 had one failed `osv-scan`, with
   15 passing, 2 pending, and 8 skipped checks. Later artifact inspection showed
   both scanner invocations exited zero and the head result survived, while the
   cross-fork head checkout had deleted the untracked base result. This is a
   shared-workflow defect, not a dependency-vulnerability verdict. Central
   `.github` PR #1209 is the upstream repair path. No PR was merged from this
   observation.

Exact-head local verification at `2026-08-21T19:16:46Z` on the working
checkout at PR #392 head `a046da4e52c484807fc28111bd813d1acbc00816` passed
846 backend tests with 17 environment skips, 200 frontend tests, frontend
lint, TypeScript/production build, and Storybook build. Build output emitted
only the existing chunk-size warning. This validates the current checkout;
it does not turn the open PR into a protected-main merge or prove the
authorized-corpus UI and image evidence gaps above.

Queue refresh at `2026-08-21T19:30:47Z`: the latest open queue contains PR
#394 at `5602096b61272a2ccb0c9997cbaddd261fa165af`, #393 at
`97baed032533a71c6a04b51d7c70df6df535e53b`, #392 at
`1412313d421445c1246a6970c5ab71a6304a483d`, #387 at
`eaea56d3b2f07f89a5dfcc7d81b032148048982d`, #383 at
`4eaa07172fde827f4ad89580326a0d2db5ceb0e4`, #373 at
`151fe6e177416a5d83b5539a73d97737c12d1ce4`, #368 at
`457fab8cbdc5a407fc8f1373481314f2dec3f6fb`, #355 at
`b606c2553f877fa85968d90dc46598ce16897fbf`, #349 at
`a6af452568ee907835689829d0a871b208053382`, and #258 at
`6dc040c6b3ea0bfc4424bb7afb11b8afd7205d77`. Every open PR targeted
`main` and remained `BLOCKED`; #373 and #349 required a fresh independent
approval, #355 retained `CHANGES_REQUESTED`, and #258 had an approval-related
review gate but no terminal Checks. The exact-head Checks snapshot had no
failed bucket on any of these ten PRs; #392 had one passing, twelve pending,
and eight skipped Checks after the static-SQL suppression push. No protected
merge was authorized. The active no-force-push ruleset had no bypass actors.

The #392 security repair at exact head `1412313d` passed Semgrep with zero
findings, its two focused Global Ask history tests, and the backend suite with
848 passed and 17 environment skips. The existing central OSV repair is
`.github` PR #1209; the earlier #383 failure is retained as historical
evidence and is not treated as a current failure after its head advanced.

Closed without merge at the same observation:

- PR #386: `closed_without_merge` head `57a013deb88fc0b23ae6448c1d3474c770360a5e`.
- PR #377: `closed_without_merge` head `a638e28af4345750e3be92f2b0f23012b24598e0`.

### 4.1 Earlier open-PR and Checks refresh

Observed at `2026-08-21T20:13:22Z` from the GitHub API. The exact open
application heads were: #258 `6dc040c6`, #349 `a6af4525`, #355 `b606c255`,
#368 `392a9dd5`, #373 `151fe6e1`, #383 `4eaa0717`, #387 `16f6341a`, #392
`fc040997`, #393 `1ac3a17a`, #394 `5219ed8b`, and #397 `4bfa642c`. No PR in
this set was reported as merged into protected `main`.

- #397's latest restacked head had Full test, frontend, CodeRabbit, and Devin
  Review pending at observation. The prior review found and the latest pushes
  fixed the stale Korean translation key, fetched tenant-config draft race, and
  non-atomic settings update. There is no independent approval, so merge is not
  authorized.
- #383 had a failed `osv-scan`; both scanner invocations completed and wrote
  results before a cross-fork head checkout replaced the workspace repository
  and deleted the untracked base result. This is not a vulnerability verdict.
  Central `.github` PR #1209 at exact head
  `225c415179180606f9a935304f61b09dc3e5c084` confines both exact checkouts to
  `source/` while retaining the proven scanner output flags. It remains
  unmerged, so downstream checks still require a rerun after protected merge.
- The active protected ruleset `LineageWeave: no force pushes` has no bypass
  actors and only the `non_fast_forward` rule. All stack pushes above were
  normal fast-forward/new-branch pushes.
- **Hourly automation boundary:** the central
  [`ContextualWisdomLab/.github` merge scheduler](https://github.com/ContextualWisdomLab/.github/blob/main/.github/workflows/pr-review-merge-scheduler.yml)
  runs the queue scan every 30 minutes and the organization-wide sweep every
  15 minutes; the central target allowlist includes
  `ContextualWisdomLab/LineageWeave`. Its reusable review-repair
  workflow is product-neutral, so LineageWeave does not add a duplicate local
  timer. The same exact-head, review, Checks, and protected-merge gates remain
  authoritative; a scheduled run is not evidence of a merge.

### 4.2 Latest open-PR and Checks refresh

Observed at `2026-08-21T20:17:13Z` from the GitHub API. These are timestamped
historical observations, not current merge claims. The exact open application
heads were: #258 `6dc040c6`, #349 `a6af4525`, #355 `b606c255`, #368 `cc052a4d`,
#373 `151fe6e1`, #383 `4eaa0717`, #387 `16f6341a`, #392 `259ce60a`, #393
`1ac3a17a`, #394 `2aee6ace`, and #397 `8988fe71`. No PR in this set was
reported as merged into protected `main`.

- #397's latest restacked head had Full test, frontend, CodeRabbit, and Devin
  Review pending at observation. The prior review found and the latest pushes
  fixed the stale Korean translation key, fetched tenant-config draft race, and
  non-atomic settings update. There was no independent approval.
- #383 had a failed `osv-scan`. Both scanner runs completed before the
  cross-fork head checkout deleted the untracked base result. This was a shared
  workflow isolation defect, not a source vulnerability verdict. Central
  `.github` PR #1209 is the repair path; no duplicate product workaround was
  added in LineageWeave.
- The active protected ruleset had no bypass actors and only the
  `non_fast_forward` rule. All stack pushes above were normal updates.

### 4.3 Protected-merge gate refresh

Observed at `2026-08-21T20:23:51Z` from the GitHub API. PR #397 was open at
head `8988fe7175c8b03e27c9ea6fe3a554955eb350a4`, based on stack head
`259ce60abdb8e0d0993635facd8c987a2999cd58`; its frontend and full-test Checks
were pending and no independent approval was present. PR #368 was open at
documentation head `cee63d91c74515f5faf80d1aa8c07e345f1719df`, with required
Checks pending and `REVIEW_REQUIRED`. Neither PR was authorized to merge.

- PR #383's only failed current-head Check was `osv-scan`. Both scanner runs
  completed before the cross-fork head checkout deleted the untracked base
  result. This was a shared workflow isolation defect, not a dependency-
  vulnerability verdict. Central `.github` PR #1209 confines both exact
  checkouts to `source/`.
- PR #387's migration replay concern was already fixed at its current head by
  `eaea56d3`: `0103_tenant_settings.sql` uses `CREATE TABLE IF NOT EXISTS`
  and `ON CONFLICT DO NOTHING`.

### 4.4 Restacked tenant validation checkpoint

Observed at `2026-08-21T20:27:03Z` from the GitHub REST API. Parent PR #392
advanced normally to `658edd0932b413420e1361c34f31adb5e14d4d04`. PR #397 was
then restacked and pushed normally at
`3aa77fc848bbcb33f5d329a21eb2822653f3b7f0`, based on that parent. The focused
backend regression set passed (`28 passed, 135 deselected`), and the frontend
suite/lint/build passed (`204 passed`). Hosted Checks for the new #397 head
were pending, so approval and merge remained unauthorized. The subsequent full
backend run on the same restacked checkout passed (`862 passed, 17 skipped`,
with deprecation/security warnings only).

### 4.5 Parent restack follow-up

Observed at `2026-08-21T20:29:48Z` from the GitHub REST API. Parent PR #392
advanced normally to `943f011a6b9e7ff74ce9e8353ecf8d9c83f6b14f`; the change was
documentation-only. PR #397 was restacked again and pushed normally at
`367f76258b8437c65fb031ccbf3e352785327c06`, based on that parent. Its hosted
Checks restarted and remained pending, with no independent approval; merge was
not authorized.

### 4.6 Current exact-head audit snapshot

Observed at `2026-08-21T20:37:43Z` from the GitHub REST API. Parent PR #392 is
open at `877dbf50aa16b65b13b25539ae16dceb84210fb9`, targeting protected `main`
and blocked by its merge gates. PR #397 is open at
`e9a562a41395eacae9d7d04e84a9674397f4dbbf`, based on that parent; its hosted
Checks are pending and it has no independent approval. PR #368 was open at
baseline head `ca4c117ac58231f9ffdb12ab6cb88eb27db02522`, targeting `main` and
blocked by its merge gates. No merge is claimed for any of these PRs.

- The current tenant branch includes migration replay hardening for legacy
  blank or out-of-range identity values, plus worker-supervision changes from
  the parent stack. Local verification passed migration/worker tests (`22
  passed`) and the full backend suite (`864 passed, 17 skipped`).

### 4.7 Current exact-head audit snapshot

Observed at `2026-08-21T20:50:15Z` from the GitHub REST API and the current
follow-up worktree. This supersedes the earlier checkpoint wording above; the
earlier sections remain historical evidence.

- PR #397 merged into the non-main stack branch at head `77e2edee`; the stack
  now contains the resulting commit `2e51a777`. This is not a protected-main
  merge.
- PR #398 is open at exact head `5822948fe915542f1f916618d8905c3b4715d676`,
  based on stack head `2e51a777`, with `mergeable=true` and
  `mergeable_state=unstable`. Devin Review and the frontend/full-test Checks
  are pending, and no independent approval is recorded. It is not authorized
  to merge.
- PR #392 is open at exact head `7882bfc32ead971d27877558ca216a95cbaeb6e0`,
  targets protected `main`, and remains blocked with no formal review
  decision. PR #368 is open at `3d0adbb9c4bbef938584b1b1e79bf3f34a34df6e`,
  targets `main`, and remains blocked without formal approval.
- PR #383 remains open at `4eaa07172fde827f4ad89580326a0d2db5ceb0e4`; its
  current `osv-scan` failure is the previously documented central workflow
  result-path defect, while its source/security checks otherwise pass. PR
  #387 remains open at `16f6341a0feec262904c1ad9275ed73449444cf5`; its major
  checks pass, but it still lacks the required independent approval.
- Follow-up local evidence for #398 is backend `864 passed, 17 skipped, 14
  warnings`, frontend `22 files, 207 passed`, lint, and production build.
  The warnings are existing deprecations and a test-only short HMAC warning;
  they are not a failed product check.

### 4.8 Current exact-head follow-up

Observed at `2026-08-21T20:57:23Z` from the GitHub REST API and the current
follow-up worktree. PR #398 is now at exact head
`f101ab938f844ea12fa78b1cdf4ea1adaf07e962`, based on stack head `2e51a777`.
The follow-up includes the review repair that separates an empty numeric input
from the `0` value and retains the whitespace-only no-op save guard. Its
frontend suite is `208 passed` with lint and production build passing; the
backend evidence remains `864 passed, 17 skipped, 14 warnings`. Hosted Checks
restarted and remain pending, with no independent approval, so merge is not
authorized. Parent PR #392 is currently at `a6d754a7` and baseline PR #368 at
`331206425fa0acf3538f7c8edff261663f2ad606`; both remain open while their
respective merge gates recalculate.

## 5. Local Buyer-Surface Verification

Observed at `2026-08-21T13:06:25Z` in the authorized local stack using a
synthetic browser account and aggregate-only evidence:

- The first authenticated board load exposed a migration drift: `/api/posts`
  returned a server error because the runtime lacked the event evidence
  column expected by the current backend. Rebuilding and running the current
  migration image applied the pending migrations through `0114`; the same
  board then returned HTTP 200 for settings, current-user, lineage, and post
  list requests.
- The authenticated browser loaded 50 post-list entries, opened the detail
  popup, and rendered Event Lineage, Knowledge Graph, original-content, and
  issue sections without a frontend error. An image-heavy summary returned
  the explicit processing-state response (HTTP 503), so image evidence is not
  claimed as live-ready.
- The exact PR #366 frontend head passed 177 tests and a production build.
  Its browser build authenticated successfully and loaded the board; the
  disclosure-summary focus path remains covered by the unit test because the
  local authorized corpus did not expose a disclosure element in the sampled
  popup.

Observed at `2026-08-21T14:07:36Z` through the local browser runtime with a
synthetic Keycloak account and aggregate-only assertions:

- The real OIDC redirect completed and returned to the board with the signed-in
  state, authorized-scope disclosure, and logout control visible.
- The board exposed 50 post controls. Clicking one opened the detail surface;
  the popup exposed Event Lineage and Knowledge Graph sections, and its close
  control removed the detail surface.
- The site-map control changed the visible navigation state. No post title,
  person, organization, source identifier, or image payload was persisted in
  this repository. Image-heavy processing remains an explicit processing-state
  gap, not a live-success claim.

Observed at `2026-08-21T20:55:11Z` in the same local Compose browser runtime
with aggregate-only assertions:

- The Keycloak login flow completed, 50 authorized list entries were loaded,
  and one detail popup opened and closed successfully.
- The rendered popup contained the Event Lineage heading, Knowledge Graph
  region, and post-action group without a frontend error element. Aggregate
  response statuses were `200×60`, `302×1`, and `503×1`.
- The `503` is generated-evidence unavailability, so this run proves the UX
  path and error boundary only; it does not prove complete summary or VISION
  readiness.

Observed at `2026-08-21T20:59:49Z` across the same authenticated browser
session at the three guide breakpoints:

- At 1280, 800, and 390 CSS pixels, `scrollWidth` equaled `innerWidth` and
  the header top offset was zero. The phone viewport exposed the drawer
  trigger; its drawer opened and its in-drawer close control closed it.
- The desktop and tablet viewports retained the desktop navigation treatment,
  consistent with the guide's adaptive-web rule for tablets. This proves the
  observed responsive shell behavior only; protected-corpus content parity
  remains a separate partial gap.

Observed at `2026-08-21T21:06:09Z` after rebuilding the frontend from the
follow-up worktree and restoring the existing Compose runtime:

- Frontend and backend liveness returned HTTP 200. The live OIDC browser run
  again loaded 50 authorized entries, opened and closed one popup, and found
  Event Lineage, Knowledge Graph, and post-action DOM regions with zero
  frontend error elements.
- Response status counts remained `200×60`, `302×1`, and `503×1`; the latter
  is still the bounded generated-evidence availability gap documented above.

Observed at `2026-08-21T16:01:40Z` in a fresh local Compose browser session:

- OIDC login, an authorized post click, popup close, and the phone-width menu
  trigger all completed. The popup opened, but the summary request returned
  HTTP 503; no generated summary, 5W1H, VISION evidence, or graph rendering is
  claimed from this run.
- The local orchestrator returned HTTP 200 for its authenticated model
  inventory with nine registered models. A synthetic `mode=auto` completion did
  not complete within 30 seconds, so provider/model readiness remains open even
  though the Compose services are running.

Observed at `2026-08-21T16:16:02Z` in a fresh local Compose browser session
against the authenticated React surface:

- The UI/UX Guide v3.0 viewport checks passed at 1920×1080, 1280×1024,
  1024×768, 768×1024, and 375×667: each rendered document had no horizontal
  overflow, the authenticated header was sticky, the footer was present, and
  the phone drawer became visible only below the phone tier.
- The post popup opened and closed. Its DOM exposed Summary, Key events, and
  Event Lineage/graph sections; no R&R rows were rendered because the summary
  request returned HTTP 503 before an evidence object existed. This is not
  evidence that the R&R component is absent: `App.tsx` still renders it when
  persisted roles are available.
- The summary response explained the current buyer-visible gap: `Post summary
  is unavailable: image evidence is still being processed`. Aggregate
  PostgreSQL evidence was 43,839 source posts, 401 empty-body posts, 97
  persisted summaries, and zero summaries at current contract version 13.
  The content-ingestion job registry had 18 failed and zero queued/running
  jobs; no live image-summary completion is claimed.
- PR #384's popup CSS was then reduced to the standard three responsive tiers
  by removing its extra 1280px media query. The focused CSS contract, lint,
  TypeScript, and production build passed locally after the final concurrent
  head was reconciled; the earlier 199-test full-suite result preceded that
  concurrent commit and is not claimed as final-head evidence. Hosted Checks
  and independent approval remain open.

Observed at `2026-08-21T16:37:48Z` after one bounded operator retry through
the real Compose backend, Valkey, and orchestrator boundary:

- One terminal image-ingestion job completed with `succeeded` after roughly
  eight minutes. Its content endpoint reported `ready` with nine semantic
  units and one image; aggregate described images increased from 24 to 25.
- The same post's summary request was still pending after a 15-second browser
  observation window, and PostgreSQL still contained zero summaries at current
  contract version 13. This proves one bounded multimodal persistence path,
  not end-to-end Korean summary readiness or corpus completion.
- The remaining aggregate image state was 421 `failed` and 12,377
  `unavailable` images. Do not bulk retry until provider throughput, bounded
  retry policy, and buyer-visible failure/retry UX are separately accepted.
- PR #258's exact head `6621eb116a4e92eb33eeae989c70fbc602450c51` now
  restarts a whole lineage group when an optional LLM adjudication channel
  fails mid-group, preventing mixed LLM and deterministic edge scores. Local
  verification at that head passed 976 backend tests (17 environment skips),
  221 frontend tests, lint, and production build; hosted Checks remain queued
  and no independent approval or merge commit is present.
- PR #258 then corrected the Unreleased changelog's Buyer-terminology ADR
  reference from 0119 to the proposed ADR 0131 on that PR branch; the focused
  reconstruction and adjudication tests still passed at the pushed
  documentation head. ADR 0131 is not present in the protected repository
  until its PR merges.

Observed at `2026-08-21T17:52:18Z` in an authenticated Playwright browser run
against the local runtime, using the eleven supplied defect routes and
aggregate-only assertions:

- OIDC login completed with the local development account. Each of the eleven
  post routes opened a detail dialog, its close control was clicked, and the
  dialog closed again; no route produced horizontal overflow at 1280x1024.
- Event Lineage and the translated Keyman section were present in all eleven
  dialogs. A footnote evidence marker was visible in one route and a rendered
  table in one route. Five Keyman list items appeared across two routes; the
  remaining nine showed the explicit no-Keyman state. This distinguishes a
  real empty extraction signal from a missing panel, while Keyman/entity
  quality and coverage remain open product gaps.
- The run intentionally did not persist or print post titles, people,
  organizations, source identifiers, credentials, tokens, or body text.

These observations are runtime evidence, not a claim that the corresponding
PRs are merged. The image-processing state and protected-corpus parsing cases
remain open gaps.

### Pull-request verification checkpoints

The dependency-stack order below is intentional; its UTC timestamps, rather
than entry position, define the observation sequence.

Observed at `2026-08-21T17:10:21Z` on PR #387's exact head
`4faf9a31371195c5ec63fca42a5afbb93a95369b`:

- A real PostgreSQL schema fixture initially raised `NameError` because the
  0102 project-event migration path was missing. The fixture now applies 0102
  before 0105; the focused schema and lineage tests passed.
- The API fixture now applies the 0105 channel-evidence migration, and the
  rebuild endpoint passes the configured contextual-orchestrator adjudication
  client; the PostgreSQL import path preserves the same client. Local backend
  regression passed 768 tests with 17 environment skips; frontend lint, 143
  Vitest tests, and production build passed.
- Devin's remaining observations about uniform channel sets and LLM
  availability are documented in the proposed ADR 0124 on the PR branch;
  active weight ordering was made deterministic, and that branch ADR records
  the orchestrated rebuild/import boundary. The ADR is not present in the
  protected repository until its PR merges. Hosted Checks are queued and no
  independent approval or merge commit is claimed.

Observed at `2026-08-21T18:28:15Z` on PR #388's exact head
`86ac1d41d0e1acb9f29588adbdc8138ba822cef5`:

- The browser fallback preserves footnote roles for synthetic HTML footnote
  lists, Word `MsoFootnoteText`, and OOXML footnote containers. Anchor tags no
  longer become false leading indentation in this path. The stacked follow-up
  also closes HTML footnote containers reliably and suppresses an empty
  container's internal control marker.
- The branch now includes the current #387 parent through a regular merge
  commit. Footnote detection is bound to class/role attributes and anchor-tag
  matching no longer strips tag names that merely start with `a`. A labeled
  `div` wrapper around an unlabeled HTML list now marks the nested footnotes,
  while closing the wrapper returns to ordinary content. Local verification
  passed 149 frontend tests, lint, build, and diff check. The PR was merged into
  the non-main #387 stack base with merge commit
  `068ed6a44a7235e2f996450f0d6a7948bdd8732a`; this is not a protected-main
  merge.

Observed at `2026-08-21T18:28:15Z` on PR #389's exact head
`788bacd998634f09ca7debc1745fe279d788122f`:

- The buyer-facing fallback renders a Markdown table in a normal source body,
  including an empty cell, without converting ordinary pipe-delimited prose.
  Persisted text units use the same renderer, while separator-free OCR rows
  remain supported only in the image-evidence path. Candidate pipe rows are
  buffered until a valid Markdown separator and data rows confirm a table, so
  a lone pipe line cannot split the surrounding paragraph. The #388 wrapped
  footnote fix is included through a regular stack merge. The PR ref also
  contains the current backend lineage parent, so exact-head verification
  passed 21 focused backend tests and 155 Vitest tests, lint, production build,
  and `git diff --check`. The PR was merged into the non-main #388 stack base
  with merge commit `778c5df1223ed60a6494e8896079b3ece97669f4`; this is not a
  protected-main merge.

Observed at `2026-08-21T18:29:27Z` on PR #387's exact head
`13c102532f4485c732a83c7741e0844c77f082e5`:

- The Event Lineage channel-evidence persistence check now budgets one
  half-quantum per six-decimal contribution plus a small floating-point guard,
  so normal three- and four-channel edges cannot abort rebuild/import solely
  because of storage rounding.
- A four-channel regression covers the former failure boundary. The async
  rebuild now offloads synchronous reconstruction and the visible graph bounds
  evidence reads to visible endpoint IDs. The rebuild transaction now starts
  only after reconstruction, and the pooled connection is released until the
  atomic replacement write, so slow orchestrator work cannot hold a pooled
  connection idle in transaction. The current branch also includes the
  merged Markdown-table and structured-footnote stack through regular merges.
  Local verification on this exact head passed 770 backend tests with 17
  environment skips; hosted Checks were non-terminal and no independent
  approval or protected-main merge was present.

Observed at `2026-08-21T18:27:23Z` on PR #390's exact head
`e2f0894b03036ea0881c00ec33c44da28e4a1dbd`:

- The follow-up keeps pipe-bearing list items as separate semantic segments,
  then merges the current stacked base `778c5df1` normally to restore PR
  ancestry. Local verification passed 156 frontend tests, lint, production
  build, and `git diff --check`. The PR was merged into the non-main #389 stack
  base with merge commit `b020378710a0e405974538d80f7ef68ae3badd7c`; this is
  not a protected-main merge.

Merged at `2026-08-21T18:54:35Z` from PR #391's exact head
`e099a916cec6f06b86f335d31c89e01aae248dfd`:

- Nested-list indentation now survives a block child such as
  `<li><p>Child</p></li>`; the regression is covered by the wrapped-child
  fixture. Local verification passed 157 frontend tests, lint, production
  build, Storybook build, and `git diff --check`. The normal stack merge into
  #387 produced `16f2b13caad10f4d999293d623405aefadeda52e`; this is not a
  protected-main merge.

Observed at `2026-08-21T18:56:50Z` on PR #387's exact head
`16f2b13caad10f4d999293d623405aefadeda52e`:

- The remote branch advanced again after the interaction and migration-test
  repairs. No failed Checks were observed; 14 hosted Checks remained pending
  and no independent approval was present.

Observed at `2026-08-21T18:56:50Z` on PR #383's current head
`6af3adc3e08fd1b0b11182d8cf3714b847c71ea8`:

- `TypeError` from post-chat/global-agent and post-content-worker paths remains
  classified as an internal failure, while provider transport/configuration
  errors retain `provider_unavailable`. The current head has no failed Checks
  observed, but hosted Checks remain non-terminal and no independent approval
  or protected merge commit is present.

- The former hosted `osv-scan` job `96871880120` failed after both scans exited
  zero because the cross-fork head checkout replaced the repository workspace
  and removed the untracked base result. This is the same central defect
  addressed, but not yet merged, by `.github` PR #1209; the application PR
  remains unmergeable until its current Checks and approval gates pass.

Observed at `2026-08-21T18:39:50Z` on PR #349's exact head
`202194a2d9ba6da49a011ca6127a00f6bf5394ba`:

- The ontology source cursor now uses `src.v2.` AES-GCM with a fresh 96-bit
  nonce and prefix/version associated data; the custom v1 keystream format is
  rejected. The concurrent ontology page retry repair remains included.
- The PR branch's proposed ADR 0125 records the decision and NIST SP 800-38D
  APA 7 reference; it is not yet present in the protected repository. The
  static SQL review contract repair passed 17 focused tests and compilation;
  hosted Checks remained non-terminal and no independent approval was present.

Observed at `2026-08-21T19:33:40Z` from the GitHub API:

- PR #392 is open at exact head `1412313d421445c1246a6970c5ab71a6304a483d`,
  targeting protected `main`; its required Checks are queued and no formal
  independent approval is present. Stacked PR #395 added buyer-visible image
  region locations and merged normally into the feature branch with merge
  commit `8502f261931b4a06ba19a33da470a47c53ed02b3`; this is not a protected
  `main` merge.
- PR #393 is open at exact head
  `97baed032533a71c6a04b51d7c70df6df535e53b`, with auto-merge armed and all
  current hosted Checks queued. PR #394 is open at exact head
  `5602096b61272a2ccb0c9997cbaddd261fa165af`, also with its required Checks
  queued; its source-indentation evidence change has local focused verification
  but no protected merge claim.
- LineageWeave PR #383 is open at exact head
  `4eaa07172fde827f4ad89580326a0d2db5ceb0e4`, with its OTel/API/Valkey/session
  Checks queued and normal auto-merge armed. Governance-risk-compliance PR #51
  remains open at exact head `1a8f90dd15f37ffc86b8a0efd217a8b2812e5f99`;
  product checks are successful while its shared OSV output check remains
  queued, and the GRC repository does not permit auto-merge.
- These observations are current queue evidence only. They do not convert
  queued Checks into success or authorize a protected merge.

## 6. Organization OpenTelemetry Evidence Boundary

The organization GRC boundary is governance-risk-compliance PR #51 at exact
head `1a8f90dd15f37ffc86b8a0efd217a8b2812e5f99`. It emits W3C-parented server
spans, low-cardinality request and authorization metrics, and redaction-safe
structured request logs through the opt-in `OTEL_EXPORTER_OTLP_ENDPOINT`.
GRC is the organization control and evidence boundary, not a raw span store:
it must not copy prompts, post bodies, images, provider responses, secrets, or
an ad-hoc `user_account + post_id` session key.

LineageWeave PR #383 at exact head
`4eaa07172fde827f4ad89580326a0d2db5ceb0e4` emits bounded API/Valkey/session
telemetry, and contextual-orchestrator PR #818 at exact head
`f5e8107df065fe83ff616f92f070feeb3b153288` preserves the same post-scoped
session correlation across provider, Responses, structured-output, VISION, and
embedding work. These are separate open, protected PRs; their current Checks
are not terminal and no independent approval or merge is claimed.

This establishes the organization integration contract, not production
collector acceptance. Collector delivery, retention, access review, dashboard
SLOs, and no-export rollback remain deployment evidence to be recorded by GRC.
The current GRC `osv-scan` failure is the shared workflow's cross-fork checkout
isolation defect, not a source vulnerability verdict; no protected merge or
bypass is authorized until the central repair and exact-head Checks pass.

Observed at `2026-08-21T19:36:33Z` from the current hosted Checks:

- contextual-orchestrator PR #820 remains open at exact head
  `4959e805c5724e7d1620639ab0151a992d717a0c`. Its unit, property, fuzz,
  supply-chain, Semgrep, and Strix checks passed; only `osv-scan` failed after
  the cross-fork head checkout deleted the base result produced by the scanner.
- The central repair is ContextualWisdomLab/.github PR #1209 at exact head
  `225c415179180606f9a935304f61b09dc3e5c084`. Downstream OSV checks must be
  rerun after its protected merge; no local suppression is valid.
- This is operational evidence for the organization boundary, not a claim that
  a collector accepted telemetry or that any protected PR merged.

## 7. Next Implementation Order

1. Revalidate open PRs #258, #349, #355, #368, #373, #383, #387, #392, #393,
   and #394 at
   their exact current heads as Checks and formal independent approvals arrive;
   the #388/#389/#390 stack merges are already recorded above, so process the
  open #387 parent only after its current-head gates pass. PR #392 is a
  separate main-targeting product follow-up and remains subject to the same
  gates.
   Verify the synthetic footnote/table cases in the authenticated browser and
   use the protected external corpus only for aggregate, non-identifying
   runtime evidence.
2. Resolve image DOM-region recognition, OCR, semantic table rendering, and
   buyer-facing caption separation through contextual-orchestrator VISION.
3. Verify 5W1H, multi-project event separation, Keyman affiliation, and
   customer-master ABAC against authorized real PostgreSQL data in the protected
   external runtime, returning only aggregate or derived non-identifying
   evidence to repository artifacts.
4. Keep the GRC and contextual-orchestrator OTEL evidence contracts aligned
   with the exact application instrumentation; validate live collector delivery
   separately from source and PR evidence, then rerun downstream OSV checks
   after central `.github` PR #1209 is protected.

*This document is continuously updated by the hourly automated agent loop.*
