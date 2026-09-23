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
   `queued` and `running` Global Ask rows. The index is created concurrently so
   migration does not require a write-blocking index build on accumulated job
   history. The corresponding rollback drops it concurrently.
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
  run outside a transaction; a failed concurrent build must be detected rather
  than treated as valid capacity evidence.
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
- Renaming the existing Valkey quota key in place was rejected because old and
  new replicas can coexist during rollout and would then enforce different
  counters for the same principal.
- Fixed repository defaults were rejected because they would be unsupported
  rules of thumb rather than observed capacity.
