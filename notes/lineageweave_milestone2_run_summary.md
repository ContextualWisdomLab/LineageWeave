# LineageWeave Product Acceptance Summary (2026-08-13)

## 실데이터 기준 최신 점검 정리 (2026-08-15 15:03 KST, direct PostgreSQL)

- 실행 명령:
  - `LINEAGEWEAVE_DSN='postgresql://seonghobae@localhost/postgres'`
  - `LINEAGE_SOURCE_TABLE='<runtime_source_table>'` (실행 환경의 런타임 테이블명을 사용)
  - `LINEAGEWEAVE_WRITE_REPORTS=1`
  - `LINEAGEWEAVE_KEYMAN_LIMIT=0`
  - `LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT=25`
  - `LINEAGEWEAVE_REPORT_JUDGE_MAX_ATTEMPTS=3`
  - `LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS=240`
  - `LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT=30`
  - `LINEAGEWEAVE_KEYMAN_LLM_TIMEOUT=30`
  - `LINEAGEWEAVE_CHAT_LLM_TIMEOUT=30`
  - `LINEAGEWEAVE_JSON_OUT='data/lineageweave_stable_real.json'`
  - `LINEAGEWEAVE_ANALYTICS_OUT='data/lineageweave_stable_real_analytics.json'`
  - `bash scripts/run_real_lineageweave.sh`
- 정량 산출치:
  - 최신 스냅샷: `2026-08-15 15:03:49+09:00`
  - `rows=43814`, `documents=43707`, `threads=42467`
  - `postgres_documents=43707`, `postgres_edges=6318`, `postgres_kg=264991`, `postgres_knowledge_edges=838908`, `postgres_lineage_edges=6318`, `postgres_affiliate=135`
  - `inferred_edges=6211`, `reports=80` (`weekly=40`, `monthly=40`)
  - `analysis_todo_items=28211`, `analysis_calendar_items=28211`, `analysis_appointment_records=6982`
- 판정/평가 상태:
  - `analysis_period_reports`: (`llm_judge`, `fail`, 26), (`llm_judge`, `pass`, 54)
  - `analysis_report_metric_scores`: 총 320건, `pass` 231 / `fail` 89 (abstain 0)
  - `analysis_linked_scores`: 400
  - `analysis_factor_items`: 15, `analysis_factor_item_evidence`: 10
- 보안/권한/동작 정합성(개발 액터 검증):
  - `analysis_run_records` 최신: `row_count=43814`, `document_count=43707`, `thread_count=42467`, `keyman_transport=live_http`, `product_transport=live_http`
  - Admin/reader actor 검증에서 `POST /api/documents/<id>/visibility` 권한 분기, `/api/admin/lineage/edges` 분기, private 문서 조회 범위가 일치.
  - `GET /api/documents/<id>/chat` 은 200으로 응답됨.
- 실행 증적:
  - `LINEAGEWEAVE_DSN='postgresql://seonghobae@localhost/postgres' uv run python scripts/check_runtime_schema_contract.py` 결과 `lineageweave-runtime-schema-contract-ok`
  - `scripts/run_real_lineageweave.sh` 실행 중 `LINEAGEWEAVE_VALIDATE_RUNTIME_SCHEMA=1` 기준 통과 후 `analysis_run_records`가 최신 값을 반영함
  - 실행 시작 시 ContextualWisdomLab/TEPP 및 ContextualWisdomLab/contextual-orchestrator open PR 상태를 read-only로 점검해 `lineageweave_audit_log`에 `tepp_open_pull_requests`, `contextual_orchestrator_open_pull_requests`를 남김
  - `uv run pytest -q tests/test_lineage_runtime_contract.py -k "parse_ragas_metric_scores or period_report_judge_stops_on_budget"` → `1 passed`
  - `uv run pytest -q tests/test_http_contract.py` → `6 passed`
  - `uv run pytest -q tests/test_application_data_flow_contract.py` → `6 passed`
  - `uv run pytest -q tests/test_lineage_runtime_contract.py -k "load_visible_document_index or load_document_detail or visibility or authorization_rejects"` → `2 passed`
  - `script run_real`/DB 갱신/브라우저 루프의 점검은 별도 섹션(2026-08-14/15)에서 지속 축적.

## 다음 순차 보강 루프 (2026-08-15)

- 첫 단계: 보고서 판정 수용성 강화
  - `abstain`이 `0`으로 수렴했고 `llm_judge` 판정이 `54`/`80`으로 확보됨.
  - `analysis_linked_scores`를 `400`으로 정상화 완료.

## 현재 인수인계 버전 (2026-08-15 기준)

- 본 장의 수치는 `2026-08-15 15:03:49+09:00` 스냅샷의 기준선이며, 아래 다른 섹션은 과거 재시도/실패복구 기록입니다.

- 파이프라인 완결성 근거(실데이터 `LINEAGE_SOURCE_TABLE`):
  - `analysis_run_records` 최신행:
    - `run_stamp=2026-08-15 15:03:49+09:00`
    - `row_count=43814`, `document_count=43707`, `thread_count=42467`
    - `source_query='SELECT zer.* FROM <runtime_table> AS zer'`
    - `keyman_transport='live_http'`, `product_transport='live_http'`
    - `metadata_payload` 기준 `knowledge_node_rows` 264755 / `knowledge_edge_rows` 838410 (현재 DB는 추가 정규화 후 264991 / 838908로 확인됨)
  - 판정/리포트:
    - `analysis_period_reports`: 80행 (`weekly`: pass 29/fail 11, `monthly`: pass 25/fail 15)
    - `analysis_report_metric_scores`: 320행 (`pass` 231 / `fail` 89, abstain 0)
    - `analysis_linked_scores`: 400행
  - KG 적재:
    - `analysis_knowledge_graph_nodes=264991`
    - `analysis_knowledge_graph_edges=838908`
    - `analysis_lineage_edges=6318`
