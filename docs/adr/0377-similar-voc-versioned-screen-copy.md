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
- Rollback provenance must resolve the ownership record by product/screen/version identity as well as resource id. `blocked` and `pending` reservations intentionally have `resource_id = NULL`; that must never let a rollback-labelled session delete the operator resource that caused the block.
- Rollback-labelled child mutation is narrower still: only `DELETE` against the exact `owned` resource is admissible. A blocked/pending operator draft must not become mutable merely because the session carries the seed rollback migration key, and rollback must not gain insert/update authority over reviewed child copy.
- Child `UPDATE` provenance must consider the source resource before the target resource. Changing `resource_id` must not make the governing ownership row disappear from the trigger lookup and thereby turn a rollback-labelled update into an ungoverned move.
- The generic ownership migration itself has a bounded rollback: it may be removed only after Similar VOC v1 and every non-Customer-Master generic owner are gone, and it must restore the pre-existing Customer Master trigger lane rather than dropping that owner boundary.
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

### Resolve rollback ownership by `resource_id` only

Rejected. That works for `owned` rows but fails exactly where destructive authority matters most: `blocked` and `pending` rows carry no `resource_id`. A rollback-labelled session could otherwise bypass the ownership boundary and delete a same-identity operator resource. The resource's immutable product/screen/version tuple is therefore the lookup key; destructive rollback still requires exact `owned` state and exact `resource_id` equality.

### Treat the rollback migration key as blanket child-write authority

Rejected. The rollback file exists to remove an exact owned draft, not to edit review data or touch a blocked operator resource. Child writes therefore remain provenance-bound: forward seed writes require exact owned resource binding, while rollback provenance permits only delete operations on that same exact owned resource.

### Validate only the target `resource_id` on child UPDATE

Rejected. `UPDATE` has both a source and target identity. Looking up only `NEW.resource_id` lets a rollback-labelled statement move a child out of a blocked or owned resource into an unrelated resource with no seed-ownership row; the trigger then sees no owner and returns early. The source identity must be checked before any target lookup whenever the resource changes.

## Decision

Migration `0249_ui_translation_seed_ownership_generic.sql` replaces the active Customer-Master-specific ownership trigger wiring with generic trigger functions over `ui_translation_seed_ownership`. The lifecycle is selected by the ownership row's `(migration_key, product_key, screen_key, resource_version)` identity and the trusted `lineageweave.migration_file` execution context.

A `pending` ownership row reserves an otherwise-empty screen identity for its seed. The forward seed may create that root and an `AFTER INSERT` binder records the exact `resource_id` as `owned`. Child writes performed by the seed are accepted only after that binding. A pre-existing resource causes `blocked` state and the forward seed fails closed without touching it.

Ordinary deletion of an exact `owned` candidate first changes the receipt to `retired` and clears `resource_id`; the root can then be deleted without `ON DELETE CASCADE` erasing the one-time completion evidence. Forward replay in `owned` or `retired` state does not restore seed text. Explicit rollback is distinguished by `rollback/<migration_key>.sql`; the generic root guard first resolves the ownership row by the root's immutable product/screen/version identity, then allows deletion only for exact `owned` state with the same `resource_id`. The child guard applies the same exact ownership check and additionally rejects rollback-labelled `INSERT` or `UPDATE`, so rollback provenance cannot mutate blocked operator child rows or rewrite reviewed copy. Cascading child deletes from the exact owned root remain admissible. The exact owned draft can therefore be removed without retiring it, allowing the ownership row to cascade away so a later intentional forward migration can seed a fresh review candidate.

Migration `0249_ui_translation_seed_ownership_generic_b.sql` hardens the child guard before any Similar VOC seed write can run. Sorted migration replay installs the generic owner first, then this companion hardening, then `0249_z_similar_voc_translation_draft.sql`. For `UPDATE` statements that change `resource_id`, the guard resolves the source resource first. If the current migration context is the matching forward or rollback seed, moving the child out of that governed resource is rejected before a target-resource lookup can erase the provenance signal. The ordinary product lifecycle remains outside migration provenance when no matching seed context is active. The existing generic rollback remains sufficient recovery because it drops the active generic child-guard function after all dependent generic owners are gone.

Migration `0249_z_similar_voc_translation_draft.sql` reserves no semantic authority. It creates 23 presentation keys × 8 locales only when ownership is `pending`, verifies the exact 184-row matrix, and then stops. Publication remains a separate one-way ADR-0362 transition after independent language/product review and unchanged-head consumer acceptance.

