# Product & Technical Gap Baseline

> Snapshot refreshed 2026-09-05 KST. Protected `main` is
> `83eba56149eb802cd63642c507c324c9976ec78e`. PR #929 is the active
> ADR 0362 candidate for issue #922 and is open / Ready with normal squash
> auto-merge armed. Required current-head checks are not yet accepted as
> terminal GREEN and the delivery boundary still requires qualifying independent
> review. The authenticated
> `GET /api/translations/{screen_key}` API is implemented on the candidate
> branch. That is candidate implementation evidence, not protected-main,
> deployed, or release evidence.
>
> Historical baseline overlays through the preceding snapshot are preserved as
> dated evidence at
> `docs/product-technical-gap-baseline-history-2026-09-04.md`. Historical
> formatting repairs do not promote dated observations into current evidence.
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
  Child-table TRUNCATE performs a nonblocking `SHARE ... NOWAIT` admission on
  `ui_translation_resource` before reading publication state. If a publisher
  already holds the root update lock, lock contention is translated to a
  domain rejection instead of waiting into a child/root lock-order deadlock;
  otherwise the SHARE lock keeps a new publisher from starting until the
  draft-only TRUNCATE decision and statement finish.
- The 0246 rollback keeps its resource lookup dynamic after acquiring the
  resource lock. A retry after a completed empty-foundation rollback therefore
  converges without resolving an already-dropped table, while existing copy
  and post-0246 member locale preferences still reject rollback before DDL.
- `backend/app/translation_ledger.py` admits exactly
  `ko/en/ja/zh/vi/es/de/fr`, returns immutable `TranslationScreen` value
  projections, validates canonical PostgreSQL text/BIGINT identities, admits
  cache hits only after PostgreSQL key-set and SHA-256 value evidence, performs
  no cross-locale fallback, and bounds each optional cache `get`/`set` at 20 ms.
  Exact-version reads perform bounded Valkey candidate I/O without holding a
  PostgreSQL lease. A missing/timed-out/unavailable candidate goes directly to
  one complete PostgreSQL projection. A present candidate is still untrusted:
  one digest/key-set PostgreSQL query admits a valid hit without transferring
  the full localized projection; malformed, identity-mismatched, incomplete,
  extra-key, or value-mismatched candidates are not returned and converge to
  the authoritative full projection after digest admission. Latest-version
  reads remain PostgreSQL-first.
- `GET /api/translations/{screen_key}` is authenticated and propagates exact
  screen/locale/version identity. Missing published resources map to 404;
  incomplete requested-locale copy maps to 409. Unsupported locale, malformed
  screen identity, and an unrepresentable resource version each map to a
  distinct 422 response that tells the caller which request value to correct.
- Focused HTTP and asyncpg-boundary tests cover the route without adding a
  direct `psycopg2` caller. The documentation-alignment contract prevents this
  baseline from regressing to the obsolete claim that the API does not exist.
- Current-head regression evidence includes exact-version query-budget
  contracts for both normal paths: a true cache miss must perform Valkey I/O
  before any PostgreSQL acquisition and use one full PostgreSQL projection; a
  valid candidate must use one digest/key-set query that does not select the
  full localized text projection. Corrupt present candidates retain explicit
  fail-closed fallback coverage and are not misreported as ordinary misses.
  Recursion exhaustion has two independent tests: synthetic fault injection
  preserves exception-classification coverage, while
  `test_translation_cache_recursion_real_payload.py` constructs a depth from
  the running interpreter's recursion limit that exhausts the standard JSON
  decoder on the supported runtime, proves
  `json.loads(raw_payload)` actually raises `RecursionError`, and then requires
  that same wire payload to converge to a cache miss. The evidence-contract test
  prevents later edits from weakening that real-wire proof or promoting a local
  or predecessor focused-pass count into current hosted evidence. Hosted required
  checks are non-terminal, so no exact-head GREEN or focused-pass total is
  claimed for this head.
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
5. Keep #929 on normal auto-merge; do not bypass or release until exact-head
   gates and independent review are complete.

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
  `tests/test_translation_exact_version_query_budget.py`,
  `tests/test_translation_cache_recursion_real_payload.py`,
  `tests/test_translation_wire_evidence_contract.py`,
  `tests/test_translation_screen_value_object.py`,
  `tests/test_translation_api_http.py`,
  `tests/test_translation_api_driver_boundary.py`,
  `tests/test_translation_cache_timeout.py`, and
  `tests/test_translation_documentation_alignment.py`.
- Historical delivery/gap overlays: `docs/product-technical-gap-baseline-history-2026-09-04.md`.