- 접근 제어 및 기능 증적:
  - 계약 테스트 근거: `tests/test_http_contract.py`, `tests/test_application_data_flow_contract.py`,
    `tests/test_lineage_runtime_contract.py`(권한 분기/공개·비공개/문서 조회/관리자 경로).
  - 실행 증적: `uv run pytest -q tests/test_http_contract.py` → `6 passed`,
    `uv run pytest -q tests/test_application_data_flow_contract.py` → `6 passed`.
  - 실브라우저 검증( `Fresh Edge reader E2E`, `Keyman Compose fallback` )에서
    일반권한/관리자 경로 분기와 문서 팝업/KG 근거 조회를 확인.

## 다음 순차 보강 루프 이관 항목 (2026-08-15 확정)

1. TEPP-REST 경계 재점검
   - TEPP는 `import/REST` 경계만 남았는지, `acth_revision`과 `row_successor` 의미 분리를 재점검.
2. 접근 제어 운영 연동
   - 실 Keyverse 생산 계정을 이용한 로그인→권한 경로→관리자 메뉴까지 E2E를 정례화.
3. KG/Semantic 표준화
   - 팀/기관/인물 동명이인 및 조직-팀-역할 정합성 규칙(동일 entity 판별)을 런타임 KG 정책으로 고정.
4. 운영 감시 자동화
   - `analysis_run_records` 기반 게이트(행 수 급변, judge_source 이상, linked_score=0, 권한 정책 변경)를 알림 자동화.

- 둘째 단계: 운영 메타-증적 일원화
  - `analysis_run_records.metadata_payload`의 `knowledge_*`/`source_query`/`evidence_policy`를 기준점화하고
    `notes/` 문서에 “latest, historical baseline, fallback” 3단계 표기 통일.
- 셋째 단계: 운영 인증 연동 완료
  - 실 Keyverse production 계정으로 로그인 플로우까지 포함한 E2E를 추가하고(권한 경로/관리자 메뉴/고객 화면 일괄),
    14일 주기로 재확인.

## Adaptive factor-item reanalysis (2026-08-15)

The live report Judge received a bounded `factor_item_catalog` request with
multiple persisted report writings. The allowlisted parser returned five
evidence-bound LLM candidates; no candidate without supplied report/document
support was accepted. The current bank contains ten fixed anchors and five
candidates. The separate Rust-backed fast-mlsirm connector returned 15 finite
calibration rows, and all 15 persisted items are marked `calibrated`.

The direct PostgreSQL reanalysis initially completed 80 report slices and 320
normalized RAGAS observations in the earlier bounded-judge attempt. Fifty-eight
report slices received five package-produced linked scores each (290 total); 22
slices remained explicitly unlinked because their item responses were
insufficient. Candidate support is stored in `analysis_factor_item_evidence`,
calibration is stored in `analysis_factor_item_calibrations`, and the post-check
found zero orphan candidate-evidence rows. The earlier 400-score reconciliation
below is a historical run record and is superseded by the report-judge recovery
and fallback state documented later.

## Package-only psychometric reconciliation (2026-08-15)

The runtime report tables were checked read-only before repair and contained
135 legacy derived score rows across 27 reports. A dry-run replayed each
persisted Judge item response through the separate local `fast-mlsirm`
connector and produced 80/80 connector-linked reports and 400/400
`fast_mlsirm` scores. The guarded PostgreSQL reconciliation then replaced only
the derived report/score rows; source documents were not changed.

A read-only post-check found 400 package-produced scores, zero reports without
scores, zero orphan scores, and zero legacy fallback payload rows. This is
runtime data evidence for the package-only boundary, not an upstream release
or independent calibration acceptance.

## Customer-surface pending-state correction (2026-08-15)

The dedicated general-user customer screen now distinguishes an actor-scoped
`/api/customers` request in flight from a settled empty customer master. Its
count, account list, selected-account detail, and affiliate-tree panel retain
loading or transport-error copy until the authorized PostgreSQL response
settles. This is a UI state correction only; it does not widen customer
visibility or create a customer without account-to-document evidence.

The current source gate passed 331 tests, 100 percent product-runtime
line-and-branch coverage (7,095 statements and 2,760 branches), Python
compilation, and the React production build.

## Fresh Edge reader E2E evidence (2026-08-15)

The built React application was served by the direct-PostgreSQL HTTP server
with an explicitly scoped local reader actor and exercised in Microsoft Edge.
The browser completed the authenticated session check, 업무 홈, 업무공간,
고객 화면, document popup, source-evidence drawer, and Knowledge Graph
request. The reader session exposed no administrator navigation and no
diagnostic `#metricRows` strip. The run returned HTTP 200 for the customer,
evidence, and knowledge routes and wrote fresh home, workspace, customer, and
popup screenshots under the external E2E artifact directory. This is local
development-session UX evidence only; it is not production Keyverse acceptance.

## Task-aware orchestration boundary recheck (2026-08-15)

The product transport now derives a bounded orchestration envelope from the
LLM task. Simple extraction/classification selects single-model routing;
customer, appointment, issue, report, ontology-verification, and multimodal
inspection tasks select a deep thinker/worker/verifier/synthesizer workflow
with one recursive pass, a fixed authorized access list, and high reasoning
effort. Direct OpenAI-compatible gateways receive only nested portable prompt
metadata. Top-level `route`/`conduct` controls are added only when the
configured base URL is explicitly the contextual-orchestrator service.

Focused transport tests and the full product suite passed after this change.
The upstream multimodal message-content contract is still an open, independently
reviewed PR; this local evidence does not claim that upstream behavior is
merged or deployed.

## Commands executed
- `uv run pytest -q`
- `python -m py_compile lineageweave.py lineageweave_server.py compose/http_standin.py`
- `cd web && npm run build`

### Real-source runbook checks

- `./scripts/run_real_lineageweave.sh` now supports `LINEAGEWEAVE_LIMIT` for
  bounded smoke execution and prints masked DSN metadata.
- Invalid limit validation is enforced (`LINEAGEWEAVE_LIMIT` must be a non-negative
  integer), and malformed values fail fast with a concise message before database
  execution.
- After analysis/reports write, runtime schema contract enforcement is now integrated
  via `LINEAGEWEAVE_VALIDATE_RUNTIME_SCHEMA` (default `1`), which executes
  `scripts/check_runtime_schema_contract.py` to reject unexpected production-schema
  drift immediately.
