# ADR 0377: Report terminal in-process background consumers without restarting them

## Status

Proposed. This private proposal is not an adopted runtime or release decision.

## Context

The ASGI lifespan owns the analysis-run, post-content, and Global Ask consumer
Tasks. An exception or an unexpected normal return can leave an HTTP process
running while one consumer is no longer processing wake-ups. Existing shutdown
settles these Tasks with `gather(return_exceptions=True)`, so eventual shutdown
need not expose an earlier terminal failure to the operator. ADR 0122 requires
bounded diagnostics that do not serialize exception values or source content.

## Proposed decision

Register one completion callback on each of the three existing lifespan Tasks.
A non-cancelled terminal Task emits one ERROR record identifying only the fixed
logical worker name and exception class (at most 128 characters), or the fixed
`unexpected_return` category when it returns without an exception. Do not include
exception values, traceback payloads, credentials, actor identifiers, or source
records. A cancelled Task emits no terminal-failure record, including routine
lifespan shutdown cancellation.

The callback does not start a new Task, retry work, restart a consumer, terminate
the process, mutate database state, or change `/healthz`. That endpoint remains a
process-liveness probe, not consumer readiness. Existing ownership, cancellation,
gather ordering, and pool/Valkey/telemetry cleanup remain unchanged. This is
terminal reporting, not automatic supervision or readiness enforcement.

## Consequences and acceptance boundary

A failed or unexpectedly returned consumer becomes observable before shutdown;
other consumers and requests remain owned by the same lifespan. Operator
intervention may still be needed. Restart/backoff/fail-fast/readiness policies
remain undecided and require their own decision rather than being implied by
this diagnostic callback.

Regression controls exercise the actual normally imported lifespan, all three
Task registrations, exception and normal-return cases, silent graceful
cancellation, sibling continuity, exact error-object preservation and complete
fixture Task/resource cleanup. Synthetic worker/resource seams do not establish
real database, broker, provider, retained-volume or deployed acceptance. Exact
whole-source independent review, owner adoption and normal protected CI/merge
remain separate gates.

## Governing references

- [ADR 0122](0122-otel-session-observability.md): bounded diagnostics and no exception-value disclosure.
- [ADR 0098](0098-valkey-backed-post-content-ingestion.md): the durable ledger remains authoritative.
- [ADR 0023](0023-analysis-run-outbox.md): PostgreSQL outbox and Valkey wake-up boundary; preserve its literal adoption-status wording.
