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
- Child resource identity remains owned by ADR 0362's base ledger guard. `ui_translation_key` and `ui_translation_text` rows cannot move between resources at all; seed ownership must not duplicate or weaken that invariant.
- The generic ownership migration itself has a bounded rollback. It must refuse while an exact `owned` Similar VOC receipt or another active non-Customer-Master generic owner remains. `pending` and `blocked` Similar VOC reservations own no product data and may be withdrawn during rollback, but a `retired` receipt is durable no-resurrection history and must survive removal and later reapplication of the shared trigger wiring. The rollback must restore the pre-existing Customer Master trigger lane rather than dropping that owner boundary.
- The base Customer Master ownership rollback must also refuse while the generic ownership functions are installed, even if all descendant ownership rows have already been removed. Otherwise it can drop `ui_translation_seed_ownership` underneath live generic triggers and leave future ledger writes calling functions whose required relation no longer exists. Recovery therefore follows strict reverse dependency order: Similar VOC draft rollback when needed, generic ownership rollback, then base ownership rollback.
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

### Add a seed-specific source-first child UPDATE guard

Rejected after review. ADR 0362 already installs `guard_ui_translation_child_mutation()`, which rejects every `resource_id` change. PostgreSQL fires same-kind triggers in alphabetical trigger-name order, but the resulting order is table-specific here: the key mutation guard precedes the seed-key guard, while the seed-text guard precedes the text mutation guard. That ordering does not create an escape. If the seed guard does not reject first, it returns the row and the ADR-0362 base guard subsequently rejects the cross-resource move. A companion migration that reimplements source-first UPDATE handling therefore adds no permissible-state distinction and duplicates the base identity authority. PostgreSQL 18 documents the trigger-order rule at https://www.postgresql.org/docs/18/trigger-definition.html.

### Require the Similar VOC resource to be absent before rolling back generic ownership wiring

Rejected after recovery review. Absence is necessary only when the seed actually owns the resource. A `blocked` receipt is explicit evidence that the same-identity resource predates the seed and is operator-owned. Requiring that resource to be deleted before generic rollback makes a failed deployment non-recoverable without destructive operator action. The safe boundary is the ownership receipt: `owned` blocks generic-layer rollback, while an unowned `pending` or `blocked` reservation may be withdrawn with the generic wiring and any operator resource remains untouched.

### Delete `retired` receipts when rolling back generic ownership wiring

Rejected after replay review. `retired` does not merely mean “currently owns no row”; it is the durable product-lifecycle fact that historical seed bytes must never regain authority after deliberate deletion. Deleting that receipt during shared-wiring rollback makes the next forward application create a fresh `pending` reservation and reseed the retired candidate. The trigger layer can therefore be removed while valid `retired`/NULL-resource receipts remain. They are historical no-resurrection markers, not active dependencies.

### Let the base ownership rollback infer descendant removal from an empty ownership table

Rejected after recovery-order review. Exact Similar VOC rollback deliberately removes its owned resource and lets the corresponding ownership row cascade away, while the generic trigger/functions remain installed until `rollback/0249_ui_translation_seed_ownership_generic.sql` runs. At that point an empty table does not prove the descendant layer is gone. Dropping the base table on that signal strands generic trigger functions that query `public.ui_translation_seed_ownership`. The installed generic functions are therefore an explicit reverse-order dependency and base rollback fails closed until the generic layer is removed.

## Decision

Migration `0249_ui_translation_seed_ownership_generic.sql` replaces the active Customer-Master-specific ownership trigger wiring with generic trigger functions over `ui_translation_seed_ownership`. The lifecycle is selected by the ownership row's `(migration_key, product_key, screen_key, resource_version)` identity and the trusted `lineageweave.migration_file` execution context.

A `pending` ownership row reserves an otherwise-empty screen identity for its seed. The forward seed may create that root and an `AFTER INSERT` binder records the exact `resource_id` as `owned`. Child writes performed by the seed are accepted only after that binding. A pre-existing resource causes `blocked` state and the forward seed fails closed without touching it.

Ordinary deletion of an exact `owned` candidate first changes the receipt to `retired` and clears `resource_id`; the root can then be deleted without `ON DELETE CASCADE` erasing the one-time completion evidence. Forward replay in `owned` or `retired` state does not restore seed text. Explicit rollback is distinguished by `rollback/<migration_key>.sql`; the generic root guard first resolves the ownership row by the root's immutable product/screen/version identity, then allows deletion only for exact `owned` state with the same `resource_id`. The child guard applies the same exact ownership check and additionally rejects rollback-labelled `INSERT` or `UPDATE`, so rollback provenance cannot mutate blocked operator child rows or rewrite reviewed copy. Cascading child deletes from the exact owned root remain admissible. The exact owned draft can therefore be removed without retiring it, allowing the ownership row to cascade away so a later intentional forward migration can seed a fresh review candidate.

