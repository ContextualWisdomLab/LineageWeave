# ADR 0018 — Related-node walks include team and organization mention edges

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

ADR 0017 already records an authorized Pending analysis-run write.
This decision is the related-node walk, not that create path.

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
from the catalog foreign keys stored on `post_summary_role` (ADR 0019).
The popup turns that name into a related-node button. Do not reconstruct
the id by `corporate_entity.entity_name`.

Thread-group run list visibility requires at least one ABAC-visible
`source_post` whose `created_at` is at or before `knowledge_cutoff`.

## Consequences

- Open a post whose R&R names 설계팀, then click the team. Sibling posts
  that mention the same cataloged team appear as related nodes.
- Click a related team chip the same way you already click a person or
  organization chip.
- A later public post in a thread group no longer lists a January run
  that could not have known that post.
- Catalog ids on those chips come from `post_summary_role` (ADR 0019).
  Do not rejoin `corporate_entity` by `entity_name`.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Reynolds, D. (Ed.). (2014). *The organization ontology*. World Wide Web
Consortium. https://www.w3.org/TR/vocab-org/

Tong, H., Faloutsos, C., & Pan, J.-Y. (2006). Fast random walk with
restart and its applications. *Proceedings of the Sixth International
Conference on Data Mining (ICDM'06)*, 613–622.
https://doi.org/10.1109/ICDM.2006.70

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
