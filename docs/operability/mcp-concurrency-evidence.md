# MCP concurrency evidence

This supporting record is governed by [ADR 0218](../adr/0218-current-contract-mcp-global-ask.md).
It reports an observation, not an SLO or production capacity claim.

## 2026-08-26 synthetic isolated-Compose observation

The candidate containing the request-lifecycle repair was run in an isolated
Compose project with synthetic fixtures only. The MCP service used the
operator-declared diagnostic quota envelope of 1,000 authenticated tool calls
per 60 seconds; this value is not a deployment recommendation. The committed
`scripts/k6_mcp_e2e.js` initialized an MCP session per VU, submitted one durable
Global Ask job, and concurrently read that job through the MCP tool contract.

```text
k6 run --vus 5 --duration 5s
REQUEST_TIMEOUT=20s
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
