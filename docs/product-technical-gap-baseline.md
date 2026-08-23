# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-24 01:08 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.
> Identifying post identifiers, organization names, and production record keys
> must never appear in this file.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 58 open PRs and 19 open issues. The audited dependency
set (#426, #496, #499, and #505) had zero approving reviews. Branch
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
| ContextualWisdomLab/.github #1258 | `9b5dba9f558d20dbb651b409ea9fa54a865e3405`; auto-merge armed; blocked on independent review | `--trust-lockfile` only on pnpm 11.3+; Jest keeps native `--coverage`; no invented Vitest instrumenter |
| ContextualWisdomLab/.github #1259 | `6041f2aa9e23af5850cd83fa838a3eb6c45d84b9`; auto-merge armed; blocked on independent review | thin LineageWeave hourly review-repair caller at minute 4; supersedes #1086 stack driver |
| LineageWeave #426 | `a2daa92438a0ea337c9567b0c7abe3607ce3cb94` (this stack) | open, mergeable but blocked, review required, auto-merge armed; 19 threads resolved, zero approvals; ontology publication coverage is 99% rather than the required 100%, while Strix and coverage remain pending |
| LineageWeave #429 | `3763e1335cd3ac38b5e02b964ab49af34c8d73a0` | open, mergeable but blocked, review required, auto-merge armed |
| LineageWeave #494 | `7eb5b2a89a6f32785bbbaf89126cb1ba931a03a8` | login-only overlap; auto-merge armed; do not fold this baseline back into #494 |
| LineageWeave #497 | `07554b238a822e4423f8e6b4c000e5882fe49163`; merged as `250f20e8a6f830479ce904448cd29ab1a106aeef` into #426 only | ADR 0001 baseline is present on this hidden stack, not on protected `main` |
| LineageWeave #498 | `35823d889c5360ebf2152ed5679d7c22d6832545` | `/healthz` + docstring coverage; overlaps #429; blocked on independent review |
| LineageWeave #496 | `195ddf597c8eceaeaa00c9c86dc8103a4c7a8b89` | accepted TEPP receipts remain Running during an unavailable recheck; open and blocked, 20 checks passing with Strix/coverage pending, 21 threads with 1 unresolved code-quality thread, zero approvals |
| LineageWeave #499 | `a985f820af7a6552bcf32860b35b513e213a498c`; merged as `8f43d7fd17ae7ae9c197fe89ddb4beee82a2886a` into `docs/customer-master-scope-adr` only | channel-weight estimation is hidden-stack evidence, not protected-`main` evidence; local descendant `715ca0c6b7da87d0f3ed336ec40a2838f9e9eb8b` is not delivered to a remote branch or PR |
| LineageWeave #505 | `fd05703d576b6cf5bc7934f6a82fc1eeea2bdccd` on #490 head `d806bb960c12ad36f6c346831f6496299a34a3f8` | planned-facility intent evidence is an open stacked PR; mergeable but unstable, 0 threads and approvals, 1 check passing and 3 pending |

This documentation is now owned by the open LineageWeave#426 stack because
#497 merged into that branch rather than protected `main`. #426 owns the login
`tsc` repair, ontology Pages, and this non-identifying baseline. #494 is the
login-only overlap and must not receive this file again. #505 depends on #490;
#499 and its undelivered local remediation are not dependencies that #426 or
protected `main` may claim. If any exact head changes, re-fetch and recheck the
diff, checks, threads, and approvals before making a lifecycle claim.

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

Heads below were open at the snapshot time and are queue evidence, not
protected-main release evidence. Recheck
SHA, checks, unresolved threads, and independent approval immediately before
any merge claim. Do not self-approve, force-push, or transfer stale review
evidence across heads.

### 3.1 Merge-blocking and shared-gate repairs

| PR | Observed head | Intent | Gap it closes when merged |
| ---: | --- | --- | --- |
| #426 | `a2daa92438a0ea337c9567b0c7abe3607ce3cb94` | Login `tsc`, ontology Pages, namespace compatibility, and canonical baseline ownership | Shared frontend typecheck and public ontology publication on protected `main`; current ontology coverage gate still fails at 99% |
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
| #490 | Wire remaining ADR 0133–0137 surfaces | Consolidated product stack |
| #505 | Planned-facility relationship intent, stacked on exact #490 head `d806bb960c12ad36f6c346831f6496299a34a3f8` | Source-grounded relationship evidence; no protected-release claim |
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
| #496 | Durable accepted TEPP receipts and recheck continuity; exact head `195ddf597c8eceaeaa00c9c86dc8103a4c7a8b89` |
| #499 | Psychometric channel-weight estimation merged only into a hidden docs stack; local fail-closed remediation `715ca0c6b7da87d0f3ed336ec40a2838f9e9eb8b` remains undelivered |

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
| Protected release | 58 PRs open; the audited #426/#496/#499/#505 dependency set has no independent current-head approval; #426 also has one failing and two pending required checks | Terminal exact-head checks, no unresolved threads, independent OpenCode/Strix/Noema approval, protected squash-merge SHA |
| Shared frontend gate | Unauthenticated `AdminPanel` + unused OIDC helpers failed `tsc -b` on `main` | #426 on protected `main`; revalidate #494 for unique value, then subsequent PRs rebase and stay green without duplicating the login patch |
| Identifying baseline regression | `main` gap file listed real post identifiers; this head cleans the current tree but protected history remains exposed | Land this non-identifying rewrite, then complete an approved incident/history-remediation process (ADR 0001) |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419) | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph, table, list, formula, and indentation work exists across stacks (#394, #427, #448–#450) | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Calendar / Naruon | Pseudo-CalDAV remains on `main`; #355 carries the projection contract | Naruon-owned projection, issue #336/#338 acceptance, no invented events |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | #496 preserves an already accepted TEPP receipt across an unavailable recheck but remains open with one unresolved review thread and pending gates; #499 is merged only into a hidden docs stack, and its fail-closed local descendant `715ca0c6b7da87d0f3ed336ec40a2838f9e9eb8b` is not delivered | Protected delivery of persisted accepted envelopes and fail-closed weighting; calibration/recovery RMSE; no invented theta |
| Planned-facility intent | #505 is stacked on open #490 rather than protected `main`; its exact head has one passing and three pending checks, no threads, and no approvals | Land and revalidate #490 first, then rebase #505 and verify source-grounded relationship evidence on the exact candidate head |
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

1. Repair #426's ontology-publication coverage from 99% to the required 100%,
   then let its queued coverage and in-progress Strix checks settle on the
   resulting exact head.
2. Obtain two independent exact-head approvals for #426 and land that stack on
   protected `main`; auto-merge being armed does not itself satisfy the gate.
3. Resolve #496's current code-quality review thread and pending gates while
   preserving the durable accepted-receipt behavior across unavailable rechecks.
4. Keep #505 behind #490: validate and land #490 first, then rebase and
   revalidate #505 before making any protected-release claim.
5. Treat #499's hidden-stack merge and local descendant
   `715ca0c6b7da87d0f3ed336ec40a2838f9e9eb8b` as unavailable until the intended
   fix has a current remote PR and an independently reviewed protected path.
6. After ContextualWisdomLab/.github#1259 is on protected `.github` main, the
   minute-4 caller owns the GitHub Actions heartbeat. Close superseded baseline
   PRs (#368, #440–#450, #455, #463, #479) once #426 is on
   `main`; #368 and #479 also carry already-covered login changes.
7. Merge smallest shared-gate repairs next (#429, #428, #393, #436, #439)
   when independently approved.
8. Advance user-visible gaps in leverage order: Event Lineage evidence (#387 /
   #274), Naruon calendar (#355 / #336), SKOS aliases (#480 / #482), ontology
   explorer (#349 / #341), Ask Agent (#415–#422 / #358–#363).
9. Keep psychometric tests as true-parameter recovery (RMSE), never fixture
   tautologies.
10. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
11. Fix only evidence-backed failures and repeat the protected merge gate.

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
