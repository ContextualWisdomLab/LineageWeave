# Product & Technical Gap Baseline

> Snapshot refreshed 2026-09-05 KST. Protected `main` is
> `83eba56149eb802cd63642c507c324c9976ec78e`. PR #929 is the active
> ADR 0362 candidate for issue #922 and is open / Ready for exact-head
> validation. Required current-head checks are not yet accepted as terminal GREEN
> and the delivery boundary still requires qualifying independent review. The
> live non-identifying queue snapshot contains 120 open PRs and 16 open issues;
> those counts describe coordination load, not product maturity or release
> readiness. The authenticated `GET /api/translations/{screen_key}` API is
> implemented on the candidate branch. That is candidate implementation
> evidence, not protected-main, deployed, or release evidence.
> A stacked Customer Master consumer candidate now exists at exact head
> `cb093960d43e95cdfb1d9ed491e920e2106305db` on top of PR #929's
> exact head `f07a755972e38b4b2a961ab11acd9d3abb229967`. It admits all eight
> locale tags, fetches the authenticated `customer-master` resource before
> customer data, rejects incomplete screen projections, ignores late responses
> from a previous locale or authorization identity, and shows an actionable
> retry state instead of
> rendering bundled Customer Master copy. Review `5119233938` found that the
> retry shell incorrectly diagnosed every transport/auth/permission/not-found/
> service exception as an unpublished translation. RED
> `fd3f0326f539f23dfae75fc3511722ead4455d36` and causal repair
> `cb093960d43e95cdfb1d9ed491e920e2106305db` keep that unclassified failure
> cause-neutral while retaining one concrete retry action. This stacked branch
> is not protected-main, hosted-product-GREEN, authenticated PostgreSQL, or
> deployed evidence.
> Current-head local evidence is 59 frontend test files / 538 tests, lint,
> production build, Storybook build, nine focused Python contract tests, and
> freshly inspected 1440 x 900 plus 390 x 844 retry-state captures. These local
> results do not satisfy the protected delivery boundary.
>
> Two adjacent candidates remain outside protected `main`: PR #911 at
> `5d40eed35a0b6e0d182397f8d02b29c38e9bdd17` replaces the synchronous
> PostgreSQL driver and defaults omitted TLS policy to identity verification;
> PR #909 at `e82aed38c0997588529e21fe0e1bf4159f3c198c` keeps authorized Customer
> Master records visible when imported hierarchy edges are malformed and adds
> synthetic desktop/mobile Storybook evidence. #911 is Ready for exact-head
> validation after moving its colliding TLS ADR to Proposed ADR 0366. Its
> repository-local Tests, PROV-O, and Ontology Pages runs are successful, while
> central Security/CodeQL/SAST remain queued. #909 is Draft because #922's
> eight-locale published-resource cutover and the required current-head
> material-UI/runtime evidence are still absent. Neither has qualifying
> independent current-head approval, and neither is protected-main or deployed
> evidence.
>
> Historical baseline overlays through the preceding snapshot are preserved as
> dated evidence at
> `docs/product-technical-gap-baseline-history-2026-09-04.md`. Historical
> formatting repairs do not promote dated observations into current evidence.
>
> The buyer-visible gap in #922 remains open. Protected `main` still ships the
> production frontend translation source in `frontend/src/i18n.ts` with only
> `en/ko/zh/ja/vi`; `es/de/fr` are not first-class frontend locales. No material
> SPA screen has yet been released on a published eight-locale ledger resource.
> The stacked Customer Master candidate covers API admission plus loading and
> retry rendering. The 1440×900 and 390×844 Storybook captures were regenerated
> and inspected after the current auth-bound/cause-neutral repair. They prove
> only the synthetic retry shell, not authenticated browser acceptance. The
> candidate does not contain reviewed eight-locale
> product copy or authenticated PostgreSQL normal/empty/permission evidence.
> There is no release evidence for normal, loading, empty, error, permission,
> responsive, keyboard/focus/screen-reader, CJK text expansion, or font fallback
> states.
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
- The Customer Master consumer does not reinterpret those backend failure
  categories when the fetch promise is caught generically. Until a typed
  frontend failure contract is introduced, its retry shell says only that the
  selected-language screen could not be loaded, retries the request first, and
  asks an administrator to check access and publication status only if the
  failure persists. It does not assert that publication is missing.
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
- The stacked Customer Master consumer has no new ADR number, migration, API
  route, schema object, or release number. It extends ADR 0362 and consumes the
  route owned by #929, avoiding collisions with ADRs 0364–0366 and the
  serialized report-release stack.

