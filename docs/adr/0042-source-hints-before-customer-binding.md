# ADR 0042: Source Hints Before Customer Binding

## Status

Accepted

## Context

The imported post row has source customer and author fields, but those fields
are evidence, not proof that the row belongs to a cataloged customer entity.
An import can also carry a synthetic authorization scope from a demo seed.
Showing that scope as the customer master makes a real source corpus appear to
belong to a fictional organization.

## Decision

- Keep `source_customer_code`, `source_author_code`, and
  `source_author_name` as raw source evidence with explicit provenance.
- Expose bounded customer-code and author-code aggregates as `hint_only`; do
  not create or bind a `corporate_entity` from those fields alone.
- Hide synthetic `DEMO-*` catalog rows when source evidence is present in the
  customer-master response. The authorization scope remains an internal
  access decision, not a customer name shown to the buyer.
- Resolve a customer or Keyman only after ontology and semantic evidence, with
  the resulting catalog id and provenance persisted separately.
- Keep `기타` and unregistered customer values unresolved until corroborating
  evidence exists.
- Include only ABAC-visible source-post references in each customer hint so a
  buyer can open the original post, read its body, and inspect semantic
  evidence without turning the hint into a customer binding.

## Authorization clarification (2026-10-03)

Source corporate/process columns remain ownership, never resolved customer identity.
Customer hint resolution captures only caller-visible eligible evidence, releases
its source connection before corroboration, delegates catalog identity to the
ADR 0010/0012 owner, and revalidates the exact source set under short share locks
before persisting the separate association (Proposed ADR 0374). Relationship
aggregates use the same corporate/process predicate. Explicit empty process scope
retains authenticated unrestricted semantics; omitted scope admits public evidence
only, never private evidence.

## Consequences

The customer master can show useful source evidence immediately without
inventing a customer binding. A later resolver must preserve the raw hint,
resolution status, catalog id, and supporting post evidence.
