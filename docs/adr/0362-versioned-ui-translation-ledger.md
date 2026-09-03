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
- A returned `TranslationScreen` is the value-object projection of that immutable version; callers must not be able to mutate its translation mapping while retaining the same product/screen/version/locale identity.
- Reads do not silently fall back to another locale. Missing or blank requested-locale copy is an error.
- `translated_text` may preserve intentional leading/trailing whitespace, but it must contain at least one non-whitespace character before publication; PostgreSQL admission cannot allow a value that the read model would later treat as blank after publication makes the version immutable.
- `(product_key, screen_key, resource_version)` is the aggregate identity and is immutable after resource creation; a reviewed draft cannot be retargeted to another product, screen, or version during editing or publication.
- `product_key` and `screen_key` are canonical identity segments: blank, colon-bearing, or leading/trailing-whitespace forms are rejected consistently by PostgreSQL and the application boundary.
- Each required `translation_key` is also a canonical identifier: blank or leading/trailing-whitespace forms are rejected by PostgreSQL rather than becoming visually ambiguous distinct keys inside one immutable screen version.
- PostgreSQL's one-argument `btrim` removes a plain space by default; it is not sufficient to implement the application boundary's broader edge-whitespace rejection. The migration therefore retains the trimmed-space check and separately rejects leading/trailing PostgreSQL regular-expression whitespace for identifiers, and rejects all-whitespace translated copy without trimming valid copy.
- Cache identity must include product, screen, immutable resource version, and locale.
- An explicit-version cache hit is admissible only after PostgreSQL confirms the published resource, its exact required screen-key set, and SHA-256 evidence for each requested-locale value. A structurally complete cache payload whose copy does not match that evidence is a miss.
- PostgreSQL pool leases must not be held while awaiting optional Valkey I/O. Published resource/key/value identity is immutable, so cache admission can occur after releasing the integrity-evidence query connection and PostgreSQL can be reacquired only on a cache miss or failure.
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

### Expose a mutable translation dictionary inside a frozen projection shell

Rejected. Freezing only the dataclass fields does not freeze a nested `dict`. A caller could alter or clear product copy while the object still claims the same immutable published identity, breaking the read-model value-object invariant without any PostgreSQL mutation. Both PostgreSQL and cache-hit construction therefore detach copy into a read-only mapping; cache serialization explicitly materializes a plain dictionary only at the adapter boundary.

### Permit draft aggregate identity edits

Rejected. The domain identity is the product/screen/version tuple, not the surrogate `resource_id`. Allowing that tuple to change after INSERT would let review or evidence refer to one aggregate while the same row is later published as another product, screen, or version. A mistaken identity is replaced with a new draft instead; child copy remains editable until publication.

### Allow padded resource identifiers and normalize only in the reader

Rejected. Raw PostgreSQL uniqueness would then distinguish identities that the application/cache boundary collapses, permitting unreachable resources and violating the aggregate identity invariant. Caller-provided padded identities are rejected rather than silently rewritten to another canonical identity.

### Use default `btrim` as the complete whitespace predicate

Rejected. PostgreSQL 18 documents that the omitted `characters` argument defaults to a space. Python `str.strip()` rejects tab/newline edge padding as well, so a default-`btrim`-only constraint lets PostgreSQL persist identities the reader refuses. The schema uses an explicit edge-whitespace regular-expression guard in addition to its existing space/canonicality checks. For presentation copy, the database rejects values made entirely of regular-expression whitespace but does not trim or forbid intentional whitespace surrounding nonblank copy.

### Allow padded required translation keys

Rejected. Required screen-copy keys are identifier values, not presentation text. Treating `title` and ` title` as distinct database keys would permit visually ambiguous requirements inside a published immutable resource and make consumer/evidence matching dependent on invisible whitespace. PostgreSQL rejects padded key spellings before publication instead of normalizing them into another identifier.

### Let the reader alone reject whitespace-only copy

Rejected. Publication is a one-way immutable transition. If PostgreSQL admits a tab/newline-only translation row, the publication matrix sees a present row and can freeze a version that every conforming reader rejects as blank. Copy validity therefore belongs at the database child-row admission boundary as well as at read-model validation.

### Preserve a caller-supplied publication timestamp

Rejected. The row becomes immutable immediately after publication, so preserving arbitrary input would permanently admit a forged audit timestamp. The database transition itself must stamp the receipt.

### Use PostgreSQL `now()` for the publication receipt

