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
- **LLM Orchestration**: Partially resolved -- every one of `backend/app/main.py`'s 13 orchestrator client factories (`_keyman_extraction_client`, `_entity_relationship_client`, `_organization_name_resolution_client`, `_customer_hint_resolution_client`, `_corporate_hierarchy_inference_client`, `_post_summary_client`, `_adjudication_client`, `_post_structure_client`, `_post_chat_client`, `_commitment_extraction_client`, `_vision_client`, `_embedding_client`, `_post_evaluation_client`) routes through `settings.orchestrator_base_url`/`orchestrator_api_key` -- confirmed no hardcoded provider SDK, key, or endpoint (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `BYTEZ_API_KEY`, `NVIDIA_NIM_API_KEY`, `OPENROUTER_API_KEY`) appears anywhere in `lineageweave/`, `backend/`, or `scripts/`. Generative and VISION requests send `"mode": "auto"` plus a `reasoning_effort` value, delegating model selection and reasoning-depth allocation per call; the embedding client uses the orchestrator's dedicated embedding contract and correctly has no reasoning-depth field. Still open: exact-head upstream evidence that `contextual-orchestrator` discovers all configured provider credentials and applies its Fugu/Conductor/TRINITY policy. That evidence must be fixed in the upstream repository when absent; LineageWeave client routing alone does not prove it.

*This document is continuously updated by the hourly automated agent loop.*
