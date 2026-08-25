# Authenticated HTTP concurrency evidence

LineageWeave provides `scripts/k6_http_e2e.js` to measure the real Compose
HTTP boundary while a synthetic Global Ask job is queued or running. It logs
in through the seeded Keycloak realm, submits one non-identifying question to
`POST /api/ask`, then drives concurrent authenticated requests to posts,
Event Lineage, the evidence Dashboard, and the Ask-status projection.

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
k6 run --vus <measured-concurrency> --duration <observation-window> \
  scripts/k6_http_e2e.js
```

Pass `BACKEND_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`,
`K6_USERNAME`, and `K6_PASSWORD` with k6's `-e NAME=value` option to point the
harness at another authorized synthetic environment. Never run repository
performance evidence against identifying production records.

## Interpret the output

k6 reports observed request counts, failure rate, and duration distributions.
The custom metrics separate:

- `lineageweave_ask_enqueue_duration`: time to persist and acknowledge the job;
- `lineageweave_read_duration{endpoint:posts|lineage|dashboard}`: ordinary reader paths;
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

## Dashboard candidate verification record

On 2026-08-26, the synthetic 27-post Compose dataset at candidate head
`b045a6e5` ran with 4 VUs for 30 seconds on alternate local ports. It completed
1,240 iterations and 4,962 authenticated HTTP requests with zero failed
requests and 4,960/4,960 successful checks across posts, Event Lineage,
Dashboard, and Ask polling. Overall request duration was 75.02 ms average,
56.73 ms median, 181.76 ms p95, and 791.89 ms maximum; the combined reader
metric was 81.68 ms average and 197.25 ms p95. The one Ask enqueue took
173.66 ms, while Ask polling averaged 54.80 ms with 132.98 ms p95.

The first candidate run exposed two Dashboard-only SQL contract defects:
an evidence-post predicate in the missing-fact query despite that query having
no evidence-post join, and a fifth bind value passed to the four-parameter
topic projection. Both failed every Dashboard request while sibling endpoints
remained responsive. The shared query boundary was repaired and regression
tests now assert the join and bind arity; the distribution above is the clean
rerun. This is synthetic candidate evidence, not protected-main evidence or a
capacity/SLO claim.

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

## Older-image diagnostic observation

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