Rejected. PostgreSQL defines `now()` as the transaction-start timestamp. A resource populated or reviewed in a long transaction would therefore receive a publication receipt older than the actual publish statement. `statement_timestamp()` records the transition statement itself while remaining database-owned.

### Trust an exact-version cache payload without database admission

Rejected. Version identity proves which projection was requested but does not prove that a syntactically valid cache payload still contains every key declared by the published screen resource. A partial cache object could otherwise become product-copy authority.

### Trust a complete cache key set without value evidence

Rejected. Key completeness proves only the shape of the projection. A correctly keyed Valkey entry can still contain altered copy and would then become a second source of truth. The admission query therefore returns PostgreSQL-owned SHA-256 evidence for each requested-locale value; cached UTF-8 copy must reproduce every digest before it can be returned.

### Hold the PostgreSQL lease while consulting Valkey

Rejected. The integrity-evidence query has already established immutable publication identity and per-key value evidence. Keeping that connection leased across an optional cache network wait adds no consistency guarantee and allows slow Valkey I/O to consume scarce PostgreSQL pool capacity. Explicit-version reads therefore release the first lease before cache I/O and reacquire only for the authoritative text projection on a miss.

### Version product-owned screen resources in PostgreSQL

Selected. It gives the read model a stable aggregate identity, keeps copy ownership local to LineageWeave, and permits exact-version caching without duplicating semantic truth.

## Decision

`ui_translation_resource` is the aggregate root identified by `(product_key, screen_key, resource_version)`. A resource starts as `draft`; publication is a one-way transition. The aggregate identity is fixed at INSERT and cannot be changed while draft or as part of publication. `ui_translation_key` declares the screen's required keys. `ui_translation_text` supplies one value for each `(resource_id, translation_key, locale)` and rejects values made entirely of PostgreSQL regular-expression whitespace; valid text is stored byte-for-byte, including intentional surrounding whitespace.

The schema remains in 3NF: resource version metadata, required keys, and localized values are separate relations. The database enforces unique resource versions and unique localized values. `product_key`, `screen_key`, and each required `translation_key` must already equal their `btrim(...)` values and must not match leading/trailing `\s` in PostgreSQL's regular-expression engine; identifier edge whitespace is rejected, not normalized. This explicit regex guard is required because default `btrim` removes only plain spaces. Publication rejects an empty key set or any missing member of the required key × eight-locale matrix, and every admitted text row must contain at least one non-whitespace character so a published immutable version cannot become unreadable by construction. On the draft-to-published transition the trigger assigns `published_at := statement_timestamp()` unconditionally, so the immutable receipt is produced by the publication statement rather than caller input or transaction-start time. Once published, the root and all child rows are immutable.

Child insert/update/delete obtains a `FOR UPDATE` lock on the parent resource. Publication already locks the resource row through its update. Therefore publication and child mutation are serialized: either the child change commits before the completeness scan, or it observes the published state and is rejected. Child rows may not be re-parented between resources.

`read_translation_screen` returns a complete `TranslationScreen` projection whose translation mapping is detached and read-only, so application code cannot mutate product copy while retaining the same immutable published identity. Latest-version reads resolve the complete projection from PostgreSQL so a stale cache alias cannot hide a newer publication. For an explicit immutable version, PostgreSQL first resolves the published resource's ordered required-key set plus `encode(sha256(convert_to(translated_text, 'UTF8')), 'hex')` evidence for the requested locale and then releases that pool lease. Valkey may serve `ui-translation:{product}:{screen}:v{resource_version}:{locale}` only when the cached key set exactly equals the authoritative set, all values are nonblank, and every cached UTF-8 value reproduces its PostgreSQL SHA-256 digest. Missing/malformed digest evidence or malformed, unavailable, identity-mismatched, partial, extra-key, or value-mismatched cache entries are misses. On a miss, the reader reacquires PostgreSQL for the localized text projection. This avoids transferring full localized copy on a valid cache hit while keeping PostgreSQL, rather than Valkey, authoritative for both shape and value integrity. PostgreSQL's built-in SHA-256/`convert_to` functions make the evidence independent of `pgcrypto`. An unavailable cache never makes a valid PostgreSQL translation unavailable. Cache serialization converts the read-only mapping to a plain JSON object only inside the cache adapter.

