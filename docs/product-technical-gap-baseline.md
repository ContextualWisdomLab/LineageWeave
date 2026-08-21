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

## 4. Current Stacked PR Product-Surface Gaps
- **Customer Master relationship composition — PR #262**: (Resolved on the current feature branch) The hierarchy, selected customer, and linked evidence were previously stacked vertically, so the selected customer scrolled away while the user inspected relationships and source posts. ADR 0125 and Figma frames `313:2` / `314:2` define a customer-centered three-pane workspace that preserves the WAI-ARIA tree, keeps the selected customer stable, and places source-backed evidence in a separate pane.
- **Responsive Customer Master flow — PR #262**: (Resolved on the current feature branch) PC uses three horizontal panes, tablet uses two columns plus full-width evidence, and phone preserves the semantic order hierarchy → selected customer → evidence at the shared 1024 px / 768 px breakpoints.
- **Effective-dated relationship authority**: (Open) The current Customer Master projection still owns only one `parent_entity_id`. Legal ownership, operating structure, sales roll-up, billing hierarchy, historical roles, and multiple simultaneous relationship types require a normalized, effective-dated relation model before they can be shown as authoritative facts.
- **Unresolved hierarchy repair workflow**: (Open) Cycle, self-parent, and missing-visible-parent members remain safely visible and marked unresolved, but operators still need a source-data quality queue, evidence review, and approved correction workflow.
- **Customer relationship exact-value export**: (Open) The three-pane workspace is accessible and source-backed, but an auditable CSV/JSON export of the selected customer, visible relations, truth status, effective interval, and evidence references remains a later product slice.

*This document is continuously updated by the hourly automated agent loop.*
