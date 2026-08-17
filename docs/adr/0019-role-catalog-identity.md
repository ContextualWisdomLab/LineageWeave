# ADR 0019 — R&R catalog identity lives on the role row

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

ADR 0009 writes `post_team_mention` and `post_organization_mention` so a
cataloged team or organization can start a related-node walk. ADR 0018
exposes `catalog_node_id` on the summary payload by joining those
mentions back to `post_summary_role` through `actor_name`.

`corporate_entity.entity_name` is not unique. Two catalog rows can share
a display name (different `corporate_entity_code`, different parents).
A fetch join on name therefore:

- attaches a homonym that this post never resolved, or
- duplicates the role when more than one same-named row exists.

Mention tables are post-scoped, not role-scoped. They cannot reconstruct
which catalog id was chosen for a specific R&R row. That reconstruction
is a transitive dependency on a non-key attribute, so it is not third
normal form (Codd, 1970; Date, 2019).

Team identity is already unique on
`(team_name, affiliated_organization_name)`. Organization identity is
not.

## Decision

`post_summary_role` stores the resolved catalog foreign keys
(`cataloged_team_id`, `cataloged_corporate_entity_id`) written during
`persist_post_summary`. `fetch_persisted_summary` reads those columns.
It does not join `corporate_entity` by `entity_name`. Person identity
is ADR 0027 (`cataloged_person_id`).

Migration `0019_role_catalog_identity.sql` backfills existing rows from
a post-scoped mention only when the name match is unique on that post.
Two same-named mentions stay unbound rather than guessing.

## Consequences

- Open a post whose R&R names an organization that shares a display
  name with another catalog row. The button walks the resolved id, not
  the homonym.
- Clicking that name still uses `GET /api/corporate-entities/{id}/related`
  or `GET /api/teams/{id}/related`. Authz stays person/entity-parity:
  a team mentioned only on another corp's private post is 403; an
  unknown UUID is 404.

## References

Codd, E. F. (1970). A relational model of data for large shared data
banks. *Communications of the ACM, 13*(6), 377–387.
https://doi.org/10.1145/362384.362685

Date, C. J. (2019). *Database design and relational theory: Normal forms
and all that jazz* (2nd ed.). Apress.
https://doi.org/10.1007/978-1-4842-5540-7

International Organization for Standardization. (2023). *ISO/IEC
11179-1:2023: Information technology—Metadata registries (MDR)—Part 1:
Framework*.

Reynolds, D. (Ed.). (2014). *The organization ontology*. World Wide Web
Consortium. https://www.w3.org/TR/vocab-org/
