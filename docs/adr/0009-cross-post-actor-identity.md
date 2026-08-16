# ADR 0009 — R&R team/organization actors get a shared cross-post identity, not just per-post text

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

Extraction (Keyman, R&R) runs per-post. For a person actor, this was
already not a dead end: Keyman extraction upserts into
`cataloged_person`, so the same name across posts (mostly) resolves to
one row with a stable `person_id` the Knowledge Graph can link through.
R&R's team actor (ADR 0007, `prov_team`) and organization actor
(ADR 0006, `prov_organization`) had no equivalent -- each post's
extraction produced a bare `actor_name` string in `post_summary_role`
with no catalog entry and no Knowledge Graph mention edge. The same
"설계팀" (design team) named in ten different posts was ten unrelated
strings, not one entity a Keyman/team panel could click through to see
every post it appears in -- exactly the "extraction results must
themselves become cross-post lineage clues, not just per-post
artifacts" requirement this product exists to satisfy for people, but
was not yet satisfying for teams or organizations.

## Decision

**Team**: a new `cataloged_team` catalog table
(`migrations/0016_cross_post_actor_identity.sql`), the same
catalog-then-mention shape `cataloged_person`/`post_person_mention`
already establishes. Identity key is `(team_name,
affiliated_organization_name)`, not the bare name alone -- "설계팀"
exists at many real companies, so the pair is what is actually
identifying (`backend/app/team_ingestion.py`'s `upsert_team`, mirroring
`keyman_ingestion.py`'s `_upsert_person`). The team's own parent
organization is resolved to a real `corporate_entity` via the *same*
`resolve_corporate_entity` collective-entity-resolution matching
(Bhattacharya & Getoor, 2007) Keyman affiliations already use -- not a
second matching algorithm.

**Organization**: an R&R organization actor's name is run through the
same `resolve_corporate_entity` matching; a resolved match writes a
`post_organization_mention` row (no new catalog needed -- `corporate_entity`
already is the shared, cross-post organization catalog every VOC
counterparty and Keyman affiliation already resolves against).

**Person** (an R&R actor, not a Keyman): opportunistically joined to an
*existing* `cataloged_person` row by exact name match, when Keyman
extraction has already cataloged that name on this or another post.
R&R does not create a new person identity itself -- `cataloged_person`
requires `person_side_code` (our-side vs. counterparty), which R&R's
prompt does not currently ask for and Keyman's does; inventing one here
risked a wrong side assignment. Documented as a real, deliberate scope
boundary below, not silently half-done.
Person evidence sources remain separate: Keyman extraction replaces
`post_person_mention`; R&R replacement writes
`post_summary_person_mention`. `combined_post_person_mention` is a
read-only union used for lineage and KG derivation. This prevents a new
summary from deleting Keyman evidence and prevents removed R&R actors
from surviving as stale Keymen. Migration 0016 copies matching R&R
actor names into `post_summary_person_mention` and must not delete
overlapping Keyman rows -- `mention_context` has no R&R column, and a
later summary replacement would otherwise erase the only remaining
person evidence.


Each resolved actor gets a real Knowledge Graph mention edge (new
`edge_mention_team` / `edge_team_affiliation` / `edge_mention_organization`
lookup codes, `lineageweave/knowledge_graph.py`'s
`knowledge_graph_edges_for_post` extended, not a second edge-writing
path), reusing the same `persist_edges_for_post` entry point Keyman
ingestion already calls -- one function computes a post's whole edge
set regardless of which extraction step triggered it.

`knowledge_graph_edge` is a deduplicated materialized registry.
`knowledge_graph_edge_evidence` records every post that currently supports an
edge; readers require support from an ABAC-visible post. Writers reconcile one
post under a transaction-scoped advisory lock, and unsupported registry rows
are pruned. Edge identity therefore cannot duplicate under concurrency, and a
replacement cannot leave a buyer-visible orphan edge.

Ontology (`docs/ontology/lineageweave-kg.ttl`): `:Team a owl:Class ;
rdfs:subClassOf org:OrganizationalUnit` (same W3C ORG grounding as
ADR 0007's `:RoleActorTeam`, but a distinct term -- `:Team` is a
`cataloged_team` row with a stable identity, `:RoleActorTeam` is the
per-row `actor_type_code` classification, the same
`:Person`/`:RoleActorPerson` split ADR 0006 already established).
`:mentionsTeam` / `:teamAffiliatedWith` / `:mentionsOrganization` are
new, distinct object properties rather than widening `:mentions`'s
domain/range -- stating `rdfs:domain :mentions` twice (once `:Person`,
once `:Team`) would let RDFS entail every `:mentions` subject is BOTH,
which is false.

## Consequences

- Team/organization mention persistence only runs when
  `summary.roles_and_responsibilities` is non-empty (a real, cheap
  guard, not a correctness gap) -- a post with no R&R never touches
  `cataloged_team`/`post_organization_mention` at all.
- **Documented, deliberate gap**: R&R never *creates* a new
  `cataloged_person` row, only joins to an existing one by exact name.
  Two failure modes follow from this, both accepted for now: (1) a
  person named only in R&R (never by Keyman on any post) gets no
  catalog identity at all until/unless Keyman also names them; (2) an
  exact-name join has the same same-name-collision risk
  `keyman_ingestion._upsert_person`'s job-title disambiguation exists
  to catch, but R&R's join here does not run that check (R&R's own
  prompt does not currently capture a job title). A future slice could
  extend the R&R prompt to also ask for `person_side_code` (and
  optionally a title) so R&R could safely originate new person
  identities the same way Keyman does, closing this gap properly rather
  than working around it with a guess.
- `cataloged_team` uses PostgreSQL's
  `UNIQUE NULLS NOT DISTINCT (team_name, affiliated_organization_name)`.
  NULL affiliation therefore participates in the identity key: two
  bare-team rows with the same name conflict and the atomic upsert
  returns one shared `team_id`. This database constraint, not a
  read-before-insert application check, closes the concurrent duplicate
  race for both affiliated and unplaced teams.

## Related

Depends on [ADR 0006](0006-role-responsibility-agent-ontology.md) and
[ADR 0007](0007-team-actor-type.md) (actor *type*) and
`lineageweave.corporate_hierarchy_resolution` (Bhattacharya & Getoor,
2007, cited there) for the organization-matching this ADR reuses rather
than re-deriving. [ADR 0019](0019-role-catalog-identity.md) stores the
resolved catalog id on `post_summary_role` so fetch does not rejoin by
display name.

## References (APA 7th)

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in relational data. *ACM Transactions on Knowledge Discovery from Data*, 1(1), Article 5. https://doi.org/10.1145/1217299.1217304

Reynolds, D. (Ed.). (2014). *The organization ontology* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/vocab-org/
