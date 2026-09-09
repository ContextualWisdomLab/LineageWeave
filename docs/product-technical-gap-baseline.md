# Product & Technical Gap Baseline

> Snapshot refreshed 2026-09-09 KST. Protected `main` is
> `83eba56149eb802cd63642c507c324c9976ec78e`. PR #929 is the active
> ADR 0362 candidate for issue #922 and is open / Ready for exact-head
> validation. Required current-head checks are not yet accepted as terminal GREEN
> and the delivery boundary still requires qualifying independent review. The
> authenticated `GET /api/translations/{screen_key}` API is implemented on the
> candidate branch. That is candidate implementation evidence, not
> protected-main, deployed, or release evidence.
>
> Live self-heads, queue counts, pending jobs, provider/model observations, and
> transient check states are deliberately not promoted into this current
> snapshot: recording them in the same documentation commit makes them stale by
> construction. Current validation authority is the live PR/check/ref state.
> Revision-scoped evidence remains in git history and the dated baseline archive.
>
> Two adjacent candidates remain outside protected `main`: PR #911 at
> `5d40eed35a0b6e0d182397f8d02b29c38e9bdd17` owns the synchronous PostgreSQL
> driver/TLS-policy slice and its live head was reverified for this snapshot;
> PR #909 at `e82aed38c0997588529e21fe0e1bf4159f3c198c` owns malformed Customer
> Master hierarchy presentation. Their validation results remain live-GitHub
> evidence rather than duplicated check-state claims here. Neither candidate
> changes the translation-ledger ownership boundary.
>
> Historical baseline overlays through the preceding snapshot are preserved as
> dated evidence at
> `docs/product-technical-gap-baseline-history-2026-09-04.md`. Historical
> formatting repairs do not promote dated observations into current evidence.
>
> The buyer-visible gap in #922 remains open. Protected `main` still ships the
> production frontend translation source in `frontend/src/i18n.ts` with only
> `en/ko/zh/ja/vi`; `es/de/fr` are not first-class frontend locales. No material
> SPA screen has yet been cut over on protected `main` to a published eight-locale
> ledger resource, and there is no protected-main desktop/mobile evidence
> covering normal, loading, empty, error, permission, responsive,
> keyboard/focus/screen-reader, CJK text expansion, or font fallback states.
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
- Current-head regression coverage includes exact-version query-budget contracts
  for both normal paths: a true cache miss must perform Valkey I/O before any
  PostgreSQL acquisition and use one full PostgreSQL projection; a valid
  candidate must use one digest/key-set query that does not select the full
  localized text projection. Corrupt present candidates retain explicit
  fail-closed fallback coverage and are not misreported as ordinary misses.
  Recursion exhaustion has two independent tests: synthetic fault injection
  preserves exception-classification coverage, while
  `test_translation_cache_recursion_real_payload.py` constructs a depth from
  the running interpreter's recursion limit that exhausts the standard JSON
  decoder, proves `json.loads(raw_payload)` actually raises `RecursionError`, and then
  requires that same wire payload to converge to a cache miss. The
  evidence-contract test prevents later edits from weakening that real-wire
  proof or promoting local/predecessor focused results into current acceptance.
- Any branch movement requires fresh exact-head hosted checks. None of the above
  is release evidence until the unchanged exact PR head has terminal
  required/security checks and qualifying independent approval, then reaches
  protected `main` normally.

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
5. Keep #929 outside merge admission until its unchanged exact head has terminal
   required/security evidence and qualifying independent review. Stacked
   consumer #932 remains a dependent Draft until this foundation reaches
   protected truth and must then be revalidated against that released parent.
   Leftover-pair accessible-name gap #976 waits for the leftover-map
   single-writer owner rather than racing that file.

## Adjacent delivery and collision audit

- The active decisions are non-overlapping: ADR 0362 belongs to the translation
  ledger, ADR 0364 to authenticated browser requests, ADR 0365 to malformed
  Customer Master hierarchy presentation, and ADR 0366 to synchronous
  PostgreSQL TLS. Release-number and ADR-number ownership must be rechecked
  against live refs before promotion; a clean historical merge calculation is
  not transferable evidence.
- The wider open queue still contains dependent report branches with serialized
  release numbers and overlapping historical ADR-number ranges. Those branches
  require ancestor-order convergence and a fresh exact-head ADR/API/schema/
  release audit before merge. A predecessor check cannot transfer acceptance to
  a changed head.
- PR #909's durable scope is the synthetic malformed-hierarchy rendering gap.
  Authenticated PostgreSQL/API and deployed UI evidence remain separate product
  acceptance requirements; its live lifecycle/check state is intentionally not
  duplicated in this baseline.
- Voice-of-X remains governed by ADR 0246/0251: the twelve atomic Voice classes
  stay extensible through evidence-backed combinations. Carrying Posts and
  derivation evidence remain distinct; hidden evidence is never substituted;
  truth status, cutoff, PROV-O derivation, exact-value UI/CSV, and paged JSON-LD
  subject merging are unchanged by these translation candidates.

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

