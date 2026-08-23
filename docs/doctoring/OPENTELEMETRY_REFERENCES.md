# OpenTelemetry references and implementation traceability

## Normative references

- OpenTelemetry Authors. (n.d.). *Manual instrumentation with OpenTelemetry
  Python*. Retrieved August 21, 2026, from
  https://opentelemetry.io/docs/languages/python/instrumentation/
- OpenTelemetry Authors. (n.d.). *Service semantic conventions*. Retrieved
  August 21, 2026, from
  https://opentelemetry.io/docs/specs/semconv/registry/attributes/service/
- ContextualWisdomLab governance-risk-compliance. (2026). *ADR 0009:
  Emit bounded OpenTelemetry request telemetry*. Retrieved August 21, 2026,
  from https://github.com/ContextualWisdomLab/governance-risk-compliance/blob/develop/docs/adr/0009-opentelemetry-request-telemetry.md

## Implementation mapping

| Concern | Implementation | Evidence boundary |
| --- | --- | --- |
| Service resource | `OTEL_SERVICE_NAME`, default `lineageweave` | One logical service name per deployment |
| Post correlation | Existing ADR 0071 session metadata plus `X-LineageWeave-Session-Id` | Correlation only; not identity or authorization |
| LLM/VISION/embedding transport | `lineageweave.http_client.post_json` | Method, peer, bounded path, status; no body or credential |
| Valkey queue | `backend/app/*worker.py` and stream producers | Operation and logical stream kind; no stream key or event content |
| Server failure metric | `lineageweave.server.failures` | Fixed operation/outcome labels; no session or exception labels |
| Server failure log/trace | `record_server_failure` | Error class, bounded stack, TraceId, and SpanId; no exception value or source content |
| Export | OTEL_EXPORTER_OTLP_ENDPOINT | Disabled by default; base URL normalized to /v1/traces, /v1/metrics, and /v1/logs |

## Correlation fields other agents must read

Join one failed Ask or post-chat operation across API, orchestrator, and
Valkey by these bounded fields. Do not treat `session_id` as a tenant, actor,
or evidence identifier.

| Field | Where | Shape |
| --- | --- | --- |
| `trace_id` | structured log extra and span context | 32-character lowercase hex W3C TraceId |
| `span_id` | structured log extra and span context | 16-character lowercase hex W3C SpanId |
| `traceparent` | outbound HTTP to contextual-orchestrator/TEPP | W3C Trace Context header `00-{trace_id}-{span_id}-{flags}` |
| `operation_code` | log extra, span attribute `lineageweave.operation_code`, metric label | one of `global_ask`, `post_chat`, `http_post_json`, `http_get_json`, `post_content_ingestion`, `unknown` |
| `failure_outcome` | log extra, span attribute `lineageweave.failure_outcome`, metric label | `provider_unavailable` or `internal_error` |
| `error_type` | log extra and span attribute `lineageweave.error_type` | exception class name only |
| `session_id` | log extra, span attribute `lineageweave.session_id`, `X-LineageWeave-Session-Id` | bounded ADR 0071 post session; correlation only |

Child Valkey spans created with `traced()` in the same process inherit the
parent TraceId. Same-process inheritance is the Valkey correlation contract;
stream payloads do not carry post bodies or raw stream keys.

The GRC repository remains the organization control and evidence owner. This
repository emits operational signals and does not copy GRC tables or persist
provider credentials.
