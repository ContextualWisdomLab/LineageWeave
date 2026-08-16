# ADR 0019 — Persist the R&R catalog identity on the role row

**Decision status:** Accepted
**Date:** 2026-08-16
**Depends on:** ADR 0009 cross-post actor identity; ADR 0018 related-node
team/organization walk

## Context

ADR 0009 and ADR 0018 expose `catalog_node_id` so a buyer can click an
R&R team or organization and walk sibling posts. The read path joined
`corporate_entity` by `entity_name`. That column is a display label, not
an identity key: two companies can share it, and `corporate_entity_code`
is the unique catalog key. A name join then either duplicated the role
or attached the homonym's id when both rows were mentioned on the same
post.

`cataloged_team` already protects the team path with
`UNIQUE NULLS NOT DISTINCT (team_name, affiliated_organization_name)`.
Person lookup used `LIMIT 1` without `ORDER BY`, so two same-named
people were non-deterministic.

Fellegi and Sunter (1969) treat a match decision as a binding to one
record, not a later re-search by a non-unique attribute. Bhattacharya
and Getoor (2007) keep that binding once collective resolution has
chosen a candidate.

## Decision

`post_summary_role` stores the catalog foreign key resolved at write
time:

- `cataloged_team_id` for `prov_team`
- `corporate_entity_id` for `prov_organization`
- `cataloged_person_id` for `prov_person`

At most one of those columns is set, and the set column must match
`actor_type_code`. `fetch_persisted_summary` reads those columns,
including `cataloged_person_id` into `catalog_node_id`. It does not
rejoin the catalog by display name.

Person lookup, when it still resolves by name, orders by
`created_at`, then `person_id`, and stores that id. It still does not
create a new `cataloged_person` row (ADR 0009 gap).

Historical backfill copies a mention only when exactly one mentioned
catalog row on that post shares the role's actor name
(`HAVING count(*) = 1`). Two same-named mentions stay unbound. A
`DISTINCT ON` / min-UUID pick is a later re-search by a non-unique
attribute and is forbidden here (Fellegi & Sunter, 1969).

`GET /api/teams/{team_id}/related` keeps person/entity parity: unknown
UUID is 404; a team mentioned only on an unseen private post is 403.
A private `post_organization_mention` does not open the related walk
through the ADR 0018 UNION (Hu et al., 2014), including when the
mentioned organization is one the requester can already see.

## Consequences

- Open a post whose R&R names an organization that shares a display
  name with another catalog row. The chip keeps the id persist stored.
  Click it to walk that organization's posts, not the homonym's.
- Open a post whose R&R names a person already in `cataloged_person`.
  The chip is a button even when Keyman extraction was not run on that
  post. Click it to walk that person, not a later same-named row.
- A later mention of the homonym on the same post does not duplicate
  the role or retarget the chip.
- Pre-0019 rows with two same-named mentions stay unbound until an
  operator re-persists the summary. Do not guess a UUID at migrate
  time.
- Team and organization related endpoints fail closed the same way
  Keyman and corporate-entity related already do. A private mention of
  an organization you can already see must not appear in that walk.

## References

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data,
1*(1), Article 5. https://doi.org/10.1145/1217299.1217304

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage.
*Journal of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

Hu, V. C., Ferraiolo, D., Kuhn, R., Schnitzer, A., Sandlin, K.,
Miller, R., & Scarfone, K. (2014). *Guide to attribute based access
control (ABAC) definition and considerations* (NIST Special Publication
800-162). National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-162
