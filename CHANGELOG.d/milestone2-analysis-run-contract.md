## Added

- Added a normalized, aggregate-only provenance root for private PostgreSQL
  analysis runs, downstream TEPP/contextual-orchestrator/fast-mlsirm service
  calls, status events, and external acceptance artifacts.
- Added a no-future-information database and Python contract requiring the
  source snapshot's latest evidence-availability time not to exceed the run's
  knowledge cutoff.
- Added deterministic, source-redacting request digests and transactional
  idempotency/conflict handling without storing SQL, DSNs, raw content, image
  bytes, provider credentials, or private source identifiers.
- Added real-PostgreSQL schema tests and 100% statement/branch coverage for the
  new Python contracts and repository.

## Security

- Private actual-data acceptance manifests remain external deployment
  artifacts referenced only by digest and URI; public API projections contain
  aggregate counts, clocks, opaque IDs, configuration, and status only.
