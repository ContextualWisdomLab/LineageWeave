# Product & Technical Gap Baseline

> Audit date: 2026-08-23. This repository records synthetic fixtures and
> aggregate, non-identifying runtime evidence only. Open PRs and local checks
> are not protected-default-branch release evidence.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The current acceptance queue was re-fetched immediately before this update:

| Repository | PR | Exact head | State | Remaining gate |
| --- | ---: | --- | --- | --- |
| LineageWeave | #392 | `a73d98850f985d0996bfbc4f2b1f17787710f206` | open, blocked, auto-merge armed | independent review and required protected checks |
| LineageWeave | #387 | `55a13f3473789a9481061ca2cd1f9ea042fc5902` | open, blocked, changes requested, auto-merge armed | current-head approval and Strix rerun after the central scope fix |
| LineageWeave | #405 | `0ac80616cb723a7810acae7c945fb12721a6cf7c` | open, blocked, changes requested, auto-merge armed | independent current-head approval |
| LineageWeave | #421 | `33ec5cd521bcf861db64b9f0c1faac3b3bf4deff` | open, blocked, auto-merge armed | terminal Strix result and independent review |
| LineageWeave | #426 | `11a60b370d7b5783733febb593e8f91678cc403d` | open, blocked, review required, auto-merge armed | independent current-head approval; current checks are terminal-success |
| LineageWeave | #468 | `48c7ec09d282e96b411e1060ea4ef1a769893ef9` | open, blocked, auto-merge armed | current-head protected checks and independent review |
| ContextualWisdomLab/.github | #1248 | `3f78370f3ad01409c7b2fcfb63dfb66862098fa6` | open, blocked | protected checks and independent review for the Strix scope repair |

PR #464 merged into its stacked base as
`df413d4e58c1d05545e7970ac8cb95f197821419`. That stack-local merge does not
prove release on the default branch.

Central PR #1248 fixes the root cause of PR #387's partial-scope false positive
by including trusted-base `backend/app/auth.py` context in backend Python Strix
scopes. Local evidence is `test_strix_quick_gate: PASS`, shell syntax success,
and `git diff --check`; the protected merge is not yet claimed.

The organization scheduler is the single review/repair control plane. Its
`*/15 * * * *` queue sweep and `0 * * * *` heartbeat satisfy the hourly loop
requirement without a duplicate repository-local scheduler.

## 2. Buyer-visible capability baseline

Substantially present in source or active PRs:

- PostgreSQL-backed import, normalized provenance, cutoff-aware analysis runs,
  source revisions, lineage reconstruction, and explicit unavailable states.
- Authenticated workspace navigation, post detail, Korean summaries, 5W1H,
  R&R/Keyman, evidence citations, chat, customer hierarchy, and lineage DAG.
- Semantic paragraph/list/table/image-region units that preserve the source
  representation and provenance instead of flattening it into one body string.
- Contextual-orchestrator boundaries for adjudication, extraction, summaries,
  chat, embeddings, and VISION; null channels remain unavailable and are
  dropped from score fusion.
- W3C PROV-O projection through normalized provenance tables, with the
  knowledge graph retained as an explicit navigation projection.

These statements describe source capability, not authenticated production
corpus acceptance or protected release.

## 3. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | The listed work remains on open or stacked PR heads | Terminal exact-head checks, no unresolved threads, independent approval, and a protected merge SHA |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region/OCR/description work exists in PR #405 | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph/table/list parsing exists across active stacks | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Scientific measurement | TEPP and fast-mlsirm adapters are present or under review | Persisted accepted envelopes, calibration/recovery evidence, and no invented theta |
| Accessibility and responsive UX | Unit coverage exists for major buyer surfaces | Keyboard, screen-reader, mobile, and authenticated Playwright acceptance on the exact release head |
| External integrations | SearXNG, Zotero, calendar, and downstream consumer contracts are bounded | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| Release quality | Local focused/full suites have passed on individual PR heads | Repository-wide coverage, docstrings, Storybook, security, browser, and release evidence on one exact head |

## 4. Evidence boundaries

- Never add a real record, title, name, identifier, screenshot, log, benchmark
  artifact, or documentation example to this repository.
- Attendance or co-occurrence is not responsibility, project, customer, or
  affiliation evidence. Preserve uncertainty and provenance.
- Missing transport, model capability, accepted envelope, or persistence is
  unavailable/failed evidence, never a placeholder result.
- Local green tests, bot statuses, auto-merge, and warning-only checks do not
  prove a protected merge.
- Re-fetch base/head SHAs, checks, review threads, approvals, rulesets, and the
  merge SHA immediately before any lifecycle claim.

## 5. Next acceptance loop

1. Complete protected review and merge of central PR #1248, then rerun Strix
   on PR #387 at the same exact head and verify the false finding is absent.
2. Re-fetch current heads, latest checks, unresolved threads, and independent
   reviews for PRs #392, #405, #421, #426, and #468 before any merge claim.
3. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
4. Reproduce buyer cases with synthetic fixtures or authorized aggregate
   runtime evidence, preserving `unavailable` explicitly.
5. Fix only evidence-backed failures and repeat the protected merge gate. Do
   not self-approve, force merge/push, bypass protection, or transfer stale
   review/check evidence across heads.
