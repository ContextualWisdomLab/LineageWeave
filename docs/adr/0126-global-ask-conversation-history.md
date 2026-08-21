# ADR 0126: Persisted Global Ask Conversation History

* Status: Accepted
* Date: 2026-08-21
* Supersedes: the non-persistence consequence in ADR 0090

## Context

Global Ask currently keeps its rendered turns only in the browser. Leaving the
Ask destination loses the question history, which makes the product behave
differently from the conversation surface it presents. ADR 0090 deliberately
left persisted multi-turn state for a later phase; the reader surface now
explicitly requires that state.

## Decision

Persist Global Ask conversations and completed turns under the authenticated
`user_account`. Store the question, answer, next action, retrieved source-post
ids, cited post ids, and reader-safe evidence facts in normalized tables. A
conversation id is explicit API state; it is never represented as a fake
post-scoped orchestrator session id.

The existing evidence retrieval and contextual-orchestrator boundary remain
unchanged. A turn is written only after the orchestrator returns a complete
answer object (including the authorized-no-source result). The history read
path owns only the requesting account's conversations and re-applies the
current post visibility rule before returning source titles, citations, or
evidence.

Before the persistence transaction commits, cited `source_post` rows are
locked with `FOR SHARE` and the same analysis-visibility predicate is applied
again. If a citation became unauthorized or disappeared, the transaction
raises a stable retryable failure and rolls back the new session, turn,
citations, and evidence together. This closes the race between evidence
retrieval and transcript persistence without exposing the discarded answer.

This is transcript persistence, not a new long-context prompt contract. The
orchestrator continues to receive the current question and its bounded,
authorized evidence set. Conversation summarization or cross-turn reasoning
requires a separate ADR and upstream orchestrator contract.

## Consequences

* Ask history survives navigation and a new authenticated browser session.
* A user cannot read another account's conversation by changing a UUID.
* Revoked post visibility removes that post's source/citation projection from
  history; the stored answer remains account-owned transcript data.
* A visibility change during a turn cannot leave a partially persisted or
  unusable conversation; the reader retries after the source boundary settles.
* The UI can select an existing conversation or start a new one without
  changing the existing `/api/ask` evidence contract.

## References (APA 7th)

PostgreSQL Global Development Group. (n.d.). *Explicit locking: PostgreSQL 18
documentation*. Retrieved August 22, 2026, from
https://www.postgresql.org/docs/current/explicit-locking.html