## Latest revision-scoped predecessor evidence

Before this documentation repair, predecessor `6c207f1e9050afa457fbecf46dc8520b99279d0d`
restored the `open / Ready` and #911 snapshot phrases but used `PR #909 owns`
where the executable scoped-entry delimiter requires `PR #909 at`. Current live
#909 was reverified at `e82aed38c0997588529e21fe0e1bf4159f3c198c` before this
repair. Older `1f0f7059...` had terminal Tests, PROV-O, Ontology Pages, and SAST
success while Security and CodeQL remained fail-closed at central owner
boundaries. These receipts explain repair lineage only and do not transfer to
this new head.

## PRD / TRD / UML derivation (durable, non-volatile)

- PRD (issue #922): buyer-visible gap is eight-locale product copy served from
  a versioned ledger. Scope is presentation copy only; ontology labels and
  concept names stay with their canonical owners. Do not invent copy and do
  not count English fallback as translated coverage. First material cutover
  candidate is one complete screen resource for all eight locales, proved in
  normal, loading, empty, error, permission, and responsive states with
  keyboard, focus, screen-reader, CJK expansion, and font-fallback evidence.
- TRD (ADR 0362 Proposed): PostgreSQL is authoritative for screen keys,
  localized text, and immutable publication versions; Valkey is only an exact
  immutable-version read cache with 20 ms bounded optional I/O. Exact-version
  reads admit a cached candidate only after PostgreSQL digest and key-set
  evidence and otherwise converge to one complete PostgreSQL projection.
  `GET /api/translations/{screen_key}` is authenticated; missing publication
  maps to 404, incomplete requested-locale copy maps to 409, and unsupported
  locale, malformed screen identity, and unrepresentable version each map to a
  distinct 422.
- UML (text): `Caller -> GET /api/translations/{screen_key} (backend/app/main.py)`
  authenticates and propagates screen, locale, and version identity;
  `translation_ledger.py` read model admits `ko/en/ja/zh/vi/es/de/fr` value
  projections against PostgreSQL (`0246`/`0247` ledger, publication
  immutability, writer serialization, TRUNCATE guard, rollback path) with
  bounded Valkey candidate admission; focused HTTP, boundary, budget,
  recursion, and evidence-contract tests guard the read path.
- Gap: protected `main` still bundles frontend translation source with only
  five first-class locales and has no material screen cut over to a published
  eight-locale ledger resource. Desktop and mobile state coverage for the
  cutover remains absent on protected `main`.
- Actions: publish one reviewed complete screen resource; cut one material SPA
  screen onto the versioned API under the product composition contract; prove
  the required states on the same exact head with fresh desktop and mobile
  evidence; keep PR #929 outside merge admission until its unchanged exact
  head has terminal required and security evidence plus qualifying independent
  review; keep stacked consumer #932 as a dependent Draft revalidated after
  the foundation reaches protected truth; leave leftover-pair accessible-name
  work to its single-writer owner.

## Exact-head RCA: `e48d52968` (2026-09-09, PR #929)

- Predecessor head `0db7d31da` (octet-bounded cache decoding) failed its Full
  test suite on one regression:
  `test_hung_cache_read_converges_to_miss_within_request_budget` raised
  `TypeError` because `_read_exact_cache` gained a required
  `expected_text_octets` argument the hung-cache contract call does not pass.
  The repair defaults `expected_text_octets` to `None` in
  `_read_exact_cache` and `_decode_cached_screen`: without authoritative copy
  no decoder bound exists, so the candidate converges to a miss instead of
  crashing. The hung-cache budget test is honored unchanged; 97 translation
  tests passed locally before the fast-forward push.
- On `e48d52968` the Full test suite is terminal SUCCESS, as are Frontend
  lint/test/build, noema-review, Analyze python/actions, Semgrep, osv-scan,
  trivy-fs, and Scorecard. Strix was still pending at record time. These are
  hosted receipts for this exact head only and do not transfer.
- Delivery stays BLOCKED on central evidence outside this repository's code:
  dependency-review fails closed on HTTP 403 from the dependency-graph
  compare API (canonical owner `.github#1725`); the three CodeQL
  compatibility shards wait on the central dispatch verdict and rerun by
  design (canonical owner `.github#2040`); opencode-review still reports no
  agent verdict on the current head despite reruns, so the dispatch-owned
  verdict loop remains the only path. No local workflow duplicate was added
  and no gate was bypassed.
- Predecessor head `0889f49b1` receipts (recorded here because its per-head
  RCA stayed local): Full test suite SUCCESS and Frontend SUCCESS after the
  route `:path` and wording alignment; its only failures were the same
  central-owner and transient agent-verdict items.
- Qualifying independent review is still outstanding; terminal merge admission
  is not claimed.
