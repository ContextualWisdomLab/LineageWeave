# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-24 01:52 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 55 open PRs and no independently approved head. Eighteen
current heads had an aggregate failed check state, eleven had pending checks,
and three current heads retained an unresolved review thread.
Those results must be re-fetched against the current head before remediation or
a merge claim.

Recent protected-default-branch evidence:

| PR | Result | Evidence boundary |
| ---: | --- | --- |
| #373 | merged as `cf419cd90676a7f8cf82fac356d4ee24468017a7` | protected merge verified after the live queue refresh |
| #420 | merged as `c7f4d6c1133e680befe076442f16ba5f1c722405` | protected merge verified; later main changes still require their own acceptance |
| #475 | merged as `02fe67005f25f2025ce29b403c42097838b751ad` | restored a non-identifying baseline; a later broad merge overwrote it and this repair removes the regression |
| ContextualWisdomLab/.github #1248 | merged as `9ad0ad50409561292b424d6f35a95d670a277e77` | central Strix scope repair is available to subsequent reruns |

The organization scheduler is the single review/repair control plane. Its
quarter-hour queue sweep and hourly heartbeat satisfy the hourly loop
requirement without a duplicate repository-local scheduler.

## 2. User-visible capability baseline

Substantially present in source or active PRs:

- PostgreSQL-backed import, normalized provenance, cutoff-aware analysis runs,
  source revisions, lineage reconstruction, and explicit unavailable states.
- Authenticated workspace navigation, post detail, localized summaries, 5W1H,
  R&R/Keyman, evidence citations, chat, organization hierarchy, and lineage DAG.
- Semantic paragraph/list/table/image-region units that preserve source and
  provenance instead of flattening a record into one body string.
- Contextual-orchestrator boundaries for adjudication, extraction, summaries,
  chat, embeddings, and VISION; null channels remain unavailable and are
  dropped from score fusion.
- W3C PROV-O projection through normalized provenance tables, with the
  knowledge graph retained as an explicit navigation projection.

These statements describe source capability, not authenticated production
corpus acceptance or protected release.

PR #486 merged as `f11a2cb546792622932011587fe6f6aa54c79948`
into non-default `docs/customer-master-scope-adr`. Its documentation follow-up
is branch commit `5ec42616e6b4ab6ed0b7757c299523110acb62ca`, but no open PR carries that
branch to `main`; both remain stack evidence, not protected-main release
evidence.

Subsequent stack evidence, verified at 2026-08-23 22:44 KST, also remains
outside protected `main`: PR #491 at
`1a5139f233f2dc484f970b25c4e1b51462dbedf8` merged normally as
`60efee9b9a97fa433f1d8a83f396c7f8d55df39e` into the non-default
`worktree-fix-frontend-build-break` branch. Its four-file documentation diff
records ADR 0157's public ontology namespace identity without a production
namespace rewrite. The exact stacked head passed the hosted full and frontend
suites, but the target-repository central review workflows did not run for
that non-default target. This is stack integration evidence, not evidence of a
protected `main` release or independent approval.

At 2026-08-23 23:00 KST, PR #492 at
`38f3734f58477bad04f82758fc685e798e9d4b7b` also merged normally as
`c8a4be8fc2417f05d53fb68d32d9e59c3d443e25` into that same non-default
branch. Its six-file, +166/-2 compatibility-publication slice is intentionally
minimal, but remains stack evidence only; it is not a protected-`main` merge
or independent approval.

The official repository Pages API was activated at 2026-08-24 00:53 KST with
`build_type=workflow`, public visibility, HTTPS enforcement, and repository-case
`html_url` `https://contextualwisdomlab.github.io/LineageWeave/`. Live
publication nevertheless remained incomplete: the lowercase
ontology URL, repository-case ontology URL, and repository-case
`namespace-compatibility.ttl` URL each returned HTTP 404. Source and active-PR
publication contracts therefore do not prove an available public endpoint.
Cross-repository organization-site PR #188 at
`3ac59eb7eb7122c101df77945abbe644922dbe34` provides the owned lowercase
route from LineageWeave artifact commit `c8a4be8f`; its 19 local tests passed
before the current provenance/semantics repair, whose focused suite passed 20
tests with zero Semgrep findings; its static acceptance returned HTTP 200. The PR remains open with hosted
Strix in progress, coverage evidence queued, no unresolved thread, and no
exact-head approval, so that result is not protected deployment evidence and
the live HTTP 404 remains authoritative.

