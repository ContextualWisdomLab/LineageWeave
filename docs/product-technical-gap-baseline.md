# Product & Technical Gap Baseline

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: Keep this gap open until a synthetic nested-footnote fixture preserves list levels end to end.
- **Table Parsing**: Keep this gap open until a synthetic table fixture survives source parsing and buyer rendering.
- **Indentation**: Keep this gap open until synthetic continuation-line fixtures preserve semantic nesting without presentation-only alignment.
- **Image/Table OCR**: Keep this gap open until synthetic image-table fixtures prove region recognition, OCR, and ontology evidence through contextual-orchestrator.
- **Math/Superscripts**: Keep this gap open until synthetic formula fixtures preserve superscripts such as m^3 under the governed ontology grammar.
- **Missing UI Elements**: (Resolved) `EventLineageSection` renders `LineageDag` whenever the authorized post-scoped graph contains nodes. If an authorized runtime post still shows no graph, record only an aggregate, non-identifying reproduction and reopen this as a reconstruction-data gap.

## 2. LLM Extraction & Knowledge Graph Gaps
- **Multiple Project Extraction**: (Resolved) LLM prompt updated to request key_events as objects with project_name, separating events correctly.
- **5W1H Missing**: (Resolved) LLM prompt updated to explicitly request 5W1H evidence items in the JSON output array.
- **R&R and Keyman Missing**: (Resolved) LLM prompt updated to explicitly instruct using actual stated names rather than collective titles.
- **Entity Resolution / Searxng**: Keep this gap open until synthetic organization-alias fixtures prove abbreviation mapping with Searxng and knowledge-graph corroboration.
- **Meso-level Team Mapping**: (Resolved) Checked extraction logic; `team` mapping logic is present and correct, but LLM needed better explicit instruction which is covered by R&R resolution.
- **Base64 Image Omni-modal**: Current text-only embedding fails on images. Omni-modal LLM processing is required for images to capture layout, font size, colors, and spatial meaning.

## 3. General Architecture Gaps
- **DB Architecture**: Ensure PostgreSQL is strictly used (no file DBs), 3rd normal form is maintained, and Hot Partitions are handled. DB locks must be managed (or use read/write replicas).
- **Zotero Integration**: Papers and standards referenced by TEPP must be synced via Local Zotero API (http://localhost:23119/api/) and cited using APA 7th edition in docstrings.
- **Testing**: We need actual testing of Psychometrics (Fast-MLSIRM parameter calibration, RMSE of estimates, Fixed-Item Parameter Calibration, CAT) against synthetic/demo data.
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

*This document is continuously updated by the hourly automated agent loop.*
