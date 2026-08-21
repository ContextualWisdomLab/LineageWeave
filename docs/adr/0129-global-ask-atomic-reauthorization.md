# ADR 0129 — Ask turn persistence and final citation reauthorization share one transaction

- Status: Accepted on this feature branch; protected-main adoption requires the normal stacked PR gates
- Date: 2026-08-21
- Depends on: ADR 0113 and ADR 0126

## Context

Global Ask and post-scoped chat persist a new answer and its citation rows
before performing the final tenant, publication, and knowledge-cutoff
reauthorization. If a cited post changes between retrieval and that final
check, the API correctly returns a generic 503, but a committed rejected turn
can poison the session or leave an invalid cached answer.

## Decision

1. The `/api/ask` cited-answer path acquires one PostgreSQL connection and
   opens one outer transaction.
2. The `/api/posts/{post_id}/chat` cited-answer path uses the same transaction
   boundary for the result and normalized citation rows.
3. Global Ask allocates its turn ordinal while the session row is locked; both
   paths run final citation reauthorization on the same connection, with the
   same tenant scope and knowledge cutoff, before the transaction exits.
4. A failed final authorization raises the existing generic 503 inside the
   transaction. PostgreSQL then rolls back only the new answer and citations;
   previously committed turns and cached exchanges remain unchanged.
5. The no-authorized-source path keeps its existing empty-turn behavior and
   does not invent evidence.

## Consequences

- A visibility/publication race cannot leave a rejected citation in Global Ask
  session history or post-scoped chat storage.
- A follow-up request can reuse the same Global Ask session after a rejected
  answer, and a post-scoped question can be retried without a poisoned cache.
- The answer, citation persistence, and final authorization share one
  database connection and lock lifetime; the transaction must not include the
  provider call or Valkey publication.
- Real PostgreSQL integration coverage is required for both rollback and
  session-continuity behavior.

## References — APA 7th

PostgreSQL Global Development Group. (2026). *Transactions*. PostgreSQL
documentation. https://www.postgresql.org/docs/current/tutorial-transactions.html

OWASP Foundation. (2025). *Error handling*. OWASP Application Security
Verification Standard. https://owasp.org/www-project-application-security-verification-standard/
