# ADR 0373: Authorization receipts for persisted Post Chat replay

- Status: Proposed
- Date: 2026-09-13
- Decision owners: LineageWeave Post Chat / evidence-read boundary
- Related: #1044, PR #1047, ADR 0136, migration 0203

## Context

`post_chat_result` persists derived answer text and `post_chat_citation` persists displayed citations, but protected `main@83eba56149eb802cd63642c507c324c9976ec78e` does not retain the authorization scope or the complete source set that was allowed to influence that derived text. `POST /api/posts/{post_id}/chat` can therefore authorize the focal post and replay an older answer before rebuilding the current authorized source set. A reader whose scope has narrowed since generation can receive text influenced by source posts that are no longer visible.

ADR 0136 already treats per-post Ask history as an account/post authorization boundary and the product gap baseline explicitly calls for bounded citation reauthorization. Migration 0203 provides the repository precedent for normalized captured authorization scope: corporate-entity and process-unit identities are stored as child relations rather than serialized policy blobs.

The current account model also has an intentional process-scope distinction that must survive persistence. An empty authenticated `process_unit_ids` set means unrestricted process-unit visibility inside the admitted corporate scope. That valid empty set must not be confused with a legacy result for which no generation receipt exists.

## Constraints

- Domain truth remains in LineageWeave's Post Chat/evidence read boundary; no sibling-service SQL or copied authorization engine is introduced.
- `SOURCE_POST_ELIGIBILITY_SQL` plus `source_post_scope_sql` remain the database authorization contract for current source visibility.
- Persisted derived text may be replayed only when current reader scope is at least as broad as generation scope and every contributing source remains currently eligible and visible.
- Every source that could influence the answer is evidence, even when the final answer did not cite it. Reauthorizing displayed citations alone is insufficient.
- Legacy rows without a receipt fail closed to live recomputation.
- Contextual-orchestrator generation/retrieval must not run inside an explicit database transaction or lock. Only bounded replay validation/serialization and the final result/evidence persistence unit may own short database transactions.
- New schema must be normalized, replay-safe, and reversible through the normal migration/rollback path.

## Alternatives considered

### Trust the focal post and filter citations at display time

Rejected. The answer text itself is derived data. Hiding a citation does not remove facts already incorporated from a now-unauthorized source.

### Persist a serialized authorization JSON blob

Rejected. It obscures identity constraints, makes referential integrity and set comparison harder, and diverges from the normalized scope pattern already used by Global Ask.

### Recompute every historical answer on every read

Rejected as the default. It is fail-closed but discards the product value of persisted conversation history and introduces unnecessary model cost and non-determinism when a valid receipt can prove safe replay.

### Persist normalized generation scope plus all contributing source identities and reauthorize on replay

Chosen. Receipt presence distinguishes scoped current rows from legacy rows. Corporate/process scopes are normalized child relations, all contributing source posts are ordered evidence children, and current replay reuses the canonical source-post eligibility/scope SQL.

## Decision

