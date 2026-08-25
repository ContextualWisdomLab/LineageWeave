# ADR 0223: Explicit semantic content unit kinds

**Status:** Accepted
**Date:** 2026-08-26

## Context

PRD-FR-4 requires ordered paragraph, list, table, formula,
conversation-turn, and image-region semantic units. The source parser already
kept those boundaries, but `post_content_unit.unit_kind_code` collapsed every
textual DOM unit to `dom` and every markup-free unit to `plain_text`. A stored
row therefore could not disclose which source boundary produced its embedding.

## Decision

1. PostgreSQL admits `paragraph`, `list`, `table`, `formula`, and
   `conversation_turn` as governed `post_content_unit_kind` values. Existing
   `plain_text`, `dom`, and `image` values remain valid historical values.
2. New writes classify only explicit source boundaries: paragraph/plain-text
   chunks, `li`, table rows, top-level MathML `math`, and caller-parsed
   conversation turns. Unknown DOM blocks remain `dom`; no prose pattern or
   model guess manufactures a kind.
3. MathML is retained as one ordered formula boundary. This decision does not
   parse, evaluate, or assign mathematical meaning to the expression.
4. Image regions remain normalized children of their document-order image
   unit under ADR 0091 rather than duplicating them as top-level content units.
5. A source adapter may pass already parsed `Chunk` units to persistence.
   LineageWeave does not infer RFC 5322 sender boundaries from an opaque body.

## Consequences

- Embedding rows remain attached to the same ordered source unit while their
  stored kind becomes inspectable and stable.
- Existing rows are not rewritten, so provenance is preserved.
- Formula evaluation and formula ontology remain outside LineageWeave.

## References

World Wide Web Consortium. (2025). *MathML Core* (Candidate Recommendation
Snapshot, June 24, 2025). https://www.w3.org/TR/2025/CR-mathml-core-20250624/

Resnick, P. W. (Ed.). (2008). *Internet message format* (RFC 5322). Internet
Engineering Task Force. https://www.rfc-editor.org/rfc/rfc5322
