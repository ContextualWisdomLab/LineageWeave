# ADR 0119 — Corroborated SKOS companion labels appear on organization chips

**Decision status:** Accepted
**Date:** 2026-08-23

## Context

[ADR 0008](0008-organization-abbreviation-resolution.md) already persists a
search-corroborated `skos:altLabel` / `skos:prefLabel` pair (Miles &
Bechhofer, 2009) in `organization_name_resolution`. Catalog matching still
compares mentions to `corporate_entity.entity_name`, so a chip that only
prints that name hides the short form the source used. After seed, a buyer
who reads "DC" in a post cannot see that the Demo Corp chip is the same
organization.

Catalog creation and mention-to-catalog resolution remain a separate stack.
This record only decides the buyer-visible caption, but that caption must be
bound to the catalog id already carried by the chip. A display-name match alone
cannot prove identity because `corporate_entity.entity_name` is not unique.

## Decision

1. Load every `verify_corroborated` pair as `OrganizationNameAlias`, bound to a
   target `corporate_entity_id` only when exactly one current catalog row has
   either stored label. Pending and uncorroborated rows stay out.
2. Attach the other label as `organization_alias` only when the pair's target
   id equals the catalog id already stored on the displayed record. An unbound
   record, catalog tie, id mismatch, name miss, identical labels, or two
   distinct companions stays unlabeled. The product never invents an
   abbreviation from letters.
3. Render the chip as `Demo Corp (DC)` when a companion is present, otherwise
   the catalog name. Affiliate-org, Keyman-affiliation, and counterparty-org
   chips reuse the existing accessible-name keys with that caption.
   Related corporate nodes use the companion in place of the ontology class
   caption when one is present, and keep the ontology caption otherwise.
4. Seed the synthetic pair `DC` / `Demo Corp` as `verify_corroborated` so the
   walk is clickable after `make seed`. Real organization names must not
   appear in fixtures.

## Consequences

- The raw/canonical mapping remains in `organization_name_resolution` (3NF).
  Chips project the companion at read time; they do not duplicate it onto
  affiliation or counterparty rows, and a same-named catalog row cannot borrow
  another row's alias.
- Default frontend tests stay on unlabeled names. A stub option supplies the
  companion so the parenthetical is covered without changing the unlabeled
  walk.
- Fail-closed on a tie matches ADR 0026's "do not guess" discipline for
  organization identity.

## Related

Extends [ADR 0008](0008-organization-abbreviation-resolution.md). Complements
[ADR 0002](0002-figma-access-boundary.md) chip presentation. Does not change
catalog create/lock policy in [ADR 0012](0012-corporate-entity-creation-lock.md)
or [ADR 0026](0026-tied-organization-similarity.md).

## References (APA 7th)

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/
