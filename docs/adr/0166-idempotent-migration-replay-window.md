# ADR 0166 — Replay every idempotent migration after the bootstrap boundary

**Decision status:** Accepted
**Date:** 2026-08-24

## Context

The PostgreSQL Official Image runs `/docker-entrypoint-initdb.d` only for an
empty data directory. A Compose service that reuses an existing volume therefore
needs a separate replay path for schema changes shipped after initialization.
LineageWeave originally replayed an explicit filename allowlist. That list
stopped at migration 0102, so migration 0103 could ship while the application
depended on `tenant_settings` and existing volumes never created the table.

Migrations 0001–0011 are the non-idempotent image bootstrap. Migrations from
0012 onward are the replay family. The replay script declares `/bin/sh`, so its
filename gate must use POSIX shell syntax. POSIX.1-2024 requires C decimal,
octal, and hexadecimal constants in arithmetic expansion; the `base#value`
notation is an optional extension and cannot be required by this script.

## Decision

- Keep the existing 0012 boundary. Accept migration filenames with exactly four
  decimal digits followed by `_`, skip 0000–0011, and replay every later file in
  the shell glob's sorted order. Do not maintain another per-file allowlist.
- Keep the gate POSIX `/bin/sh` compatible. A fixed lower-bound filename pattern
  avoids both leading-zero arithmetic and non-standard `base#value` syntax.
- Every migration numbered 0012 or later must be safe to replay. Prefer native
  PostgreSQL idempotency such as `IF NOT EXISTS` and `ON CONFLICT`; a migration
  that cannot be made idempotent requires a migration ledger ADR before it is
  added.
- A later replayed migration that supersedes and drops an earlier index also
  supersedes that earlier migration's create operation. The earlier file keeps
  its sorted schema boundary but must not recreate a corpus-wide index that the
  next file immediately drops. The current body-search example keeps the
  `pg_trgm` extension in 0035 while 0036 solely owns the normalized search
  indexes. This avoids a complete GIN build/drop cycle on every startup without
  skipping the successor's correctness boundary.
- Execute each accepted file with `psql -X -v ON_ERROR_STOP=1`. A failed
  migration stops startup instead of leaving a healthy-looking partial schema.
- Tests must cover the stable 0012 boundary and the idempotency of any changed
  replayed migration. Application code must not compensate for a missing table.

## Consequences

Existing volumes receive migrations such as 0103, 0163, and 0164 without a
whitelist edit. Invalidly named files and the non-idempotent bootstrap family do
not replay. This remains a bounded no-ledger design; introduce a durable
migration ledger before any post-0011 migration needs exactly-once semantics.

## References

Docker Library. (n.d.). *Postgres Docker Official Image README*. GitHub.
https://github.com/docker-library/docs/blob/master/postgres/README.md

IEEE & The Open Group. (2024). *Shell command language* (POSIX.1-2024).
https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html

PostgreSQL Global Development Group. (2026). *CREATE TABLE* (PostgreSQL 18
documentation). https://www.postgresql.org/docs/current/sql-createtable.html

PostgreSQL Global Development Group. (2026). *INSERT* (PostgreSQL 18
documentation). https://www.postgresql.org/docs/current/sql-insert.html
