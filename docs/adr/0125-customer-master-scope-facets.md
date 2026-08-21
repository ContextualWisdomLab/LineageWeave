# ADR 0125 — Customer Master separates authorization scope from observed relationship facets

**Decision status:** Proposed
**Date:** 2026-08-21

## Context

`/api/customer-master` currently reads its `corporate_entities` list only from
`account_affiliation`. That is a valid authorization boundary, but it is not a
customer hierarchy: verified organization mentions and counterparty entities
created by ADR 0010 are not necessarily account affiliations. The resulting UI
can show an authorized employer while hiding an observed customer or affiliate,
and it cannot distinguish an account's own company from an explicitly granted
company because the current affiliation row has no such attribute.

The fix must preserve the existing ABAC decision. A visible relationship in a
public or authorized post is evidence for navigation, not permission to read a
private post. An unresolved counterparty name is a hint, not a catalog entity.

## Decision

1. Keep `account_affiliation` as the authorization source. Every post and
   entity returned by Customer Master remains subject to the existing
   per-request visibility and source-post eligibility predicates.
2. Add an explicit, nullable `affiliation_scope_code` to
   `account_affiliation`, backed by `common_lookup_value`, with the controlled
   values `scope_own_entity`, `scope_granted_entity`, and
   `scope_unclassified`. Existing rows are migrated to `scope_unclassified`;
   no own/customer identity is inferred from a login token, a PU, a post title,
   or a corporate name. Authentication continues to authorize every existing
   affiliation row regardless of this display facet.
3. Extend the Customer Master entity contract with repeatable, provenance-bearing
   `scope_facets`: `authorized_own`, `authorized_granted`,
   `observed_organization`, and `observed_hierarchy`. Multiple facets are
   allowed because one organization may be both an authorized entity and an
   observed counterparty in different evidence.
4. Build `observed_organization` only from a visible, eligible post's resolved
   `post_organization_mention` (or an equivalently persisted, verified catalog
   binding). `post_counterparty_entity` names that remain unresolved or
   uncorroborated stay in the existing `source_customer_hints` / relationship
   evidence surfaces and do not become tree nodes.
5. Traverse `parent_entity_id` only across entities already admitted by an
   authorization or visible evidence path. If a parent is not admitted, render
   the admitted child as a root; never widen access merely to complete a tree.
6. The UI's own-company/customer filters consume these facets and expose
   `scope_unclassified` as an honest third state. No confirmation dialog or
   guessed label is introduced. The API remains the single place that applies
   authorization and provenance rules.

## Implementation sequence

The implementation is intentionally split so an ABAC regression cannot hide in
a large customer-tree change:

1. Add the lookup values and nullable affiliation column with a migration and
   update provisioning paths to write an explicit value.
2. Add an API integration test with own, granted, unclassified, visible
   organization-mention, and private-post cases. Assert that private evidence
   never adds a node and unresolved names remain hints.
3. Add the API contract and frontend filter/tree tests, then implement the
   query projection and UI facets.
4. Backfill only from an authoritative account-scope source. Until that source
   exists, retain `scope_unclassified`; do not infer it from the corpus.

## Consequences

- The tree can become useful without weakening ABAC: observed nodes are bounded
  by visible evidence and do not authorize unrelated reads.
- Existing deployments will initially show an explicit unknown scope instead of
  a misleading own/customer label. This is preferable to a silent false fact.
- `account_affiliation` remains a normalized authorization relation; the facet
  is an attribute of that relation, not a second account-to-entity authority
  table. A later need for time-bounded grants requires a separate ADR rather
  than overloading this column.
- The entity query needs an entity-first index on persisted organization
  mentions if live corpus size requires it. Add that index with the same
  migration after measuring the query plan; do not pre-emptively shard a small
  table.

## Related decisions

- [ADR 0004](0004-knowledge-graph-ontology.md) — ontology and semantic layer.
- [ADR 0010](0010-corporate-hierarchy-auto-creation.md) — verified counterparty
  hierarchy creation.
- [ADR 0041](0041-source-context-vs-authorization-scope.md) — source context
  must not be confused with authorization scope.
- [ADR 0042](0042-source-hints-before-customer-binding.md) — unresolved source
  customer values remain hints.
- [ADR 0052](0052-plain-orchestrator-semantic-evidence.md) — semantic evidence
  must retain provenance and uncertainty.

## References (APA 7th)

Hu, V. C., Ferraiolo, D., Kuhn, R., Schnitzer, A., Sandlin, K., Miller, R., &
  Scarfone, K. (2019). *Guide to attribute based access control (ABAC)
  definition and considerations* (NIST Special Publication 800-162, updated
  2019). National Institute of Standards and Technology.
  https://doi.org/10.6028/NIST.SP.800-162

Rose, S., Borchert, O., Mitchell, S., & Connelly, S. (2020). *Zero trust
  architecture* (NIST Special Publication 800-207). National Institute of
  Standards and Technology. https://doi.org/10.6028/NIST.SP.800-207

World Wide Web Consortium. (2009). *SKOS simple knowledge organization system
  reference*. https://www.w3.org/TR/skos-reference/
