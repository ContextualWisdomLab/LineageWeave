# Product & Technical Gap Baseline

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: `post=00505695-3e61-1fd1-83c5-263f88a9e77a` fails to recognize footnotes (li/oi level errors).
- **Table Parsing**: `post=00505695-3e61-1fd1-80c6-86bb61c8ddc5` completely fails at parsing tables.
- **Indentation**: Incorrect indentation rendering in `post=00505695-7571-1fd1-83c3-d521b187ad5b` and `post=00505695-3e61-1fd1-83c0-497b3c1c455e`.
- **Image/Table OCR**: `post=00505695-7571-1fd1-83dd-3d22a61a5734` fails text recognition for tables inside images, markdown parsing fails, and image OCR description is too shallow for Ontology & Semantics.
- **Math/Superscripts**: `post=00505695-9612-1fe1-83a7-e30153323f25` fails to parse superscripts like m^3 properly. Needs strict Ontology grammar for math formulas.
- **Missing UI Elements**: DAG (Directed Acyclic Graph) view is currently missing from the frontend for `post=00505695-7571-1fd1-83c5-895ed333cdbc`.

## 2. LLM Extraction & Knowledge Graph Gaps
- **Multiple Project Extraction**: (Resolved) LLM prompt updated to request key_events as objects with project_name, separating events correctly.
- **5W1H Missing**: (Resolved) LLM prompt updated to explicitly request 5W1H evidence items in the JSON output array.
- **R&R and Keyman Missing**: (Resolved) LLM prompt updated to explicitly instruct using actual stated names rather than collective titles.
- **Entity Resolution / Searxng**: Abbreviations like "한전" and "한국전력" are not mapped properly using Searxng and KG corroboration. 
- **Meso-level Team Mapping**: (Resolved) Checked extraction logic; `team` mapping logic is present and correct, but LLM needed better explicit instruction which is covered by R&R resolution.
- **Base64 Image Omni-modal**: Current text-only embedding fails on images. Omni-modal LLM processing is required for images to capture layout, font size, colors, and spatial meaning.

## 3. General Architecture Gaps
- **DB Architecture**: Ensure PostgreSQL is strictly used (no file DBs), 3rd normal form is maintained, and Hot Partitions are handled. DB locks must be managed (or use read/write replicas).
- **Zotero Integration**: Papers and standards referenced by TEPP must be synced via Local Zotero API (http://localhost:23119/api/) and cited using APA 7th edition in docstrings.
- **Testing**: We need actual testing of Psychometrics (Fast-MLSIRM parameter calibration, RMSE of estimates, Fixed-Item Parameter Calibration, CAT) against synthetic/demo data.
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

## 4. 2026-08-23 Audit: Accessibility, i18n, and Release-Process Gaps

A dedicated multi-agent audit (independently verified against live source and
cross-checked against the full PR history to rule out duplicates) found 14
new, previously-untracked gaps. None of these overlap the sections above.

### 4a. Accessibility (frontend)
- **Post detail popup has no dialog semantics**: `PostDetailPopup` in
  `frontend/src/App.tsx` renders a backdrop/panel with no `role="dialog"`,
  `aria-modal`, `aria-labelledby`, Escape-to-close, or focus trap/restore.
  Highest-severity item in this batch; needs careful focus-management work,
  not yet fixed.
- **Async error feedback isn't announced**: 17 of 19 `className="error"`
  sites in `App.tsx` render as plain `<p>` with no `role="alert"`/`aria-live`
  (Ask, Keymen extraction, lineage rebuild, Customer Master, Ask Agent, and
  more). Fixed in the accessibility-sweep PR referenced below.
- **Two inputs have no accessible name**: the "Ask about this lineage"
  question field and the new-ticket-title field use only a `placeholder`,
  unlike the adjacent due-date field. Fixed in the same sweep.
- **AdminPanel save result isn't announced**: the save-success/error `<span>`
  in `AdminPanel.tsx` carries no `role`/`aria-live`. Fixed in the same sweep.
- **Event Lineage DAG node kind (root/branch/regular) is color-only**: no
  textual indication in the `aria-label`, tooltip, or a legend; not fixed by
  the existing DAG test/story coverage (that PR explicitly found no bug).
  Needs a legend/label design decision, not yet fixed.
- **DAG keyboard focus ring is very weak**: `.lineage-dag-node:focus` strips
  the native outline and replaces it with only a 1px stroke-width bump in the
  same border color. Fixed in the accessibility-sweep PR.
- **Rendered post-body tables have no header semantics**: both the
  structured-unit table renderer and the OCR-image-text table renderer in
  `PostBody.tsx` emit only `<td>`, no `<th scope="col">`/`<caption>`. Was
  present in a prior merged PR (#303) but silently dropped by a later
  whole-file rewrite (commit `ef6f5a5f`). Not yet re-fixed.

### 4b. i18n
- **Unregistered aria-label key**: `tf("Affiliates of {name}")` (the
  customer-entity-tree `aria-label` in `App.tsx`) has no entry in any of the
  ko/zh/ja/vi locale blocks in `i18n.ts`, so it always renders in English
  regardless of the active locale. Fixed in the accessibility-sweep PR.

### 4c. Release-process / CHANGELOG hygiene
- **CHANGELOG.md stalled at `[2.12.6]`** while the tree already contains ~80
  additional ADRs and whole undocumented feature surfaces (Global Ask
  evidence workspace, the buyer-facing global nav). No version header past
  2.12.6 exists anywhere in the file. Large, needs careful reconstruction;
  logged here rather than attempted in this pass.
- **9 already-drafted `CHANGELOG.d/` fragments (2.12.7 through 2.21.1) were
  never compiled** into `CHANGELOG.md` — the release text already exists,
  the compile step was simply never run. Fixed in a dedicated compilation PR
  (mechanical, low-risk since the prose already exists).
- **The `ef6f5a5f` squash-merge (PR #347) left at least one shipped feature
  undocumented**: the durable post-content ingestion queue (ADR 0098) has no
  CHANGELOG.md entry and no `CHANGELOG.d/` fragment, unlike its sibling
  changes in the same commit. Logged, not yet fixed.
- **PR #460's own fix is missing from `CHANGELOG.md`'s `[Unreleased]`
  section.** Will be added alongside the CHANGELOG.d compilation PR.
- **Version fields agree with CHANGELOG (2.12.6) only because both are
  equally stalled**, not because the release process is healthy — real
  merged work already sits past that version with no compiled release.
  Same root cause as the two items above; resolved once a batch-release pass
  runs.

### 4d. Test coverage
- **Bookmark endpoints (`GET`/`POST /api/posts/{post_id}/bookmark`) have zero
  HTTP-level test coverage.** The only existing tests exercise the lower-level
  `_load_visible_post` helper directly, bypassing FastAPI entirely — the
  route wiring, request validation, and the `post_bookmark` insert/delete SQL
  introduced by a recent fix are unexercised. Needs a `TestClient`-level
  test; not yet added.

*This document is continuously updated by the hourly automated agent loop.*