The central Strix dependency is now superseding ContextualWisdomLab/.github
PR #1263 at `1fd718f3177d3e8ffe908aed38b50dc94e926f8d`. Its current source keeps the
provider-fallback and exact advisory-line boundary covered by eight shell cases
and 33 focused pytest cases. Three review threads arrived after that head and
hosted checks remain pending; it has no approval. Therefore the older #1213
stack and local green evidence do not authorize transfer of a Strix result.

Current active-PR evidence remains outside protected `main`:

- PR #258 at `52deb37294aa647e4be4b4b1c6448b52ba861e49` carries ADR 0146's
  distributed MCP principal rate-limit decision. Its current hosted checks
  were running while a failed Devin status remained; it had no unresolved
  thread or exact-head approval.
- PR #426 at `c0a77731d46dba5f951cf69df6578f35aa93a2d6` is the current
  prerequisite carrier for ontology publication and the merged ADR 0157 and
  compatibility-publication stacks. It had one unresolved review thread and no
  exact-head approval; hosted checks were pending. Results from its prior heads
  are stale, and Pages activation alone does not deploy this unmerged source.
- PR #355 at `6fc22a9471bfb4d94b18f884e012cd823b296382` carries ADR 0145's
  Naruon calendar projection boundary. Its aggregate checks failed, with no
  unresolved thread or exact-head approval.
- PR #417 at `c5c0929c68abf876de6c924d5a93b554d6bcadfb` preserves stale image
  summaries across provider refresh failures. Two focused unit tests and two
  API tests passed; it had no unresolved thread or exact-head approval.
- PR #494 at `b195b42dd327f6a6659cca315b34886ab11d38ed` keeps optional-extra test
  collection fail-closed without misclassifying non-skip hook results, uses the
  existing NumPy-only period-report mapping, tolerates non-UTF-8 optional source
  during collection, and restores the shared OIDC login gate after a concurrent
  regression. Its exact head passed ten collection tests, 83 frontend tests,
  lint, TypeScript compilation, and production build. It had no unresolved
  thread or exact-head approval; hosted checks restarted.
- PR #493 at `499c8b1bc4cdffff5bb985658bcb3821d312cedb` includes product-fix
  head `612c4cc1`, where the focused backend suite passed 13 tests, the App
  suite passed 81 tests, and lint plus diff-check were clean. The later head
  had no unresolved thread or exact-head approval, while hosted checks
  remained pending.
- PR #496 at `78287c08309f614ca1de04612c3e15c555bed1c6` carries savepoint,
  normalized TEPP analysis-run identifier, batched list/detail receipt, state
  progression, and replay-contract fixes. The current head also isolates the
  older optional outbox and reconstruction reads in savepoints so a missing
  optional table cannot poison the caller transaction. Its latest change keeps
  a durable accepted receipt Running across an unpersistable re-check; the
  exact-head receipt suite passed 21 tests.
  It had no unresolved thread or exact-head approval, while hosted checks were
  pending; local results are not protected-release acceptance.
- PR #498 at `35823d889c5360ebf2152ed5679d7c22d6832545` retained the public
  health probe, login return, and production docstring gate. Its informational
  review threads were resolved; it had no exact-head approval and hosted checks
  remained pending. This is source and test evidence, not a live-runtime claim.
- PR #439 at `5db6276c53e8f59499dbac0f59f6cbf0555b99f2` fixes the shared
  lineage-layout walk so a visible root feeding a cycle terminates, with a
  synthetic rooted-cycle regression. Ninety-five focused frontend tests and
  TypeScript compilation passed before the guarded fast-forward push. Its later
  informational thread was resolved; exact-head approval was absent, and hosted
  checks were pending.
- PR #501 at `b895aa57d8b7c8b70f8830ecf32a44972199e6a1` preserves the lineage
  channel-weight fallback transaction with the same savepoint boundary at both
  callers. Its informational thread was resolved; it had no approval and hosted
  checks were pending.