The existing `user_account.preferred_locale` constraint expands to the same eight language tags. API request validation and frontend consumption must be cut over to the same contract before #922 can close; the database/read-model foundation alone is not buyer-visible completion.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: versioned UI translation resource.
- Entity/value identity: immutable canonical product/screen/version aggregate identity; canonical required translation key; locale-tagged translated text.
- Repository boundary: PostgreSQL query in `backend.app.translation_ledger`; Valkey is a cache adapter, not a repository of record.
- Invariants: immutable aggregate identity after creation, canonical unpadded product/screen/required-key identity across space/tab/newline edge padding, non-whitespace translated copy at database admission, exact eight-locale completeness at publication, database-owned statement-time publication receipt, immutable published versions, read-only `TranslationScreen` value projections, no cross-resource child move, no locale fallback, exact cache identity, PostgreSQL-owned per-key SHA-256 value evidence before cache acceptance, and no PostgreSQL lease held across optional cache I/O.
- ACL: ontology labels remain external semantic truth and are not stored in these tables.

## Recovery and migration

Migration 0246 is additive for translation resources and only broadens the existing member locale constraint. While the old SPA bundle is still the consumer, deploying the migration is backward-compatible. If application rollout fails before consumers switch, roll back the application path while retaining the additive schema and any draft resources.

Published translation data is not destructively down-migrated. A bad published resource is corrected by publishing a new `resource_version` and moving consumers to that version/latest publication. A draft created with the wrong product/screen/version identity is discarded and recreated rather than retargeted in place. Once customer copy exists, rollback means application/read routing to a previously admitted version, not dropping tables or rewriting published rows.

## Evidence

