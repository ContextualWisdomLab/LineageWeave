# MCP concurrency evidence

This supporting record is governed by [ADR 0218](../adr/0218-current-contract-mcp-global-ask.md).
It reports an observation, not an SLO or production capacity claim.

## Authentication for new synthetic observations

When the identity client disallows password grants, supply an audience-correct
token through `K6_ACCESS_TOKEN_FILE`, an absolute path to a private runtime
file outside git. Obtain it through the identity owner's authorized flow;
do not enable a disabled grant. The script reads the opaque token at
initialization. Use local `k6 run` only; do not archive or upload a script
that opens this runtime file. The harness never logs the token and aborts the
entire observation if it is empty
or subsequently rejected. Acquire a fresh token before rerunning. HTTP debug
logging must stay off. MCP error envelopes and tool-error content are omitted
from diagnostics; a status code alone identifies the failed operation.

Authentication failure supplies no concurrency, latency, throughput, or
saturation evidence. Correlate a successfully authenticated synthetic run with
PostgreSQL, worker, Valkey, and gateway measurements before assigning a
bottleneck. No request-body content or identifying rows belong in that record.

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

Remote observation targets require HTTPS. HTTP is allowed only on the exact
loopback hosts `localhost`, `127.0.0.1`, and `[::1]`. Every credential-bearing
request disables redirects; synthetic identity authentication follows the same
transport rule. File-supplied tokens are never automatically renewed.
