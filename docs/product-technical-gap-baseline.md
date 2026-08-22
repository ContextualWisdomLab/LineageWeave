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
- **Testing**: Mostly resolved -- three real parameter-recovery tests now exist (`tests/test_fast_mlsirm_grm_recovery.py`, `_gpcm_recovery.py`, `_cat_recovery.py`), each simulating responses from known true item parameters and person thetas (GRM/Samejima 1969, GPCM/Muraki 1993 -- `fast_mlsirm` ships no polytomous simulator, so both formulas are implemented directly, matching `PolytomousFit`'s documented parameterization) and asserting recovered EAP thetas match true thetas within a literature-typical RMSE/correlation bound. The CAT test additionally verifies the actual adaptive-testing value proposition via `fast_mlsirm.cat_simulate_polytomous` (Dodd, De Ayala & Koch, 1995): a mean of ~8.7 of 40 items reaches accuracy (RMSE ~0.40, correlation ~0.91) comparable to the full-bank GRM test (~0.38/~0.92) -- not just "it runs," but "it recovers theta using substantially fewer items than the full bank," the property that actually distinguishes CAT from full-bank testing. Still open: Fixed-Item Parameter Calibration (Kim, 2006 FIPC -- `period_report.py` uses this for later periods, untested; check `link_fixed_item_parameters`/`fixed_item_calibration_diagnostics` for the real two-stage simulation this needs).
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

*This document is continuously updated by the hourly automated agent loop.*