- Runtime execution now logs run metadata (`source_table`, `write_reports`,
  `keyman_limit`, `limit`, `sweep_content_inspections`,
  `inspection_document_limit`, `validate_runtime_schema`) before running, and
  logs whether runtime-schema validation is enabled/disabled after execution.
- Run output now includes a compact plan line (`lineageweave_real_plan`) and
  explicit artifact path summary (`json_out`, `analytics_out`), plus
  `lineageweave_contract_check_status` so audits can assert schema contract
  gate outcome quickly.
- Audit logging for the real-source script now emits `lineageweave_audit_log` JSON
  records at run start/complete and on process exit (including failures), with
  masked DSN, limits, feature toggles, and schema-check outcomes for CI parsing.
- `bash -n scripts/run_real_lineageweave.sh` passes, and identity-boundary
  contract tests remain green: `uv run pytest -q tests/test_identity_boundary_lock.py
  tests/test_oidc_standin_lock.py` -> `9 passed`.
- New shell-script contract tests were added for the audit stream itself:
  `uv run pytest -q tests/test_run_real_lineageweave_script.py` -> `3 passed`
  (`run_real_lineageweave` emits required start/complete/exit audit JSON events and
  preserves non-zero exit codes on failure).
- Audit-stream contract now also covers validation-failure runs:
  `uv run pytest -q tests/test_run_real_lineageweave_script.py` -> `3 passed`
  (`LINEAGEWEAVE_LIMIT` validation failure emits start/exit audit events and the
  non-zero exit code is preserved in `lineageweave_real_run_exit`).
- Script audit-event contract now validates `timestamp_utc` is UTC-parsable ISO-8601
  for emitted events (`datetime.fromisoformat(...replace("Z","+00:00"))`), closing
  CI parsing consistency for all start/complete/exit events.
- Added event-schema assertions for required JSON fields by event type (`start`,
  `complete`, `exit`) to make parsing resilient to missing keys and type drift
  in CI logs.
- Event-schema assertions are now loaded from
  `tests/resources/lineageweave_real_audit_event_schema.json`, so contract
  updates can be maintained without changing Python assertions.
- A small shared test contract utility now owns contract loading/validation
  (`tests/_contract_utils.py`), and the run-real script contract test now uses it
  directly for future extension without duplicate parsing code.
- Runtime schema contract value is now also contract-asserted (`enabled`/`disabled`)
  for complete/exit events so monitoring dashboards cannot ingest invalid
  tri-state values.
- OIDC worker-route rejection is now contract-driven in tests via
  `tests/resources/compose_oidc_worker_route_contract.json`; route method/path,
  expected status, and expected JSON body are now explicit data.
- Combined regression contract run:
  `uv run pytest -q tests/test_identity_boundary_lock.py tests/test_oidc_standin_lock.py tests/test_run_real_lineageweave_script.py`
  -> `12 passed`.

The source read and common ENUM table access use direct `psycopg` connections.
The runtime query projects lineage columns and bounded content metadata; the
React app reads through `lineageweave_server.py`, not a file export.

## Full-data run outcome
- source snapshot row count: `43814`
- source document count: `43707`
- source thread count: `42467`
- observed source actors spanning more than one PU: `79`
- cross-PU actor/company pair observations: `160`
- persisted KG nodes: `88672`
- persisted KG edges: `268416`
- evidence-backed `cross_pu_transaction` edges in the full snapshot: `4`
- content manifest: 3,374 inline-image candidates, 402 artifact
  references, maximum content size 49,648,256 bytes; source bytes/base64 are
  not exported
- direct inline-image audit: 7,084 source rows containing image data; 6,955
  at or below the 6 MiB inspection ceiling and 129 above it
- verified live-image inspection: one bounded direct PostgreSQL image returned
  a model identity, 669 OCR characters, and its private digest without emitting
  source bytes in the verification output
- `data/lineageweave_full_analytics.json`
  - `documents_with_multiple_rows`: `78`
  - `multi_document_threads`: `633`
  - `max_rows_per_document`: `4`
  - `max_revision_gap_seconds`: `7297605.0`
  - `docs_with_duplicate_timestamps`: `18`
- `top_threads` 및 `top_documents` 값이 생성되어 BI 상단 카드/목록에서 바로 소비 가능

## Product evidence

- Persisted graph tables: `analysis_knowledge_graph_nodes` and
  `analysis_knowledge_graph_edges`
- API health: `GET /api/health`
- Product entrypoint: compiled `web/dist/index.html`
- Event queue: PostgreSQL `analysis_event_outbox` flushed to Valkey Stream
  `lineageweave_events`; unavailable Valkey leaves committed events pending.
- KG lookup: per-node `kg_depth` budgets with cross-entity edge cost and an
  optional request ceiling exposed through the knowledge route.
- ADR and requirement mapping: `docs/planning/adrs/0001-lineageweave-runtime-and-governance.md`
- Inline-image decision, normalized OCR/label schema, and verified-TLS policy:
  `docs/planning/adrs/0002-verified-inline-image-inspection.md`
- Keyverse authorization-code, PKCE, claim-validation, and session-lifetime policy:
  `docs/planning/adrs/0003-keyverse-authorization-code-pkce.md`

## 0.2.8 direct-source correction

- The bounded source projection now computes an inline-image/markup marker
  inside PostgreSQL. This classifies a large inline image even when its marker
  begins beyond the 512-character prefix, while returning no source bytes in
  the graph or default API payload.
- The refreshed direct-source persistence run retained `43,707` document rows
  and did not write a raw-content output artifact.

## Current container re-validation (0.2.8)

- Built the `0.2.8` product image from the locked workspace and promoted it
  only after a separately staged runtime check.
- The promoted product completed direct PostgreSQL, authenticated-session,
  document-index, authorized-inline-asset, Valkey-event-queue, and worker
  health checks.
- The database-side marker classified an oversized inline image whose marker
  was beyond the bounded prefix, without returning source bytes in the
  verification result or default API payload.
- The worker returns `404` for OpenID discovery and token paths and has no
  local identity route; the product remains a Keyverse relying party.
- A cross-company/PU KG acceptance case verified that shared nodes retain only
  the actor-visible document scope and that relationships with hidden evidence
  are not returned.
