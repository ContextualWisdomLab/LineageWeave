# ADR 0038: Distributed authenticated-principal quota for MCP Global Ask

- **Status:** Proposed
- **Date:** 2026-08-20
- **Extends:** ADR 0037
- **Issue:** #269, Slice B

## Context

Global Ask can invoke bounded database retrieval, contextual-orchestrator, image
normalization, and an explicitly requested public-verification lane. A process-
local counter does not protect that work in a horizontally scaled MCP service:
a client could obtain a fresh allowance by reaching another replica, and a
restart would erase the policy state.

The admission clock must also preserve the product authorization boundary.
Preflight, hostile Host/Origin traffic, malformed requests, unprovisioned
subjects, and principals without `post_read` are not billable Global Ask
invocations and must not consume a principal allowance. Conversely, once an
authorized principal enters the expensive answer path, the allowance is
consumed even if an upstream model or search dependency later fails; otherwise
repeated failing calls could bypass the cost boundary.

The pinned MCP Python SDK transports tool calls over JSON-RPC. Its stable public
API preserves structured JSON-RPC error `data`, while it does not currently
offer a supported application hook that reliably turns a tool-level quota
failure into an HTTP 429 response with a `Retry-After` header across Streamable
HTTP. LineageWeave must not depend on private SDK middleware internals or claim
an HTTP contract that the pinned dependency cannot preserve.

## Decision

1. Enforce one shared fixed window in Valkey for every authenticated
   `user_account_id`.
2. Resolve the bearer subject to a provisioned database account and verify the
   live `post_read` permission before consuming quota.
3. Use an opaque SHA-256 key derived from a domain-separated account identifier.
   Do not store or return the raw account UUID, subject, counter value, or the
   key digest.
4. Execute one atomic Lua script against one explicitly passed Valkey key. The
   script increments the counter, gives the first increment a bounded expiry,
   and obtains the remaining TTL for retry guidance. It never synthesizes a
   second key inside the script, preserving single-key cluster routing.
5. Default to 20 invocations per 60 seconds. Operators may configure
   `MCP_GLOBAL_ASK_RATE_LIMIT` from 1 through 10,000 and
   `MCP_GLOBAL_ASK_RATE_WINDOW_SECONDS` from 1 through 86,400. Invalid values
   prevent process startup.
6. A denied invocation raises implementation-defined JSON-RPC server error
   `-32029` with bounded public data:

   ```json
   {
     "error_code": "global_ask_rate_limited",
     "retry_after_seconds": 17,
     "retryable": true,
     "scope": "authenticated_principal"
   }
   ```

7. When the shared limiter is unavailable or returns malformed/conflicting
   data, fail closed with JSON-RPC error `-32028` and a separately bounded
   operator-configured retry suggestion. Never fall back to an in-process
   counter.
8. Bound `retry_after_seconds` to at least one second and no more than the
   configured window. Repeated denied attempts do not extend the window because
   expiry is set only on the first increment.
9. Keep transport-abuse controls separate. CORS preflight, Host/Origin rejection,
   request-byte rejection, and OAuth rejection occur before this principal
   quota and therefore do not consume it.
10. Return no HTTP `Retry-After` claim from this slice. The JSON-RPC `data`
    contract is the supported client boundary for the pinned SDK. A later SDK
    upgrade may add an HTTP projection only after end-to-end tests prove that
    intermediaries and the SDK preserve the status and header.
11. Share the same Valkey service used by the product's other distributed event
    work, but use a distinct key prefix and database-safe opaque namespace.
12. Close the Valkey client and database pool on every MCP lifespan exit,
    including partial startup failure.

## Request order

```text
Host / Origin / request-byte admission
→ OAuth bearer verification
→ provisioned user_account resolution
→ live post_read permission check
→ atomic Valkey principal quota
→ source retrieval and ABAC
→ contextual-orchestrator
→ optional public verification
```

## Consequences

- All MCP replicas observe the same allowance for one principal.
- A principal cannot bypass quota by switching replicas or restarting a process.
- Pre-auth traffic does not consume a customer's product allowance.
- Repeated upstream failures still consume quota after authorized admission,
  protecting shared model/search capacity.
- Clients receive a bounded machine-readable retry value but not an HTTP
  `Retry-After` header in this SDK slice.
- A Valkey outage makes Global Ask explicitly unavailable instead of silently
  weakening the protection.
- Fixed windows permit a bounded burst across a window boundary. This is accepted
  for the initial product contract because it is simple, atomic, explainable,
  and independently bounded by the per-window maximum. A sliding-window change
  requires a separate ADR and migration plan.

## Rejected alternatives

- **Per-process memory counter:** bypassable across replicas and erased on restart.
- **Key by bearer token or external subject:** creates token-rotation drift and
  retains more identity material than the database account key requires.
- **Consume before account/permission resolution:** charges hostile or
  unauthorized requests and cannot provide a tenant-safe principal scope.
- **Consume only after a successful answer:** lets repeated failed model/search
  calls use unbounded shared capacity.
- **Unbounded Valkey retry or local fallback:** converts an infrastructure
  failure into inconsistent authorization and cost policy.
- **Private SDK middleware patch for HTTP 429:** fragile across SDK versions and
  not supported by the pinned public API.
- **Expose counters, raw account IDs, or digest keys:** unnecessary disclosure
  that does not help the caller decide when to retry.

## Verification requirements

- fake-client unit tests for opaque keying, atomic script arguments, malformed
  responses, bounded retry, and fail-closed backend errors;
- an actual Valkey integration test proving two limiter instances share one
  principal counter while another principal remains isolated;
- an in-process MCP client test proving quota occurs after account and
  `post_read` resolution;
- exact JSON-RPC code and `data` assertions for denial and backend unavailability;
- a regression proving a principal without `post_read` consumes no quota;
- configuration-bound and Compose-wiring tests;
- full exact-head repository, security, SAST, supply-chain, and independent
  review gates before leaving Draft.
