# ADR 0081: Combine source-author Keyman evidence without identity guessing

- Status: Accepted
- Date: 2026-08-20

## Context

Imported posts contain a source-author code and an `author_account_id`, but
neither value alone proves that the author is a cataloged person. The same
author/account context is nevertheless an important prior when finding our-side
Keymen. Customer Master previously ordered author groups using only
`post_summary_role`, so dedicated Keyman extraction rows in
`post_person_mention` were omitted from the author-group hints.

## Decision

Customer Master `source_author_hints` will combine two evidence projections:

1. our-side person roles from `post_summary_role` joined to
   `cataloged_person`;
2. our-side mentions from `post_person_mention` joined to
   `cataloged_person`.

Both projections must resolve to `cataloged_person.person_side_code =
'our_side'`. They are grouped by the source-author code, the source author
account, and the cataloged person. `mention_count` counts distinct source
posts. The response provenance names both source projections and
`source_post.author_account_id`.

The source-author code, account, display name, and account affiliations remain
hint-only context. They never create or bind a `cataloged_person` by name,
account, or display-name equality. An unresolved author or an absent evidence
projection remains unresolved rather than becoming a Keyman.

## Consequences

- Customer Master can rank an author group when either summary-role extraction
  or dedicated Keyman extraction has produced evidence.
- Existing summary-role evidence remains compatible; dedicated Keyman evidence
  is no longer invisible to the author-group view.
- The Keyman extraction backfill remains an explicit operator action through
  contextual-orchestrator; this query change does not invent missing mentions.
- A source-author group can still have zero `keyman_hints` when neither
  evidence projection has a resolved our-side person.

## Rejected alternatives

- Treating `source_author_code` or `author_account_id` as a cataloged person
  would create false identities in imported data.
- Replacing summary-role evidence with `post_person_mention` would discard
  existing summary-derived evidence and make the migration order observable.
