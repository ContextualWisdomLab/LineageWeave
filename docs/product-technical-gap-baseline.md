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
- **Testing**: Partially resolved -- `tests/test_fast_mlsirm_grm_recovery.py` and `tests/test_fast_mlsirm_gpcm_recovery.py` (new) simulate polytomous responses from known true item parameters and person thetas under the GRM (Samejima, 1969) and GPCM (Muraki, 1993) formulas respectively (`fast_mlsirm` ships no polytomous-specific simulator, so both response-generation formulas are implemented directly in the tests, matching `PolytomousFit`'s own documented parameterization), fit them with `fast_mlsirm.fit_polytomous` under each model -- the same function/model options `period_report.py`'s production code uses -- and assert the recovered EAP thetas are close to true by RMSE and correlation (GRM: RMSE ~0.38, correlation ~0.92; GPCM: RMSE ~0.30, correlation ~0.95). This is real parameter-calibration accuracy testing against synthetic data with known ground truth for both models `period_report.py` can select between, not infra-only smoke tests. Still open: Fixed-Item Parameter Calibration (Kim, 2006 FIPC -- `period_report.py` uses this for later periods, untested) and CAT remain unverified -- though `fast_mlsirm.cat_simulate_polytomous` (a real adaptive-test simulator over a fitted GRM/GPCM bank, Dodd, De Ayala & Koch, 1995) was found to exist and is a concrete next step, not yet exercised anywhere in this repo's tests.
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

*This document is continuously updated by the hourly automated agent loop.*