`rollback/0249_ui_translation_seed_ownership_generic.sql` is deliberately narrower than the forward migration. It refuses while Similar VOC v1 exists or while any non-Customer-Master generic seed owner remains. Once those dependents are absent, it removes only the generic trigger/functions and restores the already-existing Customer Master ownership trigger functions from migration 0247. It does not remove the ownership table or Customer Master provenance.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: `lineageweave/similar-voc/v1` translation resource.
- Value identities: translation key and locale-tagged presentation copy.
- Repository: PostgreSQL translation ledger; Valkey remains an optional read cache under ADR 0362.
- Domain service: one-time candidate-seed ownership lifecycle.
- Invariants: no implicit adoption, no reviewed-copy replay overwrite, no post-retirement resurrection, rollback limited to exact owned draft, blocked/pending roots and child rows outside rollback authority, rollback child mutation limited to exact-owned deletion, child resource moves cannot escape provenance by changing identity first, eight-locale completeness before any publication, ontology labels excluded.
- ACL: #1126 consumes only a released/published screen-copy contract; similarity adjudication and authorization continue to come from their existing owners.

## Recovery and rollout

If the Similar VOC draft is wrong before publication, reviewers may edit it in place or explicitly run `rollback/0249_z_similar_voc_translation_draft.sql` and re-run the forward candidate. Ordinary product deletion means retirement, not authorization for historical reseeding. If a conflicting pre-existing `lineageweave/similar-voc/v1` resource exists, the migration stays blocked until an operator resolves that product decision; it never deletes or adopts the conflicting resource.

To remove the generic ownership layer itself, first remove the exact Similar VOC draft through its owned rollback (or otherwise resolve the product resource) and ensure no other generic seed owner remains. Then run `rollback/0249_ui_translation_seed_ownership_generic.sql`; Customer Master ownership remains active through its original 0247 functions/triggers. The companion child-update hardening needs no separate destructive rollback because the generic rollback drops the function it replaces as part of the same bounded owner-layer removal.

A published bad version is not down-migrated. ADR 0362 requires a new immutable resource version and consumer routing to that reviewed version.

## Evidence

- RED `c5339b820eaf2af3fe169bbb3d14d5364d0bea72` requires a complete eight-locale Similar VOC candidate, replay preservation of reviewed copy, unowned-resource refusal, retirement without resurrection, and exact-owned-draft rollback/reseed behavior on real PostgreSQL.
- Generic ownership repair `5448d8d24caa07110152f8fa1e5e5c52044ae60f` moves active seed lifecycle enforcement from Customer-Master-specific trigger wiring to the ownership aggregate and reserves `lineageweave/similar-voc/v1`.
- Candidate seed `d5f574f6e9eb04afab86c9bb9aee8acf93fb4375` adds the 23×8 review matrix and makes `owned|retired` replay purpose-complete without rewriting reviewed data.
- Draft rollback `eaaf7397fcb6db32afea599b6c17fc981bc6c9bd` limits destructive Similar VOC rollback to the exact owned unpublished resource.
- Rollback-provenance RED `f0e79fd233e01fc512d146b9e544aa9a2780efc6` found that a `resource_id`-only DELETE lookup did not see blocked ownership rows and could therefore let rollback provenance delete the operator-owned conflicting root.
- Causal rollback-provenance repair `2e673c1e00b8a19dbe526cd623e81d7ec3769e59` resolves DELETE ownership by immutable product/screen/version identity and still requires exact owned-resource equality before destructive rollback.
- Generic-migration recovery RED `27e8d53a549c34369f41f6365c99146e24cf0c72` requires rollback of the generalized trigger layer to leave the original Customer Master ownership lane executable.
- Generic-migration rollback `057eb6ed65cb80fdee40a391bc0727a0a4b925d4` refuses while dependent generic owners remain, restores the Customer Master trigger wiring, and removes only the generic trigger/functions.
- Child rollback-provenance RED `73c7397ecd7e49439662b07516d087505a769d16` proves that a blocked operator draft's child key was still directly deletable when the session carried the Similar VOC rollback migration key.
- Causal child-rollback repair `dde6ea349cdf244e1c2dd754d600c041db2f8b6f` restricts rollback-labelled child mutation to `DELETE` on the exact `owned` resource while preserving the normal exact-owned cascading rollback path.
- Child resource-move RED `eaf25d0630faa81c9e6509fe80d48c57b394395d` proves that `UPDATE ... SET resource_id = ...` could otherwise move a blocked operator child to an unrelated unowned resource because the predecessor guard looked up only `NEW.resource_id`.
- Causal source-provenance repair `cf14dc8197bc820204784e423418b76362d4d7e3` installs a source-first child-update guard before the Similar VOC seed; test wiring `6137835740da198984f6e32d2cb49712d0bf9269` exercises that hardened migration and ordering contract `86c6863da2a3609b8c5a73ce7f5b263867e15772` pins sorted replay between the generic owner and Similar VOC seed.

These commits are source-level evidence only until exact-head PostgreSQL and hosted validation run. No publication, translation approval, consumer acceptance, merge, or release is implied by this ADR.
