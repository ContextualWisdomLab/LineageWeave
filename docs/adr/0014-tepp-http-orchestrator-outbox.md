# ADR 0014 — TEPP HTTP port, fail-closed orchestrator envelope, Valkey outbox

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

Milestone 2 (#79) requires TEPP measurement through its versioned REST
boundary, a fail-closed orchestrator task envelope, and transactional
outbox delivery. LineageWeave already has `TeppClient` with a default
transport that raises `TeppNotAvailable`, orchestrator chat clients that
treated a missing number as confidence 0.0, and Valkey only as a
per-post activity stream.

A missing TEPP service is not a zero theta. A malformed orchestrator
body is not a confidently-negative adjudication. A Valkey outage must
not drop a connector submit.

## Decision

1. When `TEPP_BASE_URL` and `TEPP_API_TOKEN` are set, POST the published
   seven-field `AnalysisRunRequest` to `{base}/v1/analysis-runs`. HTTPS
   is required unless `LINEAGEWEAVE_DEV_MODE=1`. Parse only lifecycle
   metadata (`run_id`, `state`, `request_id`, `retryable`). An
   `error_code` envelope, a missing run id, or an unknown state fails
   closed. Never persist or display a TEPP theta invented here.
2. `parse_chat_completion` is the portable orchestrator envelope.
   `error_code`, missing choices, or blank content raise
   `OrchestratorEnvelopeError`. Adjudication no longer returns 0.0 on
   an unusable reply; the llm channel must be dropped instead.
3. `connector_outbox_event` stores pending TEPP/orchestrator deliveries
   (3NF, lookup-coded connector and status, unique
   `(connector_code, idempotency_key)`). Flush `XADD`s onto
   `outbox:{connector_code}` and marks published. A publish error
   leaves the row pending with `failure_code`.

## Consequences

Unset TEPP stays `TeppNotAvailable` after `make seed`. Configuring TEPP
is additive (`tepp_client_from_env` / `http_transport`). The activity
stream (`activity:{post_id}`) is unchanged. If TEPP later exposes more
of its measurement artifact, consume it through this same envelope —
do not fork TEPP arithmetic.

## References

ContextualWisdomLab/TEPP `docs/API_CONTRACT.md` (accepted target
contract, 2026-08-10). Issue #79 Milestone 2 parent; issue #87 schema
bridge remains the analysis-run registry follow-up and is not this
slice.
