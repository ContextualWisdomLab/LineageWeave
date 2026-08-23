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
- **DB Architecture**: PostgreSQL is the only datastore (no file DBs) -- verified. Split by sub-claim after checking real code, not left as one compound item: (a) *DB locks* -- (Resolved) row-level `for update` locks in `backend/app/post_content_worker.py`/`post_content_queue.py` are always keyed by an already-known `post_id` (from a Redis-stream event or an upsert target), never a "grab any available row" scan, so lock contention across concurrent workers is avoided by the Redis-stream distribution layer, not needed at the SQL level -- `SKIP LOCKED` would be solving a race that doesn't exist here. (b) *Hot partitions / read-write replicas* -- partially resolved, re-verified with a narrower finding: every table's primary key defaults to `uuid_generate_v4()` (checked all 12+ `primary key default` declarations in `migrations/0001_initial_schema.sql`), not a sequential/serial id or a time-ordered UUID -- this is the standard mitigation for the classic hot-partition failure mode (concurrent inserts contending on the same B-tree right edge / index leaf page because keys arrive in ascending order), and it is already universally in place, not something to add. Still genuinely open: no `CREATE TABLE ... PARTITION BY` exists anywhere in `migrations/*.sql` (the one `partition by` hit is an unrelated window-function clause in a view) -- so a single table growing large enough that query performance degrades (not an insert-contention problem, a scan/index-size problem) has no partitioning strategy to fall back on -- and `docker-compose.yml` defines exactly one `postgres` service with one `DATABASE_URL` used for both reads and writes, no replica topology. Not attempted here: no evidence of an actual table already large enough to need partitioning, and speculatively partitioning tables or standing up a replica without that evidence is unscoped infrastructure work, not a documentation fix -- flag for a future cycle if/when a specific table's size or a real read-latency-under-write-load symptom is observed. (c) *3rd normal form* -- not fully audited (40+ migrations); spot checks found no obvious repeating-group or partial-dependency violations, but a full audit is out of scope for a single cycle.
- **Zotero Integration**: Papers and standards referenced by TEPP must be synced via Local Zotero API (http://localhost:23119/api/) and cited using APA 7th edition in docstrings.
- **Testing**: We need actual testing of Psychometrics (Fast-MLSIRM parameter calibration, RMSE of estimates, Fixed-Item Parameter Calibration, CAT) against synthetic/demo data.
- **Security & Compliance**: PII masking cannot break the system. Need SOC 2 and CSAP compliance alternatives to blind PII masking. 
- **LLM Orchestration**: Ensure ALL LLM calls route through `contextual-orchestrator` utilizing API keys (BYTEZ, NVIDIA, OPENROUTER, OPENAI) with auto model discovery and optimal reasoning effort allocation (Fugu/Conductor/TRINITY research).

*This document is continuously updated by the hourly automated agent loop.*
