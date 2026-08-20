# ADR 0056: Source body availability and reconciliation

## Status

Accepted

## Context

The board must show the source post body when the source contract provides one.
It must not manufacture a body from a title, a summary, ontology labels, or
semantic extraction output. A private audit of the supplied PostgreSQL source
found that the exported post rows contain stable activity identifiers and
metadata, but no populated body values; only a small, separate subset has
content-block evidence. Existing target rows can therefore contain body text
without carrying the source identity that would make an exact source lookup
safe.

This creates two distinct cases:

1. A source row with body evidence: import and render the body as source
   evidence.
2. A source row without body evidence: render an explicit unavailable state;
   never substitute a generated summary or title.

## Decision

- Map the source activity GUID to `source_record_key` only through the caller's
  explicit source mapping. The importer must preflight every non-excluded row
  before mutating the target.
- Require a non-empty source body for the body-bearing import path. A missing
  body fails the import instead of silently creating title-only posts.
- Keep `source_record_key`, `source_system_code`, and body provenance separate.
  A target row with a body but no source identity is not automatically treated
  as the source row.
- The board always renders the body region. When no source body is persisted,
  it renders the localized `No post body.` state rather than an empty region.
- Reconciliation of an existing target body to a source identity is allowed
  only in a private, read-only preflight followed by a unique match on stable
  source fields. Ambiguous matches remain unbound.
- Source DSNs and source-specific SQL stay outside this repository. Only
  aggregate, non-identifying audit findings may be committed.

## Consequences

The board no longer hides the distinction between “body is present” and “the
source did not provide a body.” Exact source-ID search becomes trustworthy only
after a successful identity-bearing import or an auditable unique
reconciliation. A source export without body evidence must be corrected at the
source or supplemented with a separately governed content export before it can
support full post reading and 5W1H extraction.
