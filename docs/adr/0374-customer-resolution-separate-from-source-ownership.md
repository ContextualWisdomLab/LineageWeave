# ADR 0374: Separate Customer Resolution from Source Ownership

## Status

Proposed

## Context

Accepted ADR 0042 treats `source_customer_code` as raw evidence and requires a later corroborated customer catalog identity to be persisted separately. Protected main instead samples all `source_post` rows sharing a hint code and, after corroboration, rewrites `source_post.corporate_entity_id` to the resolved customer entity. That field is also an authorization boundary, so the implementation conflates customer identity with tenant ownership and can admit foreign evidence when a caller knows another tenant's hint code.

The resolver also holds an acquired database connection while the contextual-orchestrator and public verification calls run. Those calls can take materially longer than a database mutation and must not pin a scarce database resource or lock authorization state while waiting on an external system.

## Decision

1. `source_post.corporate_entity_id` and `source_post.process_unit_id` remain authorization ownership and are never rewritten by customer-hint resolution.
2. Corroborated identity is stored in `source_post_customer_resolution`, keyed by `post_id`. The row retains the raw hint observed at corroboration time, the resolved catalog `corporate_entity_id`, resolved name, verification status/evidence URL, and resolution timestamp.
3. Evidence capture receives the authenticated caller's corporate/process scope explicitly and may load title/body only for source posts that pass the shared source-post visibility and eligibility boundary.
4. The capture phase returns an immutable set of source-post identities and evidence, then releases the database connection before contextual-orchestrator/search verification runs.
5. Persistence reacquires a connection and a short transaction, locks only the captured source rows with `FOR SHARE`, re-runs visibility/eligibility for the same caller scope and hint, and fails closed unless the exact captured identity set is still eligible. No external call occurs inside this transaction.
6. Resolution persistence is idempotent with `INSERT ... ON CONFLICT (post_id) DO UPDATE`; a retry may refresh corroboration metadata but cannot change source-post authorization ownership.
7. Customer Master read projections expose normalized resolution identity from the association. Authorization continues to be decided from the source post and authenticated account scope, never from the resolved customer entity.
8. Creating or reusing a `corporate_entity` as a customer catalog identity does not grant the caller administration of that entity and does not alter which source evidence the caller may read.

## Alternatives rejected

- **Add a tenant predicate to the existing UPDATE.** This still uses the authorization field as customer identity and violates ADR 0042.
- **Hold row locks across external verification.** This preserves stale authorization state at the cost of long-lived locks/connections and can block unrelated writes.
- **Copy Keyverse or cross-service identity state into LineageWeave.** Authentication/identity authority remains with Keyverse; LineageWeave consumes the admitted account scope only.
- **Use the resolved customer entity as the source-post tenant.** Customer identity and evidence ownership are different domain concepts and may legitimately differ.

## Consequences

The resolver becomes a two-phase capture/verify/revalidate flow. A concurrent ownership, visibility, deletion, draft-state, process-unit, or hint change causes the resolution attempt to fail closed and be retried against fresh evidence. Existing raw hints remain visible as evidence even when corroboration is absent. The association can be deleted with its source post and does not create an independent disclosure path.

Promotion requires PostgreSQL migration/rollback replay, cross-tenant API regressions, exact-head repository/security/SAST/CodeQL/Strix/model-review evidence, independent current-head approval, and protected integration. Until then this ADR remains Proposed.
