# Product & Technical Gap Baseline

Identifiers in this file are synthetic or PR/issue numbers. Do not paste live
source-post, account, or tenant identifiers here.

## 1. Known Parsing & Frontend Display Gaps
- **Footnote Parsing**: some HTML list/footnote structures are not recognized (li/ol level errors).
- **Table Parsing**: some HTML tables fail to parse into semantic units.
- **Indentation**: some posts still render authoring-app spacing instead of semantic paragraphs.
- **Image/Table OCR**: tables inside images can produce shallow OCR/captions that are too thin for ontology work.
- **Math/Superscripts**: superscripts such as m^3 are not always parsed as math.
- **Missing UI Elements**: some post-detail paths still omit the Event Lineage DAG.

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

## 4. OpenTelemetry error traces and correlated audit logs

Evidence current as of 2026-08-23. Unmerged work is named as unmerged.

| Item | Status | Evidence |
| --- | --- | --- |
| LineageWeave #383 `feat/otel-session-diagnostics-main` | Open; protected-main merge **blocked** pending independent review | Error-status API spans; `record_server_failure` inside `traced()` so logs share TraceId/SpanId; Global Ask source-gather classified as 503; W3C `traceparent` on `post_json`/`get_json`; OTLP traces/metrics/logs when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Exact head is the open PR, not this table. |
| LineageWeave #345 | Related prior OTel work; cherry-picked onto #383 because it landed on a non-main feature branch | cited from #383 body; not a separate merge target for this gap |
| contextual-orchestrator #818 | Out of this checkout; orchestrator-side session/trace binding | correlation contract, not merged from LineageWeave |
| GRC #51 / ADR 0009 | Out of this checkout; GRC remains control-evidence owner | consume bounded `operation_code` / `failure_outcome` plus TraceId/SpanId; do not copy GRC tables |
| Live OTLP collector in Compose | **Still open** | Compose has no collector service. Export is opt-in via `OTEL_SERVICE_NAME` and `OTEL_EXPORTER_OTLP_ENDPOINT`. Orchestrator no longer interpolates an empty endpoint over `~/.env`. |

Remaining gaps: protected merge of #383; a deployment collector; cross-process Valkey W3C in stream payloads (same-process child spans already share TraceId; stream fields stay identity/digest only).

Operator join key for other agents: `docs/doctoring/OPENTELEMETRY_REFERENCES.md` names `trace_id`, `span_id`, `traceparent`, `operation_code`, `failure_outcome`, `error_type`, and bounded `session_id`.

*This document is continuously updated by the hourly automated agent loop.*
