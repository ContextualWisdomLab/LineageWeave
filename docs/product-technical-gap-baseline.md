# Product & Technical Gap Baseline

> Repository artifacts contain synthetic fixtures and derived, non-identifying
> evidence only. Real PostgreSQL rows, source payloads, images, names, and
> identifiers remain in a protected external runtime and are never copied into
> this repository, screenshots, tests, logs, or buyer evidence.

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: synthetic case `case-footnote-01` exercises numbered footnote recognition; PR #367 merged semantic-chunker coverage, and stacked PR #388 adds browser fallback recognition for HTML, Word, and OOXML footnotes. Authorized production/browser corpus evidence remains pending.
- **Table Parsing**: synthetic case `case-table-01` exercises malformed row boundaries and empty cells; image tables and browser rendering remain open.
- **Indentation**: synthetic cases `case-indent-01` and `case-indent-02` retain incorrect indentation rendering coverage gaps.
- **Image/Table OCR**: synthetic case `case-image-table-01` still needs region-aware table OCR, markdown rendering, and sufficiently detailed buyer-safe image evidence.
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

*This document is continuously updated by the hourly automated agent loop.*

## 4. Current Checkpoint Evidence

The following states are evidence-bound and must not be changed to `merged` or
`resolved` from intent alone. Observed at `2026-08-21T17:10:21Z` from the
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
- PR #367: `merge_commit` `7a0d025215fbd9f6510727c7139885b561296149`.
- PR #262: `merge_commit` `6bf75991b04601483d48384045e314db2a928e30`.

Recently merged into an open stack base (not main):

- PR #382: `merge_commit` `43e24783ae38d65d03df7cb901f93b8ac8731b9b`, merged
  into PR #373's `ci/publish-ontology-pages-clean` base.

Open PRs at the same observation:

- PR #258: `head` `6621eb116a4e92eb33eeae989c70fbc602450c51`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #349: `head` `979b4290bc62ab83668aab99cc09c2a297db8464`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #355: `head` `b606c2553f877fa85968d90dc46598ce16897fbf`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`). The overlap with PR #379's
  merge commit is intentional: #355 is the open successor from the same
  feature branch, now pointing at that merged branch tip, and is not itself
  merged.
- PR #368: `head` `2e1de2383865c548959d067f9a70a0dc008d1afd` (the exact parent
  observed for this baseline update), base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #373: `head` `43e24783ae38d65d03df7cb901f93b8ac8731b9b`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #383: `head` `46e4d6d69c1964f0cbeb761281071db7861e31dd`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #384: `head` `e4c4a3c8709a4e57654c08a838f568a1582abee3`, base
  `docs/customer-master-scope-adr` (`83ace331edc982208c290763cb0d389c1884e21b`).
- PR #387: `head` `df2519c09b224f05ac84e6997abd3b4f1bb94cb6`, base `main`
  (`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`).
- PR #388: `head` `f145b83f68731d6f31c3e1b1de59fd7be8f62001`, base
  `feat/event-lineage-channel-evidence`
  (`4faf9a31371195c5ec63fca42a5afbb93a95369b`).

The open queue remains subject to exact-current-head Checks, formal independent
approval, and protected mergeability. Green Checks alone do not prove that a
merge is authorized. PR #388 is stacked on PR #387 and must follow its
observed merge commit before rebasing onto `main`. PR #258 still targets `main` at base
`ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` and remains open; PR #385's merge
commit is later repository history, not PR #258's original base or a merge of
#258. PR #386 is closed as a duplicate of the safer #373 login fix. PR #382's
stack merge is not a main merge; #373 must still pass its own current-head
gates.

Closed without merge at the same observation:

- PR #386: `closed_without_merge` head `57a013deb88fc0b23ae6448c1d3474c770360a5e`.
- PR #377: `closed_without_merge` head `a638e28af4345750e3be92f2b0f23012b24598e0`.

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

Observed at `2026-08-21T16:01:40Z` in a fresh local Compose browser session:

- OIDC login, an authorized post click, popup close, and the phone-width menu
  trigger all completed. The popup opened, but the summary request returned
  HTTP 503; no generated summary, 5W1H, VISION evidence, or graph rendering is
  claimed from this run.
- The local orchestrator returned HTTP 200 for its authenticated model
  inventory with nine registered models. A synthetic `mode=auto` completion did
  not complete within 30 seconds, so provider/model readiness remains open even
  though the Compose services are running.

These observations are runtime evidence, not a claim that the corresponding
PRs are merged. The image-processing state and protected-corpus parsing cases
remain open gaps.

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
  reference from 0119 to the governing ADR 0131; the focused reconstruction
  and adjudication tests still passed at the pushed documentation head.

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
  availability are documented as invariants/optional-channel behavior in ADR
  0124; active weight ordering was made deterministic, and the ADR now records
  the orchestrated rebuild/import boundary. Hosted Checks are queued and no
  independent approval or merge commit is claimed.

Observed at `2026-08-21T17:20:10Z` on PR #388's exact head
`f145b83f68731d6f31c3e1b1de59fd7be8f62001`:

- The browser fallback preserves footnote roles for synthetic HTML footnote
  lists, Word `MsoFootnoteText`, and OOXML footnote containers. Anchor tags no
  longer become false leading indentation in this path.
- Local frontend verification passed lint, 144 Vitest tests, and the
  production build. Hosted Checks were queued and no independent approval or
  merge commit was present.

Observed at `2026-08-21T17:25:46Z` on PR #387's exact head
`df2519c09b224f05ac84e6997abd3b4f1bb94cb6`:

- The Event Lineage channel-evidence persistence check now budgets one
  half-quantum per six-decimal contribution plus a small floating-point guard,
  so normal three- and four-channel edges cannot abort rebuild/import solely
  because of storage rounding.
- A four-channel regression covers the former failure boundary. Local
  verification passed 769 backend tests with 17 environment skips, 20 focused
  lineage tests, and `git diff --check`; hosted Checks were queued and no
  independent approval or merge commit was present.

Observed at `2026-08-21T17:32:25Z` on PR #349's exact head
`979b4290bc62ab83668aab99cc09c2a297db8464`:

- The ontology source cursor now uses `src.v2.` AES-GCM with a fresh 96-bit
  nonce and prefix/version associated data; the custom v1 keystream format is
  rejected. The concurrent ontology page retry repair remains included.
- ADR 0125 records the decision and NIST SP 800-38D APA 7 reference. Local
  verification passed 830 backend tests with 17 environment skips, 172
  frontend tests, lint, TypeScript, and production build; hosted Checks and
  independent approval remained open.

## 6. Organization OpenTelemetry Evidence Boundary

GRC PR #51 records organization-level OTEL acceptance evidence through the
existing purpose-bound evidence contract. It does not become a raw span store
and must not copy prompts, post bodies, images, provider responses, secrets, or
an ad-hoc `user_account + post_id` session key. W3C trace context and bounded
OpenTelemetry attributes correlate the authorized operation across services;
collector delivery, retention, access review, and no-export rollback are the
GRC evidence subjects.

## 7. Next Implementation Order

1. Revalidate open PRs #258, #349, #355, #368, #373, #383, #384, #387, and
   #388 at
   their exact current heads as Checks and formal independent approvals arrive;
   process stacked parents only after their child merge commits are observed.
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
   with the exact merged application instrumentation.