Cross-resource child UPDATE remains exclusively owned by the base translation-ledger guard from migration 0246. The generic seed-ownership layer does not redefine that rule. This keeps the DDD boundary single-writer: ADR 0362 owns resource/key/text identity and immutability, while ADR 0377 owns only one-time seed provenance and recovery for the Similar VOC presentation-copy candidate.

Migration `0249_z_similar_voc_translation_draft.sql` reserves no semantic authority. It creates 23 presentation keys × 8 locales only when ownership is `pending`, verifies the exact 184-row matrix, and then stops. Publication remains a separate one-way ADR-0362 transition after independent language/product review and unchanged-head consumer acceptance.

`rollback/0249_ui_translation_seed_ownership_generic.sql` uses ownership state, not mere resource existence, as the dependency boundary. It removes only the Similar VOC `pending` or `blocked` reservation because those states never established product-data ownership. It refuses while Similar VOC remains actively owned, and it preserves a valid `retired`/NULL-resource receipt so generic rollback followed by reapplication cannot resurrect historical seed copy. Other generic owners block removal of the shared trigger layer unless their lifecycle is already a valid retired/NULL-resource marker. Once active ownership dependencies are absent, the rollback removes only the generic trigger/functions and restores the existing Customer Master ownership trigger functions. An operator-owned `lineageweave/similar-voc/v1` resource may remain in place throughout this rollback and is neither deleted nor adopted.

The descendant migration also extends `rollback/0247_z_customer_master_translation_seed_ownership.sql` with a composition guard. Presence of any generic ownership function means the descendant layer is still installed, regardless of whether current generic ownership rows are empty. Base rollback refuses in that state. After `rollback/0249_ui_translation_seed_ownership_generic.sql` restores the Customer Master trigger lane and removes the generic functions, the base rollback may evaluate its own resource, retirement, and ownership-table preconditions normally. This is a recovery-order integration guard, not a transfer of generic lifecycle ownership into ADR 0362.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: `lineageweave/similar-voc/v1` translation resource.
- Value identities: translation key and locale-tagged presentation copy.
- Repository: PostgreSQL translation ledger; Valkey remains an optional read cache under ADR 0362.
- Domain service: one-time candidate-seed ownership lifecycle.
- Invariants: no implicit adoption, no reviewed-copy replay overwrite, no post-retirement resurrection even across generic-layer rollback/reapply, rollback limited to exact owned draft, blocked/pending roots and child rows outside destructive seed rollback authority, generic-layer rollback may preserve operator-owned conflicting copy, rollback child mutation limited to exact-owned deletion, child resource moves remain prohibited by the single ADR-0362 base guard, descendant generic wiring must be removed before base ownership-table rollback, eight-locale completeness before any publication, ontology labels excluded.
- ACL: #1126 consumes only a released/published screen-copy contract; similarity adjudication and authorization continue to come from their existing owners.

## Recovery and rollout

If the Similar VOC draft is wrong before publication, reviewers may edit it in place or explicitly run `rollback/0249_z_similar_voc_translation_draft.sql` and re-run the forward candidate. Ordinary product deletion means retirement, not authorization for historical reseeding. If a conflicting pre-existing `lineageweave/similar-voc/v1` resource exists, the forward seed stays blocked and never deletes or adopts that resource.

If deployment must be rolled back while that conflict remains, the generic ownership layer may still be removed because `blocked` proves the seed owns no resource. Run `rollback/0249_ui_translation_seed_ownership_generic.sql`; it deletes only the unowned pending/blocked Similar VOC reservation, preserves the operator resource and children, restores Customer Master ownership triggers, and removes the generic functions. If the receipt is `owned`, first remove the exact Similar VOC draft through its bounded rollback. If the receipt is `retired`, leave it in place: it is the no-resurrection marker that must survive a later reapply. Any other active generic seed owner must also be resolved before the shared generic layer is removed; retired NULL-resource history is not an active dependency. No separate child-move rollback exists because no seed-specific child-move migration is retained.

Only after the generic ownership rollback has removed the generic functions may `rollback/0247_z_customer_master_translation_seed_ownership.sql` remove the base ownership table. If that base rollback is attempted first, it now refuses before deleting any base reservation or dropping the table. This keeps reverse-order recovery fail closed even in the edge case where exact Similar VOC rollback already removed the descendant ownership row.

A published bad version is not down-migrated. ADR 0362 requires a new immutable resource version and consumer routing to that reviewed version.

## Evidence

