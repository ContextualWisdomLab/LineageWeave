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
- `lineageweave_ask_state_observations{job_status:...}`: how many observations
  occurred while the one queued job was queued, running, or settled.

The harness observes one Ask job's real lifecycle; it does not keep provider
work running artificially. Report reader distributions with the state counts
so a long settled tail is not misrepresented as contended capacity. Per-VU
authentication is renewed after an HTTP 401 and the failed batch is retried
once, so observation windows longer than the realm access-token lifetime do
not silently become rejection measurements.

There are deliberately no pass/fail thresholds. A latency or concurrency SLO
requires a named deployment, representative workload, capacity evidence, and
product approval; CI runner capacity is not that evidence. Store the raw k6
output with the environment's CPU, memory, database pool, worker concurrency,
dataset counts, exact Git SHA, and observation time. Do not promote one laptop
or shared-runner result to a product guarantee.

Figma and screenshot review do not apply: this is a non-UI HTTP load harness.

## Exact-head synthetic verification record

On 2026-08-26, an isolated Compose stack built from PR #663 commit
`be361f10` completed an authenticated 4-VU, 30-second run against 27 synthetic
`source_post` rows. The run completed 5,537 iterations and 16,613 HTTP
requests; all 16,611 endpoint checks passed and k6 recorded no HTTP failures.
Ask enqueue averaged 11.88 ms. Ask polling averaged 13.61 ms, with 21.46 ms
p95 and 156.69 ms maximum. The combined post/lineage reader metric averaged
19.57 ms, with 31.39 ms p95 and 198.64 ms maximum. Overall HTTP duration
averaged 17.59 ms with 29.25 ms p95, at 183.44 iterations and 550.39 requests
per second.

The host exposed 10 logical CPUs and 32 GiB RAM; Compose imposed no explicit
backend CPU or memory limit. This exact-head observation verifies concurrent
responsiveness for the small synthetic fixture and the asynchronous Ask
enqueue/poll path. It does not represent authorized production volume,
establish capacity, isolate a causal bottleneck, or establish an SLO.

## Current-main verification record

On 2026-08-25, the follow-up change at `a700374e` was exercised against the
authorized local Compose PostgreSQL/Keycloak/Valkey/orchestrator stack after
all schema migrations and index builds had completed. Only aggregate evidence
was retained: the database held 43,189 source posts. Ten-second authenticated
observations used the same endpoint mix and reported zero HTTP errors at 1,
10, and 25 VUs. Before the bounded-lineage query, HTTP median/p95/p99 and
throughput were 809.03 ms/6.18 s/6.22 s and 0.618 requests/s at 1 VU;
4.63 s/20.10 s/20.46 s and 1.531 requests/s at 10 VUs; and
25.35 s/33.59 s/36.30 s and 1.046 requests/s at 25 VUs. The 25-VU observation
completed six iterations.

The same observations after moving the landing lineage ABAC, ordering, node
bound, and edge bound into PostgreSQL were 179.52 ms/3.43 s/4.17 s and 1.067
requests/s at 1 VU; 1.88 s/20.80 s/21.04 s and 1.487 requests/s at 10 VUs;
and 22.03 s/29.78 s/31.38 s and 2.411 requests/s at 25 VUs. The 25-VU
observation completed 25 iterations. The 10-VU tail did not improve, so this
evidence does not establish a latency SLO or a product capacity ceiling. It
does establish that repeatedly loading all visible posts and all lineage edges
before applying the 500-node contract was avoidable work; the remaining tail
requires endpoint-tagged traces and database-pool telemetry before another
cause is assigned.

