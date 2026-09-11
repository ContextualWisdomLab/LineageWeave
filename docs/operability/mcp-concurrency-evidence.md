# MCP concurrency evidence

This supporting record is governed by [ADR 0218](../adr/0218-current-contract-mcp-global-ask.md)
and its current-protocol amendment
[ADR 0272](../adr/0272-stateless-mcp-protocol-dual-era.md). It reports
observations, not an SLO or production capacity claim.

## 2026-09-11 repeated-submit observation and read-path profile (dual era)

The current-protocol candidate (PR head `aa9e391fb`) was served as the
authenticated MCP app against the synthetic Compose PostgreSQL, Valkey,
Keycloak, and contextual-orchestrator dependencies with the operator-declared
diagnostic quota envelope of 1,000 authenticated tool calls per 60 seconds;
this value is not a deployment recommendation.

The committed `scripts/k6_mcp_e2e.js` now submits a durable Ask job inside
every default-function iteration and then reads that job back, so a p95 exists
for the submit hop; the earlier harness submitted once in `setup()` and could
only ever report a single submit sample. Submit remains a queue transport call
-- a durable row insert plus wake-up publish -- and the multi-minute worker
answer stays asynchronous and outside the measured boundary.

```shell
KEYCLOAK_URL=http://127.0.0.1:18080 MCP_URL=http://127.0.0.1:18001/mcp \
  REQUEST_TIMEOUT=20s k6 run --vus 3 --duration 10s scripts/k6_mcp_e2e.js
KEYCLOAK_URL=http://127.0.0.1:18080 MCP_URL=http://127.0.0.1:18001/mcp \
  MCP_PROTOCOL_VERSION=2025-11-25 REQUEST_TIMEOUT=20s \
  k6 run --vus 3 --duration 10s scripts/k6_mcp_e2e.js
```

| Observation | Modern 2026-07-28 | Legacy 2025-11-25 |
| --- | ---: | ---: |
| Completed iterations | 23 | 14 |
| Interrupted iterations | 0 | 0 |
| HTTP requests | 47 | 35 |
| HTTP request failures | 0 | 0 |
| Successful MCP checks (submit + read) | 46 / 46 | 28 / 28 |
| Submit duration, average / median / p95 / maximum | 1.06 s / 343.92 ms / 6.25 s / 6.68 s | 1.57 s / 531.36 ms / 5.81 s / 5.81 s |
| Read duration, average / median / p95 / maximum | 248.52 / 166.75 / 600.96 / 656.54 ms | 371.64 / 315.74 / 676.58 / 741.97 ms |
| Initialize duration, average / p95 / maximum | not applicable (stateless) | 1.34 s / 1.53 s / 1.53 s |

### Synchronous read-path profile

Acceptance 8 profiles the read boundary because its p95 exceeded 20 ms. The
read tool runs one synchronous chain -- bearer verification, account resolution,
quota consumption, then the durable row read. Each hop was timed once against
the PR-head application functions and the live PostgreSQL and Valkey
dependencies (25 warm samples per hop):

| Hop | Average | p95 | Maximum |
| --- | ---: | ---: | ---: |
| `decode_access_token` (cached JWKS) | 1.63 ms | 2.73 ms | 7.30 ms |
| `resolve_current_account` (PostgreSQL) | 88.43 ms | 174.40 ms | 549.63 ms |
| `limiter.consume` (Valkey) | 47.72 ms | 120.00 ms | 740.39 ms |
| `read_global_ask_job` (PostgreSQL) | 90.11 ms | 87.67 ms | 1432.25 ms |

Every hop is a bounded network round trip to a backing service. No hop performs
unbounded or CPU-bound work, and the lone in-process hop (signature
verification against cached JWKS) is sub-3 ms at p95. The observed seconds-scale
tail is a contended-host artifact, not application structure: on the same host
a bare `select 1` measured 29.41 ms p95 / 916.35 ms maximum and the direct
job-by-id read measured 88.13 ms p95 / 3.54 s maximum, while load average was
45 on 10 logical cores with the PostgreSQL container at 213% CPU, Valkey at
117%, and the orchestrator at 46%. This profile therefore resolves the causal
structure of the read boundary but is not a capacity measurement.

This workstation result proves only that the declared synthetic workload
completed on this candidate. Representative infrastructure telemetry and an
approved quota/SLO decision remain required before a production capacity
claim.

## 2026-08-26 synthetic isolated-Compose observation

The candidate containing the request-lifecycle repair was run in an isolated
Compose project with synthetic fixtures only. The MCP service used the
operator-declared diagnostic quota envelope of 1,000 authenticated tool calls
per 60 seconds; this value is not a deployment recommendation. The committed
`scripts/k6_mcp_e2e.js` initialized an MCP session per VU, submitted one durable
Global Ask job, and concurrently read that job through the MCP tool contract.

```shell
REQUEST_TIMEOUT=20s k6 run --vus 5 --duration 5s scripts/k6_mcp_e2e.js
```

| Observation | Result |
| --- | ---: |
| Completed iterations | 628 |
| Interrupted iterations | 0 |
| HTTP requests | 642 |
| HTTP request failures | 0 |
| Successful MCP Ask-read checks | 628 / 628 |
| Iteration rate | 115.30467/s |
| Initialize duration, average / p95 / maximum | 37.46 / 55.76 / 57.39 ms |
| Submit duration | 34.13 ms |
| Read duration, average / p95 / maximum | 38.96 / 79.96 / 268.31 ms |

The first live initialization exposed a transport defect: the bounded-body
middleware manufactured `http.disconnect` immediately after replaying the
admitted body, so the streaming response ended incomplete. The shared
middleware now replays the body once and then delegates subsequent lifecycle
messages to the real client receive channel. Focused admission and MCP contract
tests pass, and the repeated live run completed without the incomplete-response
error.

This workstation result proves only that the declared synthetic workload
completed on this candidate. Representative infrastructure telemetry and an
approved quota/SLO decision remain required before a production capacity
claim.