- RED `092d32137fd6764a4f1fc7a53125a15318814292`: executable contract required the eight locales, normalized schema, exact cache identity, and fail-closed completeness before implementation existed.
- RED `370f83a28f4a0fdeb000ea5a259d66c415c1a746`: review found that child mutation could race publication; the contract required parent-row serialization.
- Repair `bb61753db7a483c766690e830700637694135208`: child mutation now locks the parent resource with `FOR UPDATE`, preserving completeness across concurrent publication.
- RED `3b68e4ed16731e97e8743748ab5775fa78240064`: a correct-identity cache payload containing only a subset of the published screen keys was required to fall back to PostgreSQL instead of returning incomplete product copy.
- Repair `249b6cfba21c37899cae10ee7519d4e77132269d`: explicit-version reads now establish the published required-key set in PostgreSQL before accepting a cache hit; cache key sets must match exactly.
- Verification-contract alignment `f666a5b12b9ddd0bbef040c238ef541ec1fa1af1`: cache-hit and fallback tests assert one authoritative key-set query and reject partial cached projections.
- RED `d75d0a963319ca1b353346092f44095010f5756a`: the migration contract requires PostgreSQL `product_key` and `screen_key` to equal their trimmed canonical forms.
- Repair `d4d03da3835cf0722d707738c095386d5ed258b8`: migration 0246 rejects padded aggregate identities so database uniqueness and application/cache identity semantics cannot diverge.
- Application-boundary RED `527abd6dd2527ebc932583bd17c10019c12aaa4c`: padded `product_key` / `screen_key` inputs must fail instead of being normalized to a different persisted/cache identity.
- Application-boundary repair `66ff153246443a686f53706dd165fc9795c6f197`: `_validate_identity_segment()` now rejects leading/trailing whitespace before lookup or cache-key construction, matching the database invariant.
- RED `c60693dd8bdea620b029c16c127d214f98eacdaf`: the migration contract requires a database-owned publication timestamp rather than a caller-preserved value.
- Repair `5973bbb8b029e962793a68f127dfcc96584dbbcd`: publication stopped preserving caller-supplied timestamps.
- PostgreSQL verification `d982d2658792087f107d81f28becf37af557e2d4`: the repository's real PostgreSQL path now exercises canonical identity, immutable database-owned publication receipts, and eight-locale completeness against the actual migrations.
- RED `74f0521bc3d297128f583ebb6c84ca58d0343678`: a real PostgreSQL transaction is deliberately aged before publication and requires the receipt to be later than `transaction_timestamp()`.
- Repair `e2429b144eaf20254d22a6e26d421915f8c1a9e7`: publication now uses `statement_timestamp()` so a long transaction cannot backdate the receipt.
- Verification-contract alignment `3a3f80980d9e5848bf611135edaa9e2f20cd7bb5`: static contract and real-PostgreSQL evidence agree on statement-scoped publication time.
- Aggregate-identity RED `aa050f1db2a0033eba4debd935ac2560a7d23a95`: real PostgreSQL verification requires product, screen, and resource-version identity to remain unchanged after resource creation.
- Aggregate-identity repair `04c851f905bdb90d48268902d45f0e41ba335981`: the root mutation guard now rejects any draft or publication update that would retarget the aggregate identity.
- Pool-lease RED `e32539220638faaedc53e508e9d71c9df37615fa`: the read-model test observes the asyncpg lease state at Valkey read time and fails if optional cache I/O occurs while PostgreSQL remains acquired.
- Pool-lease repair `024154938f1dedd1ed51a4f4406465c116418267`: explicit-version reads release the key-set query lease before cache I/O and reacquire PostgreSQL only after a cache miss/failure.
- Verification alignment `f077d19cc77c8d6a11ee5545c80e1c0d309213ee`: miss/failure-path tests require the two bounded acquisitions while cache-hit paths retain a single short PostgreSQL acquisition.
- Required-key identity RED `e2b5b5fde6fd884a4735ac95af49afc6e2765dfb`: real PostgreSQL verification requires leading/trailing-space required translation keys to fail instead of becoming distinct immutable identifiers.
- Required-key identity repair `413ea3ba785e82949b92d2e51fcef000129d9ee8`: `ui_translation_key` now requires `translation_key = btrim(translation_key)` in addition to nonblank content.
- Hosted verification alignment `913e3d1ea5e2e1ddb6f52a1c01fb66e5b03df340`: static migration evidence preserves the canonical required-key guard when a hosted runner has no PostgreSQL server.
- Non-space whitespace RED `da3b9c5c97c1775d6a1bd489012ed9031093b4c4`: real PostgreSQL verification extends resource and required-key identity cases to tab/newline edge padding that default `btrim` does not remove.
- Non-space whitespace repair `f74b7e23bce92d1ab310a13a6dbdc23f79122035`: migration 0246 adds PostgreSQL `\s` edge guards for product, screen, and required translation keys.
- Hosted verification alignment `d8c386433417e66b6c4350f3740d17f2d77f64d1`: the static contract preserves the regex guards and application tab/newline rejection on runners without PostgreSQL.
- Whitespace-only copy RED `47c2c21be97db585b5eef2f02e8b0ebabaaef92b`: hosted migration contract requires database admission to reject translated text made entirely of whitespace.
- Real-PostgreSQL RED `55df3d8b078a35c9c505ea27a6caa414b86b5cef`: tab/newline-only updates must fail with the table check before an immutable resource can be published.
- Whitespace-only copy repair `9b42748e9b296a88ed4bc01664945c23c65a720a`: `ui_translation_text` now rejects all-whitespace values while preserving nonblank presentation text exactly.
- Value-object RED `9f04f097fab7a9da0d9086b29776b01b42f082eb`: both PostgreSQL and exact-version cache-hit paths must reject mutation of the returned translation mapping.
- Value-object repair `035fbc862caccbd74428021314f534f1b4bce35d`: both construction paths detach translations behind `MappingProxyType`; cache serialization materializes a plain dictionary only at the adapter boundary.
- Cache-authority RED `ea95121a3bf93c606e2214161941d23bbed53794`: a complete exact-version cache payload with correct identity and key coverage but altered copy must fall back to PostgreSQL.
- Cache-authority repair `34955985965bef045614cb445b65853760991fb6`: the explicit-version admission query now returns PostgreSQL SHA-256 evidence for each requested-locale value and cached copy must reproduce every digest before return.
- Read-model verification alignment `1e9d6f984e108f1505e33eb94c56a0b123ace693`: cache-hit fixtures carry the same authoritative digests, while the poisoned complete payload requires a second PostgreSQL acquisition and authoritative copy.
- Real-PostgreSQL verification `dc5e374bb2e309bd45086b4d928c7cc9a4a0aa22`: migration-backed PostgreSQL executes the exact admission query and proves its built-in UTF-8 SHA-256 output matches the application digest.

These commits are branch evidence only. This ADR remains Proposed until the exact protected-line implementation and dependent API/frontend cutover are verified.

## References

Internet Engineering Task Force. (2009). *Tags for identifying languages (BCP 47 / RFC 5646)*. RFC Editor. https://www.rfc-editor.org/rfc/rfc5646.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.4. String functions and operators*. https://www.postgresql.org/docs/18/functions-string.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.5. Binary string functions and operators*. https://www.postgresql.org/docs/18/functions-binarystring.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.7. Pattern matching*. https://www.postgresql.org/docs/18/functions-matching.html
