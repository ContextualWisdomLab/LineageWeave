# Product & Technical Gap Baseline

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: Resolved for the committed contract -- synthetic regressions in `tests/test_chunking.py` cover markerless, HTML, Word, citation, and OOXML footnote forms while preserving separate list-item chunks. Private-runtime validation is retained only as a non-identifying aggregate.
- **Table Parsing**: Partially resolved -- a synthetic HTML-table regression proves row-atomic DOM chunking. Reader-facing table rendering remains unverified.
- **Indentation**: Authorized private-runtime validation found incorrect indentation rendering in two records. Only the non-identifying count is retained here.
- **Image/Table OCR**: Authorized private-runtime validation found one image-table record whose text recognition, markdown parsing, and ontology description were insufficient. No identifying record evidence is retained here.
- **Math/Superscripts**: Authorized private-runtime validation found one record whose superscript quantity was rendered incorrectly. Strict ontology grammar for mathematical notation remains open.
- **Missing UI Elements**: Authorized private-runtime validation found one record whose lineage DAG was unavailable in the reader surface. No identifying record evidence is retained here.

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
