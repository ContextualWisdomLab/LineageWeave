# ADR 0364: Authenticated browser request boundary

- Status: Proposed
- Date: 2026-09-04

## Context

The browser sends an access token to the configured LineageWeave API. A remote
cleartext URL would expose that credential in transit. Local Compose development
still needs loopback HTTP.

Global Ask is an asynchronous job. Its existing fifteen-minute product ceiling
was checked only between requests, so a stalled submission or poll could keep
the visible waiting state alive indefinitely.

## Decision

Authenticated browser requests admit HTTPS destinations. HTTP is admitted only
for `localhost`, `127.0.0.1`, and `[::1]`; embedded URL credentials and every
other scheme or cleartext host fail before the authorization header is built.

Global Ask establishes its existing whole-operation deadline before submission.
The submission and every poll receive an abort signal for the remaining time.
A deadline abort becomes the existing actionable Ask timeout outcome, while
other connectivity failures keep the shared unavailable outcome.

## Consequences

- A deployment cannot send an access token to a remote cleartext API by
  configuration mistake.
- Loopback Compose development keeps its current HTTP URL.
- A stalled request cannot outlive the same ceiling that governs polling.
- This decision changes no server job deadline and does not claim that a timed
  out job was cancelled server-side.

## Alternatives considered

- Enforce the rule only in deployment documentation: rejected because the
  browser would still attach the token when configuration drifts.
- Start the Ask deadline after submission: rejected because submission latency
  is part of the user's wait.
- Add a second shorter per-request timeout: rejected because no separate
  evidence supports another threshold.
