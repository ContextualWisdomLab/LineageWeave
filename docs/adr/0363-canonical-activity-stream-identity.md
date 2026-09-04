# ADR 0363: Canonical activity-stream identity

- Status: Proposed
- Date: 2026-09-04

## Context

`source_post.post_id` is a PostgreSQL `uuid`, while historical HTTP requests
could spell the same UUID with upper-case digits, braces, omitted hyphens, or
other PostgreSQL-accepted hyphen placement. Earlier activity writes embedded
the request spelling in a Valkey stream key. Canonicalizing only new writes can
therefore strand authorized history, and enumerating selected spellings cannot
cover PostgreSQL's input grammar.

The activity feed is a retained operational projection. It is not a source of
record truth, and its compatibility work must not broaden a request into a
keyspace scan.

## Decision

New activity writes use PostgreSQL's canonical lower-case, hyphenated UUID
form. Before the application begins serving reads, startup scans the existing
activity-key namespace once and records every actually present, UUID-equivalent
legacy key in a durable canonical-post alias set. A request reads the canonical
stream and only the aliases in that set. Non-UUID synthetic and legacy keys
retain exact spelling.

Cross-stream ordering uses the persisted millisecond component and declared
canonical-first precedence for equal milliseconds. Stream-local sequence
numbers never become a global chronology. Alias event identifiers remain
namespaced so two streams cannot emit the same public identity.

WATCH retries, retained-window read limits, and alias-index startup are fixed
product contracts. Failure to build the alias index makes the application
unready; the product does not silently hide historical activity.

## Consequences

- Canonical reads retain every historical UUID spelling that actually exists.
- Request-time work is limited to the canonical stream and its durable aliases.
- Startup performs a cursor scan and must finish before readiness.
- The alias index is additional derived Valkey state and can be rebuilt from
  retained activity keys.

## Alternatives considered

- Enumerate common UUID spellings: rejected because PostgreSQL accepts more
  forms than a finite hand-picked list would honestly cover.
- Scan the activity keyspace on each request: rejected because latency and work
  would scale with unrelated posts.
- Drop legacy aliases: rejected because canonicalization would hide retained
  authorized history.
