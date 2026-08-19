# ADR 0058: Source publication-state gate

## Status

Accepted

## Context

The board is not an archive of every exported row. Temporary saves and deleted
records are outside the visible post set. A source lifecycle field must be
checked before a row is imported or exposed to search.

The current private source audit found that the mapped draft field is `NULL`
for all 43,814 rows. A separate deletion field contains 295 marked rows. The
source dictionary available to the importer does not establish that a `NULL`
draft value means published. Treating `NULL` as published would therefore
expose rows without evidence of publication state.

## Decision

- The source adapter must select an explicit draft-state field and an explicit
  deletion-state field when those fields exist.
- The adapter must supply the source-dictionary values that mean “temporary”
  and “deleted”; lifecycle labels are never guessed from UI text or local
  conventions.
- A missing or all-`NULL` draft signal is `publication_state_unknown`, not
  “published”. The import must stop before target mutation unless an
  independently governed source contract states how that value is interpreted.
- There is no command-line or runtime bypass for this preflight gate. A caller
  must provide the governed source interpretation and explicit excluded values
  before the importer can proceed.
- Rows marked temporary or deleted are excluded before identity resolution,
  body persistence, semantic extraction, lineage reconstruction, and search
  indexing.
- The board's type and visibility filters are built from persisted eligible
  values only. They must not offer “temporary save” as a normal post type when
  no eligible source value exists.
- The current source audit is evidence for a blocked import preflight only; no
  source rows are imported from it until publication-state semantics and body
  evidence are supplied.

## Consequences

The product may show fewer posts until the source lifecycle contract is
provided, but it cannot leak temporary or deleted records or present unknown
rows as published. A future source adapter must carry both the immutable
record key and the publication-state evidence in the same preflight result.
