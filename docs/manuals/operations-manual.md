# LineageWeave operations manual

This manual is for deployment operators. It separates customer-visible
recovery actions from service ownership, authorization, and evidence handling.
Use synthetic data for repository tests and demonstrations; never copy runtime
records, credentials, prompts, answers, or identifiers into git artifacts.

## Service ownership

| Concern | Owner and operator action |
| --- | --- |
| Identity and access | Keyverse in production; bundled Keycloak only for standalone/local/dev/test. Configure one authority and verify its exact audience and claims. |
| LLM, vision, embeddings, structured output | contextual-orchestrator. Restore its provider-neutral endpoint; do not select or hardcode a provider model in LineageWeave. |
| Temporal and psychometric measurement | TEPP and fast-mlsirm. Accept only versioned, completed, provenance-bearing results. Keep the feature unavailable otherwise. |
| Event reconstruction and product evidence | LineageWeave. Preserve source provenance, ABAC, durable job state, and cited evidence. |
| Ranking and reference threading | RankWeave and ThreadWeave through their published contracts; do not duplicate their algorithms locally. |

## Start and verify the canonical stack

Compose declares the project name `lineageweave`. Credentials remain in
`~/.env`; do not print or copy that file into the checkout.

```bash
make up
make ps
make smoke
make seed   # synthetic local data only
curl --fail http://localhost:18420/healthz
```

The default stack includes the durable worker. `/healthz` proves only process
liveness, so also confirm that `backend-worker` is progress-healthy before
opening the frontend. In production, set the Keyverse issuer/audience values;
do not combine central Keyverse and the bundled realm as simultaneous
authorization authorities.

An isolated test may use `docker compose -p <isolated-name> ...`. After the
test, run `docker compose -p <isolated-name> down` without `-v` unless the
approved procedure explicitly retires its data. Remove exited test containers
after their evidence has been retained. Do not run a second long-lived copy of
the canonical stack under a different project name.

## Configure optional integrations

- Set `ORCHESTRATOR_BASE_URL` and `ORCHESTRATOR_API_KEY` for the internal
  LineageWeave-to-orchestrator connection. Provider credentials remain in the
  orchestrator environment.
- Set `TEPP_TRANSPORT_URL` and its runtime credential only when the accepted
  TEPP producer contract is deployed. A configured URL is not proof of an
  accepted result.
- Enable the `mcp` Compose profile only after setting exact OAuth resource,
  Host/Origin, request-size, and k6-evidenced quota values described in the
  [MCP manual](mcp-manual.md).

