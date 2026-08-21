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

## 4. Public Ontology Publication Gap
- **Observed gap**: `https://contextualwisdomlab.github.io/LineageWeave/ontology#` has no deployed public resource even though the authoritative OWL/RDFS/SKOS Turtle ontology already exists in `docs/ontology/lineageweave-kg.ttl`.
- **Active remediation — PR #371**: Add a deterministic GitHub Pages renderer, fail-closed publication boundary, and protected deployment workflow that publishes fragment-addressable HTML, byte-identical Turtle, isomorphic JSON-LD and N-Triples, the PROV-O support profile, and a source-digest manifest.
- **Publication safety**: The deployment path rejects duplicate term fragments, linked RDF IRIs outside HTTP(S), symlink outputs, source-overlapping output paths, and replacement of directories not marked as generated. Pull requests validate only; only `main` may publish, and an in-progress deployment is not cancelled by a newer run.
- **Namespace boundary**: The knowledge-graph ontology/runtime use a lowercase `lineageweave` namespace while the PROV-O support profile uses repository-case `LineageWeave`. PR #371 does not silently rewrite either semantic identity. Issue #372 owns the inventory, canonical namespace decision, compatibility vocabulary, deprecation window, stored-data migration, and downstream consumer verification.
- **Completion criteria**: Exact-head ontology/publication tests pass; owned renderer and publication-boundary statement/branch coverage is 100%; required security and repository Checks reach terminal success; an independent approval exists; the repository Pages source is GitHub Actions; the protected `main` deployment succeeds; and the requested URL resolves with stable anchors such as `#Post`.
- **Current truth**: Until PR #371 is merged and the `main` Pages deployment is verified, the URL remains unbuilt and must not be reported as live.

*This document is continuously updated by the hourly automated agent loop.*
