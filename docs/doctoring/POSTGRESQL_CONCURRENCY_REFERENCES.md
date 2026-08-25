# PostgreSQL concurrency references

Supporting research register for ADR 0204. ADR 0204 is normative.

PostgreSQL Global Development Group. (2026a). *PostgreSQL 18.6 documentation:
13.3 explicit locking*. https://www.postgresql.org/docs/18/explicit-locking.html

PostgreSQL Global Development Group. (2026b). *PostgreSQL 18.6 documentation:
9.28 system administration functions*.
https://www.postgresql.org/docs/18/functions-admin.html

Adopted facts: session-level advisory locks survive transaction commit, are
released explicitly or when their session ends, are observable through
`pg_locks`, and `pg_try_advisory_lock` returns immediately when ownership is
unavailable. These properties replace an application-defined lease timeout.
