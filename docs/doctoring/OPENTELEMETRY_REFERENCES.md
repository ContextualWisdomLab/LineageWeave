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
| Server failure log/trace | `record_server_failure` | Error class and bounded stack only; no exception value or source content |
| Export | OTEL_EXPORTER_OTLP_ENDPOINT | Disabled by default; base URL normalized to /v1/traces and /v1/metrics |

The GRC repository remains the organization control and evidence owner. This
repository emits operational signals and does not copy GRC tables or persist
provider credentials.
