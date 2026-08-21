# Product & Technical Gap Baseline

> Repository artifacts contain synthetic fixtures and derived, non-identifying
> evidence only. Real PostgreSQL rows, source payloads, images, names, and
> identifiers remain in a protected external runtime and are never copied into
> this repository, screenshots, tests, logs, or buyer evidence.

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: synthetic case `case-footnote-01` exercises numbered footnote recognition; PR #367 merged the parser coverage, while authorized production/browser evidence remains pending.
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
`resolved` from intent alone. Observed at `2026-08-21T15:43:49Z` from the
GitHub API. Checkpoint types are `merge_commit`, `head`, and
`closed_without_merge`; the latter records a closed PR's exact `head` when
`merged_at` and `merge_commit_sha` are both absent. A merged commit is
identified by `merge_commit`; an open PR is identified by its exact `head` and
`base`.

Recently merged into the protected repository:

- PR #385: `merge_commit` `8b356a8399d40bcecc68a07bcfacab78eef303a0`.
- PR #366: `merge_commit` `ec6a829c88f9d2fdb6c34d2d089945aefb59c7a4`.
- PR #374: `merge_commit` `79c40bc8c25050084e5bbed62b8f145f6fa47775`.
- PR #262: `merge_commit` `6bf75991b04601483d48384045e314db2a928e30`.

Open PRs at the same observation:

- PR #258: `head` `8b356a8399d40bcecc68a07bcfacab78eef303a0`, base `main`.
- PR #349: `head` `feb55d029eb9d17c2b4f01cf8c86366fb603206a`, base `main`.
- PR #355: `head` `b606c2553f877fa85968d90dc46598ce16897fbf`, base `main`.
- PR #368: `head` `34103b5b23503524cef6a6cf97b0e7b364b0f852`, base `main`.
- PR #373: `head` `6b84bea10881e2f82fb676d5b01cf56f7d8f4adb`, base `main`.
- PR #382: `head` `5eb707f02209a46d4d046480cec960ac40f59375`, base
  `ci/publish-ontology-pages-clean`.
- PR #383: `head` `745113829469a7c09e03fe783ea942ca884f2ea6`, base `main`.
- PR #384: `head` `e8637fb82cb3abe216eaba64761d2a86011267e0`, base
  `docs/customer-master-scope-adr`.

The open queue remains subject to exact-current-head Checks, formal independent
approval, and protected mergeability. Green Checks alone do not prove that a
merge is authorized. PR #385's merge is the current parent of PR #258; the
other open entries remain separate until their own merge commits are observed.

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

These observations are runtime evidence, not a claim that the corresponding
PRs are merged. The image-processing state and protected-corpus parsing cases
remain open gaps.

## 6. Organization OpenTelemetry Evidence Boundary

GRC PR #42 records organization-level OTEL acceptance evidence through the
existing purpose-bound evidence contract. It does not become a raw span store
and must not copy prompts, post bodies, images, provider responses, secrets, or
an ad-hoc `user_account + post_id` session key. W3C trace context and bounded
OpenTelemetry attributes correlate the authorized operation across services;
collector delivery, retention, access review, and no-export rollback are the
GRC evidence subjects.

## 7. Next Implementation Order

1. Let the protected Checks and independent approvals complete for open PRs
   #258, #349, #355, #368, #373, #382, #383, and #384, then revalidate each
   exact current head before merge; PRs #367, #375, #379, and #385 are already
   merged.
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
