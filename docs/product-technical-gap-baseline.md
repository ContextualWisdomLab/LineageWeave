# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-23 22:28 KST. This repository records synthetic
> fixtures and aggregate, non-identifying runtime evidence only. Open PRs and
> local checks are not protected-default-branch release evidence.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The live queue contained 52 open PRs and no independently approved head. Six
current heads had an aggregate failed check state, eight had pending checks,
and four retained unresolved review threads. Those results must be re-fetched
against the current head before remediation or a merge claim.

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

Current active-PR evidence remains outside protected `main`:

- PR #258 at `2e2ddd1998734d6e29dad0ba916053dd8cf27983` carries ADR 0146's
  distributed MCP principal rate-limit decision. Its aggregate checks failed;
  it had no unresolved thread or exact-head approval.
- PR #355 at `de7f78c5afe1a9e7f50303da9b5ee81a6f767633` carries ADR 0145's
  Naruon calendar projection boundary. Its checks were pending, with no
  unresolved thread or exact-head approval.
- PR #490 at `87f74c6395b7090421965359222fa29f9dd9a84d` is the current carrier
  of the consolidated product stack and includes ADR 0143. ADR 0144 was absent
  from both this exact tree and protected `main`, so it is not attributed to
  this head. Its aggregate checks failed, with no unresolved thread or
  exact-head approval.
- PR #491 at `29817c4171f9ce7990ffcb2e6abb1faf6a27f84c` proposes ADR 0157's
  public ontology namespace identity without a production namespace rewrite.
  Its checks were pending, it retained one unresolved thread, and it had no
  exact-head approval.

## 3. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | 52 PRs remained open, none had an independent current-head approval, six current heads had an aggregate failed check state, eight had pending checks, and four retained unresolved review threads | Terminal exact-head checks, no unresolved threads, independent approval, and a protected merge SHA |
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
