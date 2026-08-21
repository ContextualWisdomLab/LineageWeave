# External lineage analysis v1 operability boundary

The pure package entry point is synchronous and bounded. Remote or model-backed production use must wrap it in a separately reviewed service or plugin lifecycle with durable idempotency, cancellation, timeout, retry classification, rate limiting, resource budgets, artifact retention, OpenTelemetry signals, and user-visible degraded states.

A consumer must not call optional model-backed pair adjudication directly on an unbounded web request path. LineageWeave #289 tracks the durable asynchronous reconstruction requirement for product persistence, and Naruon #1437 requires an equivalent consumer-side job receipt before integration is enabled.