- Historical release commands completed: Python compile, React production
  build, Compose configuration validation, and 82 passing tests. Measured
  branch coverage was 90% at that earlier baseline; the recheck below is the
  current coverage evidence.

## Acceptance boundary

The direct-source/API acceptance checks passed using the explicit development
actor. Production acceptance additionally requires a provisioned Keyverse
issuer, confidential client, HTTPS redirect URI, and approved claim mappers to
complete the OIDC redirect, then open `/`, load `/api/documents`, open a
document popup, retrieve evidence/content through document-scoped routes, and
select a precomputed KG node. Image inspection is available on demand to
authorized writers; semantic embedding remains a separate follow-on worker.

## Reconciled runtime evidence (2026-08-14)

A fresh aggregate-only direct PostgreSQL read supersedes earlier point-in-time
counts in this note: 43,814 source rows, 43,707 document nodes, 42,467 threads,
88,708 KG nodes, and 268,473 KG edges. The maximum source content cell remains
49,648,256 bytes; no source text, image bytes, identifiers, or model output
were exported for this reconciliation.

One controlled, document-scoped, bounded raster inspection completed through
the live HTTPS model path and is now durable in PostgreSQL: one inspection with
a recorded model, 887 OCR characters, zero persisted object-label rows, and
one `content_inspected` outbox event with zero pending delivery. This is actual
analysis-path evidence, not evidence of browser-based Keyverse acceptance.

## Fresh full-data and provenance verification (2026-08-14)

The current aggregate-only PostgreSQL read reports 43,814 source rows, 43,707
documents, 42,467 threads, 88,672 KG nodes, 132,379 semantic nodes, and
268,425 KG/semantic edges. The persisted lineage edge set contains 4,419 rows:
3,023 inferred, 1,372 observed, and 24 predicted. These counts are aggregate
evidence only; raw source identifiers and content are not copied into this
public note.

The same live database contains 80 reports (all 80 live-judge labels), 5 factor definitions with 5 factor items, 400
linked scores, 28,211 To Do rows, 28,211 calendar rows, 6,982 appointments,
one inference run, one bounded content inspection, and 10 published outbox
events with zero pending outbox rows. No image bytes or base64 content are
exported by the graph/API snapshot.

The Local Zotero verification stored twelve method-paper parents and twelve
bounded OA originals; all twelve originals have non-empty SHA-256 digests and
explicit attachment outcomes in `analysis_method_paper_records`. Exact local
parent/child lookup resolves a Connector attachment key only after URL and
digest verification.

The prior product verification completed 208 collected tests, Python
compilation, the React production build, Compose configuration validation, and
100% line and branch coverage for the three shipped Python modules.

## Recheck after browser and semantic-preservation fixes (2026-08-14)

The current source-hash-guarded isolated-PostgreSQL rerun completed 260 tests
and one intentional skip (261 collected) with 100% line and branch coverage across `lineageweave.py`,
`lineageweave_embeddings.py`, `lineageweave_server.py`, and
`compose/http_standin.py` (5,947 statements and 2,312 branches), plus Python
compilation, React build, and Compose configuration validation. The live
bundled-browser run used the explicit
local development actor and exercised the Keyverse redirect/form, list, popup,
source drawer open/close, KG lookup, and admin visibility POST. It is local
authorization evidence, not an accepted real-user Keyverse credential. The
updated run selects an actor-manageable document from authorized corp/PU index
metadata and completed both private and public visibility POSTs with HTTP 200.

The R&R KG now persists model-supplied `node`, `entity`, `relationship`, and
`direction` metadata on qualified attribution nodes. Cold mutations return
after their direct PostgreSQL/outbox write without forcing a full graph
rebuild. These changes preserve the direct-PostgreSQL and TEPP HTTP boundary.

Compose product and worker services now optionally load the operator environment
file `${LINEAGEWEAVE_ENV_FILE:-$HOME/.env}` without copying credentials into the
image or repository. A one-off Compose probe confirmed the local live gateway
is visible inside the worker container.

## Operational verification on requested source (2026-08-14)

- Executed full source-table analysis directly against the operator-configured
  PostgreSQL source using `uv run python lineageweave.py --table "$LINEAGE_SOURCE_TABLE" --write-reports`.
  - rows=43814, documents=43707, threads=42467.
  - reports=80 generated (weekly/monthly × project/team/pu slices), linked score artifacts written via fast-mlsirm path.
  - `data/lineageweave.json` (artifact) and `data/lineageweave_analytics.json` created, and `data/lineageweave_analytics.json` includes 400 linked scores.
- Re-ran the persisted 80 report slices with the installed local fast-mlsirm
  connector after making `report_id` the temporal psychometric observation
  unit. All 80 judge labels are live `llm_judge` results and all 400 linked
  scores are package-produced `fast_mlsirm` results; no recorded response was
  used to fill a missing score.
- Verified auth boundary with local Keyverse container (`http://127.0.0.1:28080/realms/cwl`) by running the product server with explicit dev actor config:
  - `GET /api/health` -> `{"status":"ok","database":"ok"}`.
  - `GET /api/login` -> HTTP 302 to Keyverse authorization endpoint with S256 challenge.
  - `GET /api/documents` (without session) -> `401 keyverse_session_required`.
- Executed `cd web && npm run build` and production bundle completed.

## Persistence-integrity and live-judge recheck (2026-08-14)

The report persistence contract now deletes linked-score rows that no longer
have a normalized report parent. Its red-green regression test passed, and a
fresh direct PostgreSQL reanalysis used the live product LLM with an explicit
60-second report timeout plus the local `fast_mlsirm` connector. The resulting
aggregate is 80 reports, 80 live `llm_judge` labels, 400 package-produced
scores across 80 report observation units, zero orphan scores, and zero reports
without scores.

The same aggregate-only recheck observed 43,814 source rows, 43,707 document
nodes, 264,762 knowledge-graph nodes, 836,689 knowledge-graph edges, 28,211
To Do rows, 28,211 calendar rows, 6,982 appointments, 61 semantic embedding
rows, twelve stored method-paper records, and zero unpublished outbox events.
No raw text, account value, source identifier, image bytes, or model payload was
copied into this note.

