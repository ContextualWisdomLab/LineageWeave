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
- Cache identity must include product, screen, immutable resource version, and locale.
- Publication must serialize with child key/text mutation so a complete resource cannot become incomplete after the publication check.
- The design must stay independent from ontology-label persistence and from another CWL product's domain tables.

## Alternatives considered

### Keep translations in the SPA bundle

Rejected. It couples copy lifecycle to frontend deployment, cannot provide an immutable database identity for a screen/version/locale projection, and perpetuates the five-locale gap.

### Store product copy with ontology labels

Rejected. Product UI copy and semantic concept labels have different ownership, versioning, review, and rollback semantics. Sharing their source of truth would violate the canonical-owner boundary and make ordinary copy changes semantic changes.

### Use a mutable key/value translation table

Rejected. In-place mutation destroys the evidence needed to reproduce what a buyer saw and makes cache invalidation dependent on timing rather than identity.

### Version product-owned screen resources in PostgreSQL

Selected. It gives the read model a stable aggregate identity, keeps copy ownership local to LineageWeave, and permits exact-version caching without duplicating semantic truth.

## Decision

`ui_translation_resource` is the aggregate root identified by `(product_key, screen_key, resource_version)`. A resource starts as `draft`; publication is a one-way transition. `ui_translation_key` declares the screen's required keys. `ui_translation_text` supplies one nonblank value for each `(resource_id, translation_key, locale)`.

The schema remains in 3NF: resource version metadata, required keys, and localized values are separate relations. The database enforces unique resource versions and unique localized values. Publication rejects an empty key set or any missing member of the required key × eight-locale matrix. Once published, the root and all child rows are immutable.

Child insert/update/delete obtains a `FOR UPDATE` lock on the parent resource. Publication already locks the resource row through its update. Therefore publication and child mutation are serialized: either the child change commits before the completeness scan, or it observes the published state and is rejected. Child rows may not be re-parented between resources.

`read_translation_screen` returns a complete `TranslationScreen` projection. Latest-version reads resolve PostgreSQL first so a stale cache alias cannot hide a newer publication. Explicit immutable versions may be served by Valkey under `ui-translation:{product}:{screen}:v{resource_version}:{locale}`. Malformed, unavailable, or identity-mismatched cache entries are misses and fall back to PostgreSQL. An unavailable cache never makes a valid PostgreSQL translation unavailable.

The existing `user_account.preferred_locale` constraint expands to the same eight language tags. API request validation and frontend consumption must be cut over to the same contract before #922 can close; the database/read-model foundation alone is not buyer-visible completion.

## DDD mapping

- Subdomain: product composition / presentation read model.
- Bounded context: LineageWeave product read model.
- Aggregate: versioned UI translation resource.
- Entity/value identity: required screen key; locale-tagged translated text.
- Repository boundary: PostgreSQL query in `backend.app.translation_ledger`; Valkey is a cache adapter, not a repository of record.
- Invariants: exact eight-locale completeness at publication, immutable published versions, no cross-resource child move, no locale fallback, exact cache identity.
- ACL: ontology labels remain external semantic truth and are not stored in these tables.

## Recovery and migration

Migration 0246 is additive for translation resources and only broadens the existing member locale constraint. While the old SPA bundle is still the consumer, deploying the migration is backward-compatible. If application rollout fails before consumers switch, roll back the application path while retaining the additive schema and any draft resources.

Published translation data is not destructively down-migrated. A bad published resource is corrected by publishing a new `resource_version` and moving consumers to that version/latest publication. Once customer copy exists, rollback means application/read routing to a previously admitted version, not dropping tables or rewriting published rows.

## Evidence

- RED `092d32137fd6764a4f1fc7a53125a15318814292`: executable contract required the eight locales, normalized schema, exact cache identity, and fail-closed completeness before implementation existed.
- RED `370f83a28f4a0fdeb000ea5a259d66c415c1a746`: review found that child mutation could race publication; the contract required parent-row serialization.
- Repair `bb61753db7a483c766690e830700637694135208`: child mutation now locks the parent resource with `FOR UPDATE`, preserving completeness across concurrent publication.

These commits are branch evidence only. This ADR remains Proposed until the exact protected-line implementation and dependent API/frontend cutover are verified.

## References

Internet Engineering Task Force. (2009). *Tags for identifying languages (BCP 47 / RFC 5646)*. RFC Editor. https://www.rfc-editor.org/rfc/rfc5646.html
