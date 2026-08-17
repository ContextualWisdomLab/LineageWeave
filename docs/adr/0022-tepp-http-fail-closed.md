# ADR 0022 — TEPP HTTP port stays fail-closed

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

`TeppClient` already builds TEPP's published `AnalysisRunRequest`
(`schemas/analysis_run_request_v1.json`). Protected TEPP main is still
crate-only; the target HTTP resource is `POST /v1/analysis-runs`
(TEPP `docs/API_CONTRACT.md`). LineageWeave must not invent a theta
when that service is unset or unreachable, and must not treat IRT
period-report θ as a TEPP measurement.

## Decision

1. When `TEPP_BASE_URL` is set, POST the published request through
   `http_client.post_json` to `{TEPP_BASE_URL}/v1/analysis-runs`.
2. When it is empty, keep the crate-only default transport.
3. Every caller uses `submit_fail_closed`, which returns a
   `FailClosedEnvelope` (`accepted` / `tepp_not_available` /
   `tepp_transport_failed`) with a customer-actionable `next_action`.
   The envelope has no theta field; a provider `theta` key is stripped.
4. `POST /api/tepp/analysis-runs` is `post_admin`. Unavailable is a
   200 envelope, not a fabricated score.

## Consequences

- The buyer can request a TEPP run after `make seed` and read why
  none exists yet.
- IRT `calibrate_period_report` thetas stay on the period-report
  panel and are never copied into the TEPP envelope.

## Related

Outbox persistence is [ADR 0023](0023-tepp-valkey-outbox.md).
TEPP contract: ContextualWisdomLab/TEPP `docs/API_CONTRACT.md`.
