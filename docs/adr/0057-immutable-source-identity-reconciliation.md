# ADR 0057: Immutable source identity for reconciliation

## Status

Accepted; supersedes ADR 0056

## Context

`title + written date + customer code + PU` is a useful search heuristic, but
it is not a source identity. A private source audit found duplicate groups for
this composite key, including groups with more than one record. A candidate
being unique in the current target snapshot does not make the mapping safe:
new imports, deleted rows, or incomplete target data can change that result.

## Decision

- Populate the internal `post_id` from the immutable source UUID during import
  and preserve any separate source lookup key in `source_record_key`, or use an
  externally governed mapping artifact that independently records the source
  identifier-to-target-post relationship.
- Never reconcile or backfill source identity from title, date, customer,
  process unit, project, author, or any combination of those fields.
- Keep a target body with no source identity unbound. Do not overwrite it or
  attach a source identifier merely because a natural-key query returns one
  current candidate.
- Exact source-ID search is authoritative only for persisted source UUID or
  `source_record_key` values. A source lookup key is not assumed unique; the
  board may return every authorized post carrying that exact key. If the source
  identifier was not imported, the board must report that the source identity is
  unavailable rather than guess.
- The body-bearing importer continues to preflight source identity and body
  completeness before mutating the target. A source without body evidence is
  not converted into a title-only post.

## Consequences

Some existing target rows will remain unbound until the source export is
re-run with its immutable identifier or an independently auditable mapping is
provided. This is preferable to silently assigning a real post body or source
ID to the wrong record. Natural-key matching remains available for analyst
review and candidate presentation, but never for persisted provenance.
