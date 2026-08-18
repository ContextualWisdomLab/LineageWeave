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

## Consequences

The customer master can show useful source evidence immediately without
inventing a customer binding. A later resolver must preserve the raw hint,
resolution status, catalog id, and supporting post evidence.
