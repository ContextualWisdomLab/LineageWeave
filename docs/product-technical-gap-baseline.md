# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-23 23:49 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.
> Identifying post identifiers, organization names, and production record keys
> must never appear in this file.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 55 open PRs and 19 open issues. No independently
approved current head was available for a protected squash-merge. Branch
protection / rulesets continue to require independent exact-head review;
the authenticated GitHub identity that authors these PRs cannot self-approve.

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

| PR | Result | Evidence boundary |
| ---: | --- | --- |
| #347 | merged as `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` | Korean UI standards on the current protected head |
| ContextualWisdomLab/.github #1248 | merged | central Strix scope repair is available to subsequent reruns |
| ContextualWisdomLab/.github #1258 | open; blocked; no auto-merge | pnpm `--trust-lockfile` only on major >= 11; Jest keeps native `--coverage`; no invented Vitest instrumenter |
| ContextualWisdomLab/.github #1259 | open; blocked; no auto-merge | thin LineageWeave hourly review-repair caller at minute 4; supersedes #1086 stack driver |
| LineageWeave #426 | open; blocked; auto-merge armed | shared login `tsc` repair and ontology Pages stack; exact-head approval still required |
| LineageWeave #494 | open; blocked; no auto-merge | overlapping login repair; retain only value not already owned by #426 |

The Grok durable hourly loop and the central thin GitHub Actions caller
ContextualWisdomLab/.github#1259 (minute 4, `pr-review-fix-scheduler.yml`)
both target this repository. Do not add a LineageWeave-local duplicate
workflow. OpenCode coverage-evidence currently fails pnpm 9.15.9 heads on
`--trust-lockfile` (a pnpm 11.3 flag) and on a synthesized `--coverage`
flag; ContextualWisdomLab/.github#1258 is the exact-head repair.

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
- Semantic paragraph/list/table/image-region units that preserve source and
  provenance instead of flattening a record into one body string.
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
| #426 | `d4e9548661bdd71a0c2cd683796959299eec498e` | Login `tsc`, ontology Pages, and the stacked namespace map formerly reviewed as #492 (`38f3734f58477bad04f82758fc685e798e9d4b7b`) | Shared frontend typecheck and public ontology publication on protected `main` |
| #494 | `7eb5b2a89a6f32785bbbaf89126cb1ba931a03a8` | Overlapping login repair | Audit for unique value after #426; do not create a second shared dependency |
| #497 | `4de605b1ee512aac78c6ce04da24af77b7b8b3a2` | Non-identifying gap baseline (ADR 0001) | Removes identifying post identifiers from the current tree; protected history still requires incident remediation |
| #429 | Not captured | `/healthz` routes to the liveness probe | Operability: liveness vs settings mix-up |
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

### 3.5 Gap-baseline documentation queue (superseded by this file)

PRs #368, #440–#450, #455, #463, #479 rewrite slices of this baseline.
Once this non-identifying inventory lands on protected `main`, those
docs-only heads should be closed as superseded rather than merged as
conflicting rewrites. Do not merge an identifying baseline over this file.
Do not fold this rewrite back into #426 or #494; #426 owns the shared login
typecheck and #494 must remain limited to any independently verified unique
value.

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
| Protected release | 55 PRs open; no independent current-head approval; frontend `tsc` broken on `main` until #426 merges | Terminal exact-head checks, no unresolved threads, independent OpenCode/Strix/Noema approval, protected squash-merge SHA |
| Shared frontend gate | Unauthenticated `AdminPanel` + unused OIDC helpers failed `tsc -b` on `main` | #426 on protected `main`; revalidate #494 for unique value, then subsequent PRs rebase and stay green without duplicating the login patch |
| Identifying baseline regression | `main` gap file listed real post identifiers; this head cleans the current tree but protected history remains exposed | Land this non-identifying rewrite, then complete an approved incident/history-remediation process (ADR 0001) |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419) | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph, table, list, formula, and indentation work exists across stacks (#394, #427, #448–#450) | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Calendar / Naruon | Pseudo-CalDAV remains on `main`; #355 carries the projection contract | Naruon-owned projection, issue #336/#338 acceptance, no invented events |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | TEPP and fast-mlsirm adapters present or under review | Persisted accepted envelopes, calibration/recovery RMSE, no invented theta |
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

## 8. Evidence boundaries

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

## 9. Next acceptance loop

1. Land ContextualWisdomLab/.github#1258 so OpenCode coverage-evidence can
   complete LineageWeave JavaScript tests on pnpm 9.15.9.
2. Land LineageWeave#426 so the shared frontend typecheck and ontology Pages
   stack are on protected `main`; then audit #494 and retain only unique value.
3. Land this head so ADR 0001 holds on protected `main`.
4. Request independent exact-head review; squash-merge only after that review
   and current checks. Enable auto-merge rather than waiting as a blocker.
5. After ContextualWisdomLab/.github#1259 is on protected `.github` main, the
   minute-4 caller owns the GitHub Actions heartbeat. Close superseded
   docs-only baseline PRs (#368, #440–#450, #455, #463, #479) once this file
   is on `main`.
6. Merge smallest shared-gate repairs next (#429, #428, #393, #436, #439)
   when independently approved.
7. Advance user-visible gaps in leverage order: Event Lineage evidence (#387 /
   #274), Naruon calendar (#355 / #336), SKOS aliases (#480 / #482), ontology
   explorer (#349 / #341), Ask Agent (#415–#422 / #358–#363).
8. Keep psychometric tests as true-parameter recovery (RMSE), never fixture
   tautologies.
9. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
10. Fix only evidence-backed failures and repeat the protected merge gate.

## 10. Spec pointers (derive, do not fork)

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
