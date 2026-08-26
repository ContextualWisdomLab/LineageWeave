# ADR 0238: Source conversation-turn import contract

**Status:** Accepted
**Date:** 2026-08-26

## Context

ADR 0062 and PRD-FR-4 require sender-bounded conversation turns to remain
ordered semantic units. The PostgreSQL importer currently receives only an
opaque body, so its production path cannot call the existing
`chunk_by_conversation_turn` boundary without guessing where a sender's turn
starts. Naruon and other source adapters own authorized source parsing and
identity; LineageWeave owns semantic-unit persistence, retrieval, and evidence
provenance.

## Decision

1. The importer optionally accepts one caller-mapped JSON/JSONB column with
   contract kind `lineageweave.source_conversation_turns` and version `1`.
2. A supplied envelope contains 1–32 turns in exact list order. Each turn has
   exactly `ordinal`, `speaker`, `text`, and `evidence_reference`; ordinals are
   the contiguous integers beginning at zero. Speaker and text are explicit
   source values, never inferred from body syntax or account metadata.
3. Each text is bounded to 8,000 characters, a turn list to 32
   entries, and the complete UTF-8 serialized envelope to 24,000 bytes. These are exactly
   the existing post-structure unit, unit-batch, and provider request-body
   transport limits. Speaker and opaque evidence-reference strings must be
   nonblank, fit within that same bounded envelope, and contain no NUL that
   PostgreSQL `text` cannot represent; no new empirical cutoff, semantic
   weight, or scoring heuristic is introduced.
4. The entire source result set is validated before any target write. Unknown
   keys, kind/version drift, malformed JSON, non-contiguous order, blank or
   oversized values, and non-string fields fail closed.
5. The opaque evidence reference persists as nullable
   `post_content_unit.source_evidence_reference`. Null means that an older or
   non-conversation unit has no caller-supplied reference; it is never filled
   from another source field.
6. An absent or SQL `NULL` envelope keeps the existing source-body unit path.
   An explicitly supplied empty or malformed envelope is rejected rather than
   treated as absence.

The version 1 envelope is:

```json
{
  "kind": "lineageweave.source_conversation_turns",
  "version": 1,
  "turns": [
    {
      "ordinal": 0,
      "speaker": "Synthetic requester",
      "text": "Please verify the synthetic order.",
      "evidence_reference": "message-part:synthetic:0"
    }
  ]
}
```

## Consequences

- Authorized adapters can preserve who supplied each searchable passage and
  link a match back to caller-owned evidence without database coupling.
- ThreadWeave's message-to-message reference tree remains separate from turns
  inside one imported record.
- Re-import replaces the post's derived units transactionally, so the same
  source envelope is idempotent and stale turn references do not survive.

## References

Resnick, P. W. (Ed.). (2008). *Internet message format* (RFC 5322). Internet
Engineering Task Force. https://www.rfc-editor.org/rfc/rfc5322
