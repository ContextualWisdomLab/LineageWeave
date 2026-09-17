# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-17.
>
> Live protected refs, PRs/Issues, ADRs, exact heads and exact-head receipts remain authoritative. Historical overlays through 2026-09-13 live in [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve every valid product/test/fixture/contract/evidence delta, but validation receipts never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN.

LineageWeave consumes released canonical-owner contracts/ACLs and does not copy contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions/locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence as well as repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and applicable performance evidence.

## Current foundations

### Customer Master / shared catalog

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the Customer Master/shared-catalog authorization candidate. Product Tests/SAST/Security are GREEN; required CodeQL remains RED on repository-baseline owner findings outside #1079's authorization delta. #1077/#1080 retain separate connection-lease/TOCTOU responsibility. No provider/model execution belongs in Customer Master transactions.

### Governed translation delivery

#929 exact `cb3d42629c30225cb2dec452c4de7100322fa72f` owns the concrete Customer Master eight-locale review candidate. The original RED `eb6eca97df64656ab0bce1e5d3deeaa7c5566760` still requires the exact 37 governed keys across `ko/en/ja/zh/vi/es/de/fr`, 296 nonblank localized values, placeholder parity, no non-English source fallback, replay idempotency, publication completeness and rollback safety; migration 0248 deliberately leaves version 1 in `draft`.

Data-ownership RED `ed23e14b49a7bcef1bcd124e5eb744fb7adb9a86` reproduces the predecessor defect where an already-existing `lineageweave/customer-master` v1 draft could be adopted, overwritten and later deleted by 0248 rollback. The ownership repair establishes `migrations/0247_z_customer_master_translation_seed_ownership.sql` before 0248 with `pending/owned/blocked` ownership and exact per-file `lineageweave.migration_file` provenance from `docker/postgres-init/migrate.sh`. Exact forward 0248 provenance may create a pending target or replay an owned seed but explicitly refuses a blocked target; child ownership checks are scoped to that forward migration so an operator-owned draft remains normally editable. `rollback/0248_customer_master_translation_draft.sql` stamps transaction-local rollback provenance, and only that rollback context requires the root target to be owned before deletion. Ordinary operator deletion remains available outside 0248 rollback. Empty pending/blocked reservations can be released only after the product resource is absent, while any other ownership record keeps the shared boundary fail-closed.

Ownership TEMP-shadow RED `2b7951a0384add445b4c2086337397772dc008e5` covers caller-created `pg_temp.ui_translation_seed_ownership` spoofing the new migration-ownership trigger functions. Repair `92cf139fac69729387e6e3dc744658b9355160d1` pins all three ownership functions to `SET search_path = pg_catalog, public, pg_temp`; `tests/test_customer_master_translation_seed_ownership.py` preserves that real-PostgreSQL regression alongside ordering/provenance, ordinary operator lifecycle, byte-preserving unowned refusal, owned replay/rollback and empty-reservation cleanup.

Fresh review identified the same permanent-vs-TEMP relation-resolution defect in the pre-existing translation-ledger integrity functions. RED `0ea88968ff13b6b5003904a8bc306f5164b4f65b` adds three real-PostgreSQL adversarial paths: TEMP `ui_translation_key`/`ui_translation_text` must not make incomplete permanent copy publishable; TEMP `ui_translation_resource` reporting `draft` must not make published permanent child rows mutable; and a TEMP root must not let `TRUNCATE public.ui_translation_text` bypass immutable published-copy evidence. Causal repairs `ff1084ba6eb6ff02f17745ea1e6fb3abc77895f9` and `ac60da45aa12d8b85a2f4b45a63ce7df4e4cd539` pin `guard_ui_translation_resource_mutation()`, `guard_ui_translation_child_mutation()` and `guard_ui_translation_truncate()` to `pg_catalog, public, pg_temp`. No privilege elevation, source copy or alternate publication authority is introduced.

Replay-concurrency RED `45f11ea2d730e5bb701e045d2c27599d789cde96` adds a real-PostgreSQL overlap where one transaction holds an uncommitted migration-key reservation while a second replay reaches the ownership initializer. Repair `4fdb2945d15fb849bf12143ea3caa4785af1301e` uses `ON CONFLICT (migration_key) DO NOTHING` as the unique-index serialization point, then locks and validates the committed ownership row before locking the product resource. Identity drift, blocked/unowned adoption, pending/resource collision and owned replay remain fail-closed/idempotent; the lock order is ownership then product resource.

A second concurrency RED `1becd50316d9beef74d647975fc2380c23a517f5` covers the next stage of replay: two actual 0248 seed transactions can both observe no Customer Master root before either creates it. The ownership trigger serializes those inserts, but the predecessor loser resumed with a plain root INSERT and could fail on the aggregate unique constraint after the winner committed. Repair `cb3d42629c30225cb2dec452c4de7100322fa72f` makes the root INSERT conflict-idempotent, then re-reads the committed resource under `FOR UPDATE` and continues only when `ui_translation_seed_ownership` proves that exact resource is `owned` by migration 0248. An external/unowned collision remains fail-closed; ownership → product-resource lock order is preserved.

#929 remains Ready-for-validation only. Fresh exact-head Tests `35217912584`, PROV-O `35217912606`, Ontology Pages `35217912616`, SAST `35217912666`, Security `35217912706`, and CodeQL `35217912605` exist on `cb3d4262...`. Tests jobs `105190696580` (Full suite/PostgreSQL) and `105190696884` (Frontend) are queued with `runner_id=0` and `steps=[]` at the latest snapshot. No queued/pending/skipped/predecessor receipt is GREEN and no qualifying current-head independent approval exists. The original migration-ownership review thread remains open pending hosted exact-head GREEN.

Direct consumer #932 has been ordinarily/non-force two-parent converged to `270fa7a7979f9c828c8f244b7a302ca029c883bd` on parent #929 `cb3d4262...` and remains Draft. The convergence preserves the existing consumer tree while inheriting both replay-concurrency regressions/repairs through ancestry only; it does not copy ledger truth into frontend source. Exact-head Tests `35217978564` is terminal `skipped` by Draft admission and is not GREEN. Product-wide locale admission remains the currently complete `ko/en/ja/zh/vi` set; the eight-locale Customer Master ledger is a separate publication contract. The publication thread remains unresolved because a complete and safely owned draft is not qualifying language/product review, immutable publication, hosted PostgreSQL GREEN, or authenticated browser evidence.

### Commercial PostgreSQL tooling

#911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` has Tests/PROV-O/Ontology/SAST GREEN. Security and CodeQL remain fail-closed at canonical Dependency Review / compatibility-publication owner paths. This is not a new pg8000/libpq source regression.

### Contextual-orchestrator ownership boundary

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` keeps ADR 0300 `Proposed`. Direct/current descendants remain #902 `9487e029...`, #915 `e2a00383...`, #919 `d78390c5...`, and #966 `f93715af...`; Draft-skipped Tests are not product GREEN. Numerical IRT remains in fast-mlsirm, temporal/multilevel measurement in TEPP, and provider/judge execution in contextual-orchestrator.

### CodeQL baseline / frontend coverage

#974 exact `6911954363888d1e2d523ebbcf68f68d7217752a` owns the Python CodeQL findings. TLS/ReDoS fixes are present; Tests `35033878120`, SAST `35033619322`, Security `35033619472` are GREEN. CodeQL `35033619584` is terminal fail-closed in central compatibility/verdict enforcement even though dispatch handoff succeeded; leaf code does not bypass that owner path. Child #979 `2431fa8c...` inherits no acceptance receipt.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body parsing plus LineageWeave frontend coverage closure. Causal quoted-attribute `<br>` repair remains `4800c818...`; preserved artifact `10449646541` measured 96.91% lines, 95.14% statements, 95.54% functions and 86.50% branches. Test-only slices `816423c4...`, `e5104121...`, `6519c8e3...`, and `f48afbe...` exercise measured branches without production/gate changes. Tests `35130878136` is terminal cancelled pre-runner; exact evidence is with canonical Actions owner `.github#712` comment `5704726190`. SAST/Security/CodeQL remain queued and the product review thread remains unresolved. Descendants #984/#985/#992 inherit no acceptance receipt.

### Embedded-image structural extraction

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` retains structural `HTMLParser` extraction, narrow data-URI allowlist, strict base64 validation, remote-image rejection and LF-correct provenance positioning. Tests `35065642195`, SAST `35065642221`, and Security `35065642147` are GREEN. Consumer CodeQL `35065642188` is terminal FAILURE only in compatibility/verdict enforcement: exact PR/head/base verification succeeded, authenticated verdict remained `pending`, and dispatch job `104906720511` succeeded. Canonical producer `.github` run `35152871013` is correctly bound and has progressed: `validate-dispatch` job `104985222128` completed SUCCESS on runner `1002002647`; actions `105039317121`, python `105039317130`, and javascript-typescript `105039317150` scan jobs now exist but remain queued pre-runner with `runner_id=0` and `steps=[]`. No SARIF/terminal `codeql-dispatch/*` verdict exists. Owner-path evidence is `.github#1929` comment `5705660388`. Current `.github/main@41c1911549aed53068ad0eb80d1edb4e0a771db1` is eight commits ahead of the previous recorded `d35788d...`; it includes merged #2234, which repairs a SARIF allowlist false positive and reads the dispatch gate result rather than inverting a clean verdict because a wake-only step failed, plus #2217 trusted-path traversal hardening. These owner fixes do not retroactively execute the already-bound #1115 scan jobs, create SARIF, or transfer a fresh compatibility receipt. No qualifying current-head approval exists.

## Leftover-map report/comparison stack

### σ/share foundation

The hosted predecessor #874 RED was six stale source-text assertions, not a product regression. The valid contract is four-state empty/share/σ/σ+share with neither field derived from the other. The predecessor #873 Tests `35150049852` later left runner admission: Full suite `104975772740` completed SUCCESS, while Frontend `104975772417` failed at `Test with coverage`; build/Storybook were skipped after that failure. Therefore the earlier pre-runner diagnosis for that predecessor run is historical only.

Current #873 exact `262700d3936d7e783817f4c6fd008afe119d0b23` is test-only. It adds `frontend/src/leftoverMapPlotAxisSingular.test.ts` (blob `c766dc99d4db9882fdeba0d3f9b3cc94fd44809a`) to execute report/comparison tick empty, σ-only, share-only, σ+share and invalid persisted-value fail-closed branches. Production code, coverage denominator/threshold and owner boundaries are unchanged. Exact-head Tests `35176068027` is queued; Frontend `105057942668` and Full suite `105057942759` remain pre-runner with `runner_id=0`, empty runner identity and `steps=[]`. The three remaining inline threads on #873 were outdated informational observations and are now resolved without source changes. Current queue evidence is maintained in canonical Actions owner `.github#712` comment `5706253600`.

The new test delta has been preserved through ordinary two-parent/non-force convergence, not by tree-discarding merge metadata:

- #873 `262700d3936d7e783817f4c6fd008afe119d0b23` -> #874 `3a191487420fd9d06b4fb35fef5d407e078f152a` (Tests `35179432486` queued).
- #874 `3a191487...` -> #875 `1ac7ddd0637a126c59d0102dcd75a051b059e9f4` (Tests `35179782014` queued).
- #875 `1ac7ddd0...` -> #876 `4be3c382ce18ce6be272efbcdedfdaa66dc334ff` (Tests `35179807983` queued).
- #875 `1ac7ddd0...` -> sibling #877 `edcf5baa051046be448a0b356d01c3543b69408a` (Tests `35180148203` queued).
- #876 `4be3c382...` -> #1033 `38967642e1efbd299dfcd68514c289716edfb597` (Tests `35180490196` queued).
- #1033 `38967642...` -> #1034 `825f47a268c5c31fecaef3537c24b78511823f4d` (Tests `35180509845` queued).

Each convergence tree explicitly carries blob `c766dc99...` at `frontend/src/leftoverMapPlotAxisSingular.test.ts`. No moved-head Tests receipt is GREEN yet.

### Marker identity and i18n

#876 `4be3c382...` retains report criterion ζ from persisted finite item-axis pairs only. #1033 `38967642...` retains comparison criterion ζ on the same item-coordinate boundary with distinct comparison identity. #1034 `825f47a2...` retains comparison post ξ from persisted finite person-axis pairs only: an unplaceable marker is omitted rather than assigned invented geometry, while the pair-button open path remains available. Existing React/Vitest accessibility evidence (`449a0aa4...` -> `e2b6724b...`) exercises Korean final `aria-label` composition, fail-closed plot omission and surviving pair-button action; that evidence is preserved in the moved #1034 tree, but hosted current-head GREEN and review-thread resolution are still required.

Sibling #877 `edcf5baa...` retains formatted-zero origin identity plus independent share/σ composition. Single-writer commit `d08dafb8...` changed only `frontend/src/i18n.ts`, +32/-0, adding eight regular/origin templates to each ko/zh/ja/vi catalog with placeholders preserved. Writer run `35093668549` / job `104785690763` completed SUCCESS. The later parent-convergence commit preserves both this i18n delta and the #873 test blob. Historical #877 receipts (`35151334447` cancelled; `35135308646` action_required/jobs=0) do not transfer.

Historical #878/#879 remain open evidence carriers until complete verified successor inheritance is proven; their authority points to current #1033 `38967642...` / #1034 `825f47a2...`. No historical tree is replayed wholesale over repaired ancestry.

## Warning / operability ownership

Warnings are repaired at existing owners, not filtered:

- OpenTelemetry `LoggingHandler` deprecation: #1036 / PR #973.
- PROV-O explicit-migration transaction warnings: #1035.
- person-projection migration transaction warnings: #1038 / PR #1040 `4d74c32a...`.
- PostgreSQL Alpine locale and initdb local-auth warnings: #1037 / PR #1039; initdb evidence comment `5695341589`.

Expected PostgreSQL constraint-violation `ERROR` records from negative contract tests are intentional and are not warning-cleanliness defects.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Shared-catalog authorization | #1079 `c2923950...` | Product Tests/SAST/Security GREEN; canonical CodeQL owner RED outside authorization delta. | Owner repair integration, fresh CodeQL/model-review settlement, qualifying approval, normal protected merge. |
| Commercial PostgreSQL tooling | #911 `6030b295...` | Tests/PROV-O/Ontology/SAST GREEN; Dependency Review/CodeQL fail closed centrally. | Canonical Security/CodeQL GREEN and approval. |
| CO ownership decision lifecycle | #899 `a2da5875...` | ADR 0300 Proposed; #902/#915/#919/#966 preserved; Draft Tests skipped. | Prerequisite integration, fresh required evidence, approval, then Accepted. |
| Ask HTTP/chat security baseline | #974 `69119543...` -> #979 `2431fa8c...` | TLS/ReDoS fixes; Tests/SAST/Security GREEN; central CodeQL fail-closed. | Canonical CodeQL settlement and approval. |
| Post-body parser / frontend 100% evidence | #983 `f48afbe...` | Functional fix present; previous coverage below 100%; current Tests cancelled pre-runner, other required lanes queued. | Canonical queue recovery, exact-head full/coverage/rendered/security/CodeQL GREEN, review resolution, approval. |
| Embedded-image ingestion | #1115 `6545b5ff...` | Tests/SAST/Security GREEN; consumer CodeQL fail-closed on pending authenticated verdict; producer validation is GREEN, but actions/python/javascript-typescript scan jobs are queued pre-runner. | Canonical scan execution/SARIF and terminal status publication, exact consumer compatibility GREEN, exact-head approval. |
| Singular/share tick foundation | #873 `262700d...` -> #874 `3a191487...` -> #875 `1ac7ddd0...` | Test-only branch-coverage delta is preserved through non-force convergence; all moved-head Tests are queued; #873 stale informational threads are resolved. | Exact-head coverage/full/build/Storybook/rendered/a11y/security/performance evidence and review; no predecessor transfer. |
| Report/comparison marker identity | #876 `4be3c382...` -> #1033 `38967642...` -> #1034 `825f47a2...` | ζ/ζ/ξ boundaries and executable localized/fail-closed a11y evidence are preserved; moved-head Tests queued. | Current-head GREEN, remaining review-thread resolution, parent-first rendered/security evidence and qualifying approval. |
| Comparison origin/a11y identity | #877 `edcf5baa...` | 32-entry ko/zh/ja/vi repair and #873 test blob both preserved; moved-head Tests queued. | Full/rendered/a11y/security evidence and approval. |
| Warning-clean acceptance | #1036/#973; #1035; #1038/#1040; #1037/#1039 | Existing owner lanes retain deprecation/transaction/locale/initdb findings. | Normal integration and warning-free protected evidence; no suppression. |
| Catalog connection leases / TOCTOU | #1077 / #1080 | Separate owner lanes; no long DB lease across external/model work. | Causal RED->GREEN, short-transaction evidence, protected integration. |
| Governed translation delivery | #929 `cb3d4262...` -> #932 `270fa7a7...` | 37×8 Customer Master draft remains unpublished; ownership/TEMP-shadow repairs remain present. Initializer RED `45f11ea2...` is repaired in `4fdb2945...`; seed-root RED `1becd503...` is repaired in `cb3d4262...` with conflict-idempotent root creation and owned-target revalidation. #929 Tests `35217912584` is queued; #932 Tests `35217978564` is Draft-skipped. | Exact-head hosted PostgreSQL/full-suite GREEN, ownership review resolution, fresh current-head review of both concurrency repairs, independent language/product review, immutable publication, authenticated API/browser eight-locale evidence, state/responsive/keyboard/focus/screen-reader/CJK checks, Security/SAST/CodeQL and qualifying approval. |
| MCP buyer-path latency | #1009 | Target p95 <= 20 ms where applicable. | Representative cold/authenticated measurements and causal profiling; Rust-first repair when warranted. |
| Release identity / immutable publication | #961 / #1056 | Protected main is not release-ready. | One protected SHA with version/CHANGELOG/tag/package/immutable release, SBOM/provenance, reproducibility and rollback evidence. |