## Next buyer cut

1. Use reviewed product copy to create and publish one complete screen resource
   for all eight locales. Do not invent copy to satisfy coverage.
2. Finish the stacked Customer Master cutover by publishing reviewed product
   copy for its declared keys in all eight locales and proving the authenticated
   PostgreSQL/API normal path. The consumer and fail-closed loading/retry gate
   exist only as branch evidence.
3. Prove normal/loading/empty/error/permission/responsive states plus
   keyboard/focus/screen-reader behavior, CJK rendering, text expansion, and
   font fallback on the same exact head with fresh desktop and mobile evidence.
   Include the small loading/retry shell in locale and text-expansion review;
   its English source copy is not evidence of eight-locale behavior.
4. Converge PRD/TRD/ARCHITECTURE/UX/OPERABILITY/TEST_STRATEGY/CHANGELOG and this
   baseline with the actual cutover. Keep ontology labels separate from product
   copy and consume only released owner contracts where another CWL product is
   authoritative.
5. Keep #929 in the Ready validation lane while this exact head is evaluated.
   Normal merge or release still requires terminal required/security gates and
   the qualifying independent review; do not bypass or inherit predecessor
   evidence.

## Adjacent delivery and collision audit

- The active decisions are non-overlapping: ADR 0362 belongs to the translation
  ledger, ADR 0364 to authenticated browser requests, ADR 0365 to malformed
  Customer Master hierarchy presentation, and ADR 0366 to synchronous
  PostgreSQL TLS. PR #911 removed its colliding ADR 0363 before re-entering
  review. It alone adds the `2.28.0` changelog fragment; #909 and #929 do not
  claim that release number.
- The wider open queue still contains dependent report branches with serialized
  release numbers and overlapping historical ADR-number ranges. Those branches
  require ancestor-order convergence and a fresh exact-head ADR/API/schema/
  release audit before merge. A clean local merge calculation or predecessor
  check cannot transfer acceptance to a changed head.
- PR #909 closes only the synthetic rendering gap: lint, focused regressions,
  Storybook build, and 320 x 568 plus desktop visual audits passed on its exact
  head. Authenticated PostgreSQL/API and deployed UI evidence are absent, so the
  product acceptance condition remains explicitly unavailable and the PR stays
  Draft behind #922.
- Voice-of-X remains governed by ADR 0246/0251: the twelve atomic Voice classes
  stay extensible through evidence-backed combinations. Carrying Posts and
  derivation evidence remain distinct; hidden evidence is never substituted;
  truth status, cutoff, PROV-O derivation, exact-value UI/CSV, and paged JSON-LD
  subject merging are unchanged by these three candidates.

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
- Stacked Customer Master consumer: `frontend/src/api.ts`,
  `frontend/src/i18n.ts`, `frontend/src/App.tsx`,
  `frontend/src/components/ScreenTranslationGate.tsx`,
  `frontend/src/components/ScreenTranslationGate.test.tsx`, and
  `tests/test_customer_master_translation_auth_gate_contract.py`; current-head
  synthetic visual evidence is
  `docs/screenshots/customer-master-translation-gate-{desktop,mobile}.png`.
- Historical delivery/gap overlays: `docs/product-technical-gap-baseline-history-2026-09-04.md`.
