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
`resolved` from intent alone:

Observed at `2026-08-21T14:07:36Z` from the GitHub API. A merged commit is
identified as `merge_commit`; an open PR is identified by its exact `head`.

- LineageWeave PR #344: `merge_commit`
  `497ac120c2ea22f97ef2e4a4bcd15fc2a3610046`, merged at
  `2026-08-21T10:23:02Z`; focused tests passed before merge, while the
  authorized-runtime browser result remains open.
- LineageWeave PR #367: `merge_commit`
  `7a0d025215fbd9f6510727c7139885b561296149`, merged at
  `2026-08-21T11:56:07Z`; focused parser tests passed before merge, while
  authorized production/browser evidence remains open.
- LineageWeave PR #349: `head`
  `2eb6d13903d8d20b27dfeccd476a149fdd801c1b`, base `main`; ontology
  provenance explorer remains open and required Checks and independent
  approval remain external gates.
- LineageWeave PR #368: `head`
  `3e233eeb6ba4e8649006e4c7eb42d74cc48e5a03`, base `main`; this baseline
  checkpoint is updated by the stacked documentation PR for the newer queue
  evidence below.
- LineageWeave PR #378: `merge_commit`
  `333c705294a4faa76869f34d3e08dc09d760487d`, merged at
  `2026-08-21T13:36:41Z`; this checkpoint's buyer-surface and exact-head
  evidence is delivered in the merged baseline documentation.
- LineageWeave PR #366: `head`
  `588dc91f5689d77281cd6bbd10a8e922f9eaa159`, base
  `8bed77e7e7b91b633bb92d3a82d0187c387206af`; customer-master authorization
  scope is implemented, while required Checks and independent approval remain
  external gates.
- LineageWeave PR #369: `head`
  `eb9e520cbac412b7f85f8ceddd86624515bb29cb`, base
  `e88f3862215e76d0702204f29aba75ddc902d19f`; ontology source-window
  continuation is open and required Checks and independent approval remain
  external gates.
- LineageWeave PR #370: `head`
  `d5495162fbf4950ca180d43d5c13a636f1889e0c`, base
  `8bed77e7e7b91b633bb92d3a82d0187c387206af`; its runtime boundary fixes are
  now part of the current Customer Master stack; required Checks and
  independent approval remain external gates.
- LineageWeave PR #374: `head`
  `fb0d185a2da707e57d2ed10900b06707126d8300`, base
  `0a5a5799b444c44dc2952edc7227b1b96b97457e`; its post-chat atomic
  reauthorization fix is stacked in PR #377.
- LineageWeave PR #376: `merge_commit`
  `860545f7bece99359ec7b9840c675ddc14e9acbc`, merged at
  `2026-08-21T13:10:45Z`; migration, relation-boundary, image-job transaction,
  and overflow-test fixes are delivered in the Customer Master stack.
- LineageWeave PR #380: `merge_commit`
  `9f8f4b742759e15ad34c7ef09c401dbc8b1d1ae5`, merged at
  `2026-08-21T13:11:02Z`; the workspace-refresh and accessibility changes are
  delivered in the current #370 head.
- LineageWeave PR #377: `head`
  `a638e28af4345750e3be92f2b0f23012b24598e0`, base
  `repair/global-ask-atomic-rollback-v2203`; post-chat rollback and test
  cleanup are locally verified; required Checks and independent approval
  remain external gates.
- LineageWeave PR #385: `head`
  `d0c7decf4767902642c9805629bb8c7d5440ead8`, base
  `feat/analysis-run-name-evidence-lineage`; stacked on PR #258's exact head
  `481bdb6eafa1d3f074ca7d9d05275ce36a4708d8`, it hardens the external
  lineage contract, removes the self-modifying repair workflow, and fixes the
  responsive board CSS. Checks and independent approval remain external gates.
- LineageWeave PR #373: `head`
  `84fd2993fcec5d3d683c391818f85e27ebd7347f`, base `main`; ontology
  publication has unresolved review work and is not treated as delivered.
- LineageWeave PR #375: `merge_commit`
  `fb0d185a2da707e57d2ed10900b06707126d8300`, merged at
  `2026-08-21T13:18:01Z`; post-chat citation authorization is delivered in
  the merged stack.
- LineageWeave PR #379: `merge_commit`
  `b606c2553f877fa85968d90dc46598ce16897fbf`, merged at
  `2026-08-21T13:19:00Z`; malformed provider replies and focused regression
  coverage are delivered in the current PR #355 head.
- LineageWeave PR #355: `head`
  `b606c2553f877fa85968d90dc46598ce16897fbf`, base `main`; it remains
  open and is not treated as merged solely because stacked PR #379 merged.
- LineageWeave PR #382: `head`
  `d14dc49025886a00251a3f579f4e9d53ed55f0ba`, base
  `ci/publish-ontology-pages-clean`; it carries the ontology-site safety
  repair stacked on PR #373 and remains gated by Checks and approval.
- Legacy open PR #258: `head`
  `481bdb6eafa1d3f074ca7d9d05275ce36a4708d8`, base `main`; hardening stack
  #385 is open and parent delivery remains gated by Checks and review.
- Legacy open PR #262: `head`
  `fcb9bd3ad4714380946d29c0889b940aceaa5496`, base
  `feat/calendar-open-focus-event-lineage-v2140`; it remains unmerged and
  separately gated.
- Legacy open PR #287: `head`
  `9d2a536d7fba14f87a9fe4c9e7e578c16f97aea9`, base
  `feat/global-ask-public-claim-verification-v2200`; it is conflicting and
  remains unmerged.
- LineageWeave PR #371: `closed_without_merge`
  head `4c3e43f9e96ecc2d868657dd9b0ce5524a15c76c`, closed at
  `2026-08-21T11:59:57Z`; no merge commit exists, so ontology publication is
  not claimed as delivered by this checkpoint.
- LineageWeave PR #345: `merge_commit`
  `9316d281ae396cc1bc33ac3ba470a9e3afd41a90`, merged at
  `2026-08-21T09:08:31Z`; application and Valkey caller OpenTelemetry spans
  are merged, while raw telemetry remains outside buyer evidence.
- contextual-orchestrator PR #802: `merge_commit`
  `407747626598d763a127509f81d23c2ad8aaee23`, merged at
  `2026-08-21T11:42:06Z`; request session context is delivered through local
  batch workers.
- contextual-orchestrator PR #805: `merge_commit`
  `537915715c4b050d4b5fa18ce2b7559080c675ba`, merged at
  `2026-08-21T11:45:58Z`; structured Responses and JSON-schema orchestration
  are delivered in the merged upstream boundary.

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

1. Let the protected Checks and independent approvals complete for open stacked
   PRs #377, #382, and #385, then revalidate parent PRs #374, #373, and #258
   at their exact current heads; PRs #367, #375, and #379 are already merged.
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
