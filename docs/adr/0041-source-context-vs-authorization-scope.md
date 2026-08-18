# ADR 0041: Separate source context from authorization scope

- Status: Accepted
- Date: 2026-08-18

## Context

The local authorization fixture can assign every imported row to one demo
account, company, and authorization business unit. That assignment is useful for exercising
OIDC/RBAC/ABAC, but it is not evidence that the source author, company,
customer, sales pool, or project is the demo value. Treating it as source truth
made real records appear to belong to the demo identity.

## Decision

- Preserve caller-mapped raw source context separately from the authenticated
  account and authorization scope: author code/name, company code, business
  unit (PU), sales pool, customer code, and project code.
- Treat `ZCRHT811.VOCCTS` (`voccts_field`) as the source post body when that
  column is available. A missing body remains missing; do not summarize a
  title-only row.
- Treat `pucode_field` and `voc_pucode` as PU/business-unit evidence. They are
  not sales-pool evidence. Populate `source_sales_pool_code` only from an
  explicitly mapped authoritative sales-pool column; otherwise keep it null.
- Feed those raw values to semantic hints with explicit provenance and keep
  unresolved customer/project codes as weak hints.
- Display raw source context in the authorized post detail without replacing
  the ABAC scope or creating catalog identities from a code alone.
- Resolve names, Keymen, projects, and customers only through their existing
  catalog/ontology evidence or an authoritative source lookup.

## Consequences

The product no longer presents a demo authorization identity as the source
author or customer. A local demo can still exercise access control, while a
real deployment can populate source context from its mapped export without
shipping real records in this repository.