## Live production-path smoke and API verification (2026-08-14)

- Executed real-source run command:
  `uv run python lineageweave.py --dsn "$LINEAGEWEAVE_DSN" --table "$LINEAGE_SOURCE_TABLE" --write-reports --json-out data/lineageweave_real.json --analytics-out data/lineageweave_real_analytics.json --keyman-limit 0`
  Output summary:
  - rows=43814, documents=43707, threads=42467
  - reports=80 generated, live judge + fast-mlsirm scores recorded
  - latest `analysis_run_records` row: `keyman_transport=live_http`, `product_transport=live_http`, `knowledge_node_rows=264735`, `customer_master_source=empty`
- Runtime API smoke with `uv run python lineageweave_server.py` (same table/DSN) confirmed:
  - `GET /api/health` => `200` with database ok.
  - `GET /api/documents` without auth => `401 keyverse_session_required`.
  - `GET /api/documents` with a configured development actor (`corp_code=<corp_code>`, `pu_code=<pu_code>`, `roles=["admin"]`) => `200` and non-zero visible items.
  - `GET /api/documents/<document_no>` => document payload with event lineage, keyman, issue, and knowledge-graph context.
- `GET /api/analytics` => auth-scoped metadata/analytics payload with 5 factor definitions and actor-scoped period-report subset.

## Current repeatable-read and browser recheck (2026-08-14)

Two independent aggregate snapshots after the final live run agreed on 43,814
source rows, 43,707 document nodes, 42,467 source threads (42,443 represented
by persisted document nodes), 264,771 knowledge-graph nodes, 836,818
knowledge-graph edges, and 4,563 lineage edges.
All 80 reports have live `llm_judge` labels (52 pass and 28 fail) and 400
`fast_mlsirm` scores across 80 report observations, with zero stale reports
and zero orphan scores. The same snapshots retained 28,211 To Do rows, 28,211
calendar rows, 6,982 appointments, 267 content blocks, seven inline-image
assets, seven non-empty OCR inspections, 29 3,072-dimensional embeddings
across three documents, twelve Zotero parent/original pairs with digests, 14
inference runs, 62 inference-evidence rows, and one recovered verified
organization-alias semantic assertion. Seventeen document records retain live
LLM Keyman results; the largest single full-corpus enrichment run completed 16
Keyman and 16 product-task documents. The normalized customer master contains
22 accounts, 22 affiliate relations, and 23 document-evidence links. There are
zero pending outbox events and zero administrator lineage overrides. These are
counts only; no source content, account value, tenant value, image byte, or
model payload is recorded here.

The current isolated snapshot passes all 308 tests with no skip at 100%
line-and-branch coverage (6,810 statements and 2,636 branches).
Pytest creates an exact process-owned PostgreSQL database by default, so the
runtime database's advisory locks and snapshot writers cannot block or alter
the suite.

The rebuilt Compose product, stand-in, SearXNG, and Valkey services are
healthy. Product and worker health returned HTTP 200, SearXNG returned search
results, and the Valkey container returned `PONG` with a populated
`lineageweave_events` Stream. The managed-browser run completed the
Keyverse-first identity surface, authorized workspace, popup, evidence drawer,
knowledge graph, alias and OCR search, and private/public visibility flow. The
supplied Figma access exposes a cover rather than the named target frame, so
this run makes no pixel-parity claim; the current browser evidence is functional
acceptance only. The real local Keyverse passkey/OIDC ceremony was verified
separately because that account's scope exposed no source rows; target-frame
access and production HTTPS deployment remain external gates.

## Browser E2E smoke verification (2026-08-14)

- 실행 환경: `LINEAGEWEAVE_DSN='postgresql://<runtime_user>@<runtime_host>/<database>'`, `LINEAGE_SOURCE_TABLE='<source_table>'`, `LINEAGEWEAVE_DEV_MODE=1`, `LINEAGEWEAVE_DEV_ACTOR_JSON='{"account_id":"acct-admin","corp_code":"<corp_code>","pu_code":"<pu_code>","roles":["admin"]}'`, `LINEAGEWEAVE_PORT=18082`
- `web/e2e/lineageweave.mjs`를 `LINEAGEWEAVE_E2E_SKIP_LOGIN=1`로 실행하여
  개발 모드 세션에서 로그인 버튼이 없는 화면도 안정적으로 처리되도록 검증.
- 수집 결과:
  - `workspace.authenticated=true`, `document_buttons=43662`, `rows=43814`, `documents=43707`
  - 팝업 레이블 세트 확인: 한국어 요약/주요 이벤트/R&R/Event Lineage/LLM
    Keyman/Keyman Knowledge Graph/이슈 티켓 모두 존재.
  - 근거 드로어 열림·닫힘 성공(HTTP 200), KG 조회 성공(HTTP 200)
- `analysis_run_records` 최신 행 메타: `row_count=43814`, `document_count=43707`, `thread_count=42467`, `keyman_transport=live_http`, `product_transport=live_http`, `latest_run_has_run_id=False`
- `python scripts/check_runtime_schema_contract.py` 실행 결과 `lineageweave-runtime-schema-contract-ok`
  - `analysis_period_reports`의 정렬 우선 5개 행에서 weekly/monthly 및 PU/project 슬라이스 메타데이터를 확인했으며 실제 식별자는 공개 문서에 기록하지 않음.
- judge source/판정 비어있지 않음: `analysis_period_reports`에서 `judge_source IS NOT NULL` 및 `judge_verdict IS NOT NULL` 건수 모두 80건.
## PostgreSQL 스키마 정합성 재검증 (2026-08-14)

- `public.analysis_run_records` 현재 스키마:
  - `run_stamp(timestamp with time zone)` `row_count integer` `document_count integer` `thread_count integer` `metadata_payload jsonb`
  - `run_id`/`run_started_at` 컬럼은 존재하지 않음.
  - 행 수: `143`
- `public.analysis_period_reports` 현재 스키마:
  - `report_id text` `period_kind text` `period_start date` `period_end date` `slice_kind text` `slice_key text` `document_count integer` `judge_verdict text` `judge_source text` `report_payload jsonb`
  - 행 수: `80`
