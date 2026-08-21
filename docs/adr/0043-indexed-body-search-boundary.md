# ADR 0043: Indexed body search boundary

- Status: Accepted
- Date: 2026-08-18

## Context

The buyer board must search body evidence as well as titles, identifiers, and
ontology/semantic projections. A direct `ILIKE` and `word_similarity` over the
full imported `source_post.post_body` makes a real-corpus search unbounded; the
detail view must still show the complete source body.

## Decision

Use a migration-backed PostgreSQL `simple` full-text index over the complete
source body for token retrieval, plus a trigram index over the first 16 KiB for
partial-substring retrieval. Search also retains the existing indexed
identifier/title fields and semantic projection joins. The post detail route
and body renderer remain full-body paths; the 16 KiB limit applies only to the
partial-substring accelerator, never to displayed evidence or persisted source
data.

If substring search must cover arbitrary positions after the prefix, add a
normalized full-body trigram projection rather than removing the detail-body
contract or reintroducing an unbounded scan.
