# ADR 0051: Preserve explicit source names as weak hints

- Status: Accepted
- Date: 2026-08-19

## Context

Some source exports provide a project, sales-pool, or customer name while
their normalized code is missing, opaque, or set to a sentinel such as
`기타` or `미등록고객`. Dropping the name prevents Ontology/Semantics from
using an explicit clue; binding it directly would turn source text into an
unverified catalog identity.

## Decision

- Preserve caller-mapped `source_project_name`, `source_sales_pool_name`,
  `source_customer_name`, `source_company_name`, and
  `source_process_unit_name` beside their raw code fields on `source_post`.
- Include names in authorized detail, board search, customer evidence, Ask
  source facts, and contextual-orchestrator semantic hints with column-level
  provenance. `source_process_unit_name` is explicitly a PU/business-unit
  hint and is never treated as a sales-pool name.
- The semantic extraction prompt must preserve the same distinction in both
  directions: source PU fields cannot fill a sales-pool value, and source
  sales-pool fields cannot fill a PU value.
- Keep every name hint non-binding. `기타`, `미등록`, `unknown`, and equivalent
  customer names remain low-trust hints and never create or bind a catalog row.
- The importer accepts explicit column mappings only; it never guesses a name
  from a PU, sales-pool, customer, or project code.

## Consequences

The product can use an explicitly written name when a code is absent while
retaining authorization scope, raw source evidence, and catalog resolution as
separate concerns. Existing rows and synthetic fixtures remain valid because
the new fields are nullable.
