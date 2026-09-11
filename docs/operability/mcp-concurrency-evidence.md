# MCP concurrency evidence

This supporting record is governed by [ADR 0218](../adr/0218-current-contract-mcp-global-ask.md)
and its current-protocol amendment
[ADR 0272](../adr/0272-stateless-mcp-protocol-dual-era.md). It reports
observations, not an SLO or production capacity claim.

## 2026-09-11 synthetic isolated-Compose observation (dual era)

The current-protocol candidate was run in the isolated synthetic Compose
stack with the operator-declared diagnostic quota envelope of 1,000
authenticated tool calls per 60 seconds; this value is not a deployment
recommendation. The committed `scripts/k6_mcp_e2e.js` ran its default
2026-07-28 stateless lane (self-contained requests, `Mcp-Method` /
`Mcp-Name` routing headers, no session) and then the explicitly selected
2025-11-25 handshake lane as a compatibility regression.

```shell
KEYCLOAK_URL=http://127.0.0.1:18080 MCP_URL=http://127.0.0.1:18001/mcp \
  REQUEST_TIMEOUT=20s k6 run --vus 3 --duration 5s scripts/k6_mcp_e2e.js
MCP_PROTOCOL_VERSION=2025-11-25 ... k6 run --vus 3 --duration 5s scripts/k6_mcp_e2e.js
```

| Observation | Modern 2026-07-28 | Legacy 2025-11-25 |
| --- | ---: | ---: |
| Completed iterations | 112 | 64 |
| Interrupted iterations | 0 | 0 |
| HTTP requests | 114 | 74 |
| HTTP request failures | 0 | 0 |
| Successful MCP Ask-read checks | 112 / 112 | 64 / 64 |
| Submit duration, average | 1.39 s | 765.23 ms |
| Read duration, average / p95 / maximum | 136.05 / 575.86 / 1010 ms | 246.28 / 695.31 / 926.78 ms |
| Initialize duration, average / p95 / maximum | not applicable (stateless) | 78.97 / 202.46 / 230.71 ms |

An earlier run on the saturated stack reported two Ask-read check failures
while every MCP POST still returned 200; the repeat after the synthetic
queue drained shows 0 failed checks and 0 HTTP failures, so the earlier
failures were queue saturation, not transport.

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
