# ADR 0376: Global Ask admission is shared and capacity-bound

## Status

Proposed (2026-09-23).

## Context

`POST /api/ask` and authenticated MCP submit the same durable Global Ask work,
but only MCP consumed the shared Valkey quota. REST could therefore enqueue
unbounded provider-backed work. A separate process-local limiter would diverge
across replicas, and a count followed by an insert would overshoot under
parallel requests.

The repository has no authoritative universal request size, rate, window, or
active-job capacity. Those values depend on an authenticated k6 workload and a
named deployment's PostgreSQL, worker, Valkey, and gateway saturation evidence.

Active-job admission is a synchronous buyer path. The authoritative count is
scoped by principal and queued/running status, while `global_ask_job` retains
terminal history. Relying on the pre-existing single-column account and status
indexes lets historical rows remain part of the candidate access path and makes
admission cost grow with a principal's completed-job history.

PostgreSQL retains a same-named `INVALID` index after some failed
`CREATE INDEX CONCURRENTLY` attempts. Replaying `CREATE INDEX CONCURRENTLY IF
NOT EXISTS` against that relation can otherwise return success while leaving the
capacity access path unusable. A valid same-named index on a different relation
is equally unsafe: relation-name reuse must not satisfy the canonical
`global_ask_job` access-path contract. Textual token checks alone are also
insufficient on the canonical table: a narrower predicate such as the intended
queued/running predicate combined with `AND false` still contains every expected
token while being unusable for the admission query. A catalog comment/version
marker is identity evidence, not proof of predicate semantics; a copied marker
on a malformed index must therefore fail as well.

A preflight followed by `CREATE INDEX CONCURRENTLY IF NOT EXISTS` also has a
TOCTOU ownership failure. If the name is absent during preflight but another
session creates a same-named relation before the CREATE, PostgreSQL can skip the
CREATE and continue to `COMMENT ON INDEX`. The migration would then stamp the
LineageWeave ownership marker onto a foreign relation it never created. The
create/no-create decision must therefore be captured before validation and, when
creation was required, executed as a plain concurrent CREATE that fails on a
raced duplicate before any ownership marker is written.

Index names share PostgreSQL's schema relation namespace with tables, views,
sequences, and other relations. A same-named non-index relation can therefore
occupy `public.global_ask_job_active_account_idx` before migration 0251 runs.
That collision is not an invalid-index recovery case: `DROP INDEX` is not the
safe remediation for a table, view, sequence, or unsupported index relation
kind. Migration diagnostics must distinguish the relation kind before giving an
operator the paired index-rollback procedure.

Rollback has a second ownership boundary. A valid ordinary index can occupy the
canonical name and even have the same useful physical definition without being
a LineageWeave-owned object. An unconditional `DROP INDEX CONCURRENTLY IF
EXISTS` would delete that operator-owned relation merely because its name
matches the migration. Conversely, a failed `CREATE INDEX CONCURRENTLY` can
leave an unmarked but incomplete index before the catalog ownership marker is
written. Recovery must therefore distinguish a valid unowned index from an
incomplete canonical-shaped failed-build artifact: valid unmarked or mismarked
indexes require an explicit operator decision, while an invalid/not-ready
canonical-shaped unmarked index may be removed by the paired rollback as the
failed migration artifact it is intended to recover.

PostgreSQL temporary relations also shadow same-named permanent relations for
the creating session unless the permanent object is schema-qualified. Because
indexes on temporary tables are always built and dropped non-concurrently, an
unqualified migration or rollback can appear to succeed while operating only on
a session-local `pg_temp` relation. The durable admission access path must
therefore bind both forward and rollback DDL to `public` explicitly rather than
trusting `search_path`.

The active-admission migration also needs an unambiguous composition slot across
live LineageWeave lanes. Open translation-ledger work owns 0246 through 0248 and
customer-resolution work owns 0250, so this lane uses 0251 rather than colliding
with another writer's migration identity.

## Decision

1. The shared application service enforces a UTF-8 question-byte ceiling, the
   existing atomic Valkey per-principal shared request window, and a
   per-principal active durable-job ceiling before accepting work.
