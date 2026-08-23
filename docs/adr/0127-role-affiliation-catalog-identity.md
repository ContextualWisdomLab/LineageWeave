# ADR 0127: R&R affiliations become separate catalog-backed organization evidence

- Status: Accepted
- Date: 2026-08-21

## Context

R&R already preserved a person's or team's extracted
`affiliated_organization_name`, but only an organization actor could receive
the `post_summary_role` corporate-entity identity. A person such as a member
of a named company therefore remained free text, so the company could not
enter the post-scoped organization mention or Knowledge Graph projection.

The same extraction also allowed a generic label such as `사업부` to become a
cataloged team without a named unit or affiliation. That is not an ontology
identity: a source process-unit code/name is source context and must not be
silently promoted into a team actor.

## Decision

- Add `cataloged_affiliated_corporate_entity_id` to `post_summary_role`.
  It is separate from the actor's own catalog identity, so a person/team can
  retain its own identity and its organization affiliation at the same time.
- Resolve an extracted R&R affiliation through the existing organization
  name-resolution, hierarchy, and verification clients. Preserve the raw
  extracted name; only a unique or verified catalog result receives the FK.
  A miss, tie, or unavailable enrichment channel remains visibly unresolved.
- Write every resolved R&R affiliation to `post_organization_mention` so the
  existing Knowledge Graph edge projection can expose the organization.
- Do not catalog generic team labels (`사업부`, `부서`, `팀`, `business unit`,
  `department`, or `division`) without a specific named unit. Keep the source
  process-unit code/name as separately labeled source evidence.
- Increase the summary contract version so existing summaries are regenerated
  under the corrected extraction contract.

## Consequences

The popup can make a resolved affiliation clickable while still showing the
wording extracted from the source. It can also explain that an unnamed
business-unit label is not a resolved organization or team. Existing rows are
not guessed during migration; they receive the new identity when their
summary is regenerated with source evidence.

## Related

Extends ADR 0006, ADR 0009, ADR 0010, and ADR 0019. Source process-unit
display remains subject to ADR 0051: it is a hint, not a catalog binding.