For authenticated runtime acceptance, start the exact-revision stack with the
MCP profile and declare separate provider-probe and readiness-observation
budgets. `ORCHESTRATOR_PROBE_TIMEOUT_SECONDS` accepts 0.1 through 30 seconds;
`ORCHESTRATOR_READINESS_TIMEOUT_SECONDS` is the positive-integer wall-clock
budget for the asynchronous job. The acceptance runner reads the cached agent
catalog inside the orchestrator container, probes only active agents belonging
to the configured gateway for the structured workflow used by content
analysis, and fails closed if no such agent becomes ready. While the job is
pending, the runner accepts only the positive integer polling cadence declared
by contextual-orchestrator (upstream PR #907) and never substitutes a local
polling interval.

Declare `OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS` and
`OPERATIONS_CASE_POLL_SECONDS` as separate positive-integer observation inputs.
The runner does not enqueue a demonstration record or assume a fresh ledger. It
first accepts aggregate grounded evidence produced since the exact worker
container started. If none exists yet, an eligible queued/running record with no
current-source-digest analysis must already be present; the runner then waits
for both deployment-bound analysis and grounded aggregate counts to advance.
It fails closed when neither path is available. Source rows and record
identifiers remain inside the database and are never printed.

The 2026-08-26 diagnostic run supplied `MCP_RATE_LIMIT_REQUESTS=1000` and
`MCP_RATE_LIMIT_WINDOW_SECONDS=60` only to its acceptance invocation. Those
observed inputs are neither source defaults nor a production capacity SLO;
repeat k6 measurement in the target deployment before selecting production
quota values.

## Durable asynchronous work

The API enqueues Ask and content-analysis work; workers perform provider calls
outside pooled database transactions. Keep workers enabled during backfill.
Stopping a worker does not turn queued work into a completed analysis.

For an incident:

1. Preserve the job id and inspect aggregate job-state counts without printing
   source content or account identifiers.
2. Confirm backend-worker progress health, Valkey availability, PostgreSQL
   connectivity, and the owner service's readiness.
3. Restore the failed dependency before retrying. Do not convert an unavailable
   provider response into a negative classification.
4. The enabled worker admits the next bounded incomplete page every recovery
   cycle. For an operator-controlled catch-up, run
   `scripts/queue_post_content_backfill.py --all-pages`. After restoring a
   terminal dependency, run `scripts/queue_post_content_backfill.py
   --retry-failed` for one bounded page. Do not combine those flags: observe
   aggregate worker, PostgreSQL, Valkey, and orchestrator health until the page
   settles before choosing whether to admit another terminal page. Both modes
   persist each page before publishing wake-ups and report aggregate counts
   only.
   The post-content consumer is intentionally serial. Do not derive a worker
   concurrency value from low CPU or memory while it waits on the provider:
   there is no measured gateway concurrency envelope, and the database pool is
   shared with the worker lease and other durable consumers. A page can take
   one provider deadline per attempted record; keep observing the admitted page
   rather than opening another one.
5. For one terminal content job, run
   `uv run python scripts/requeue_failed_post_content.py --post-id <post-id>`
   from the governed operator environment. This preserves the original source
   digest, orchestrator session lineage, and idempotency boundary. Do not edit
   queue rows or publish a wake-up manually.
5. Verify the affected aggregate returns to completed and that no partial
   result became visible.

One record uses the same bounded post-scoped orchestrator session lineage for
its related analysis work. Treat those session values as correlation metadata:
retain them in governed storage, do not expose or log them as customer content.

## Dashboard and semantic evidence recovery

- **Pending count grows:** verify worker progress, queue publication, and
  owner-service readiness; do not add more HTTP workers as a substitute for
  consumers.
- **Failed count grows:** inspect safe failure categories and retry through the
  durable queue after the root cause is fixed.
- **Voice counts are unavailable:** confirm that current source and derived
  assertions completed. Preserve multi-membership and disagreement; do not
  coerce a record into one category.
- **Product mention is missing, tied, or unavailable:** repair or review the
  governed product catalog and rerun extraction. Do not bind by display-name
  similarity alone.
- **A governed product is absent:** an account with `post_admin` submits
  `PUT /api/product-catalog/{product_code}` with the explicit product-master
  label, level, source organization/system/record, optional existing parent,
  and source-supported aliases. Preserve the returned digest with the import
  evidence. On `409`, reconcile the source-master conflict instead of changing
  the catalog implicitly; on `422`, provision the named parent or correct the
  invalid row. Then rerun product analysis and open the cited post to verify the
  connection.
- **Project journey is unavailable:** verify an accepted TEPP result exists for
  the exact snapshot and cutoff. Do not substitute chronological sorting.
- **Related public source is absent:** verify publication eligibility and the
  governed public-research service. Do not invent or manually insert a title,
  URL, or excerpt.

## Database checks

Observe PostgreSQL before changing it. Record only aggregates:

- active and waiting sessions by wait-event class;
- transaction age and lock blockers;
- queue-state totals and oldest queued age;
- WAL growth/checkpoint statistics; and
- query plans through the repository's bounded `EXPLAIN` procedure.

Do not cancel a migration or disable WAL durability solely because it is slow.
Use `scripts/explain_post_content_backfill.py` for the bounded backfill plan;
it rolls back and reports aggregate timing, buffers, temporary blocks, WAL,
node kinds, and relation scans without exposing rows. Tune only from measured
evidence, then capture the root-cause fix in Compose/configuration and tests.
The observed PostgreSQL tuning procedure revalidates exact settings, aggregate
transaction/lock quiescence, and current cgroup/disk capacity immediately
before any approved restart; a saved plan is not permission to reuse stale
runtime evidence.

## Load and responsiveness verification

With the canonical synthetic stack healthy, declare the environment-specific
concurrency, duration, and timeout:

```bash
LINEAGEWEAVE_VUS=<concurrency> \
LINEAGEWEAVE_DURATION=<duration-with-unit> \
LINEAGEWEAVE_REQUEST_TIMEOUT=<timeout-with-unit> \
make load-http

LINEAGEWEAVE_VUS=<concurrency> \
LINEAGEWEAVE_DURATION=<duration-with-unit> \
LINEAGEWEAVE_REQUEST_TIMEOUT=<timeout-with-unit> \
make load-mcp
```

Retain aggregate request rates, latency distributions, functional-check
failures, Ask job-state counts, CPU, memory, database waits, and worker backlog
outside git. These observations do not establish a production SLO until the
named deployment and representative workload approve one.

## Shutdown and rollback

```bash
make down
```

Do not remove named volumes during ordinary shutdown. Apply migration rollback
files only under the migration-specific reviewed recovery plan; application
code must not compensate for a missing table. After recovery, repeat OIDC,
authenticated API, worker-progress, Dashboard, Ask, and relevant k6 checks at
the exact deployed revision.

Customer actions are documented separately in the [user guide](user-guide.md).
