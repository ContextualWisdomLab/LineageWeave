# ADR 0162 — Persist TEPP AnalysisRunAccepted as transport evidence

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-23
**Depends on:** ADR 0022 authorized TEPP start; ADR 0023 analysis-run outbox
**Amends:** ADR 0022 (accepted envelopes are no longer Failed /
`tepp_result_not_persisted` when they carry a remote run id)
**Refs:** Issue #277; blocked completed-result poll remains
[TEPP#156](https://github.com/ContextualWisdomLab/TEPP/issues/156)

## Context

TEPP's published start response is `AnalysisRunAccepted`: a durable
submission receipt with a remote `run_id`. It is not a temporal
measurement. ADR 0022 treated any non-completed envelope as Failed /
`tepp_result_not_persisted` so LineageWeave would not stamp Succeeded
from transport evidence. That is honest about measurement authority
and dishonest about operator progress: a normal live TEPP accept
looks like a product failure.

Issue #277 requires a split lifecycle. This slice covers the
unblocked half: persist the accepted receipt, keep the local run
`Running`, and never invent a theta. Polling TEPP's versioned
completed-result contract stays blocked on TEPP#156.

## Decision

Classify a `TeppClient.submit_analysis_run` envelope as follows:

1. `TeppNotAvailable` → Failed / `tepp_not_available`. Seed keeps
   this default. Do not change seed to Running.
2. `status` or `run_state` in `{completed, succeeded}` plus a result
   object plus a remote run id → Succeeded, persist
   `analysis_run_tepp_result` (migration 0027).
3. `status` or `run_state` in `{accepted, queued, running}` plus a
   remote run id (`analysis_run_id`, `run_id`, or `remote_run_id`) →
   persist `analysis_run_tepp_accepted_receipt`, leave the local run
   Running, do not append a terminal status, and do not mark the
   outbox delivered.
4. `accepted` / `queued` / `running` without a remote run id → Failed /
   `tepp_result_not_persisted` (empty envelopes stay unpersistable).
5. Anything else → Failed / `tepp_result_not_persisted`.

The receipt table stores transport evidence only: remote run id,
request digest, receipt digest, accepted status code, model contract
version, snapshot id, knowledge cutoff, and received time. It does
not store a result JSON, a theta, or a calibrated score. A changed
receipt digest for the same local run fails closed. Duplicate
identical receipts are idempotent.

`GET /api/analysis-runs/{id}` may attach `tepp_accepted_receipt`
`{remote_run_id, accepted_status_code, received_at}` so the operator
can see that TEPP accepted the work. Missing migration 0106 is an
empty attachment, not a 500. Global Ask must not promote this
receipt into an answer claim.

Completed-result polling, bounded backoff, and request-binding
revalidation remain TEPP#156. This ADR does not invent a local
psychometric substitute while waiting.

```mermaid
sequenceDiagram
    participant Operator
    participant API
    participant TeppClient
    participant Registry
    Operator->>API: POST /api/analysis-runs/{id}/start
    API->>Registry: Running + outbox
    API->>TeppClient: AnalysisRunRequest v1
    alt TeppNotAvailable
        Registry->>Registry: Failed tepp_not_available
        Registry->>Registry: outbox delivered
    else accepted with remote run id
        Registry->>Registry: persist accepted receipt
        Note over Registry: stay Running, outbox stays claimed
        API-->>Operator: 200 Running + receipt
    else completed with result
        Registry->>Registry: persist tepp result + Succeeded
        Registry->>Registry: outbox delivered
    else accepted without remote run id
        Registry->>Registry: Failed tepp_result_not_persisted
        Registry->>Registry: outbox delivered
    end
```

## Consequences

A connected TEPP transport that returns `accepted` plus a remote run
id no longer looks like a product failure. The operator refreshes a
Running run. Refresh may replay the same idempotent submit; it still
must not stamp Succeeded from the receipt. Seed and an empty
`accepted` envelope stay Failed. Do not invent a theta.

## References — APA 7th

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns:
Designing, building, and deploying messaging solutions*. Addison-Wesley.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/