- PR #435 at `36164fbcc1bb15b8fab991dbe5629f719b74896c`, PR #500 at
  `487b5b487dddf2d40df71f6add88c7f07347c086`, and PR #502 at
  `accc33f1343a2ae3e5ad04447e7fce861c82d9b9` now share the existing safe
  OIDC return-URL persistence and remove the unreachable unauthenticated Admin
  render. Their exact composed heads passed frontend lint, respectively 140,
  140, and 147 tests, and production builds. Hosted checks restarted; none had
  an exact-head approval. Their aggregate hosted failures still require
  exact-head diagnosis before release.
- Stacked PR #504 at `166436d519341aa10ec9b32b4d67b1a24818f5c8`
  merged normally into non-default #426 and stops the PROV-O support profile
  from minting repository-case product IRIs. Its 67 focused tests and
  deterministic site build passed, but the stack merge is not protected-main
  release evidence. The stored project-mention migration remains deferred
  until #428, #484, and #426 reach protected `main`.
- PR #428 at `f81f831c14aa080f671fbdb781bf8afecdd36e82`
  makes migration 0103 replay idempotent while preserving operator-customized
  synthetic catalog rows. Five focused static tests and a twice-applied local
  PostgreSQL replay passed; hosted evidence remained pending and it had no
  exact-head approval.
- PR #507 at `6751623df553c1e26976cef26b12b0ec4d0e15cf`
  reuses that migration replay fix and the existing safe OIDC return helpers.
  Its review follow-up reused existing imports and a named helper; 36 focused
  backend tests passed. It had no unresolved thread, failure, or exact-head
  approval; hosted checks restarted.
- PR #490 at `494ccf53da6e4a12d54e171bbb6dfeea9b336ffc` is the current carrier
  of the consolidated product stack and includes ADR 0143. ADR 0144 was absent
  from both this exact tree and protected `main`, so it is not attributed to
  this head. The validated post-merge #505 migration correction was transplanted
  here because #505 merged before that source-branch commit; fifteen migration
  replay tests passed. Hosted checks restarted, with no unresolved thread or
  exact-head approval.
- Stacked PR #509 at `bba8a8ac43a43db70c563dd9612ab74c3fbe7930`
  was normally restacked and merged as `e4d692c6e5daede2af7c0e259d3fc5a4c1c7636a`
  into non-default #490 after its duplicate migration slice conflicted.
  Ninety-six focused tests and twelve PostgreSQL schema tests passed; that stack
  merge is not protected-main evidence.
- Stacked PR #511 at `3c61e8fd5de116231cdaf5b681e03878f825f5aa`
  aligns the Python reconciliation boundary with the database's strict
  `1e-6` constraint and reuses the shared login-return path. Twenty-one focused
  Python tests, 146 frontend tests, lint, and production build passed; hosted
  checks restarted with no unresolved thread or exact-head approval.

## 3. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | 55 PRs remained open, none had an independent current-head approval, eighteen current heads had an aggregate failed check state, eleven had pending checks, and three retained an unresolved review thread | Terminal exact-head checks, no unresolved threads, independent approval, and a protected merge SHA |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists across active heads | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph, table, list, and formula parsing exists across active stacks | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Scientific measurement | TEPP and fast-mlsirm adapters are present or under review | Persisted accepted envelopes, calibration/recovery evidence, and no invented theta |
| Accessibility and responsive UX | Unit coverage exists for major user surfaces | Keyboard, screen-reader, mobile, and authenticated Playwright acceptance on the exact release head |
| External integrations | Search, Zotero, calendar, and downstream consumer contracts are bounded | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| Release quality | Local focused/full suites have passed on individual PR heads | Repository-wide coverage, docstrings, Storybook, security, browser, and release evidence on one exact head |

## 4. Evidence boundaries

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

## 5. Next acceptance loop

1. Reproduce and repair the current Strix failure without weakening the
   scanner or transferring results across heads.
2. Re-fetch every open head, latest checks, unresolved threads, and independent
   reviews before any merge claim.
3. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
4. Reproduce user cases with synthetic fixtures or authorized aggregate
   runtime evidence, preserving `unavailable` explicitly.
5. Fix only evidence-backed failures and repeat the protected merge gate. Do
   not self-approve, force merge/push, bypass protection, or transfer stale
   review/check evidence across heads.
