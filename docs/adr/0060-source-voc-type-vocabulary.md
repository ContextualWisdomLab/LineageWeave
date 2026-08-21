# ADR 0060: Preserve the source VOC type vocabulary

## Status

Accepted

## Context

The source contract carries five VOC type codes: `VOC`, `VOCC`, `VOCO`,
`VOM`, and `VOP`. The target previously registered only `voc` and `vom`, and
the importer defaulted an absent or empty mapped value to `voc`. That silently
collapsed distinct source semantics and made the Board type filter appear to
have only two choices.

## Decision

- Register the canonical target codes `voc`, `vocc`, `voco`, `vom`, and `vop`
  with their lookup labels and stable display order.
- Normalize the governed source codes case-insensitively at the import
  boundary; preserve no other code by guessing.
- Reject an empty mapped VOC value or an unsupported value before target
  mutation. The fallback `voc` is permitted only when the caller explicitly
  omitted a VOC column mapping.
- Build Board filter options from the distinct eligible persisted values, so
  all five values are returned when the authorized corpus contains them.

## Consequences

The Board reflects source semantics instead of the importer's default. Existing
rows that were already collapsed to `voc` cannot be reconstructed from the
target alone; they require a governed re-import from the source `voctp_field`.
