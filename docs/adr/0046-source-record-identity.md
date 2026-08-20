# ADR 0046: Preserve source record identity

## Context

`source_post.post_id` is an internal UUID. Some source systems provide both a
UUID record identity and a separate opaque record key that users enter when
searching. Treating those values as one field either changes the stable post
UUID or discards the searchable source identity.

## Decision

Persist `source_system_code` and `source_record_key` on `source_post` as a
nullable source identity pair. The private importer accepts an optional
source UUID column for `post_id`; when it is supplied, that UUID remains the
internal post identity while `record_key_column` is preserved independently.
Without that optional column, the existing deterministic UUID derivation is
retained for compatibility. Existing synthetic rows remain valid with no
source identity. The pair is an indexed lookup, not a uniqueness constraint:
a source export may repeat a human-entered lookup key for distinct immutable
source UUIDs. The raw key is exposed only through the existing authorized post
API.

Board search matches the source system and key exactly, and applies trigram
similarity to the key for short transcription errors. The internal UUID stays
the navigation and foreign-key identity; the source key is evidence, not an
authorization scope and not a replacement for ontology resolution.

The importer must preserve the key on insert and update. No real source key,
title, body, screenshot, or fixture is added to this repository.

Before creating or mutating the target scope, the importer preflights every
non-excluded source row and rejects an empty record key or body. This prevents
a partially imported batch from appearing valid while its source identity is
missing.

## Consequences

- A buyer can search an opaque source identifier and open its authorized post.
- A one-character key typo can still reach the candidate through PostgreSQL
  trigram similarity.
- Legacy rows without an imported key remain searchable by their existing
  UUID, title, body, and semantic evidence until re-imported.
- Raw source identity remains distinct from customer, project, PU, sales-pool,
  and Keyman ontology assertions.