An exact-code-head 4-VU, 60-second confirmation at `a700374e` completed 36
iterations and 110 HTTP requests with zero failed checks or requests. Overall
HTTP median/p95/p99 were 392.15 ms/8.82 s/9.68 s at 1.644 requests/s. The
combined posts/lineage read median/p95/p99 were 3.21 s/9.14 s/9.89 s; Ask poll
median/p95/p99 were 41.39 ms/413.16 ms/462.65 ms. All 36 iterations observed
the Ask lifecycle state. This confirms asynchronous Ask polling remained
responsive in that observation while also preserving the remaining reader-tail
gap; it is not a deployment SLO.

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
external question embedding inside `pool.acquire()`. ADR 0213 moves that call
before acquisition and adds a regression check that observes zero held pool
slots during embedding. With one virtual user, a 10-second observation, and a
declared 20-second request window, the post-fix branch then observed Ask enqueue
at 3.11 seconds and Ask polling at 1.31 seconds while both reads failed under
that incomplete migration state (one reached the 20-second request boundary;
combined read duration averaged 14.13 seconds). This is replay-in-progress
failure evidence, not a steady-state capacity result or product latency claim.
Re-run only after migration replay completes.

A subsequent exact-head run reached the 0140 interval migration but still was
not steady state: replay stopped at migration 0165 because its queue table and
indexes lacked the ADR 0166 replay guards, so migration 0174's edge-signal
table was absent. With one virtual user, a 15-second observation, and the same
20-second request window, Ask enqueue averaged 125.05 milliseconds, Ask polls
averaged 123.41 milliseconds, and posts succeeded, but all four Event Lineage
reads failed on that absent table. The branch now makes migration 0165
idempotent and regression-checks both Global Ask migrations. These values are
diagnostic evidence only.

After replaying the repaired 0165–0205 range to completion, a four-VU,
30-second observation with the declared 20-second request window completed 13
iterations and all 39 endpoint checks without an HTTP failure. Ask enqueue was
57.32 milliseconds, Ask polling averaged 359.91 milliseconds (p95 969.66
milliseconds), and the combined posts/Event-Lineage read distribution averaged
5.75 seconds (p95 11.88 seconds, maximum 12.36 seconds). A second four-VU,
15-second diagnostic run also completed every endpoint check; concurrent
`pg_stat_activity` samples repeatedly observed the authorized filter-option,
post-list, and lineage-page queries as active, including `MessageQueueSend` and
one temporary-buffer write. This identifies the measured database work to
profile next; it does not by itself assign causality or establish an SLO.

## Older-image diagnostic observation

On 2026-08-26, the same non-exact local Compose boundary completed an
authenticated 4-VU, 30-second run over 43,189 aggregate synthetic
`source_post` rows: 87 full iterations, 263 HTTP requests, and 261/261 endpoint
checks succeeded. Ask enqueue was 57.25 ms. Ask polling was 56.83 ms mean,
233.37 ms p95, and 765.24 ms maximum. The combined post/lineage reader metric
was 842.14 ms mean, 1.53 s p95, and 2.80 s maximum. The host exposed 10 logical
CPUs and 32 GiB RAM; Compose imposed no explicit backend CPU or memory limit.
The backend container came from image `sha256:28234aa5db0e` created on
2026-08-24, not the current PR head. These distributions show that concurrent
readers remained responsive on that image; they do not validate an exact-head
regression, identify a causal bottleneck, or establish an SLO.

On 2026-08-25, an application-ready local Compose stack configured with four
worker VUs completed zero full iterations in two observations. In the second
30-second observation, Ask enqueue took 2.69 seconds, the maximum completed
HTTP request took 45.26 seconds, and k6 recorded no failures among requests
that completed. Isolated observations were: `/api/posts` did not complete
within 30 seconds, `/api/lineage` took 12.152 seconds, and Ask polling took
0.456 seconds. The database contained 43,189 aggregate `source_post` rows;
`pg_stat_activity` showed repeated post-filter `DISTINCT` queries active with
`MessageQueueSend` waits.

The backend image was from an older branch, not the current or ADR 0212 change
head. These aggregate, non-identifying values support investigating the
duplicate filter-option query; they do not demonstrate current-head latency,
causality, capacity, or an SLO. ADR 0212 combines the two option projections
into one database query; its physical plan remains to be measured exact-head.
Repeat the synthetic k6 run on an exact-head image before comparing effects.
