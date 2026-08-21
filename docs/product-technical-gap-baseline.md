# Product & Technical Gap Baseline

## 0. Current exact-head evidence

- PR #349 remains open and unmerged at code head `eb84dea51f961417e269f4059b26f8e657ebeedb`,
  based on `main` at `ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7`. The current
  repair hardens OIDC return-url validation, corrects the OWL-Time maturity
  citation, accumulates cursor pages in the ontology explorer, and preserves
  fail-closed LLM and ontology direction contracts.
- Validation at that code head is `uv run pytest -q`: `812 passed, 17 skipped,
  4 warnings`; frontend `pnpm run lint`, `pnpm run test` (`168 passed` in 20
  files), `pnpm run build`, and `pnpm run build-storybook` all passed. Hosted
  checks, independent approval, and merge remain open external gates.
- Repository artifacts use synthetic case labels only; private source records
  and identifiers stay outside git.

## 1. Known Parsing & Frontend Display Gaps

- **Footnote Parsing**: `case-footnote-01` fails to recognize footnotes
  (li/oi-level errors).
- **Table Parsing**: `case-table-01` completely fails at parsing tables.
- **Indentation**: Incorrect indentation rendering in `case-indent-01` and
  `case-indent-02`.
- **Image/Table OCR**: `case-image-table-01` fails text recognition for tables
  inside images, markdown parsing fails, and image OCR description is too shallow
  for Ontology & Semantics.
- **Math/Superscripts**: `case-math-01` fails to parse superscripts like m^3
  properly. Needs strict Ontology grammar for math formulas.
- **Missing UI Elements**: DAG (Directed Acyclic Graph) view is currently
  missing from the frontend for `case-dag-01`.
- **Ontology neighborhood (ADR 0119 / #341)**: Event Lineage remains post-to-post reconstruction. Typed `Post -> mentions -> Person -> affiliatedWith -> CorporateEntity` inspection now has `GET /api/ontology/neighborhood` plus the Keyman **Inspect ontology neighborhood** control. Remaining work is independent APPROVE + exact-head CI, not a second GNB destination.

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

*This document is continuously updated by the hourly automated agent loop.*
