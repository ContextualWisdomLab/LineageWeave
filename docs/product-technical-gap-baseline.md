# Product & Technical Gap Baseline

> Exact-head snapshot: 2026-09-04. Protected `main` is
> `b0e94aa2a6f7a943f96dc5c4f2fdecd0021978a1`. PR #929 is the active
> ADR 0362 candidate for issue #922 and is open / Draft / mechanically
> mergeable. The authenticated `GET /api/translations/{screen_key}` API is
> implemented on this branch. That is candidate implementation evidence, not
> protected-main, deployed, or release evidence.
>
> Historical baseline overlays through the preceding snapshot are preserved
> byte-for-byte at
> `docs/product-technical-gap-baseline-history-2026-09-04.md`. They remain dated
> evidence and must not override this current snapshot.
>
> The buyer-visible gap in #922 remains open. Protected `main` still ships the
> production frontend translation source in `frontend/src/i18n.ts` with only
> `en/ko/zh/ja/vi`; `es/de/fr` are not first-class frontend locales. No material
> SPA screen has yet been cut over to a published eight-locale ledger resource,
> and there is no exact-head desktop/mobile evidence covering normal, loading,
> empty, error, permission, responsive, keyboard/focus/screen-reader, CJK text
> expansion, or font fallback states.
>
> Do not synthesize translations and do not count English fallback as translated
> coverage. Ontology labels and concept names remain outside this presentation
> ledger and with their canonical owners.

## Current implementation boundary

- ADR 0362 remains **Proposed**. PostgreSQL is authoritative for versioned UI
  translation resources, required screen keys, and localized text; Valkey is
  only an exact immutable-version read cache.
- Migrations `0246_ui_translation_ledger.sql` and
  `0247_ui_translation_truncate_guard.sql` define the normalized ledger,
  publication immutability, eight-locale completeness, writer serialization,
  statement-level TRUNCATE protection, and replay/fail-closed rollback path.
- `backend/app/translation_ledger.py` admits exactly
  `ko/en/ja/zh/vi/es/de/fr`, returns immutable `TranslationScreen` value
  projections, validates canonical PostgreSQL text/BIGINT identities, admits
  cache hits only after PostgreSQL key-set and SHA-256 value evidence, performs
  no cross-locale fallback, and releases the PostgreSQL lease before optional
  Valkey I/O.
- `GET /api/translations/{screen_key}` is authenticated and propagates exact
  screen/locale/version identity. Missing published resources map to 404;
  incomplete requested-locale copy maps to 409; unsupported admission maps to
  422.
- Focused HTTP and asyncpg-boundary tests cover the route without adding a
  direct `psycopg2` caller. The documentation-alignment contract prevents this
  baseline from regressing to the obsolete claim that the API does not exist.
- None of the above is release evidence until the unchanged exact PR head has
  terminal required/security checks and qualifying independent approval, then
  reaches protected `main` normally.

## Next buyer cut

1. Use reviewed product copy to create and publish one complete screen resource
   for all eight locales. Do not invent copy to satisfy coverage.
2. Cut one material SPA screen off bundled `TRANSLATIONS` and onto the versioned
   API. Customer Master is the natural first slice because #922 gates its open
   material-UI work, but the screen identity must follow the actual product
   composition contract rather than creating a second domain owner.
3. Prove normal/loading/empty/error/permission/responsive states plus
   keyboard/focus/screen-reader behavior, CJK rendering, text expansion, and
   font fallback on the same exact head with fresh desktop and mobile evidence.
4. Converge PRD/TRD/ARCHITECTURE/UX/OPERABILITY/TEST_STRATEGY/CHANGELOG and this
   baseline with the actual cutover. Keep ontology labels separate from product
   copy and consume only released owner contracts where another CWL product is
   authoritative.
5. Keep #929 Draft and do not merge, bypass, or release until exact-head gates
   and independent review are complete.

## Traceability

- Product gap: issue #922, `i18n: move UI translations to versioned DB ledger
  and complete 8-locale coverage`.
- Decision: `docs/adr/0362-versioned-ui-translation-ledger.md`.
- Persistence: `migrations/0246_ui_translation_ledger.sql`,
  `migrations/0247_ui_translation_truncate_guard.sql`, and their rollback
  artifacts.
- Read model: `backend/app/translation_ledger.py`.
- HTTP boundary: `backend/app/main.py` (`GET /api/translations/{screen_key}`).
- Verification: `tests/test_translation_ledger_*`,
  `tests/test_translation_screen_value_object.py`,
  `tests/test_translation_api_http.py`,
  `tests/test_translation_api_driver_boundary.py`, and
  `tests/test_translation_documentation_alignment.py`.
- Historical delivery/gap overlays: `docs/product-technical-gap-baseline-history-2026-09-04.md`.
