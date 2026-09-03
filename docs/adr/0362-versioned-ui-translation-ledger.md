# ADR 0362: Version product UI translations in PostgreSQL

- Status: Proposed
- Date: 2026-09-03
- Owners: LineageWeave product read model / Customer Master UI composition
- Related: #922, `migrations/0246_ui_translation_ledger.sql`, `backend/app/translation_ledger.py`

## Problem

LineageWeave currently ships product UI copy in the frontend bundle and admits only `en`, `ko`, `zh`, `ja`, and `vi` as persisted member locale preferences. That makes a deploy artifact the mutable source of product copy, leaves the required `es`, `de`, and `fr` buyer paths unsupported, and provides no immutable screen-version identity for evidence, rollback, or cache correctness.

This ledger is strictly for LineageWeave-owned product UI copy. Ontology labels, concept names, and semantic truth remain with their canonical owners and must enter LineageWeave only through released contracts or ACLs.

## Constraints

- The product locale contract is exactly `ko`, `en`, `ja`, `zh`, `vi`, `es`, `de`, and `fr` for this increment.
- Locale identifiers are language tags interpreted according to BCP 47 / RFC 5646; adding region or script distinctions requires an explicit product decision and a new compatible version of the contract.
- PostgreSQL is authoritative. Valkey is an optional read cache and must not become a second source of truth.
- A published screen version is immutable and complete for every required screen key in all eight locales.
- Reads do not silently fall back to another locale. Missing or blank requested-locale copy is an error.
- `product_key` and `screen_key` are canonical identity segments: blank, colon-bearing, or leading/trailing-whitespace forms are rejected consistently by PostgreSQL and the application boundary.
- Cache identity must include product, screen, immutable resource version, and locale.
- An explicit-version cache hit is admissible only after PostgreSQL confirms the published resource and its exact required screen-key set; structurally valid partial cache payloads are misses.
- Publication must serialize with child key/text mutation so a complete resource cannot become incomplete after the publication check.
- `published_at` is database-owned evidence of the one-way publication transition. Caller-supplied timestamps are never retained, and a long-lived transaction must not backdate the receipt to its transaction start.
- The design must stay independent from ontology-label persistence and from another CWL product's domain tables.

## Alternatives considered

### Keep translations in the SPA bundle

Rejected. It couples copy lifecycle to frontend deployment, cannot provide an immutable database identity for a screen/version/locale projection, and perpetuates the five-locale gap.

### Store product copy with ontology labels

Rejected. Product UI copy and semantic concept labels have different ownership, versioning, review, and rollback semantics. Sharing their source of truth would violate the canonical-owner boundary and make ordinary copy changes semantic changes.

### Use a mutable key/value translation table

Rejected. In-place mutation destroys the evidence needed to reproduce what a buyer saw and makes cache invalidation dependent on timing rather than identity.

### Allow padded resource identifiers and normalize only in the reader

Rejected. Raw PostgreSQL uniqueness would then distinguish identities that the application/cache boundary collapses with `strip()`, permitting unreachable resources and violating the aggregate identity invariant.

### Preserve a caller-supplied publication timestamp

Rejected. The row becomes immutable immediately after publication, so preserving arbitrary input would permanently admit a forged audit timestamp. The database transition itself must stamp the receipt.

### Use PostgreSQL `now()` for the publication receipt

Rejected. PostgreSQL defines `now()` as the transaction-start timestamp. A resource populated or reviewed in a long transaction would therefore receive a publication receipt older than the actual publish statement. `statement_timestamp()` records the transition statement itself while remaining database-owned.

### Trust an exact-version cache payload without database admission

Rejected. Version identity proves which projection was requested but does not prove that a syntactically valid cache payload still contains every key declared by the published screen resource. A partial cache object could otherwise become product-copy authority.

### Version product-owned screen resources in PostgreSQL

Selected. It gives the read model a stable aggregate identity, keeps copy ownership local to LineageWeave, and permits exact-version caching without duplicating semantic truth.

## Decision

`ui_translation_resource` is the aggregate root identified by `(product_key, screen_key, resource_version)`. A resource starts as `draft`; publication is a one-way transition. `ui_translation_key` declares the screen's required keys. `ui_translation_text` supplies one nonblank value for each `(resource_id, translation_key, locale)`.

The schema remains in 3NF: resource version metadata, required keys, and localized values are separate relations. The database enforces unique resource versions and unique localized values. `product_key` and `screen_key` must already equal their `btrim(...)` values, matching the application boundary that canonicalizes caller input before lookup/cache identity construction. Publication rejects an empty key set or any missing member of the required key × eight-locale matrix. On the draft-to-published transition the trigger assigns `published_at := statement_timestamp()` unconditionally, so the immutable receipt is produced by the publication statement rather than caller input or transaction-start time. Once published, the root and all child rows are immutable.

