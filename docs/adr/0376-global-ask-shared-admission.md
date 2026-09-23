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

That fail-closed external-race rule does not by itself make cooperating rollout
processes idempotent. Two LineageWeave migration runners can both observe the
name as absent, pass preflight, and then race the same unconditional concurrent
CREATE. One can succeed while the other fails with a duplicate relation even
though both are executing the same repository migration against the same valid
state. `CREATE INDEX CONCURRENTLY` cannot run inside a transaction, so a
transaction-scoped advisory lock cannot span the capture, preflight, concurrent
DDL, and ownership comment. The production runner is one `psql` session,
however, so a session-level advisory lock can serialize only cooperating 0251
runners across that full sequence. PostgreSQL releases session advisory locks
when the session ends, including abnormal disconnect; successful migration also
releases the lock explicitly. Non-cooperating external DDL remains outside that
coordination and must continue to fail closed through the duplicate-relation
path rather than being adopted.

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

Destructive rollback also cannot leave ownership validation and deletion as two
independent autocommit statements. After a valid repository-owned index passes
preflight, another privileged session could drop it and install a same-named
foreign index before `DROP INDEX CONCURRENTLY` executes. The rollback would then
delete an object that never passed its destructive-action guard. A second name
or catalog re-check immediately before DROP only moves the race window; the
validation and destructive action need one lock-protected transaction boundary.
That protective `ACCESS EXCLUSIVE` acquisition must not wait indefinitely on a
busy production table. Recovery is operator-driven and exceptional, so a busy
table is a fail-closed condition when a destructive target actually exists:
acquire the table lock with `NOWAIT`, leave the owned index untouched when the
lock is unavailable, drain conflicting traffic or transactions, and retry
explicitly. Conversely, if the canonical index is already absent, rollback is
complete and must remain an idempotent no-op without acquiring an exclusive lock
that could fail merely because ordinary production reads are active.

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
   runner is `psql -X -v ON_ERROR_STOP=1 -f`. Migration 0251 first acquires the
   session-level advisory lock derived from
   `lineageweave:migration:0251_global_ask_active_admission_index`, holds it
   across create-decision capture, replay validation, concurrent CREATE, and the
   ownership comment, then explicitly releases it on success. This serializes
   cooperating LineageWeave rollout runners even though concurrent index DDL
   must remain outside a transaction; an error still releases the session lock
   when `psql` exits. Under that lock, migration 0251 captures whether the
   canonical name was absent before validation. If creation was required it
   executes an unconditional concurrent CREATE through psql conditional
   execution. A non-cooperating relation that races into the namespace after
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
   paired rollback first resolves the canonical target inside its transaction.
   If the target is absent, rollback returns without acquiring an exclusive
   table lock. If a candidate ordinary index belongs to
   `public.global_ask_job`, rollback acquires `ACCESS EXCLUSIVE ... NOWAIT`,
   re-resolves the canonical name under that lock, and performs final
   destructive-action validation and DROP before the transaction ends. The
   final validation accepts only the canonical `public.global_ask_job` btree,
   non-unique, single-key, no-INCLUDE shape and exact queued/running predicate.
   A valid/ready index must additionally carry the exact repository marker before
   rollback may delete it. An unmarked index is rollback-eligible only while it
   is invalid or not ready and otherwise has that exact canonical physical
   shape, covering a failed concurrent build that stopped before `COMMENT ON
   INDEX` ran. A valid unmarked index, an unexpected marker, another table,
   another access method/key/predicate, or a non-index relation fails closed and
   requires an explicit operator ownership decision. Because `DROP INDEX
   CONCURRENTLY` cannot execute inside that protective transaction, the
   exceptional rollback uses ordinary schema-qualified `DROP INDEX` while
   holding the parent-table lock. If the parent table is busy and a destructive
   target exists, `NOWAIT` aborts before deletion; operators must drain the
   conflicting workload and retry rather than leaving a destructive recovery
   session queued behind production traffic. Recovery of an accepted
   failed-build artifact is paired rollback, migration 0251 replay, and
   verification of the marker plus `indisvalid=true` / `indisready=true`.
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
- Cooperating 0251 migration runners serialize through one session-level
  advisory lock spanning capture through ownership publication. A rolling
  deployment therefore does not turn two correct repository migration attempts
  into a duplicate-DDL startup failure. Non-cooperating external DDL is not
  trusted by that lock and still fails closed before ownership can be stamped.
- The create decision is bound before replay validation. A same-named relation
  created concurrently after an absent preflight causes the plain CREATE to
  fail before LineageWeave can attach its ownership marker; foreign ownership is
  never adopted merely because the raced name exists.
- Rollback is fail-closed as a destructive operation. It can remove a marked
  repository-owned canonical index or an incomplete unmarked canonical-shaped
  failed-build artifact, but it refuses a valid unmarked/mismarked index or an
  incompatible relation even when the canonical name matches.
- Rollback validation and deletion share one transaction and parent-table lock,
  so a privileged concurrent session cannot replace the validated index before
  the destructive statement. The lock acquisition is `NOWAIT`: busy production
  traffic causes an immediate rollback failure with the canonical index retained
  instead of an unbounded recovery wait. Operators must drain conflicting work
  and retry the exceptional rollback explicitly.
- Replaying rollback after the canonical index is already absent is a lock-free
  idempotent no-op. Ordinary readers therefore cannot turn a completed rollback
  into a false operational failure merely because the parent table is busy.
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
- Leaving cooperating rollout processes uncoordinated was rejected because two
  correct 0251 invocations can both capture an absent name and race the same
  CREATE, turning idempotent rollout into an avoidable duplicate-DDL failure.
  A transaction-level advisory lock is insufficient because `CREATE INDEX
  CONCURRENTLY` cannot run in that transaction. The session-level lock matches
  the repository's one-session `psql` runner and spans the complete
  capture/preflight/create/comment sequence without weakening the external-DDL
  fail-closed rule.
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
- Keeping ownership preflight and `DROP INDEX CONCURRENTLY` as separate
  autocommit statements was rejected because a privileged session can replace
  the validated relation in that gap. Re-checking immediately before DROP does
  not remove the race. Exceptional rollback therefore uses one lock-protected
  transaction and an ordinary DROP instead of concurrent deletion.
- Waiting indefinitely for the rollback `ACCESS EXCLUSIVE` lock was rejected.
  PostgreSQL `LOCK` waits by default, which can leave an operator-started
  destructive recovery session blocked behind ordinary application traffic.
  `NOWAIT` keeps the failure explicit and leaves the index untouched until the
  operator has created a quiescent recovery window.
- Acquiring `ACCESS EXCLUSIVE` before checking whether the canonical index
  exists was rejected. It makes an already-complete, idempotent rollback fail on
  ordinary read traffic even though there is no destructive target. Rollback
  therefore checks for target absence first, acquires the lock only when a
  candidate index exists on the canonical table, and re-resolves/revalidates the
  name after the lock is held before deleting anything.
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
- PostgreSQL Global Development Group. (2026). *LOCK*. PostgreSQL 18
  documentation. https://www.postgresql.org/docs/current/sql-lock.html
- PostgreSQL Global Development Group. (2026). *System Administration Functions:
  Advisory Lock Functions*. PostgreSQL 18 documentation.
  https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS
- PostgreSQL Global Development Group. (2026). *CREATE TABLE: Temporary tables*.
  PostgreSQL 18 documentation.
  https://www.postgresql.org/docs/current/sql-createtable.html