- RED `c5339b820eaf2af3fe169bbb3d14d5364d0bea72` requires a complete eight-locale Similar VOC candidate, replay preservation of reviewed copy, unowned-resource refusal, retirement without resurrection, and exact-owned-draft rollback/reseed behavior on real PostgreSQL.
- Generic ownership repair `5448d8d24caa07110152f8fa1e5e5c52044ae60f` moves active seed lifecycle enforcement from Customer-Master-specific trigger wiring to the ownership aggregate and reserves `lineageweave/similar-voc/v1`.
- Candidate seed `d5f574f6e9eb04afab86c9bb9aee8acf93fb4375` adds the 23×8 review matrix and makes `owned|retired` replay purpose-complete without rewriting reviewed data.
- Draft rollback `eaaf7397fcb6db32afea599b6c17fc981bc6c9bd` limits destructive Similar VOC rollback to the exact owned unpublished resource.
- Rollback-provenance RED `f0e79fd233e01fc512d146b9e544aa9a2780efc6` found that a `resource_id`-only DELETE lookup did not see blocked ownership rows and could therefore let rollback provenance delete the operator-owned conflicting root.
- Causal rollback-provenance repair `2e673c1e00b8a19dbe526cd623e81d7ec3769e59` resolves DELETE ownership by immutable product/screen/version identity and still requires exact owned-resource equality before destructive rollback.
- Generic-migration recovery RED `27e8d53a549c34369f41f6365c99146e24cf0c72` requires rollback of the generalized trigger layer to leave the original Customer Master ownership lane executable.
- Generic-migration rollback `057eb6ed65cb80fdee40a391bc0727a0a4b925d4` restores the Customer Master trigger wiring and removes only the generic trigger/functions after its then-known dependencies are absent.
- Child rollback-provenance RED `73c7397ecd7e49439662b07516d087505a769d16` proves that a blocked operator draft's child key was still directly deletable when the session carried the Similar VOC rollback migration key.
- Causal child-rollback repair `dde6ea349cdf244e1c2dd754d600c041db2f8b6f` restricts rollback-labelled child mutation to `DELETE` on the exact `owned` resource while preserving the normal exact-owned cascading rollback path.
- Intermediate `eaf25d0630faa81c9e6509fe80d48c57b394395d` / `cf14dc8197bc820204784e423418b76362d4d7e3` / `6137835740da198984f6e32d2cb49712d0bf9269` / `86c6863da2a3609b8c5a73ce7f5b263867e15772` attempted to treat cross-resource UPDATE as a seed-provenance escape. Fresh review rejected that causal claim because ADR 0362 already prohibits the move independently of seed-specific provenance.
- Correction RED `6ed44ea51f4cb935625dbc6249d4c3e498ca7357` pins the single-writer boundary: no seed-specific companion migration may own child resource moves, and rollback-labelled child moves must still reach the ADR-0362 immutable-identity rejection when an earlier seed guard does not already reject them.
- Causal correction `8d220fbcd8d3016fd310d3a5aac1fc597d3969a9` removes the duplicate companion migration without weakening the base resource-identity invariant.
- Coverage `0d598231ca49aac1b61fef572f3bf8f7378d9bf0` exercises both `ui_translation_key` and `ui_translation_text`, covering both trigger-name orderings and requiring the same base-ledger cross-resource-move rejection.
- Blocked-rollback RED `e9eb46990fc3e70d9d06afb01f2321745c1088ed` reproduces the failed-deployment recovery case: a pre-existing operator-owned Similar VOC v1 causes `blocked`, after which the generic-layer rollback must succeed without deleting the operator resource or its child copy.
- Causal blocked-rollback repair `df9a39e98df366a6d49e3dbb8b635698e867cd2b` removes the resource-absence precondition and makes the ownership receipt the dependency boundary: unowned `pending|blocked` reservations are removable, while an `owned` receipt still refuses generic-layer rollback.
- Retirement-replay RED `12e4857381551b7617242a92a518518ef5425e85` retires an exactly owned candidate by ordinary product deletion, rolls back the shared generic wiring, reapplies it and reruns the seed, and requires the resource to remain absent with the receipt still `retired`.
- Causal retirement preservation `8860128580dcb8c9455c922f3b64955148318598` keeps retired NULL-resource receipts across generic rollback while allowing inactive retired history to coexist with restoration of the Customer Master-specific trigger lane.
- Recovery-order RED `7a01cfbf3e892b2a8f86a5c395ee1ba88f9c32a2` materializes and exactly rolls back the Similar VOC draft while leaving generic trigger wiring installed, then requires the base Customer Master ownership rollback to refuse rather than drop `ui_translation_seed_ownership` underneath live descendant functions.
- Causal recovery-order repair `200110f5a2677ba59c63be32867ef242cfd7e0f9` makes the base ownership rollback fail closed while any generic ownership function remains installed; normal reverse-order recovery succeeds after the generic rollback removes those functions.

These commits are source-level evidence only until exact-head PostgreSQL and hosted validation run. No publication, translation approval, consumer acceptance, merge, or release is implied by this ADR.