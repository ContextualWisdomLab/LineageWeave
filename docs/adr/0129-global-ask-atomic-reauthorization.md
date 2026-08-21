# ADR 0129 — Global Ask turn persistence and final citation reauthorization share one transaction

- Status: Accepted on this feature branch; protected-main adoption requires the normal stacked PR gates
- Date: 2026-08-21
- Depends on: ADR 0113 and ADR 0126

## Context

Global Ask persists a new answer and its citation rows before performing the
final tenant, publication, and knowledge-cutoff reauthorization. If a cited
post changes between retrieval and that final check, the API correctly returns
a generic 503, but a committed rejected turn can poison the session and cause
the next request to receive 409.

## Decision

1. The `/api/ask` cited-answer path acquires one PostgreSQL connection and
   opens one outer transaction.
2. The new turn and normalized citation rows are inserted inside that outer
   transaction, with the session row locked before the ordinal is allocated.
3. Final citation reauthorization runs on the same connection, with the same
   tenant scope and knowledge cutoff, before the outer transaction exits.
4. A failed final authorization raises the existing generic 503 inside the
   transaction. PostgreSQL then rolls back only the new turn and citations;
   previously committed turns remain unchanged.
5. The no-authorized-source path keeps its existing empty-turn behavior and
   does not invent evidence.

## Consequences

- A visibility/publication race cannot leave a rejected citation in session
  history.
- A follow-up request can reuse the same session after a rejected answer when
  no previous citation remains.
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