1. `post_chat_authorization_receipt` is a one-to-one child of `post_chat_result`. Its presence is the generation-scope receipt; absence means legacy/unscoped and is never replayable.
2. `post_chat_corporate_entity_scope` and `post_chat_process_unit_scope` persist normalized generation scope. `process_scope_limited=false` represents a valid authenticated unrestricted process-unit scope; therefore an empty process child set is meaningful only when the receipt exists.
3. `post_chat_source` persists every source post presented to the reason-and-cite step, including the focal post, with deterministic ordinal and uniqueness constraints. `post_chat_citation.cited_post_id` must be a subset of that captured source set at the application boundary.
4. Replay requires generation corporate scope to be a subset of the current corporate scope. A generation receipt with unrestricted process scope may replay only to a currently unrestricted reader. A generation receipt with restricted process scope may replay to a currently unrestricted reader or to a restricted current scope that is a superset of the captured process units.
5. After scope comparison, every captured `post_chat_source` is rechecked through the shared current eligibility/scope SQL. Any missing/ineligible source makes the cached answer non-replayable and the POST path falls through to live authorized source gathering.
6. Receipt validation, captured-source reauthorization, and answer serialization execute in one short replay transaction. The parent `post_chat_result` is locked with `FOR KEY SHARE` before its receipt is trusted so replacement through the product's delete-and-insert persistence path cannot swap new derived text under an old receipt. Captured `source_post` rows are locked with `FOR SHARE`, not merely `FOR KEY SHARE`, so non-key visibility or eligibility fields cannot change between authorization and serialization. These locks end before any live generation begins.
7. Deleting a `source_post` that contributed to a persisted answer invalidates that derived answer in the same database transaction before the source row disappears. Migration 0249 uses a `BEFORE DELETE` trigger to delete matching `post_chat_result` aggregates while their `post_chat_source` evidence is still queryable; the existing aggregate cascades then remove receipt, citation, scope, and source children. A contributing-source delete must never leave replayable derived text whose evidence row vanished by cascade alone.
8. GET history applies the same replay policy; it must not become an alternate path for stale derived-data disclosure.
9. Model/retrieval work completes before persistence begins. The persistence transaction contains only replacement of the result and its citation/source/scope children. No contextual-orchestrator call, embedding call, or long computation may hold that transaction open.
10. Demo/API fixtures that intentionally exercise persisted replay must seed a valid receipt and contributing-source set using an explicit generating account scope. Production runtime is not weakened to preserve legacy fixture behavior, and author identity is not substituted for reader/generator authorization scope.

## DDD mapping and invariants

`post_chat_result` is the persisted derived-answer entity under the Post Chat read-model boundary. Its authorization receipt and source/citation children share the same `(post_id, question_norm)` aggregate identity and lifecycle through cascading foreign keys. Generation authorization scope is a value object reconstructed from normalized child identities plus `process_scope_limited`; replay authorization is a domain policy that compares that immutable value with the current `CurrentAccount` scope before current-source reauthorization.

Invariants are executable: no receipt means no replay; persisted process-scope metadata cannot contradict its normalized child set; the captured source set is non-empty and contains the focal post; citations are drawn only from captured sources; process unrestricted/restricted semantics are explicit; all captured sources must remain currently authorized; the derived-answer identity and authorization-relevant captured-source rows remain stable through replay serialization; deleting a contributing source invalidates the parent derived answer; and generation completes before any persistence transaction starts.

## Consequences and risks

The first read of a legacy persisted answer will recompute instead of replaying it. That is an intentional security behavior, not a migration backfill opportunity: historical generation scope cannot be reconstructed reliably after the fact.

Replay adds one receipt lookup, bounded child-scope/source reads, and one bounded source-post authorization query. It also holds row-level locks only across those replay reads and serialization of the already-persisted answer. The source set is product-bounded by Post Chat retrieval. If measured buyer-path p95 exceeds the repository target, profile query preparation, bounded reads, authorization query, lock wait, and serialization before considering a separate read model; do not move contextual-orchestrator work into the transaction or weaken the authorization snapshot.

Deleting a contributing source now also deletes any persisted Post Chat answer that depended on it. That write amplification is deliberate: retaining stale derived text would break the evidence lifecycle. The trigger executes inside the source deletion transaction and performs only indexed aggregate-key deletion; real PostgreSQL promotion evidence must verify bounded behavior and rollback removal of the trigger/function.

The migration adds no mutable policy labels and no PII beyond identifiers already used by the authorization model. Retention follows the parent `post_chat_result` lifecycle through `ON DELETE CASCADE`.

## Promotion evidence

Before changing this ADR to Accepted, one exact head must prove the legacy/no-receipt fallback, broader-generation to narrower-reader rejection, restricted/unrestricted process semantics, malformed-receipt rejection, corporate-scope contraction, changed contributing-source visibility, source-deletion invalidation, citation-subset invariant, idempotent current-scope replay, GET-history filtering, parent-result replacement blocking, authorization-relevant source-update blocking, real PostgreSQL migration/rollback, explicit demo generation-account scope, short transaction boundaries, full PostgreSQL/API suites, Security/SAST/CodeQL/Strix/model-review gates, and qualifying independent current-head review.