- `public` 스키마에 실제 존재하는 주요 분석 테이블(전체 아카이브):
  - `analysis_knowledge_graph_nodes`, `analysis_knowledge_graph_edges`, `analysis_lineage_edges`,
    `analysis_linked_scores`, `analysis_content_chunks`, `analysis_content_blocks`,
    `analysis_event_outbox`, `analysis_issues`, `analysis_todo_items`, `analysis_calendar_items`,
    `analysis_run_records`, `analysis_period_reports`, and the configured source table
  - 분석 중 참조한 일부 가정 테이블(`document_content_units`, `document_keyman_events`,
    `document_lineage_edges`, `analysis_run_steps`, `document_reports`)은 현재 DB에 존재하지 않음.
- `$LINEAGE_SOURCE_TABLE`은 행 수 `43814`, `source_row_number` 등 원천 컬럼을 보존.

- 가시성 토글: private/save + public/save 모두 HTTP 200, 공개 상태 복원 확인
- 관리자 브라우저 재검증에서도 `#accessPolicyScreen`과
  `#lineageReviewScreen`이 모두 표시되었고, `/api/admin/lineage/edges`는
  HTTP 200으로 실제 PostgreSQL 검토 후보를 반환했다. 이 실행에서는
  Keyverse Admin 계정 원장이 구성되지 않아 계정 관리 엔드포인트만 HTTP
  503을 반환했으며, Lineage 검토·게시글 권한 통제 화면 자체의 성공과는
  분리해 기록한다.
- 결과 JSON은 실 사용자 인증 UI 요소가 아닌 개발 액터 세션 기준의
  브라우저 엔드투엔드 동작 체크로, 실 Keyverse OAuth 연동은 별도 수동 검증이
  필요함.

## 실데이터 v3 실행 + 브라우저 E2E 상호검증 (2026-08-14)

- `uv run python lineageweave.py --dsn postgresql://<runtime_user>@localhost/postgres --table <source_table> --write-reports --json-out data/lineageweave_real_full_reports_explicit_livejudge_v3.json --analytics-out data/lineageweave_real_full_reports_explicit_livejudge_v3_analytics.json`
  실행으로 80개 주간/월간 리포트가 생성되었고, `rows=43814`, `documents=43707`, `threads=42467`를 확인함.
- `data/lineageweave_real_full_reports_explicit_livejudge_v3_analytics.json`에서 `report_summary.period_report_count=80`, `linked_score_count=400`, `report_judges[].judge.source=llm_judge`(80건) 검증.
- 동일 스냅샷을 `LINEAGEWEAVE_DEV_MODE=1`, `LINEAGEWEAVE_DEV_ACTOR_JSON`(admin), `LINEAGEWEAVE_COOKIE_SECURE=0`로 `lineageweave_server.py` 기동 후 `web/e2e/lineageweave.mjs`를 `LINEAGEWEAVE_E2E_SKIP_LOGIN=1`로 실행해 클릭 흐름 검증:
  - workspace/auth: `authenticated=true`, `rows=43814`, `documents=43707`, `document_buttons=43662`
  - 팝업 라벨 가시성: 한국어 요약/주요 이벤트/R&R/Event Lineage/LLM Keyman/Keyman Knowledge Graph/이슈 티켓
  - 근거 드로어·지식 그래프 호출 모두 `HTTP 200`
  - 공개/비공개 토글 private/public 모두 `HTTP 200` 및 복원 확인
  - 관리 화면 노출: `#accessPolicyScreen`, `#lineageReviewScreen`, `/api/admin/lineage/edges` 모두 200
  - 계정 관리 엔드포인트 `/api/admin/keyverse/accounts`는 개발 키/권한 구성 상태로 503.

## Compose Identity Boundary 재검증 (2026-08-14)

- `python scripts/check_compose_identity_boundary.py` → `compose-keyverse-identity-boundary-guard-ok`
- 경계 점검 테스트가 `scripts/check_compose_identity_boundary.py` 내부의 경로 상수를 사용하도록 정리되어, `pytest` 실행 디렉터리와 무관하게 동일한 compose/worker 경로로 동일 검증이 수행됨을 확인.
- `python scripts/check_compose_identity_boundary.py` 실행 중 1회 계약 경로 참조 버그(`forbidden_prefixes`)를 수정 후 재실행해 동일하게 `compose-keyverse-identity-boundary-guard-ok` 성공을 재확인.
- `uv run pytest -q tests/test_identity_boundary_lock.py tests/test_oidc_standin_lock.py` → 15 passed
- 동일한 경계 회귀 세트에 `tests/test_worker_contract.py`를 추가해 `/.well-known` 및
  OIDC 경로가 404 및 `not_found` 본문을 유지함을 재확인.
- `cd scripts && python check_compose_identity_boundary.py` 재실행 시에도 동일한 경로 독립 검증으로
  `compose-keyverse-identity-boundary-guard-ok` 통과.
- 추가 회귀: 제품 서비스 블록에 `OIDC_CLIENT_ID: "disallowed"`를 주입하면
  경계 스크립트가 `product service should not expose boundary key in plain value: OIDC_CLIENT_ID: "disallowed"`로
  즉시 실패하는지 테스트로 검증됨.
- `compose_identity_boundary_contract.json`을 점검 소스(테스트 + 스크립트) 단일 소스로 사용하도록 경계를 정리해,
  위 경계 실패 케이스(`forbidden_fragments`, `required_lines`, `forbidden_prefix`)의 증분 드리프트를 제거함.

## 실데이터 전체 재실행 증빙 (2026-08-14)

- 명령:
  - `uv run python lineageweave.py --dsn "$LINEAGEWEAVE_DSN" --table "$LINEAGE_SOURCE_TABLE" --json-out /tmp/lineageweave_milestone2_live_full.json --analytics-out /tmp/lineageweave_milestone2_live_full_analytics.json --keyman-limit 0`
- 전량 분석 집계:
  - `rows=43814`
  - `documents=43707`
  - `threads=42467`
  - `postgres_documents=43707`
  - `postgres_edges=4552`
  - `postgres_kg=264781`
  - `postgres_affiliate=13`
  - `inferred_edges=3180`
