# ADR 0213 — Global Ask embeds before acquiring a pooled connection

**Decision status:** Accepted
**Date:** 2026-08-25
**Related:** [0204](0204-analysis-run-short-transaction-delivery.md)

## Context

The authenticated k6 HTTP exercise found ordinary post and Event Lineage
reads waiting while Global Ask jobs called the external embedding provider.
`compute_global_ask_answer` acquired an asyncpg connection before
`gather_global_chat_sources` called that provider, so provider latency could
occupy every slot in the shared ten-connection pool. Moving the call to a
thread kept the event loop responsive but did not release the pool resource.

## Decision

Resolve and validate the question embedding before acquiring an asyncpg
connection. Acquire the pool only for the bounded persisted-vector query and
release it before answer generation. An unavailable, empty, unbound, or
zero-norm embedding disables the embedding channel. Persisted semantic and
Knowledge Graph evidence retrieval remains available; LineageWeave does not
substitute lexical retrieval, a local model, or an invented vector.

The same boundary applies to future provider work: a provider call must not
run inside a pooled-connection context unless one atomic database operation
requires it and an ADR records that exception.

## Consequences

- Embedding latency cannot exhaust the shared HTTP database pool.
- Authorization predicates and persisted model/dimension matching remain in
  the database query and are unchanged.
- A regression test observes the pool state at the embedding boundary.
- Capacity remains environment-specific; k6 observations do not create an
  uncited concurrency or latency threshold.

## References

PostgreSQL Global Development Group. (2026). *PostgreSQL 18.6 documentation:
19.4 resource consumption*. https://www.postgresql.org/docs/18/runtime-config-resource.html
