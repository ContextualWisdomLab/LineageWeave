# Product & Technical Gap Baseline

> Audit snapshot: 2026-08-23 17:32 KST. This repository records synthetic fixtures and
> aggregate, non-identifying runtime evidence only. Open PRs and local checks
> are not protected-default-branch release evidence.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The current acceptance queue was re-fetched immediately before this update:

| Repository | PR | Exact head | State | Remaining gate |
| --- | ---: | --- | --- | --- |
| LineageWeave | #392 | `b76ae7b9aa7bf16f70d712dffb2514dc9467dde1` | open, blocked, review required, auto-merge armed | independent current-head approval; current checks are terminal |
| LineageWeave | #387 | `c34681fdc692a25e688fe4a5eb06ad3fe50f2281` | open, blocked, changes requested, auto-merge armed | terminal rerun after central scope repair and current-head approval |
| LineageWeave | #405 | `0b1b1fcfed875f8ba6795537567a8b28a2497044` | open, blocked, changes requested | terminal protected checks and independent current-head approval |
| LineageWeave | #421 | `2fc08835485d5bfadfd105ad0a95e17f23cf66cc` | open, blocked, review required, auto-merge armed | terminal protected checks and independent current-head approval |
| LineageWeave | #426 | `11a60b370d7b5783733febb593e8f91678cc403d` | open, blocked, review required, auto-merge armed | independent current-head approval; current checks are terminal-success |
| LineageWeave | #468 | `34d73da224b88e23cb0e1e7d3994ddd2d9c963b0` | open, blocked | terminal current-head protected checks and independent review |
| ContextualWisdomLab/.github | #1248 | `3f78370f3ad01409c7b2fcfb63dfb66862098fa6` | merged as `9ad0ad50409561292b424d6f35a95d670a277e77` | protected-main scope repair is available to the rerun |

PR #464 merged into its stacked base as
`df413d4e58c1d05545e7970ac8cb95f197821419`. That stack-local merge does not
prove release on the default branch.

Central PR #1248 fixed the root cause of PR #387's partial-scope false positive
by including trusted-base `backend/app/auth.py` context in backend Python Strix
scopes. The protected merge SHA is
`9ad0ad50409561292b424d6f35a95d670a277e77`; PR #387 still requires a
terminal same-head rerun before that repair can be credited to its acceptance.

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

1. Complete the in-flight Strix rerun on PR #387 at the same exact head and
   verify the merged central scope repair removed the false finding.
2. Re-fetch current heads, latest checks, unresolved threads, and independent
   reviews for PRs #392, #405, #421, #426, and #468 before any merge claim.
3. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
4. Reproduce buyer cases with synthetic fixtures or authorized aggregate
   runtime evidence, preserving `unavailable` explicitly.
5. Fix only evidence-backed failures and repeat the protected merge gate. Do
   not self-approve, force merge/push, bypass protection, or transfer stale
   review/check evidence across heads.