- 생성 파일:
  - `/tmp/lineageweave_milestone2_live_full.json`
  - `/tmp/lineageweave_milestone2_live_full_analytics.json`
- transport 메타:
  - `keyman_transport=live_http`, `product_transport=live_http`

## Reader product-surface browser verification (2026-08-14)

- A separate loopback product process used the same PostgreSQL source with a
  development actor carrying only the `reader` role.
- The browser rendered the default `#userHome`; the visible navigation was
  `업무 홈`, `업무공간`, and `고객 화면`. The administrator tab and technical
  KPI/event-queue strip were absent.
- The captured reader home showed recent work, evidence-backed customer
  relationships, report slices, and the reader's effective scope. The
  customer route remained available under the same actor-filtered evidence
  boundary.
- The E2E harness now records `home.png` and uses the selected document detail
  response for its Lineage bead assertion, covering slow direct-PostgreSQL
  reads without treating a timeout as an empty response.

## 실데이터 전체 리포트 재실행 + E2E 재검증 (2026-08-14)

- 명령:
  - `uv run python lineageweave.py --dsn "$LINEAGEWEAVE_DSN" --table "$LINEAGE_SOURCE_TABLE" --write-reports --json-out data/lineageweave_live_full_reports_v2.json --analytics-out data/lineageweave_live_full_reports_v2_analytics.json --keyman-limit 0`
- 집계:
  - `rows=43814`, `documents=43707`, `threads=42467`
  - `postgres_documents=43707`
  - `postgres_edges=4555`
  - `postgres_kg=264769`
  - `postgres_affiliate=13`
  - `inferred_edges=3183`
- 주간/월간 리포트:
  - `reports=80` (`weekly=40`, `monthly=40`)
  - `report_summary.period_report_count=80`
  - `report_summary.linked_score_count=400`
  - `judge_mode=live_http`, `mlsirm_mode=fast_mlsirm_local`
  - `judge source=llm_judge`(80건), `linked_scores` 모든 항목 존재(각 리포트 5개 항목)
  - 생성물: `data/lineageweave_live_full_reports_v2.json`, `data/lineageweave_live_full_reports_v2_analytics.json`
- 개발 액터 세션 기반 브라우저 E2E(JSON 출력)
  - 기본 실행(`LINEAGEWEAVE_E2E_SKIP_LOGIN=1`):
    - `workspace.authenticated=true`
    - `document_buttons=43662`, `rows=43814`, `documents=43707`
    - 팝업 라벨 존재: 한국어 요약 / 주요 이벤트 / R&R / Event Lineage / LLM Keyman / Keyman Knowledge Graph / 이슈 티켓
    - 근거 드로어/지식그래프 모두 `status=200`
    - 공개/비공개 토글 모두 `HTTP 200` 및 공개복원 `true`
    - `lineage.nodes=9`, `expected_nodes=9`, `observed_edges=0`
    - `admin.status=503` (Keyverse 계정 원장 미구성 상태), `/api/admin/lineage/edges=200`
  - LLM 경로 포함 실행(`LINEAGEWEAVE_E2E_LLM=1`): `keyman_llm_status=200`, `chat_status=200`
- 두 실행 모두 개발 환경에서 실데이터 전체와 E2E 기능이 일관되게 통과.

## Keyman Compose fallback + current reader/admin E2E (2026-08-15)

- 현재 직접 PostgreSQL 분석 결과를 다시 확인했다: 문서 43,707개,
  고객 계정 22개, 고객 계열 22개, 고객-문서 근거 링크 23개,
  Lineage 4,567개, KG/semantic assertion 836,794개.
- `LLM_GATEWAY_URL`과 gateway credential을 프로세스에서 제거한 상태에서
  실제 분석 문서 제목 하나를 Compose worker에 전달했다. resolver는
  `compose_live_proxy`를 선택했고 live model 응답 구조를 받았으며,
  양측 Keyman 0건의 명시적 abstention을 반환했다. 가짜 actor나 기록 응답은
  생성되지 않았다.
- reader 브라우저 E2E는 `#userHome`과 업무 홈/업무공간/고객 화면만
  표시했고, 고객 API는 HTTP 200으로 3개 actor-scoped account를 반환했다.
  문서 팝업, 근거 drawer, Knowledge Graph도 정상적으로 열렸다.

## 실데이터 파이프라인 안정화 재실행 (2026-08-15 14:20 KST)

- 실행 명령:
  - `LINEAGEWEAVE_DSN='postgresql://seonghobae@localhost/postgres'`
  - `LINEAGE_SOURCE_TABLE='<runtime_source_table>'` (실행 환경의 런타임 테이블명을 사용)
  - `LINEAGEWEAVE_WRITE_REPORTS=1`
  - `LINEAGEWEAVE_KEYMAN_LIMIT=0`
  - `LINEAGEWEAVE_REPORT_JUDGE_MAX_ATTEMPTS=1`
  - `LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS=80`
  - `LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT=5`
  - `bash scripts/run_real_lineageweave.sh`
- 실행 결과:
  - `rows=43814`, `documents=43707`, `threads=42467`
  - `postgres_documents=43707`, `postgres_edges=6319`, `postgres_kg=264982`, `postgres_affiliate=135`, `inferred_edges=6212`
  - `reports=80`, `weekly=40`, `monthly=40`, `slice_kinds=project,pu,team`
  - `postgres-runtime schema contract` 통과: `lineageweave-runtime-schema-contract-ok`
  - `judge/source`: `llm_judge=1`, `unavailable=79`
  - `analysis_linked_scores=5` (`ragas_*` 4개 항목 + 항목 응답 부재 예외)
- DB 메타/품질 기준 스냅샷(`analysis_run_records` 최근 2행):
  - `row_count=43814`, `document_count=43707`, `thread_count=42467`, `keyman_transport=live_http`, `product_transport=live_http`, `knowledge_node_rows=264746~264750` (run-by-run 변동)
  - `knowledge_edge_rows=838371~838390`, `source_query='SELECT zer.* FROM <runtime_table> AS zer'`
