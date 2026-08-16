# ADR 0021 — Persist the R&R person catalog identity on the role row

**Decision status:** Accepted
**Date:** 2026-08-16
**Depends on:** ADR 0009 cross-post actor identity; ADR 0019 role catalog
identity

## Context

ADR 0019 stores `cataloged_team_id` and `cataloged_corporate_entity_id`
on `post_summary_role` so fetch does not rejoin by display name. Person
actors were still joined at read time by `person_name`, or dropped from
the payload entirely. Two people can share a display name. A later
Keyman row with the same name then steals the chip, and a person named
only in R&R (Keyman not extracted on that post) has no button.

Fellegi and Sunter (1969) treat a match decision as a binding to one
record, not a later re-search by a non-unique attribute.

## Decision

`post_summary_role` stores `cataloged_person_id` written during
`persist_post_summary`. `fetch_persisted_summary` reads that column into
`catalog_node_id` / `node_person`. Person lookup binds by name only when
exactly one `cataloged_person` row matches. Two same-named catalog rows
leave the role unbound. Persist still does not create a new
`cataloged_person` row (ADR 0009 gap).

Migration `0021_role_person_catalog_identity.sql` backfills existing
rows from a post-scoped mention only when the name match is unique on
that post (`HAVING count(*) = 1`). Two same-named mentions stay unbound.

At most one of `cataloged_team_id`, `cataloged_corporate_entity_id`, and
`cataloged_person_id` is set, and the set column must match
`actor_type_code`.

## Consequences

- Open a post whose R&R names a cataloged person. The chip is a button
  even when Keyman extraction was not run on that post. Click it to walk
  that person, not a later same-named row.
- Two catalog people who share a display name stay unbound until an
  operator supplies a unique binding. Do not guess the oldest UUID.
- Pre-0021 rows with two same-named mentions stay unbound until an
  operator re-persists the summary. Do not guess a UUID at migrate time.

## References

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage.
*Journal of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.1080/01621459.1969.10501049

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data,
1*(1), Article 5. https://doi.org/10.1145/1217299.1217304
