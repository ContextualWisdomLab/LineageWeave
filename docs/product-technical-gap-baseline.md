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

Observed at `2026-08-21T13:35:16Z` from the GitHub API. A merged commit is
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
  `539b65287da5ac4635f6965c6dc21d7437dede9c`, base `main`; ontology
  provenance explorer remains open and required Checks and independent
  approval remain external gates.
- LineageWeave PR #368: `head`
  `f45fcdebfd54bf236b55f5d892aeb6091b51ba5b`, base `main`; this baseline
  checkpoint is updated by the stacked documentation PR for the newer queue
  evidence below.
- LineageWeave PR #378: `head`
  `333c705294a4faa76869f34d3e08dc09d760487d`, base
  `codex/product-gap-baseline-20260821`; this checkpoint's local
  buyer-surface verification is the current documentation delta.
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
  `9f8f4b742759e15ad34c7ef09c401dbc8b1d1ae5`, base
  `8bed77e7e7b91b633bb92d3a82d0187c387206af`; its runtime boundary fixes are
  now part of the current Customer Master stack; required Checks and
  independent approval remain external gates.
- LineageWeave PR #374: `head`
  `f6ce19f8e10aa7ec2b0a95f3adbbea816bd39594`, base
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
  `16ab01a9ab7d88487a3c984e192709857f6cfd1c`, base
  `repair/global-ask-atomic-rollback-v2203`; post-chat rollback and test
  cleanup are locally verified; required Checks and independent approval
  remain external gates.
- LineageWeave PR #385: `head`
  `cda7d483717addf6f62b7771a5cdcd244cad8fa9`, base
  `feat/analysis-run-name-evidence-lineage`; stacked on PR #258's exact head
  `efcc3c615cf4809a7ec265a1074a10e12877dd15`, it hardens the external
  lineage contract, removes the self-modifying repair workflow, and fixes the
  responsive board CSS. Checks and independent approval remain external gates.
- LineageWeave PR #373: `head`
  `bc91481dac7350975de7ec00f11d4e54f676eb2c`, base `main`; ontology
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
- Legacy open PRs #258, #262, and #287 remain explicitly unmerged. PR #258
  has the separate hardening stack #385; neither PR is treated as delivered
  until GitHub reports a merge commit.
- LineageWeave PR #371: `closed_without_merge`
  head `4c3e43f9e96ecc2d868657dd9b0ce5524a15c76c`, closed at
  `2026-08-21T11:59:57Z`; no merge commit exists, so ontology publication is
  not claimed as delivered by this checkpoint.
- LineageWeave PR #345: `merge_commit`
  `9316d281ae396cc1bc33ac3ba470a9e3afd41a90`, merged at
  `2026-08-21T09:08:31Z`; application and Valkey caller OpenTelemetry spans
  are merged, while raw telemetry remains outside buyer evidence.
- contextual-orchestrator PR #802: `head`
  `b2fe47e78ade89b13aa4c239c71562c65af5f12e`, base
  `f1b0cd48271e870571b022463e1ec2c857ae4a8a`; request session context is
  propagated through local batch workers and approval is not recorded.
- contextual-orchestrator PR #805: `head`
  `1d11e7d40dc52121d440991969be2967adf2136e`, base
  `f1b0cd48271e870571b022463e1ec2c857ae4a8a`; structured Responses and
  JSON-schema orchestration remain a separate open merge prerequisite.

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