2. Operators supply all four positive capacity values. Missing values make
   submission unavailable; LineageWeave does not invent defaults.
3. MCP keeps its existing transport admission charge and marks that charge when
   calling the shared service, so one accepted MCP submission is never charged
   twice. REST consumes the same principal quota inside the service. The
   existing opaque `lineageweave:mcp-rate-limit:v1:<digest>` key identity is
   preserved so mixed-version replicas in a rolling deployment cannot split one
   principal's quota into independent old/new counters.
4. Active-job admission takes a transaction-scoped PostgreSQL advisory lock
   derived from the normalized account identity, counts only queued/running
   jobs, and inserts within that transaction. No database transaction remains
   open during Valkey, worker, or contextual-orchestrator work.
5. PostgreSQL maintains a partial index on `requesting_account_id` for only
   `queued` and `running` Global Ask rows. The index is created concurrently on
   `public.global_ask_job`, and the paired rollback addresses
   `public.global_ask_job_active_account_idx` explicitly, so neither path can be
   redirected by `pg_temp` or another `search_path` entry. Migration 0251 stamps
   the repository-owned index with the immutable catalog marker
   `lineageweave/global-ask-active-admission-index/v1`. The production migration
   runner is `psql -X -v ON_ERROR_STOP=1 -f`; migration 0251 uses that contract
   to capture whether the canonical name was absent before validation. If
   creation was required it executes an unconditional concurrent CREATE through
   psql conditional execution. A relation that races into the namespace after
   the captured decision therefore causes duplicate-relation failure before the
   ownership comment instead of turning `IF NOT EXISTS` into a false success.
   Before index-specific replay validation, migration 0251 resolves the existing
   schema relation and verifies that it is an ordinary index relation. A
   same-named table, view, sequence, partitioned/otherwise unsupported index
   relation, or other relation kind fails closed with explicit operator
   remediation and is never described as safe to remove through the paired
   index rollback. For an ordinary index, replay then requires the exact
   canonical table, valid/ready non-unique single-key shape,
   `requesting_account_id` key, the exact PostgreSQL-decompiled active predicate
   for queued/running rows, and that version marker. The predicate check is
   anchored to the whole decompiled expression rather than token presence, so a
   version-marked `AND false` or otherwise narrowed lookalike cannot pass. The
   paired rollback performs its own destructive-action preflight: it accepts
   only the canonical `public.global_ask_job` btree, non-unique, single-key,
   no-INCLUDE shape and exact queued/running predicate. A valid/ready index must
   additionally carry the exact repository marker before rollback may delete it.
   An unmarked index is rollback-eligible only while it is invalid or not ready
   and otherwise has that exact canonical physical shape, covering a failed
   concurrent build that stopped before `COMMENT ON INDEX` ran. A valid unmarked
   index, an unexpected marker, another table, another access method/key/predicate,
   or a non-index relation fails closed and requires an explicit operator
   ownership decision. Recovery of an accepted failed-build artifact is paired
   rollback, migration 0251 replay, and verification of the marker plus
   `indisvalid=true` / `indisready=true`.
6. Quota-window rejections expose the measured remaining window as bounded
   retry metadata. Active-job rejections instead tell the customer to finish or
   cancel existing work; they do not reuse the unrelated quota window as an
   estimate of job completion time. Neither response echoes question content or
   another principal's counts.

## Consequences

- REST can no longer bypass the distributed cost boundary.
- Rolling deployment of this change preserves the already-live distributed
  counter identity instead of temporarily multiplying effective allowance.
- Parallel submissions for one account cannot overshoot the configured active
  work ceiling.
- Active-capacity lookup is bounded to active rows rather than growing with
  terminal per-principal history; the smaller partial index also avoids indexing
  terminal rows that the admission query never consumes.
- Concurrent index creation follows the repository migration contract and must
  run outside a transaction. A failed concurrent build cannot be silently
  accepted on replay, and neither a same-named index on another relation nor a
  version-marked narrower same-table lookalike can masquerade as the canonical
  access path.
- The create decision is bound before replay validation. A same-named relation
  created concurrently after an absent preflight causes the plain CREATE to
  fail before LineageWeave can attach its ownership marker; foreign ownership is
  never adopted merely because the raced name exists.
