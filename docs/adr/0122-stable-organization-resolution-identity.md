# ADR 0122 — Link verified organization resolutions by catalog identity

- Status: Accepted
- Date: 2026-08-21
- Owners: LineageWeave ingestion / Global Ask retrieval
- Depends on: [0008](0008-organization-abbreviation-resolution.md), [0107](0107-verified-organization-label-evidence.md)
- Figma File ID: N/A (backend persistence and query-integrity decision; no UI change)

## Context

`organization_name_resolution.resolved_organization_name` is a label, not a
stable identity. Joining it to `corporate_entity.entity_name` can attach a
verified alias to the wrong organization when two catalog entities share the
same display name. Existing rows also need an additive migration path because
Compose volumes can predate the feature migration.

## Decision

Persist the resolved catalog identity in
`organization_name_resolution.resolved_corporate_entity_id` with a foreign-key
constraint. Global Ask nomination and evidence disclosure join through that
identifier. The ingestion path links only the exact raw-name/context cache row
after corroboration and catalog resolution. Historical rows remain unlinked
and are excluded until a future authorized ingestion can establish the stable
relationship; no name-based backfill is permitted.

`docker/postgres-init/migrate.sh` replays both the verified-label indexes and
this identity migration on existing Compose volumes.
The paired rollback removes only the new index and nullable foreign-key column;
it assumes the application has first been rolled back to the prior contract.

## Consequences

- Same-named organizations cannot cross-match through a display-label join.
- Foreign-key integrity prevents references to a missing catalog entity.
- Historical cache rows may be temporarily unavailable to verified-label search
  until they are safely re-linked.
- The schema remains normalized: the resolution stores a foreign key, while the
  catalog remains the owner of the organization label.

## Buyer next action

Open the cited post from a verified label result; if the alias has not yet been
linked to a catalog identity, continue with the ordinary organization search
flow instead of treating the label as authoritative.

## References

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/
