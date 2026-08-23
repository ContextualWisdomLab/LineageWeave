# ADR 0131: Explicit organization-to-project semantic relations

## Status

Accepted

## Decision

The semantic relationship contract may persist an organization-to-project
`lw_supports` or `lw_responsible_for` relation only when the source
explicitly assigns that organization work, ownership, contracting, or
support for the named project. `lw_supports` (`:supports`) and
`lw_responsible_for` (`:responsibleFor`) are both LineageWeave profile
properties with `prov:Agent` domain and `prov:Entity` range. Neither is a
PROV alias, and neither creates an inferred inverse, ownership, or causal
edge. `lw_supports` is the general support/contribution relation;
`lw_responsible_for` is the stronger primary-responsibility relation (for
example, the prime contractor on a named project).

Explicit organization membership uses W3C Organization Vocabulary
`org_member_of` (`org:memberOf`). A project mention, affiliation, or shared
meeting does not create either relation. Unresolved names remain text in the
qualified semantic table and its evidence-bearing navigation projection.

## Consequences

- A post can show distinct organization-to-project responsibilities instead
  of collapsing every organization under one project label.
- The graph remains a navigation projection; evidence and confidence stay in
  `post_summary_semantic_relationship`.
- Attendance-only actors remain event clues, not role/responsibility rows.