- Rollback is fail-closed as a destructive operation. It can remove a marked
  repository-owned canonical index or an incomplete unmarked canonical-shaped
  failed-build artifact, but it refuses a valid unmarked/mismarked index or an
  incompatible relation even when the canonical name matches.
- A table, view, sequence, partitioned index, or other unsupported relation that
  occupies the canonical index name stops rollout without destructive automated
  cleanup. Operators must resolve that ownership collision explicitly before
  migration replay; the ordinary index rollback is not advertised as a remedy.
- Forward migration and rollback are immune to temporary-table/index name
  shadowing because the durable table and index are schema-qualified; a session
  cannot satisfy recovery by mutating only `pg_temp`.
- Live migration identities remain composable with the translation-ledger and
  customer-resolution lanes instead of depending on merge order to resolve a
  duplicate numeric slot.
- An unmeasured deployment remains explicitly unavailable until it records
  capacity evidence.
- The advisory lock can conservatively serialize colliding hash keys; it does
  not weaken authorization or reveal account identity.

## Alternatives considered

- A process-local semaphore was rejected because replicas would disagree.
- A naked `count(*)` check was rejected because concurrent transactions could
  all pass before inserting.
- Relying on separate account and status indexes was rejected because the
  planner can still scan/filter historical rows as a principal accumulates
  completed jobs.
- A full `(requesting_account_id, job_status_code)` index was rejected because
  it indexes terminal history even though synchronous admission only consumes
  queued/running rows, increasing index size and write amplification without
  serving this invariant better.
- Silently replaying `CREATE INDEX CONCURRENTLY IF NOT EXISTS` after a failed
  concurrent build was rejected because PostgreSQL can retain a same-named
  invalid relation and turn the replay into a false-success deployment.
- Re-checking name existence with `IF NOT EXISTS` after preflight was rejected
  because a relation can be created in that gap and then receive the repository
  ownership comment despite never being created or validated by LineageWeave.
- Treating every same-named relation as an invalid index and recommending
  `DROP INDEX` was rejected because PostgreSQL's relation namespace can contain
  a table, view, sequence, partitioned index, or other unsupported relation at
  that name. Recovery guidance must not turn a fail-closed collision into an
  unsafe or inapplicable destructive action.
- Making the paired rollback an unconditional `DROP INDEX CONCURRENTLY IF
  EXISTS` was rejected because a valid same-named ordinary index can be
  operator-owned. Destructive rollback requires canonical physical shape plus
  repository ownership, except for an incomplete canonical-shaped failed-build
  artifact that can exist before the ownership marker is written.
- Accepting a same-named index by textual definition tokens or catalog marker
  alone was rejected because another relation can carry a lookalike index and a
  narrower predicate on the canonical table can retain both the expected tokens
  and copied marker while still being unusable. Replay therefore validates the
  decompiled predicate as a complete expression in addition to identity and
  physical-key metadata.
- Leaving forward or rollback DDL unqualified was rejected because a temporary
  relation can shadow the durable name for the session; successful DDL against
  `pg_temp` is not durable migration or recovery evidence.
- Retaining migration number 0246 was rejected because another live owner lane
  already uses 0246 for the UI translation ledger; merge order must not decide
  which semantic migration owns a sequence identity.
- Renaming the existing Valkey quota key in place was rejected because old and
  new replicas can coexist during rollout and would then enforce different
  counters for the same principal.
- Fixed repository defaults were rejected because they would be unsupported
  rules of thumb rather than observed capacity.

## Traceability

- PostgreSQL Global Development Group. (2026). *CREATE INDEX*. PostgreSQL 18
  documentation. https://www.postgresql.org/docs/current/sql-createindex.html
- PostgreSQL Global Development Group. (2026). *DROP INDEX*. PostgreSQL 18
  documentation. https://www.postgresql.org/docs/current/sql-dropindex.html
- PostgreSQL Global Development Group. (2026). *CREATE TABLE: Temporary tables*.
  PostgreSQL 18 documentation.
  https://www.postgresql.org/docs/current/sql-createtable.html
