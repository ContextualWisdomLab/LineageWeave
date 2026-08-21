# ADR 0121: Resolve source bodies from governed MHTML artifacts

## Status

Accepted

## Context

The authorized export used by the private runtime contains post metadata and
MHTML artifact provenance, but some rows do not contain a body column. ADR
0056/0057 prohibit turning a title, summary, or inferred content into a
source body. The importer therefore needs an explicit, auditable path from a
source row to its separately stored MHTML artifact.

## Decision

- A body-bearing import uses exactly one of two mappings: an explicit body
  column, or an artifact path column plus an artifact SHA-256 column and an
  operator-supplied artifact root.
- Artifact paths must resolve beneath the configured root after symlink
  resolution. Missing files, traversal outside the root, non-regular files,
  malformed hashes, and digest mismatches fail preflight before any target
  mutation.
- The resolver accepts RFC 2557 `multipart/related` messages and selects the
  first leaf `text/html` part as the source body. It never falls back to a
  title, plain-text summary, generated content, or an unrelated MIME part.
- Every non-excluded source row is resolved and validated before the target
  scope or any `source_post` row is written. The artifact bytes remain
  operator-local; only the source body and existing provenance-bearing target
  fields are persisted.
- The source UUID/record-key mapping remains explicit and independent from
  the artifact path. An artifact match cannot repair a missing immutable
  source identity.

## Consequences

The private runtime can consume an authorized MHTML export without weakening
the fail-closed source-body contract. A missing or incorrect artifact is an
actionable import error rather than a silently incomplete post. The public
repository continues to contain only synthetic artifact fixtures.

## References

Palme, J., Hopmann, A., & Shelness, N. (1999). *MIME encapsulation of
aggregate documents, such as HTML (MHTML)* (RFC 2557). RFC Editor.
https://www.rfc-editor.org/rfc/rfc2557.html
