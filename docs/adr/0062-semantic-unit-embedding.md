# ADR 0062: Embed paragraph and meaning-identifiable content units

- Status: Accepted
- Date: 2026-08-19

## Context

Ontology and semantic retrieval cannot reliably represent a long post as one
vector. A relevant project, customer, PU, sales-pool, or Keyman mention can be
buried by unrelated text elsewhere in the same post. The repository already
has paragraph, sentence, DOM-block, and conversation-turn chunkers, but the
decision was not recorded as an ADR.

## Decision

Embedding is performed on meaning-identifiable units, not on a flattened whole
post whenever the source contains more than one unit:

- paragraph boundaries for plain text;
- DOM block boundaries for HTML/MHTML;
- sentence boundaries when the caller explicitly selects the finer unit;
- conversation-turn boundaries for sender/receiver shaped content.

`chunked_max_similarity` embeds every selected unit through the
contextual-orchestrator embedding channel and max-pools unit-pair similarity.
If a source produces zero or one unit, it falls back to one whole-text
embedding because there is no meaningful pairwise chunk comparison. Persisted
`post_content_unit` rows are the provenance anchor for unit-level embeddings;
`post_content_embedding` and its value rows retain model and dimension
identity. The model identity is selected and returned by
contextual-orchestrator, then bound across the remaining batches for that
client and persisted as provenance; LineageWeave does not select it from a
provider-specific environment variable.

No local heuristic vector or whole-document replacement is allowed when the
configured embedding channel is unavailable.

## Consequences

- Ontology and semantic search can attribute a match to the specific content
  unit that supplied the signal.
- Rich HTML body parsing must preserve block boundaries instead of collapsing
  every tag into one paragraph.
- Short records remain cheap and behaviorally compatible through the explicit
  one-unit fallback.
