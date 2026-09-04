# ADR 0363 — Verify synchronous PostgreSQL server identity by default

**Decision status:** Accepted
**Date:** 2026-09-05

## Context

LineageWeave's synchronous administrative and test adapter accepts PostgreSQL
URIs and translates their transport policy to pg8000. PostgreSQL documents
`sslmode=prefer` as a backwards-compatibility default that may reconnect in
plaintext and does not authenticate the server. That behavior is unsuitable as
an implicit product default for credentials in transit. Explicit DSN policy
must remain representable for controlled compatibility paths.

## Decision

A network DSN that omits `sslmode` uses `verify-full`: TLS is required, the
certificate chain is validated, and the requested hostname must match. It never
retries in plaintext. An explicit `sslmode=prefer` remains TLS-first with
plaintext fallback only after PostgreSQL's exact SSL-refusal response.
`disable`, `require`, `verify-ca`, and `verify-full` retain their documented
meanings. Unix-socket inference remains unavailable because the adapter cannot
recover libpq's socket selection from a hostless URI.

## Consequences

- Accidental network DSNs fail closed against untrusted or mismatched servers.
- Existing private-CA deployments must install their CA or state an explicit
  reviewed compatibility mode; a silent downgrade is no longer possible.
- Explicit `prefer` remains weaker and must be chosen in the DSN rather than
  inherited from an omission.

## Alternatives considered

### Keep implicit `prefer`

Rejected because an SSL-refusing endpoint can cause credential-bearing tooling
to reconnect without encryption.

### Default to `require`

Rejected because encryption without certificate and hostname verification does
not authenticate the server.

## References

- PostgreSQL 18, *SSL Support* and *Database Connection Control Functions*.
- pg8000 1.31.5, `ssl_context` connection contract.
