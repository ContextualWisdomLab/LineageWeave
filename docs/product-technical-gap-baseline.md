# Product & Technical Gap Baseline

> Repository artifacts contain synthetic fixtures and derived, non-identifying
> evidence only. Real PostgreSQL rows, source payloads, images, names, and
> identifiers remain in a protected external runtime and are never copied into
> this repository, screenshots, tests, logs, or buyer evidence.

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: synthetic case `case-footnote-01` exercises numbered footnote recognition; PR #367 adds parser coverage, while authorized production/browser evidence remains pending.
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

Observed at `2026-08-21T11:16:36Z` from the GitHub API. A merged commit is
identified as `merge_commit`; an open PR is identified by its exact `head`.

- LineageWeave PR #344: `merge_commit`
  `497ac120c2ea22f97ef2e4a4bcd15fc2a3610046`, merged at
  `2026-08-21T10:23:02Z`; focused tests passed before merge, while the
  authorized-runtime browser result remains open.
- LineageWeave PR #367: `head`
  `5194d267b90430d7a27a9752a49d73617cb5756c`, base
  `f66991699506ef14607de5946da1efcfd20ae6da`; focused parser tests passed,
  while required Checks and independent approval remain external gates.
- LineageWeave PR #366: `head`
  `696f8d46372ef6f5af9eb1b2dbc30fff4e9c9f6c`, base
  `8bed77e7e7b91b633bb92d3a82d0187c387206af`; customer-master authorization
  scope is implemented, while required Checks and independent approval remain
  external gates.
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

## 5. Organization OpenTelemetry Evidence Boundary

GRC PR #42 records organization-level OTEL acceptance evidence through the
existing purpose-bound evidence contract. It does not become a raw span store
and must not copy prompts, post bodies, images, provider responses, secrets, or
an ad-hoc `user_account + post_id` session key. W3C trace context and bounded
OpenTelemetry attributes correlate the authorized operation across services;
collector delivery, retention, access review, and no-export rollback are the
GRC evidence subjects.

## 6. Next Implementation Order

1. Complete PR #367's protected Checks and verify the synthetic footnote/table
   cases in the authenticated browser; use the protected external corpus only
   for aggregate, non-identifying runtime evidence.
2. Resolve image DOM-region recognition, OCR, semantic table rendering, and
   buyer-facing caption separation through contextual-orchestrator VISION.
3. Verify 5W1H, multi-project event separation, Keyman affiliation, and
   customer-master ABAC against authorized real PostgreSQL data in the protected
   external runtime, returning only aggregate or derived non-identifying
   evidence to repository artifacts.
4. Keep the GRC and contextual-orchestrator OTEL evidence contracts aligned
   with the exact merged application instrumentation.
