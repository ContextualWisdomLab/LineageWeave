# ADR 0117: Catalog-backed source semantic hints

- Status: Accepted
- Date: 2026-08-20
- Figma: N/A; this is a prompt/data-boundary decision with no new buyer UI.
- Depends on: [0080](0080-semantic-backfill-for-missing-project-fields.md), [0084](0084-lineage-research-grounding.md)

## Context

Imported posts often contain source-system codes but omit the corresponding
display names. A project, process unit, company, customer, or author-side
context can therefore be present in the source record while remaining opaque
to semantic extraction. The shared corporate-entity scope may also contain
synthetic seed rows, so account affiliations and display-name joins cannot be
treated as facts about the imported author.

## Decision

1. Resolve `source_company_code` and `source_customer_code` against
   `corporate_entity.corporate_entity_code`, and resolve
   `source_process_unit_code` against `process_unit.process_unit_code`.
2. Pass the resulting display names to contextual-orchestrator as explicitly
   labeled catalog lookup hints. A lookup name is evidence about the source
   code, not a bound entity, customer identity, author affiliation, or project
   fact.
3. If a source code has no catalog match, retain the code and emit no invented
   name. Generic customer values such as `other` and `unregistered` remain
   weak hints under ADR 0080.
4. Use the same hint contract for buyer post operations and bounded operator
   summary backfills. Do not reintroduce account-affiliation joins as the
   imported author's organization.

## Consequences

Semantic extraction can use authoritative catalog labels when source codes are
otherwise opaque, improving project, PU, company, customer, and Keyman
interpretation. The labels remain auditable and non-binding, and a missing
catalog row fails closed to the source code instead of creating a false
identity.
