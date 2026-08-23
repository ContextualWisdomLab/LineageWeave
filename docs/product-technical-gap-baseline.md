# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-24 01:42 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.
> Identifying post identifiers, organization names, and production record keys
> must never appear in this file.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 58 open PRs and 19 open issues. The audited dependency
set (#426, #496, #499, #505, #507, and #509) had zero approving reviews. Branch
protection / rulesets require two independent approvals, resolved review
threads, and last-push approval; the authenticated GitHub identity that authors
these PRs cannot self-approve.

Protected `main` currently has two defects that poison downstream work:

1. Unauthenticated login rendered `AdminPanel` with an undefined access token,
   so `tsc -b` failed on `main`. LineageWeave#426 owns the shared login repair
   (OIDC return-URL helpers; no admin settings before authentication) and the
   ontology Pages stack. #494 overlaps this contract and must preserve only
   demonstrably unique value rather than becoming a second dependency.
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
| LineageWeave #426 | `b2d9bdb07cd8267742bbd5c8bad13985bd250aef` (this stack) | open, mergeable but blocked, review required, auto-merge armed; all 21 threads resolved, zero approvals; 9 checks passing, 10 pending, and 8 skipped |
| LineageWeave #429 | `3763e1335cd3ac38b5e02b964ab49af34c8d73a0` | open, mergeable but blocked, review required, auto-merge armed |
| LineageWeave #494 | `327c359b35add7b8011542fb5bd07e625de41e29` | login `tsc` plus optional-extra collection skip; auto-merge armed; hosted frontend typecheck passing; do not fold this baseline back into #494 |
| LineageWeave #497 | `07554b238a822e4423f8e6b4c000e5882fe49163`; merged as `250f20e8a6f830479ce904448cd29ab1a106aeef` into #426 only | ADR 0001 baseline is present on this hidden stack, not on protected `main` |
| LineageWeave #498 | `35823d889c5360ebf2152ed5679d7c22d6832545` | `/healthz` + docstring coverage; overlaps #429; blocked on independent review |
| LineageWeave #496 | `78287c08309f614ca1de04612c3e15c555bed1c6` | accepted TEPP receipts remain Running during an unavailable recheck; the mixed-import review fix has 21 focused tests passing; open and blocked with 20 checks passing, 2 pending, all 22 threads resolved, and zero approvals |
| LineageWeave #499 | `a985f820af7a6552bcf32860b35b513e213a498c`; merged as `8f43d7fd17ae7ae9c197fe89ddb4beee82a2886a` into `docs/customer-master-scope-adr` only | channel-weight estimation remains hidden-stack evidence, not protected-`main` evidence; #507 is the clean protected-main restack of the fail-closed repair |
| LineageWeave #505 | `cbc6bd727d613216e8b0bf93b80d476205e2dd37`; merged as `c6d0ae57ca88684f3e7de992891adc2c208f06ed` into #490 only | merged into the non-default, unprotected parent branch rather than protected `main`; all 5 threads, including the 4 latest findings, are resolved; 4 checks passed and zero approvals |
| LineageWeave #506 | closed unmerged at `fd27f2d52766ac6cfe00e0713dcfc3fe938c6078` | its public PR head and pre-existing public history contain a real private runtime source-table identifier; this baseline intentionally neither names nor describes its value |
| LineageWeave #507 | `e4e5bf321b303248d14d735fbf717ef2f4c0ce81` directly on protected `main` | clean fail-closed weighting restack; open, mergeable but blocked, 17 checks passing, 1 failing, 2 pending, 7 skipped, all 7 threads unresolved, zero approvals |
| LineageWeave #490 | `fc3ea87470dc840e38aa36f9f0c25294c334734c` directly on protected `main` | open, mergeable but blocked, review required; migration 0138 is now the parent of #509; 10 checks passing, 1 failing, 6 pending, 7 skipped, no threads, and zero approvals |
| LineageWeave #509 | `bba8a8ac43a43db70c563dd9612ab74c3fbe7930` on #490 head `fc3ea87470dc840e38aa36f9f0c25294c334734c` | normally merge-restacked without force; unique diff is limited to the changelog, legacy-JSON fail-closed parser/test, and live PostgreSQL schema regression; local focused validation is 108 passed/1 skipped including 12 live PostgreSQL, migration vocabulary 54/55/54, compile and diff checks passing; hosted gates restarted at 1 passing/3 pending, no threads, and zero approvals |

This documentation is now owned by the open LineageWeave#426 stack because
#497 merged into that branch rather than protected `main`. #426 owns the login
`tsc` repair, ontology Pages, and this non-identifying baseline. #494 is the
login-only overlap and must not receive this file again. #505 is merged only
into #490's non-default branch; #509 contains its isolated fixes after a normal
merge-restack on current #490 migration 0138. That stack remains unprotected.
#499 remains hidden-stack evidence; #507 is the clean
protected-main delivery path for its fail-closed repair. If any exact head
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
The file is a safe, empty design-system boundary; popup/Event Lineage frames
are not yet present. Do not copy source-organization cover content into this
repository. Storybook, `ui-ux-pro-max-skill`, and Anti-Slop-UI remain the
scene and edge-case inventory for repeated web objects.

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
| #426 | `b2d9bdb07cd8267742bbd5c8bad13985bd250aef` | Login `tsc`, ontology Pages, namespace compatibility, and canonical baseline ownership | Shared frontend typecheck and public ontology publication on protected `main`; all 21 threads resolved, hosted checks pending, and no independent approval |
| #507 | `e4e5bf321b303248d14d735fbf717ef2f4c0ce81` | Clean fail-closed weighting repair restacked directly on protected `main` | Resolve all 7 review threads and the failing frontend gate, then obtain independent exact-head approval |
| #494 | `7eb5b2a89a6f32785bbbaf89126cb1ba931a03a8` | Overlapping login repair | Audit for unique value after #426; do not create a second shared dependency |
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
| #481 | Persist leftover LSIRM interaction-map coordinates | fast-mlsirm leftover pairs |
| #485 | Land leftover pair clicks on the named Post quality criterion | Same leftover surface |
| #490 | Wire remaining ADR 0133–0138 surfaces; exact head `fc3ea87470dc840e38aa36f9f0c25294c334734c` is still open against protected `main` | Consolidated product stack; #505's earlier merge here is not protected delivery, and one hosted check currently fails |
| #505 | Planned-facility relationship intent merged as `c6d0ae57ca88684f3e7de992891adc2c208f06ed` into #490 only | All review findings resolved, but the merge target is a non-default unprotected branch |
| #509 | Isolated #505 follow-up fixes at `bba8a8ac43a43db70c563dd9612ab74c3fbe7930` on exact #490 head `fc3ea87470dc840e38aa36f9f0c25294c334734c`; normally merge-restacked without force | Unique changelog/parser/test/live-schema diff; 108 focused passed, 1 skipped including 12 live PostgreSQL, migration vocabulary 54/55/54, compile/diff pass; hosted checks and independent review remain incomplete |
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
not merge an identifying baseline over this file. #494 likewise remains
limited to value independently verified as unique from #426.

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
| Protected release | 58 PRs open; the audited #426/#496/#499/#505/#507/#509 dependency set has no independent current-head approval; #426 has 10 pending checks, #490 has one failing check, and #507 has 7 unresolved threads plus one failing check | Terminal exact-head checks, no unresolved threads, independent OpenCode/Strix/Noema approval, protected squash-merge SHA |
| Shared frontend gate | Unauthenticated `AdminPanel` + unused OIDC helpers failed `tsc -b` on `main` | #426 on protected `main`; revalidate #494 for unique value, then subsequent PRs rebase and stay green without duplicating the login patch |
| Identifying baseline regression | `main` gap file listed real post identifiers; separately, closed #506 and pre-existing public history contain a private runtime source-table identifier, while current `main` and #507 trees are clean | Land this non-identifying rewrite, then coordinate ADR 0001 history remediation with security/privacy owners; do not reproduce the value, force-push, or delete evidence ad hoc |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419) | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph, table, list, formula, and indentation work exists across stacks (#394, #427, #448–#450) | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Calendar / Naruon | Pseudo-CalDAV remains on `main`; #355 carries the projection contract | Naruon-owned projection, issue #336/#338 acceptance, no invented events |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | #496 preserves an already accepted TEPP receipt across an unavailable recheck and has all 22 review threads resolved, 20 checks passing, 2 pending, and zero approvals; #499 is merged only into a hidden docs stack, while #507 is the clean protected-main restack of the fail-closed repair | Protected delivery of persisted accepted envelopes and fail-closed weighting; calibration/recovery RMSE; no invented theta |
| Planned-facility intent | #505 is merged only into open #490's non-default branch; its 4 latest findings are resolved, with actual fixes normally merge-restacked on #509 at `bba8a8ac43a43db70c563dd9612ab74c3fbe7930` over #490 migration 0138; #509's restarted hosted gates have 1 passing, 3 pending, and zero approvals | Complete #509 exact-head checks and independent review, then deliver the #490 stack through protected `main` before making a release claim |
| Accessibility and responsive UX | Unit coverage exists for major surfaces; Storybook inventory incomplete | Keyboard, screen-reader, mobile, and authenticated Playwright acceptance on the exact release head |
| Design tokens and repeated objects | Token extraction started (`CHANGELOG.d` badge-color tokens); Figma file is empty of product frames | Tokens in CSS + Storybook stories for board, popup, DAG, Ask, calendar, forms, charts |
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

1. Let #426's exact-head checks settle; its current 9 passing, 10 pending, and
   8 skipped checks are not a terminal protected gate even though all 21 review
   threads are resolved.
2. Obtain two independent exact-head approvals for #426 and land that stack on
   protected `main`; auto-merge being armed does not itself satisfy the gate.
3. Let #496's re-queued checks settle and obtain independent exact-head review
   while preserving the durable accepted-receipt behavior across unavailable
   rechecks.
4. Treat #505's merge as #490-only evidence. Finish #509's restarted hosted
   gates on exact head `bba8a8ac43a43db70c563dd9612ab74c3fbe7930`, obtain independent review,
   repair #490's failing gate, and deliver the resulting stack through
   protected `main` before a release claim.
5. Resolve #507's 7 current review threads and failing frontend check, then
   obtain independent exact-head approval for that clean protected-main path;
   do not credit #499's hidden-stack merge as protected delivery.
6. Coordinate the ADR 0001 history incident with security/privacy owners. Keep
   current `main` and #507 clean, never reproduce the private identifier, and
   do not force-push or delete public-history evidence ad hoc.
7. After ContextualWisdomLab/.github#1259 is on protected `.github` main, the
   minute-4 caller owns the GitHub Actions heartbeat. Close superseded baseline
   PRs (#368, #440–#450, #455, #463, #479) once #426 is on
   `main`; #368 and #479 also carry already-covered login changes.
8. Merge smallest shared-gate repairs next (#429, #428, #393, #436, #439)
   when independently approved.
9. Advance user-visible gaps in leverage order: Event Lineage evidence (#387 /
   #274), Naruon calendar (#355 / #336), SKOS aliases (#480 / #482), ontology
   explorer (#349 / #341), Ask Agent (#415–#422 / #358–#363).
10. Keep psychometric tests as true-parameter recovery (RMSE), never fixture
   tautologies.
11. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
12. Fix only evidence-backed failures and repeat the protected merge gate.

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