Child insert/update/delete obtains a `FOR UPDATE` lock on the parent resource. Publication already locks the resource row through its update. Therefore publication and child mutation are serialized: either the child change commits before the completeness scan, or it observes the published state and is rejected. Child rows may not be re-parented between resources.

`read_translation_screen` returns a complete `TranslationScreen` projection. Latest-version reads resolve the complete projection from PostgreSQL so a stale cache alias cannot hide a newer publication. For an explicit immutable version, PostgreSQL first resolves the published resource's ordered required-key set. Valkey may then serve `ui-translation:{product}:{screen}:v{resource_version}:{locale}` only when the cached translation-key set exactly equals that authoritative set and all values are nonblank. Malformed, unavailable, identity-mismatched, partial, or extra-key cache entries are misses and fall back to the PostgreSQL text projection. This keeps cache reads useful for avoiding localized text-row work while preventing Valkey from deciding screen completeness. An unavailable cache never makes a valid PostgreSQL translation unavailable.

The existing `user_account.preferred_locale` constraint expands to the same eight language tags. API request validation and frontend consumption must be cut over to the same contract before #922 can close; the database/read-model foundation alone is not buyer-visible completion.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: versioned UI translation resource.
- Entity/value identity: canonical product/screen/version aggregate identity; required screen key; locale-tagged translated text.
- Repository boundary: PostgreSQL query in `backend.app.translation_ledger`; Valkey is a cache adapter, not a repository of record.
- Invariants: canonical unpadded product/screen identity, exact eight-locale completeness at publication, database-owned statement-time publication receipt, immutable published versions, no cross-resource child move, no locale fallback, exact cache identity, authoritative screen-key admission before cache acceptance.
- ACL: ontology labels remain external semantic truth and are not stored in these tables.

## Recovery and migration

Migration 0246 is additive for translation resources and only broadens the existing member locale constraint. While the old SPA bundle is still the consumer, deploying the migration is backward-compatible. If application rollout fails before consumers switch, roll back the application path while retaining the additive schema and any draft resources.

Published translation data is not destructively down-migrated. A bad published resource is corrected by publishing a new `resource_version` and moving consumers to that version/latest publication. Once customer copy exists, rollback means application/read routing to a previously admitted version, not dropping tables or rewriting published rows.

## Evidence

- RED `092d32137fd6764a4f1fc7a53125a15318814292`: executable contract required the eight locales, normalized schema, exact cache identity, and fail-closed completeness before implementation existed.
- RED `370f83a28f4a0fdeb000ea5a259d66c415c1a746`: review found that child mutation could race publication; the contract required parent-row serialization.
- Repair `bb61753db7a483c766690e830700637694135208`: child mutation now locks the parent resource with `FOR UPDATE`, preserving completeness across concurrent publication.
- RED `3b68e4ed16731e97e8743748ab5775fa78240064`: a correct-identity cache payload containing only a subset of the published screen keys was required to fall back to PostgreSQL instead of returning incomplete product copy.
- Repair `249b6cfba21c37899cae10ee7519d4e77132269d`: explicit-version reads now establish the published required-key set in PostgreSQL before accepting a cache hit; cache key sets must match exactly.
- Verification-contract alignment `f666a5b12b9ddd0bbef040c238ef541ec1fa1af1`: cache-hit and fallback tests assert one authoritative key-set query and reject partial cached projections.
- RED `d75d0a963319ca1b353346092f44095010f5756a`: the migration contract requires PostgreSQL `product_key` and `screen_key` to equal their trimmed canonical forms.
- Repair `d4d03da3835cf0722d707738c095386d5ed258b8`: migration 0246 rejects padded aggregate identities so database uniqueness and application/cache identity semantics cannot diverge.
- RED `c60693dd8bdea620b029c16c127d214f98eacdaf`: the migration contract requires a database-owned publication timestamp rather than a caller-preserved value.
- Repair `5973bbb8b029e962793a68f127dfcc96584dbbcd`: publication stopped preserving caller-supplied timestamps.
- PostgreSQL verification `d982d2658792087f107d81f28becf37af557e2d4`: the repository's real PostgreSQL path now exercises canonical identity, immutable database-owned publication receipts, and eight-locale completeness against the actual migrations.
- RED `74f0521bc3d297128f583ebb6c84ca58d0343678`: a real PostgreSQL transaction is deliberately aged before publication and requires the receipt to be later than `transaction_timestamp()`.
- Repair `e2429b144eaf20254d22a6e26d421915f8c1a9e7`: publication now uses `statement_timestamp()` so a long transaction cannot backdate the receipt.
- Verification-contract alignment `3a3f80980d9e5848bf611135edaa9e2f20cd7bb5`: static contract and real-PostgreSQL evidence agree on statement-scoped publication time.

These commits are branch evidence only. This ADR remains Proposed until the exact protected-line implementation and dependent API/frontend cutover are verified.

## References

Internet Engineering Task Force. (2009). *Tags for identifying languages (BCP 47 / RFC 5646)*. RFC Editor. https://www.rfc-editor.org/rfc/rfc5646.html
