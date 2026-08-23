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

## 4. Ask Agent Gaps
- **Korean relative-time understanding**: (Resolved, PR #415 / ADR 0150)
  Global Ask could not answer "어제", "오늘", "그제", "작년 이맘때쯤",
  "재작년에", "언젠가", or the general "N일/주/개월/년 전" pattern -- the
  expression only ever became a literal keyword search term. Resolved by
  `lineageweave.temporal_expressions.resolve_korean_relative_time`, wired
  into `gather_global_chat_sources` as a `created_at` retrieval bound.
- **Multi-thread Event Lineage in answers**: (Resolved, PR #418 / ADR 0151)
  An Ask answer could speak to at most one connected Event Lineage
  timeline (ADR 0090's single-top-match expansion), shown as prose only.
  Resolved by `lineage_graphs_for_posts` merging every cited post's full
  thread into one `lineage_graph` response field, rendered as N
  independent git-branch-style figures by the existing `LineageDag`
  component.
- **Image citation in answers**: (Resolved, PR #419 / ADR 0152) A citation
  whose evidence came from an embedded picture read as an unmarked text
  claim. Resolved by `cited_post_images`, surfacing the same persisted
  caption/OCR/tags `GET /api/posts/{id}/content` already renders, scoped
  to cited posts -- no new image-serving mechanism, consistent with this
  codebase's existing never-raw-bytes boundary.
- **Evidence Layer Popup**: (Resolved, PR #420 / ADR 0153) Inspecting one
  citation's evidence meant either scanning every citation's facts inline
  at once or leaving the answer for the full post detail popup. Resolved
  by `AskEvidenceLayerPopup`, a focused modal opened per citation.
- **Ask Agent e2e coverage**: (Resolved, PR #421) No Playwright config
  existed despite `playwright` already being a frontend devDependency.
  Resolved by `frontend/playwright.config.ts` + `frontend/e2e/` (a
  Keycloak-OIDC login helper, a verified-passing smoke spec, and a spec
  covering all four capabilities above -- the latter requires PRs
  #415/#418/#419/#420 merged and the images rebuilt from `main` before it
  can pass; not yet true as of this entry).

*This document is continuously updated by the hourly automated agent loop.*
