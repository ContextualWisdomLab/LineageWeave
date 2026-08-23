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
- **Testing**: (Partially resolved -- FIPC) `tests/test_fast_mlsirm_fipc_recovery.py` now exists, exercising the actual production functions (`fit_polytomous`, `score_polytomous`, `cat_simulate_polytomous`) for Fixed-Item Parameter Calibration against synthetic data with known ground truth. It simulates a two-period design matching `period_report.py`'s own documented rationale ("Independent refits would re-center each week at 0 and hide real movement") and proves the claim directly -- FIPC-scoring period 2 on period 1's fixed item bank recovers a deliberate period-2 mean shift (~0.37 detected vs. ~0.43 true), while an independent free refit of the identical period-2 data re-centers to ~0.01, erasing the shift entirely. Not a placebo comparison; the test asserts both outcomes. The remaining three recovery tests this entry asked for -- GRM (`tests/test_fast_mlsirm_grm_recovery.py`, #451), GPCM (`_gpcm_recovery.py`, #452), and CAT (`_cat_recovery.py`, #453) -- are on separate open PRs, not yet in this tree; once all three land this entry is (Resolved).
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

*This document is continuously updated by the hourly automated agent loop.*
