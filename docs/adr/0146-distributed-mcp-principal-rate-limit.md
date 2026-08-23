# ADR 0146: Distributed MCP principal rate limit

## Status

Accepted

## Context

Authenticated MCP Global Ask can invoke database and orchestrator work.  A
per-process counter neither composes across replicas nor survives restarts, and
the bearer subject is not the provisioned account authority used elsewhere.
The existing runtime already provisions Valkey for shared operational state.

## Decision

Global Ask consumes a fixed-window quota only after a verified bearer subject
resolves to a provisioned `user_account`, and before answer generation.  The
shared Valkey key contains a SHA-256 digest of `user_account_id`, never the raw
account or bearer subject.  One atomic Valkey script increments the counter,
sets the first-entry expiry, and returns the remaining window.

An exceeded quota returns the stable `mcp_rate_limit_exceeded` MCP error with a
non-reserved application error code, a bounded `retry_after_seconds` value, and
the same bounded delay in the HTTP `Retry-After` header.  Authentication,
provisioning, transport, successful responses, and request-shape failures do
not consume quota or advertise a retry delay.  If Valkey is unavailable or
returns an invalid result, Global Ask fails
closed with `mcp_rate_limiter_unavailable`; it never substitutes process-local
state.  Limits remain bounded runtime configuration so an invalid deployment
cannot create an unbounded window or counter.

## Consequences

All service replicas enforce one account quota and no customer identifier is
placed in a Valkey key.  Valkey availability becomes a deliberate prerequisite
for Global Ask, while other authenticated product paths remain unchanged.
