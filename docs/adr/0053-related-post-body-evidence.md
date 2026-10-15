# ADR 0053: Bounded body evidence in related-post navigation

- Status: Accepted
- Date: 2026-08-19

## Context

Buyer navigation must let a user judge a related post before opening it. A
title-only customer, author, or lineage card is not evidence, but returning the
full body for every related row would expose unnecessary content and force the
large source-post heap into every lookup.

## Decision

- Board, lineage, customer-master, and entity-related post references expose
  `post_body_excerpt` as normalized source text truncated to 420 characters,
  plus `post_body_truncated`.
- Customer and source-author hint lists include at most the 20 newest related
  posts per hint; aggregate `post_count` remains the full authorized count.
- The full `post_body` remains available only from the ABAC-checked post-detail
  endpoint and is rendered by the source-body component.
- Customer and author hint lookups use partial covering indexes so the lookup
  does not scan the large body heap before selecting bounded related rows.
- Raw ontology IRIs, extraction metadata, and provider metadata remain outside
  this Buyer evidence projection.

## Consequences

Related navigation is evidence-bearing without duplicating full source bodies.
The 20-row navigation bound is intentional; users can search the board or open
the detail view for the complete authorized record set.

## Amendment (2026-10-07): bounded excerpt normalization

Synthetic authenticated k6 observation of the formal Compose stack found
PostgreSQL CPU saturated by Board reads. Building each 420-character excerpt
ran three regular expressions over the complete source body, so a page of 50
large bodies normalized megabytes to return kilobytes.

- `source_post_excerpt_text(body, max_chars)` normalizes only the first 16,384
  source characters (the existing search-prefix bound), after dropping an
  unterminated trailing tag. When that prefix yields at least `max_chars`
  normalized characters, its leading excerpt is returned; otherwise the
  function falls back to normalizing the whole body. The returned excerpt is
  therefore identical to `btrim(left(source_post_search_text(body), max_chars))`;
  the prefix bound changes cost, never content.
- Board, lineage, related-post, and knowledge-graph excerpts use the function.
  A search-hit excerpt still locates the term in the complete normalized body.
- `post_body_truncated` keeps its existing source-length meaning.
