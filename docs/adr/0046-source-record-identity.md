# ADR 0046: Preserve source record identity

## Context

`source_post.post_id` is an internal UUID. The private importer derives it
from `source_system_code` and the source row's opaque `record_key`, but the
record key was discarded after UUID generation. That made an authorized buyer
unable to find a record by the identifier shown by the source system and made
the evidence trail incomplete.

## Decision

Persist `source_system_code` and `source_record_key` on `source_post` as a
nullable source identity pair. Existing synthetic rows remain valid with no
source identity. The pair is unique when present, and the raw key is exposed
only through the existing authorized post API.

Board search matches the source system and key exactly, and applies trigram
similarity to the key for short transcription errors. The internal UUID stays
the navigation and foreign-key identity; the source key is evidence, not an
authorization scope and not a replacement for ontology resolution.

The importer must preserve the key on insert and update. No real source key,
title, body, screenshot, or fixture is added to this repository.

## Consequences

- A buyer can search an opaque source identifier and open its authorized post.
- A one-character key typo can still reach the candidate through PostgreSQL
  trigram similarity.
- Legacy rows without an imported key remain searchable by their existing
  UUID, title, body, and semantic evidence until re-imported.
- Raw source identity remains distinct from customer, project, PU, sales-pool,
  and Keyman ontology assertions.