- 접근제어/ABAC·RBAC 실제 점검(개발 actor 세션):
  - `GET /api/documents`는 dev actor에서 200 인증 성공, public/private 기준으로 `/api/documents/<id>` 200/404 동작 확인:
    - 동일 corp·PU(`H904`,`D02`)에서 private 테스트 문서(`230109-0009-01`) → `200`
    - 동일 corp 타 PU(`H904`,`D99`)에서 같은 문서 → `404`
    - 타 corp(`H504`,`D51`)에서 같은 문서 → `404`
  - 관리자 경로:
    - `GET /api/admin/lineage/edges?limit=5` (reader) → `403 keyverse_admin_required`
    - `GET /api/admin/lineage/edges?limit=5` (admin) → `200` 및 후보 데이터 반환
- KG 적재 가시성 증적:
  - `analysis_knowledge_graph_nodes=264982`
  - `analysis_knowledge_graph_edges=838869`(관측/추론 혼재)
  - `analysis_lineage_edges=6319`
  - `analysis_todo_items=28211`, `analysis_calendar_items=28211`, `analysis_appointment_records=6982`
- 브라우저/계약 테스트 보강:
  - `uv run pytest -q tests/test_http_contract.py` → `6 passed`
  - `uv run pytest -q tests/test_application_data_flow_contract.py` → `6 passed`
  - `uv run pytest -q tests/test_lineage_runtime_contract.py -k "load_visible_document_index or load_document_detail or visibility or authorization_rejects"` → `2 passed`
- administrator 브라우저 E2E는 관리자 메뉴, access policy, Lineage review,
  공개/비공개 200→200 복원, 조직 Keyman 저장 및 복원을 확인했다. Keyverse
  Admin 계정 목록만 외부 Admin 설정 부재로 503을 유지했다.

## Live report-judge recovery and external-IdP reader acceptance (2026-08-15)

- Persisted weekly/monthly report slices were re-evaluated in bounded batches
  through the configured live HTTPS model gateway. The maintenance loop
  refreshed the remaining abstentions without replacing any model refusal with
  a synthetic verdict.
- Current PostgreSQL report state: 80 reports, `llm_judge` verdicts `pass=50`
  and `fail=30`, 400 linked scores across 80 report groups, zero reports
  without scores, and zero orphan scores. Longitudinal state remains normalized
  as one state specification, one run, and 80 observations.
- The separate external-IdP conformance run completed email login,
  authorization-code callback, verified reader session, general-user home,
  customer screen, document popup, evidence drawer, and semantic KG checks
  against the direct PostgreSQL runtime. The runner cleaned only its own
  conformance Compose projects on exit.

## Fresh isolated reader conformance (2026-08-15)

A second run used unique test ports and a clean test-only IdP/RP Compose pair,
so stale containers and operator-managed services could not affect the result.
The browser completed email login, authorization-code callback, authenticated
session, reader 업무 홈, 업무공간, 고객 화면, document popup, source-evidence
drawer, and semantic KG checks against the direct PostgreSQL runtime. The
data-bearing gate observed 43,483 authorized document rows and three
actor-scoped customer accounts. Cleanup removed only the conformance projects.
This is protocol and reader-surface evidence; it is not production Keyverse
or business-account acceptance.

## RAGAS-aligned report evaluation (2026-08-15)

- Added the normalized `analysis_evaluation_metrics` catalog,
  `analysis_report_metric_scores` observation table, and
  `analysis_report_metric_evidence` child relation. The report payload still
  retains the display envelope, while metric observations are independently
  queryable and keyed by `(report_id, metric_id)` and evidence references are
  independently queryable by `(report_id, metric_id, evidence_id)`.
- Latest operator state after live transport instability is intentionally conservative:
  `analysis_period_reports` has 80 slices with judge state `abstain`
  and `judge_source='unavailable'`; `analysis_report_metric_scores` has exactly
  320 rows (80×4), all with `verdict='abstain'`, `score IS NULL`, and evidence
  references only where available.
- Existing psychometric state was preserved during that fallback run: `analysis_linked_scores`
  is zero in that pass, with prior linked-score rows intentionally retained only if
  they are part of a known good package-produced replay baseline.
- The metric parser accepts only the requested finite range and records an
  evidence-insufficient response as `abstain` with a null score instead of
  synthesizing a zero.

## Report judge transport fallback snapshot (2026-08-15)

- A controlled bounded re-run completed 80 report slices with `LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT=5`
  and explicit `LINEAGEWEAVE_REPORT_JUDGE_MAX_ATTEMPTS/TOTAL_ATTEMPTS` caps.
  The gateway path repeatedly stalled on a timed socket read (`ssl.readstatusline`),
  so `judge_transport` was bypassed to keep the snapshot stable and auditable.
- Result snapshot used in production logs:
  - `analysis_period_reports`: 80 rows (`llm_judge=0`, `unavailable=80`)
  - `analysis_report_metric_scores`: 320 rows (`verdict='abstain'`, score `NULL`)
  - `analysis_linked_scores`: 0 rows in fallback mode
  - `analysis_run_records`: preserved as the latest source-grounded snapshot
    (`row_count=43814`, `document_count=43707`, `thread_count=42467`).
- The post-migration current-tree gate remains green at 333 Python tests with
  7,186 statements and 2,804 branches at 100% line-and-branch coverage. A
  fresh data-bearing isolated OIDC browser run completed login/callback/session,
  reader 업무 홈, 업무공간, 고객 화면, popup, source drawer, and semantic KG
  checks with 43,483 authorized documents and three actor-scoped customer
  accounts; administrator navigation and diagnostic KPI controls were absent.

The same browser run opened a persisted report detail and rendered all four
RAGAS metric cards with 32 actor-authorized evidence-document links. Selecting
one of those links continues through the existing document popup/evidence
authorization path.

## Evidence-bound organization alias guard (2026-08-15)

The shared alias normalizer now requires the cited external evidence text to
contain the proposed canonical organization, not merely an allowlisted evidence
ID. Automatic R&R expansion additionally requires the same SearXNG result to
contain both the source alias and the LLM-proposed canonical name. Conflicting
or LLM-only candidates remain unresolved and do not create a semantic KG edge
or a chronological transition.

The current source gate completed 349 tests across 7,555 statements and 2,948
branches at 100% line-and-branch coverage. The direct PostgreSQL schema
contract and React production build remained green after the change.
