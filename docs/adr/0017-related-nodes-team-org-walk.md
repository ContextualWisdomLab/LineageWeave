# ADR 0017 — Related-node walks include team and organization mention edges

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

ADR 0009 persists `edge_mention_team`, `edge_team_affiliation`, and
`edge_mention_organization` so a cataloged team or organization can
become a cross-post Knowledge Graph clue. The buyer-visible related-node
walk (`load_visible_subgraph` + Tong et al., 2006 random walk with
restart) still loaded only person mention, co-mention, and affiliation
edges, and returned an empty graph when a visible post had no people.
A team-only follow-up therefore never appeared as a related node, and
clicking an R&R team name had no catalog id to start a walk.

The same temporal honesty ADR 0016 applied to run *detail* posts was
still missing from thread-group *run list* visibility: a later public
post in that thread group could surface a run the account was not
allowed to know at `knowledge_cutoff`.

## Decision

`load_visible_subgraph` loads person, team, and organization mention
channels independently. Empty person evidence is not a reason to drop
team or organization edges. `hydrate_related_nodes` labels
`cataloged_team` rows. `GET /api/teams/{team_id}/related` starts the
same RWR walk Keyman and corporate-entity related already use.
`visible_affiliation_post_ids` unions direct `post_organization_mention`
rows with person-affiliation posts so an org-only mention can start a
walk.

The summary payload exposes `catalog_node_id` / `catalog_node_type_code`
when the R&R actor resolved to a team or organization mention on that
post. The popup turns that name into a related-node button.

`fetch_persisted_summary` binds those ids from `post_team_mention` /
`post_organization_mention` first, then name-checks the catalog row.
`corporate_entity.entity_name` is not unique (Bhattacharya & Getoor,
2007; two legal entities can share a trading name). A global name join
duplicates the R&R row or attaches the wrong catalog id. Two same-named
mentions on one post pick a deterministic mention id; they do not emit
two chips for one actor.

Thread-group run list visibility requires at least one ABAC-visible
`source_post` whose `created_at` is at or before `knowledge_cutoff`.

## Consequences

- Open a post whose R&R names 설계팀, then click the team. Sibling posts
  that mention the same cataloged team appear as related nodes.
- Click a related team chip the same way you already click a person or
  organization chip.
- A later public post in a thread group no longer lists a January run
  that could not have known that post.
- Two catalog orgs that share a label do not duplicate the R&R chip.
  Click the chip to walk the mention this post actually stored.
- A team or org mentioned only on another corporation's private post
  403s. An unknown team UUID 404s. A private org mention does not
  authorize or leak that post into a related walk.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Reynolds, D. (Ed.). (2014). *The organization ontology*. World Wide Web
Consortium. https://www.w3.org/TR/vocab-org/

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data,
1*(1), 5-es. https://doi.org/10.1145/1217299.1217304

Tong, H., Faloutsos, C., & Pan, J.-Y. (2006). Fast random walk with
restart and its applications. *Proceedings of the Sixth International
Conference on Data Mining (ICDM'06)*, 613–622.
https://doi.org/10.1109/ICDM.2006.70

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
