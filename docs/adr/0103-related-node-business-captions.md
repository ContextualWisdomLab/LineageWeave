# ADR 0103: Related-node chips use business context, not ontology class

- Status: Accepted
- Date: 2026-08-20

## Context

The related-node walk is a buyer decision surface. Showing only `Person`,
`Organization`, or `Post` does not identify the next useful action. A person
may have several memberships, and `person_affiliation` has no primary marker;
choosing the first sorted row would invent a primary organization.

## Decision

- Use the authorized side label and a unique organization only when one
  identity remains after catalog-id and case-folded alias reconciliation.
- Mark more than one identity as `affiliation_ambiguous` and render
  `multiple organizations`; never expose a guessed primary.
- Use the cataloged entity level for organization chips and the source title
  only for post chips.
- Keep the full affiliation list on the Keyman surface. The related panel
  tells the buyer to read that list, or extract Keymen first, before clicking
  the chip to continue the walk.
- Reuse `RelatedNodeChip` and `--related-node-*` design tokens for every
  repeated walk control. Visible captions are included in accessible names.

## Consequences

The compact walk remains scannable while retaining multiple-membership truth.
An unavailable or unresolved affiliation remains unavailable; it is never
converted into a plausible-sounding company name. Temporal membership
intervals remain a follow-up schema decision and are not inferred here.

## References

See [RELATED_NODE_AFFILIATION_REFERENCES.md](../doctoring/RELATED_NODE_AFFILIATION_REFERENCES.md).
