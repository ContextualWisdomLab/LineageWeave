# ADR 0374: Separate Customer Resolution from Source Ownership

## Status

Proposed

## Context

Accepted ADR 0042 treats `source_customer_code` as raw evidence and requires a later corroborated customer catalog identity to be persisted separately. Protected main instead samples all `source_post` rows sharing a hint code and, after corroboration, rewrites `source_post.corporate_entity_id` to the resolved customer entity. That field is also an authorization boundary, so the implementation conflates customer identity with tenant ownership and can admit foreign evidence when a caller knows another tenant's hint code.

The resolver also holds an acquired database connection while the contextual-orchestrator and public verification calls run. Those calls can take materially longer than a database mutation and must not pin source authorization state or locks while waiting on an external system.

A second defect was found while repairing this boundary: Customer Master had introduced its own `lower(entity_name)` lookup plus direct `corporate_entity` insert. Accepted ADR 0010 explicitly makes `backend.app.corporate_entity_ingestion.get_or_create_corporate_entity` the shared corporate-catalog creation policy, with ADR 0012 concurrency control and ADR 0160 corroborated alias binding. Customer Master must not create a third name-only identity algorithm or silently force every new customer to `company` level.

## Decision

1. `source_post.corporate_entity_id` and `source_post.process_unit_id` remain authorization ownership and are never rewritten by customer-hint resolution.
2. Corroborated identity is stored in `source_post_customer_resolution`, keyed by `post_id`. The row retains the raw hint observed at corroboration time, the resolved catalog `corporate_entity_id`, resolved name, verification status/evidence URL, and resolution timestamp.
3. Evidence capture receives the authenticated caller's corporate/process scope explicitly and may load title/body only for source posts that pass the shared source-post visibility and eligibility boundary.
4. The capture phase returns an immutable set of source-post identities and evidence, then releases the source-evidence database connection before contextual-orchestrator/search verification runs.
5. Customer-name corroboration never performs catalog persistence. Once a name is corroborated, Customer Master delegates corporate catalog binding to `get_or_create_corporate_entity`, which owns similarity/tie handling, corroborated SKOS aliases, hierarchy inference, catalog creation, and ADR 0012's advisory-lock discipline. Customer Master must not query `corporate_entity` by display name or insert its own catalog row.
6. Catalog binding occurs before source rows are locked. The canonical owner may use a database connection while resolving the catalog, but its ADR 0012 transaction/advisory lock is acquired only after its external inference/verification has completed; Customer Master never holds source authorization locks across that network work.
7. Association persistence reacquires a connection and a short transaction, locks only the captured source rows with `FOR SHARE`, re-runs visibility/eligibility for the same caller scope and hint, and fails closed unless the exact captured identity set is still eligible. No external call occurs inside this transaction.
8. Resolution persistence is idempotent with `INSERT ... ON CONFLICT (post_id) DO UPDATE`; a retry may refresh corroboration metadata but cannot change source-post authorization ownership.
9. Customer Master read projections expose normalized resolution identity from the association. Authorization continues to be decided from the source post and authenticated account scope, never from the resolved customer entity.
10. Creating or reusing a `corporate_entity` as a customer catalog identity does not grant the caller administration of that entity and does not alter which source evidence the caller may read.

## Alternatives rejected

- **Add a tenant predicate to the existing UPDATE.** This still uses the authorization field as customer identity and violates ADR 0042.
- **Hold row locks across external verification.** This preserves stale authorization state at the cost of long-lived locks/connections and can block unrelated writes.
- **Look up or create `corporate_entity` locally by display name.** Display names are not unique catalog identifiers, the path bypasses tied-candidate/alias handling, and direct insertion duplicates the accepted ADR 0010/0012/0160 owner.
- **Copy Keyverse or cross-service identity state into LineageWeave.** Authentication/identity authority remains with Keyverse; LineageWeave consumes the admitted account scope only.
- **Use the resolved customer entity as the source-post tenant.** Customer identity and evidence ownership are different domain concepts and may legitimately differ.

## Consequences

The resolver becomes a capture -> customer-name corroboration -> canonical catalog binding -> source revalidation/persistence flow. A concurrent ownership, visibility, deletion, draft-state, process-unit, or hint change causes association persistence to fail closed and be retried against fresh evidence. Existing raw hints remain visible as evidence even when corroboration is absent. The association can be deleted with its source post and does not create an independent disclosure path. Corporate catalog identity semantics remain centralized under ADR 0010/0012/0160 rather than drifting inside Customer Master.

Promotion requires PostgreSQL migration/rollback replay, cross-tenant API regressions, canonical-catalog delegation regression, exact-head repository/security/SAST/CodeQL/Strix/model-review evidence, independent current-head approval, and protected integration. Until then this ADR remains Proposed.
