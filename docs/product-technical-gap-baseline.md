# Product & Technical Gap Baseline

> Audit date: 2026-08-23. This repository records synthetic fixtures and
> aggregate, non-identifying runtime evidence only. Open PRs and local checks
> are not protected-default-branch release evidence.

## 1. Exact-head and governance evidence

The protected default branch was
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` when this baseline was refreshed.
The acceptance queue remains active; every lifecycle decision must re-fetch
the current base, head, checks, threads, approvals, rulesets, and merge SHA.

Central PR #1248 repairs the backend-Python Strix partial-scope context by
including trusted-base authentication code. Its local quick-gate evidence is
not a protected merge or release result.

The organization scheduler is the single review/repair control plane. Its
quarter-hour queue sweep satisfies the required hourly loop without adding a
duplicate repository-local scheduler.

## 2. Reader-visible capability baseline

Substantially present in source or active PRs:

- PostgreSQL-backed import, normalized provenance, cutoff-aware analysis runs,
  source revisions, lineage reconstruction, and explicit unavailable states.
- Authenticated workspace navigation, post detail, Korean summaries, 5W1H,
  R&R/Keyman, evidence citations, chat, customer hierarchy, and lineage DAG.
- Semantic paragraph/list/table/image-region units that preserve source
  representation and provenance instead of flattening one opaque body string.
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
| Protected release | Material work remains on open or stacked PR heads | Terminal exact-head checks, no unresolved threads, independent approval, and a protected merge SHA |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Image understanding | Region, OCR, and description work exists on active heads | Orchestrator-backed rendered workflow, original/derived asset provenance, and honest unsupported states |
| Semantic source rendering | Paragraph, table, and list parsing exists across active stacks | Authenticated browser evidence that semantic units render without authoring-layout artifacts |
| Scientific measurement | TEPP and fast-mlsirm adapters are present or under review | Persisted accepted envelopes, calibration/recovery evidence, and no invented theta |
| Accessibility and responsive UX | Unit coverage exists for major reader surfaces | Keyboard, screen-reader, mobile, and authenticated Playwright acceptance on the exact release head |
| External integrations | SearXNG, Zotero, calendar, and downstream consumer contracts are bounded | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| Release quality | Local focused/full suites have passed on individual PR heads | Repository-wide coverage, docstrings, Storybook, security, browser, and release evidence on one exact head |

## 4. Ask Agent delivery evidence

ADRs 0150-0153 record the intended boundaries before implementation becomes
protected-main evidence:

- PR #415 implements Korean relative-time retrieval under ADR 0150.
- PR #418 implements scoped multi-thread Event Lineage answers under ADR 0151.
- PR #419 implements persisted image-evidence citations under ADR 0152.
- PR #420 implements a focused citation evidence popup under ADR 0153.
- PR #421 adds the Playwright harness intended to verify the combined flow.

These capabilities remain active-PR evidence until their exact heads pass all
protected gates and merge. The combined browser scenario is not release
evidence until it runs successfully against one merged release candidate.

## 5. Evidence boundaries

- Never add a real record, title, name, identifier, screenshot, log, benchmark
  artifact, or documentation example to this repository.
- Attendance or co-occurrence is not responsibility, project, customer, or
  affiliation evidence. Preserve uncertainty and provenance.
- Missing transport, model capability, accepted envelope, or persistence is
  unavailable/failed evidence, never a placeholder result.
- Local green tests, bot statuses, auto-merge, and warning-only checks do not
  prove a protected merge.

## 6. Next acceptance loop

1. Complete protected review of central PR #1248 and rerun affected Strix
   evidence only on unchanged exact heads.
2. Re-fetch current heads, latest checks, unresolved threads, and independent
   reviews before every merge decision.
3. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
4. Reproduce reader cases with synthetic fixtures or authorized aggregate
   runtime evidence, preserving `unavailable` explicitly.
5. Fix only evidence-backed failures and repeat the protected merge gate. Do
   not self-approve, force merge/push, bypass protection, or transfer stale
   review/check evidence across heads.
