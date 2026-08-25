# ADR 0178 — Read TEPP terminal results through the provider contract

**Decision status:** Accepted on this stacked PR; not protected-main truth until merge  
**Date:** 2026-08-26  
**Depends on:** ADR 0022, ADR 0023, ADR 0162; TEPP PR #157  
**Refs:** LineageWeave issue #277; TEPP issues #156 and #249

## Context

ADR 0162 correctly separates TEPP's accepted receipt from measurement, but it
predates TEPP's versioned `AnalysisRunStatus` and
`AnalysisRunTerminalResult` v1 contracts. TEPP PR #157 merged those Rust wire
contracts on 2026-08-25. It deliberately did not publish a production HTTP
status service, so LineageWeave must not guess a URL or poll interval.

## Decision

`TeppClient` exposes a pluggable status-read transport alongside its existing
submission transport. A stored accepted receipt causes the delivery retry to
read that remote run once instead of resubmitting the request. The read is
bounded by the supplied transport call and is crash-resumable because the
receipt and PostgreSQL outbox remain durable.

The consumer requires the exact v1 status shape and revalidates remote run,
idempotency key, tenant/workspace, snapshot, cutoff, model contract, output
profile, terminal state, result schema, lowercase SHA-256 digest, bounded
identity-free summary, completion time, and failure code. Accepted/running
contains no terminal result and keeps the local run Running. A succeeded
terminal result is persisted before Succeeded. A terminal provider failure
appends its validated snake-case failure code without a result. Any mismatch
fails closed. Replaying the same remote run with a changed canonical result
digest is rejected.

The configured HTTP client does not synthesize `GET /v1/analysis-runs/{id}`
while TEPP documents it only as a target endpoint. A production status
transport is enabled only when the owning TEPP service publishes that route.
No theta, score, estimator, poll cadence, or backoff coefficient is implemented
in LineageWeave.

```mermaid
sequenceDiagram
    participant Worker
    participant Registry
    participant TEPP
    Worker->>Registry: read accepted receipt + immutable request
    Worker->>TEPP: read status(remote run id)
    alt accepted or running
        Note over Registry: remain Running; outbox remains claimed
    else succeeded and all bindings match
        Worker->>Registry: persist terminal DTO + Succeeded atomically
    else failed and all bindings match
        Worker->>Registry: append typed Failed
    else unavailable
        Note over Registry: retain receipt; retry remains possible
    else invalid or mismatched
        Worker->>Registry: fail closed
    end
```

## Consequences

The contract consumer is testable now through an in-process or future HTTP
adapter without pretending TEPP has deployed a route. Automatic scheduled
polling remains unavailable until the provider owns an executable status
endpoint and an evidence-based retry policy.

## References — APA 7th

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns: Designing,
building, and deploying messaging solutions*. Addison-Wesley.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/
