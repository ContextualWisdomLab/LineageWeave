## Added

- Added a normalized PostgreSQL registry for immutable source snapshots,
  aggregate reconciliation counts, authenticated analysis requests, product
  scopes, and append-only lifecycle evidence.
- Added a run-owned knowledge cutoff and snapshot-owned evidence-availability
  clock so one capture can support multiple historically valid analyses without
  future-information leakage.
- Added account-scoped idempotency, immutable request configuration, serialized
  count/run locking, legal lifecycle transitions, and a derived current-status
  view.
- Added fail-closed rollback, real-PostgreSQL contract tests, ADR 0013, and APA
  7th standards traceability.

## Security

- The registry deliberately excludes source SQL, DSNs, raw records, inline
  images, provider payloads, credentials, private source identifiers, and raw
  exceptions. Necessary PII remains in purpose-bound authorized product/source
  contexts rather than being copied into audit metadata or blanket-masked.
