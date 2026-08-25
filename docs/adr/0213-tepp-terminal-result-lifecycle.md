# ADR 0213 — Persist TEPP acceptance and consume terminal results

**Decision status:** Accepted on this active PR; not protected-main truth until merge  
**Date:** 2026-08-26  
**Depends on:** ADR 0022, ADR 0023, ADR 0204; TEPP PR #157  
**Refs:** LineageWeave issue #277; TEPP issues #156 and #249

## Context

TEPP's `AnalysisRunAccepted` is transport evidence, not measurement. TEPP PR
#157 merged strict `AnalysisRunStatus` and `AnalysisRunTerminalResult` v1 Rust
contracts, but deliberately did not deploy a production HTTP status service.
LineageWeave must retain accepted asynchronous work and consume a future
provider result without guessing a URL, retry interval, score, or theta.

## Decision

The existing PostgreSQL outbox remains lifecycle authority. A strict accepted
v1 response persists to `analysis_run_tepp_receipt`, leaves the local run
Running, and leaves the outbox claimed. A later delivery retry sees that
receipt and invokes `TeppClient`'s pluggable status-read port rather than
resubmitting the request.

The status consumer enforces the provider's 64 KiB limit and exact v1 shape,
then revalidates remote run, idempotency key, tenant/workspace, snapshot,
knowledge cutoff, model contract, output profile, terminal state, RFC 3339
completion time, result artifact/schema, lowercase SHA-256 digest, bounded
identity-free summary, and failure code. Accepted/running contains no terminal
result. Succeeded persists the validated terminal DTO before the local
Succeeded event. Failed persists no result and appends the validated provider
failure code. Any changed terminal payload for the same local run fails closed.

Provider work remains outside the asyncpg pool and transaction under ADR 0204.
The configured HTTP client does not synthesize the target
`GET /v1/analysis-runs/{run_id}` route. TEPP issue #249 owns its executable
service and evidence-based retry policy.

The `Analysis/TeppAcceptedReceipt` Storybook scene asserts that acceptance does
not read as measurement or success. Its synthetic desktop (1280×720) and mobile
(390×844) renderings were screenshot-reviewed on this exact head; neither
screenshot is committed, preserving the repository artifact boundary.

```mermaid
sequenceDiagram
    participant Worker
    participant Registry
    participant TEPP
    Worker->>TEPP: submit immutable request v1
    TEPP-->>Worker: accepted receipt v1
    Worker->>Registry: persist receipt; remain Running
    Worker->>Registry: later claim reads remote run id
    Worker->>TEPP: status read through provider port
    alt accepted or running
        Note over Registry: remain Running
    else succeeded and bound
        Worker->>Registry: terminal DTO + Succeeded
    else failed and bound
        Worker->>Registry: typed Failed, no result
    else invalid or mismatched
        Worker->>Registry: fail closed
    end
```

## Consequences

LineageWeave owns transport and provenance persistence only. TEPP retains all
statistical, psychometric, CPU, and GPU arithmetic. Automatic polling remains
unavailable until the owning service publishes its route and retry policy.

## References — APA 7th

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns: Designing,
building, and deploying messaging solutions*. Addison-Wesley.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/
