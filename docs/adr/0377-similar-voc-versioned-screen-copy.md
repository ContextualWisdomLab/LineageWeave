# ADR 0377: Govern Similar VOC screen copy as an owned versioned draft

- Status: Proposed
- Date: 2026-09-24
- Owners: LineageWeave product composition / presentation read model
- Extends: ADR 0362
- Related: #929, #1126, migration 0249

## Problem

The Similar VOC repair lane adds buyer-visible retry, loading, empty, evidence-label, and recovery copy. Keeping those strings in `SimilarVocPanel` would preserve a second static frontend translation authority and would leave the required `ko/en/ja/zh/vi/es/de/fr` contract unverifiable. ADR 0362 already makes PostgreSQL authoritative for LineageWeave-owned UI copy, but its first one-time seed lifecycle was implemented specifically for Customer Master v1. A second review candidate must not copy that lifecycle ad hoc, overwrite reviewed draft text on startup replay, adopt a pre-existing operator-owned resource, or resurrect historical seed bytes after deliberate product deletion.

This ADR does not move ontology labels, VOC semantic truth, similarity adjudication, or authorization scope into the translation ledger. It governs product presentation copy only.

## Constraints

- The screen aggregate identity is `lineageweave/similar-voc/v1`.
- Candidate copy covers the full Similar VOC presentation surface needed by the current panel, including retry and recovery text introduced by #1126.
- Every required key has exactly the eight ADR-0362 locales: `ko`, `en`, `ja`, `zh`, `vi`, `es`, `de`, `fr`.
- The migration produces a `draft`. It must not publish or claim language/product approval.
- Seed replay after first materialization is a no-op. Review edits are product data and historical migration bytes must not overwrite them.
- A resource that existed before the seed reservation is operator-owned and cannot be adopted implicitly.
- Ordinary deletion of an exactly owned candidate retires the one-time seed receipt so startup cannot resurrect it.
- Explicit rollback may delete only the exact owned unpublished draft. Published versions remain immutable under ADR 0362.
- Seed ownership must be reusable for future LineageWeave screen-copy candidates rather than adding another Customer-Master-specific trigger family.
- Similar VOC consumer cutover remains in its existing source-owner lane; this owner PR must not become a second writer for `SimilarVocPanel`.

## Alternatives considered

### Keep the new Korean strings in the component and translate only later

Rejected. The component would remain a source of product copy, exact eight-locale evidence could not be bound to a screen version, and the known #1126 delivery-gate failure would simply be deferred.

### Add a static eight-locale dictionary beside `SimilarVocPanel`

Rejected. That would duplicate ADR 0362's PostgreSQL authority and make deployment artifacts authoritative again.

### Reuse the Customer Master resource

Rejected. `customer-master` and `similar-voc` are separate screen aggregates with different required keys, review lifecycles, and buyer evidence. Sharing one resource would couple unrelated releases and violate aggregate boundaries.

### Copy the Customer-Master-specific ownership triggers for Similar VOC

Rejected. A second screen-specific trigger family would encode the same lifecycle twice and make later seed safety fixes diverge. The ownership table is already generic; trigger enforcement is generalized instead.

### Re-run the seed on every startup and upsert its values

Rejected. Once a draft exists, reviewers own its copy. An upsert replay would silently restore historical migration text over reviewed product data. After first exact-owned materialization, replay must not mutate keys or text.

## Decision

Migration `0249_ui_translation_seed_ownership_generic.sql` replaces the active Customer-Master-specific ownership trigger wiring with generic trigger functions over `ui_translation_seed_ownership`. The lifecycle is selected by the ownership row's `(migration_key, product_key, screen_key, resource_version)` identity and the trusted `lineageweave.migration_file` execution context.

A `pending` ownership row reserves an otherwise-empty screen identity for its seed. The forward seed may create that root and an `AFTER INSERT` binder records the exact `resource_id` as `owned`. Child writes performed by the seed are accepted only after that binding. A pre-existing resource causes `blocked` state and the forward seed fails closed without touching it.

Ordinary deletion of an exact `owned` candidate first changes the receipt to `retired` and clears `resource_id`; the root can then be deleted without `ON DELETE CASCADE` erasing the one-time completion evidence. Forward replay in `owned` or `retired` state does not restore seed text. Explicit rollback is distinguished by `rollback/<migration_key>.sql`; it may delete the exact owned draft without retiring it, allowing the ownership row to cascade away so a later intentional forward migration can seed a fresh review candidate.

Migration `0249_z_similar_voc_translation_draft.sql` reserves no semantic authority. It creates 23 presentation keys × 8 locales only when ownership is `pending`, verifies the exact 184-row matrix, and then stops. Publication remains a separate one-way ADR-0362 transition after independent language/product review and unchanged-head consumer acceptance.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: `lineageweave/similar-voc/v1` translation resource.
- Value identities: translation key and locale-tagged presentation copy.
- Repository: PostgreSQL translation ledger; Valkey remains an optional read cache under ADR 0362.
- Domain service: one-time candidate-seed ownership lifecycle.
- Invariants: no implicit adoption, no reviewed-copy replay overwrite, no post-retirement resurrection, rollback limited to exact owned draft, eight-locale completeness before any publication, ontology labels excluded.
- ACL: #1126 consumes only a released/published screen-copy contract; similarity adjudication and authorization continue to come from their existing owners.

## Recovery and rollout

If the Similar VOC draft is wrong before publication, reviewers may edit it in place or explicitly run `rollback/0249_z_similar_voc_translation_draft.sql` and re-run the forward candidate. Ordinary product deletion means retirement, not authorization for historical reseeding. If a conflicting pre-existing `lineageweave/similar-voc/v1` resource exists, the migration stays blocked until an operator resolves that product decision; it never deletes or adopts the conflicting resource.

A published bad version is not down-migrated. ADR 0362 requires a new immutable resource version and consumer routing to that reviewed version.

## Evidence

- RED `c5339b820eaf2af3fe169bbb3d14d5364d0bea72` requires a complete eight-locale Similar VOC candidate, replay preservation of reviewed copy, unowned-resource refusal, retirement without resurrection, and exact-owned-draft rollback/reseed behavior on real PostgreSQL.
- Generic ownership repair `5448d8d24caa07110152f8fa1e5e5c52044ae60f` moves active seed lifecycle enforcement from Customer-Master-specific trigger wiring to the ownership aggregate and reserves `lineageweave/similar-voc/v1`.
- Candidate seed `d5f574f6e9eb04afab86c9bb9aee8acf93fb4375` adds the 23×8 review matrix and makes `owned|retired` replay purpose-complete without rewriting reviewed data.
- Rollback repair `eaaf7397fcb6db32afea599b6c17fc981bc6c9bd` limits destructive rollback to the exact owned unpublished Similar VOC resource.

These commits are source-level evidence only until exact-head PostgreSQL and hosted validation run. No publication, translation approval, consumer acceptance, merge, or release is implied by this ADR.
