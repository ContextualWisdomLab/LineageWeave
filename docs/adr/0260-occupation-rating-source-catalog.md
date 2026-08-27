# ADR 0260: Imported occupation-rating source catalog

- Status: Accepted
- Date: 2026-08-27
- Extends: ADR 0257, ADR 0258, ADR 0259

## Context

ADR 0259 initially requires users to type internal release and source-table
codes. That makes a valid product action depend on repository knowledge and
allows a user to request a source that was never imported. The normalized
rating store already owns the exact imported artifact catalog and therefore is
the only authoritative selector source.

## Decision

1. Add an authenticated read endpoint that lists rating artifacts containing
   at least one persisted occupation observation. Exclude the Scales Reference
   support artifact from selectable rating sources.
2. Return release code/version, publisher and license, source code/name, URL,
   SHA-256, and declared row count. Order releases by persisted import time and
   sources by stored name/code; do not infer recency from a version string.
3. The Dashboard selects only an entry returned by this endpoint. If the
   catalog is loading, empty, or unavailable, disable profile submission and
   give the user a next action. Do not retain a hidden hand-written fallback.
4. Authentication matches ADR 0258: imported O*NET artifacts are public
   reference data, while the catalog still requires a valid workspace account.
5. The catalog does not claim that all official O*NET artifacts are imported.
   It describes only current database state with immutable artifact provenance.

## Consequences

The occupation evidence workflow no longer asks users to know storage codes,
and an unavailable artifact cannot masquerade as a selectable source. Adding
an official artifact remains an importer operation with digest and row-count
validation rather than a UI-created catalog row.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html
