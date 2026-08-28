# ADR 0122: Correlate product, orchestrator, and Valkey telemetry by post session

## Status

Accepted.

## Context

Post structure, VISION, OCR, embeddings, summaries, and queue work can run in
different processes. Existing ADR 0071 already defines a deterministic,
post-scoped session metadata value, but transport and queue failures were not
visible as one trace. The proposed organization control contract currently
lives in [GRC PR #51 at exact head
`1a8f90dd15f37ffc86b8a0efd217a8b2812e5f99`](https://github.com/ContextualWisdomLab/governance-risk-compliance/blob/1a8f90dd15f37ffc86b8a0efd217a8b2812e5f99/docs/adr/0009-opentelemetry-request-telemetry.md),
not on protected `develop`. Until that proposal lands, this accepted
LineageWeave ADR remains the operative product boundary and the GRC proposal
must not be cited as protected organization evidence.

## Decision

1. LineageWeave uses the OpenTelemetry Python API and SDK and exports OTLP only
   when OTEL_EXPORTER_OTLP_ENDPOINT is explicitly configured. The exporter
   treats that value as a base URL and sends traces, metrics, and correlated
   logs to the normalized /v1/traces, /v1/metrics, and /v1/logs signal
   endpoints. The service resource name is lineageweave unless the operator
   overrides it with the standard OTEL_SERVICE_NAME variable. A blank or unset
   endpoint leaves the SDK unconfigured so a later operator value can still
   enable export.
2. Every contextual-orchestrator POST carries the existing
   `lineageweave_post_session_id` as both the top-level payload `session_id`
   and `X-LineageWeave-Session-Id`. The orchestrator binds it to the request
   context and adds it to provider spans, so chat, Responses, structured
   output, VISION, and embedding work for one post can be investigated
   together. The post identifier remains authorized provenance metadata and
   is not copied into the public response.
3. LineageWeave emits bounded HTTP and Valkey operation spans. HTTP client
   failures follow the OpenTelemetry HTTP semantic conventions: error
   responses and invalid response bodies end the client span with an error.
   Valkey spans identify the operation and logical stream kind, not the stream
   key, post body, summary, actor, source identifiers, token, or provider
   response. Idle blocking reads do not emit empty spans; a non-empty batch
   emits one bounded consumption span.
4. Failure telemetry uses two fixed outcomes: `provider_unavailable` for
   explicitly classified provider, transport, or schema failures, and
   `internal_error` for unexpected programming failures. The counter labels
   contain only operation code and outcome, so high-cardinality session IDs and
   exception classes remain in bounded structured logs and traces instead of
   metric labels.
5. Failure logs contain operation, error type, the bounded session
   correlation, and the active W3C TraceId and SpanId so another agent can
   join the structured log to the Error span. Unexpected failures may include
   a bounded stack trace, but never the exception value, prompt, response,
   source body, credential, actor, or tenant identifier. They do not become a
   second evidence database. GRC may consume aggregate control evidence and
   OTLP-derived SLO signals through its existing contracts; LineageWeave does
   not copy GRC tables or credentials.
6. No ad hoc session table is introduced. The existing normalized post-scoped
   session metadata remains the source of correlation.

## Consequences

Operators can follow a slow or failed post-content job from the LineageWeave
HTTP client through contextual-orchestrator and Valkey without exposing source
content. Global Ask and post chat return a reader-safe generic 503 while GRC
can distinguish provider unavailability from an internal defect. An OTLP
collector is a deployment concern, not a local default, so a developer stack
remains usable without a telemetry backend. Raw session IDs remain
correlation data and must not be used as tenant, actor, or evidence labels in
GRC dashboards.

## References

OpenTelemetry Authors. (n.d.). *Manual instrumentation with OpenTelemetry
Python*. Retrieved August 21, 2026, from
https://opentelemetry.io/docs/languages/python/instrumentation/

OpenTelemetry Authors. (n.d.). *Service semantic conventions*. Retrieved
August 21, 2026, from https://opentelemetry.io/docs/specs/semconv/registry/attributes/service/

OpenTelemetry Authors. (n.d.). *Semantic conventions for HTTP spans*.
Retrieved August 22, 2026, from
https://opentelemetry.io/docs/specs/semconv/http/http-spans/
