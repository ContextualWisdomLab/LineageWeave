# Authenticated HTTP concurrency evidence

LineageWeave provides `scripts/k6_http_e2e.js` to measure the real Compose
HTTP boundary while a synthetic Global Ask job is queued or running. It logs
in through the seeded Keycloak realm, submits one non-identifying question to
`POST /api/ask`, then drives concurrent authenticated requests to posts,
Event Lineage, and the Ask-status projection.

This implements the measurement side of ADR 0204's resource-release decision:
provider work is asynchronous, so ordinary readers should remain observable
while the worker runs. The harness does not prove why a slow observation is
slow. Correlate a run with backend/PostgreSQL/Valkey/orchestrator telemetry and
`pg_stat_activity` before naming a bottleneck.

## Run

Start and seed the synthetic stack, then supply the concurrency and observation
window that match the environment under review:

```bash
make up
KEYCLOAK_ADMIN_PASSWORD=admin_dev_only make seed
k6 run -e REQUEST_TIMEOUT=<declared-request-window> \
  --vus <measured-concurrency> --duration <observation-window> \
  scripts/k6_http_e2e.js
```

Pass `BACKEND_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`,
`K6_USERNAME`, and `K6_PASSWORD` with k6's `-e NAME=value` option to point the
harness at another authorized synthetic environment. Never run repository
performance evidence against identifying production records.

`REQUEST_TIMEOUT` is mandatory because an unbounded request hid the first
observed saturation behind k6's graceful-stop window. It is an operator-declared
observation boundary, not a product latency threshold.

## Interpret the output

k6 reports observed request counts, failure rate, and duration distributions.
The custom metrics separate:

- `lineageweave_ask_enqueue_duration`: time to persist and acknowledge the job;
- `lineageweave_read_duration{endpoint:posts|lineage}`: ordinary reader paths;
- `lineageweave_ask_poll_duration`: owner-scoped status polling.

There are deliberately no pass/fail thresholds. A latency or concurrency SLO
requires a named deployment, representative workload, capacity evidence, and
product approval; CI runner capacity is not that evidence. Store the raw k6
output with the environment's CPU, memory, database pool, worker concurrency,
dataset counts, exact Git SHA, and observation time. Do not promote one laptop
or shared-runner result to a product guarantee.

Figma and screenshot review do not apply: this is a non-UI HTTP load harness.

## Current-main verification record

On 2026-08-25, a worktree based on protected-main commit `48f013a2` passed
`k6 inspect` for this script. A fresh Compose project did not reach an
application-ready state: the build was stopped
after backend dependency synchronization alone had reached 225.5 seconds and
was still incomplete; other observed BuildKit metadata, copy, and image-export
steps ranged up to 292.3 seconds. No containers were running afterward, so no
HTTP latency distribution was produced and no application bottleneck is
claimed. This is local build-environment evidence only. Re-run the command
above on an application-ready stack to obtain the product measurement.

The next application-ready exercise on protected-main `d7d5eeb3` exposed two
failures before a capacity distribution could be accepted. A clean backend
process could not start because `Settings` omitted the already-consumed
`tepp_api_key`, and the replay database lacked the non-idempotent 0203 Global
Ask scope tables. After repairing those startup and replay contracts, the k6
setup completed, but its authenticated read batch overlapped migration replay:
PostgreSQL was still building the 0035 trigram index with a `DataFileRead` wait,
and the not-yet-reached 0140 migration meant Event Lineage correctly failed on
its absent interval column. This run therefore cannot attribute read latency to
Global Ask and is not a valid steady-state capacity exercise.

Independent code-path diagnosis did confirm that Global Ask resolved its
external question embedding inside `pool.acquire()`. ADR 0212 moves that call
before acquisition and adds a regression check that observes zero held pool
slots during embedding. With one virtual user, a 10-second observation, and a
declared 20-second request window, the post-fix branch then observed Ask enqueue
at 3.11 seconds and Ask polling at 1.31 seconds while both reads failed under
that incomplete migration state (one reached the 20-second request boundary;
combined read duration averaged 14.13 seconds). This is replay-in-progress
failure evidence, not a steady-state capacity result or product latency claim.
Re-run only after migration replay completes.
