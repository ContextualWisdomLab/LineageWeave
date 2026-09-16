# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-17.
>
> Protected `main` was observed at `83eba56149eb802cd63642c507c324c9976ec78e` before the final protected-ref sweeps for this maintenance turn. Live protected refs, PRs/Issues, ADRs, exact heads and exact-head receipts remain authoritative. Historical overlays through 2026-09-13 live in [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Delivery rules

No release is admitted from the current protected head. A moved parent invalidates descendant acceptance evidence. Ordinary/non-force convergence may preserve valid product/test/fixture/contract deltas, but never transfers validation receipts. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited, or source-neutral results are not GREEN.

LineageWeave consumes released canonical-owner contracts/ACLs and does not copy contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling, or other owner implementations. External/model work stays outside long-lived DB transactions/locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence as well as repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and applicable performance evidence.

## Current foundations

### Customer Master / shared catalog

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the Customer Master/shared-catalog authorization candidate. Product Tests/SAST/Security are GREEN; required CodeQL remains RED on repository-baseline owner findings outside #1079's authorization delta. #1077/#1080 retain separate connection-lease/TOCTOU responsibility. No provider/model execution belongs in Customer Master transactions.

### Commercial PostgreSQL tooling

#911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` has Tests/PROV-O/Ontology/SAST GREEN. Security and CodeQL remain fail-closed at canonical Dependency Review / compatibility-publication owner paths. This is not a new pg8000/libpq source regression.

### Contextual-orchestrator ownership boundary

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` keeps ADR 0300 `Proposed`. Direct/current descendants remain #902 `9487e029...`, #915 `e2a00383...`, #919 `d78390c5...`, and #966 `f93715af...`; their Draft-skipped Tests are not product GREEN. Numerical IRT remains in fast-mlsirm, temporal/multilevel measurement in TEPP, and provider/judge execution in contextual-orchestrator.

### CodeQL baseline / frontend coverage

#974 exact `6911954363888d1e2d523ebbcf68f68d7217752a` owns the Python CodeQL findings. TLS/ReDoS fixes are present; Tests `35033878120`, SAST `35033619322`, Security `35033619472` are GREEN. CodeQL `35033619584` is terminal fail-closed in central compatibility/verdict enforcement even though dispatch handoff succeeded; leaf code does not bypass that owner path. Child #979 `2431fa8c...` inherits no acceptance receipt.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body parsing plus LineageWeave frontend coverage closure. Causal quoted-attribute `<br>` repair remains `4800c8180f44bb53feeff82c5d4d116e4c49ea3c`. Preserved artifact `10449646541` measured 96.91% lines, 95.14% statements, 95.54% functions and 86.50% branches. Test-only slices `816423c4...`, `e5104121...`, `6519c8e3...`, and `f48afbe...` exercise measured branches without production/gate changes.

Current #983 Tests `35130878136` is terminal **cancelled** after about 3h08m with both required jobs `steps=[]`; the frontend job has no downloadable log. That is pre-runner incomplete infrastructure evidence, not a product result. Exact evidence is with canonical Actions owner `.github#712` comment `5704726190`. SAST `35130877960`, Security `35130878012`, CodeQL `35130878009` remain queued. The live product review thread remains unresolved; descendants #984 `0d307987...`, #985 `d7016b4a...`, #992 `538d3237...` inherit no acceptance receipt.

### Embedded-image structural extraction

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` retains structural `HTMLParser` embedded-image extraction, the narrow data-URI allowlist, strict base64 validation, remote-image rejection and LF-correct provenance positioning. Tests `35065642195`, SAST `35065642221`, Security `35065642147` are GREEN; CodeQL `35065642188` is queued and no qualifying current-head approval exists.

## Leftover-map report/comparison stack

### σ/share foundation

The hosted #874 RED was six stale source-text assertions, not a product regression: predecessor tests encoded the obsolete rule that persisted share could not coexist in the same helper/source with persisted σ. The valid contract is four-state empty/share/σ/σ+share with neither field derived from the other.

Concurrent repairs were adopted rather than overwritten:

- #873 `a27c2485a3354214e47bd96eefbb9d97810eea09`: report-graphic four-state product delta plus five shared stale-test repairs. Tests `35150049852` remains queued.
- #874 `d749cdbe57954e62ccad0f317c95e02e48a36c5e`: comparison-strip product repair `f8298afa...`, ordinary adoption `6ddde3d8...`, and the sixth comparison-specific stale-test repair. Tests `35150644199` is **cancelled before runner execution**.
- #875 `582491effefbbe47ad4e32d497117794fef9a887`: report-axis product repair `b771f634...`, ordinary/non-force convergence onto #874. Tests `35151212618` is **cancelled before runner execution**.

Current ancestry is `#867 09ee432b... -> #868 3cbed781... -> #869 e395e3f8... -> #870 327518f8... -> #871 17135548... -> #872 299bae80... -> #873 a27c2485... -> #874 d749cdbe... -> #875 582491ef...`.

### Marker identity and i18n

- #876 `ac19cbcc19590fa132c469f250a8f0c729bfac84`: report criterion ζ, persisted finite item-axis pair only. Tests `35151293427` is **cancelled before runner execution**.
- #1033 `a5538f5f92bc6105e546b3595c7d32e710a95010`: comparison criterion ζ, same item-coordinate boundary with distinct comparison identity. Tests `35151386184` is **cancelled before runner execution**.
- #1034 `e2b6724bd35cab36137d21ab76874fb4a06bccb6`: comparison post ξ, persisted finite person-axis pair only. Two historical review claims were re-verified and resolved rather than implemented: a post without finite person coordinates cannot have a truthful SVG marker without invented geometry, and the rendered comparison marker already composes localized comparison-label copy with the localized shared post action instead of the unused comparison-only string. Executable React/Vitest coverage added at `449a0aa4...` then `e2b6724b...` checks the Korean final `aria-label`, fail-closed plot omission when person coordinates are unavailable, and survival of the pair-button open action. Tests `35154171440` is queued; the remaining source-text-only-test review thread stays open until exact-head GREEN.
- sibling #877 `19856fa60690fdfb9b76c4132923f4d8fd2f4335`: formatted-zero origin identity plus independent share/σ composition. Single-writer commit `d08dafb8...` changed only `frontend/src/i18n.ts`, +32/-0, adding eight regular/origin templates to each ko/zh/ja/vi catalog with placeholders preserved. Writer run `35093668549` / job `104785690763` completed SUCCESS. Ordinary convergence `19856fa6...` preserves that delta. Fresh Tests `35151334447` is **cancelled before runner execution**; predecessor `35135308646` remains the distinct `action_required + jobs=0` admission class.

The predecessor cancellation cluster for #874/#875/#876/#877/#1033/#1034 had both required jobs cancelled without execution steps while those predecessor refs were current. #1034 has since moved to `e2b6724b...` for executable accessibility coverage and now has fresh queued Tests `35154171440`; predecessor cancellation does not transfer. Exact stack-wide infrastructure evidence remains with canonical Actions owner `.github#712` comment `5704801424`; repository branches must not create wake commits or weaken gates. Historical #878/#879 remain open evidence carriers until complete verified successor inheritance is proven, and their authority now points to #1033 `a5538f5f...` / #1034 `e2b6724b...`.

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
| Embedded-image ingestion | #1115 `6545b5ff...` | Tests/SAST/Security GREEN; CodeQL queued. | CodeQL GREEN and exact-head approval. |
| Singular/share tick foundation | #873 `a27c2485...` -> #874 `d749cdbe...` -> #875 `582491ef...` | Six stale contracts repaired; #873 Tests queued, #874/#875 Tests cancelled pre-runner. | Canonical queue recovery, exact-head repository/rendered/a11y/security/performance evidence and review. |
| Report/comparison marker identity | #876 `ac19cbcc...` -> #1033 `a5538f5f...` -> #1034 `e2b6724b...` | ζ/ζ/ξ boundaries preserved; #1034 executable localized/fail-closed a11y coverage added; fresh Tests queued. | #1034 exact-head GREEN, remaining review-thread resolution, then parent-first rendered/security evidence and qualifying approval. |
| Comparison origin/a11y identity | #877 `19856fa6...` | 32-entry ko/zh/ja/vi repair landed and survived convergence; fresh Tests cancelled pre-runner. | Canonical queue recovery, full/rendered/a11y/security evidence and approval. |
| Warning-clean acceptance | #1036/#973; #1035; #1038/#1040; #1037/#1039 | Existing owner lanes retain deprecation/transaction/locale/initdb findings. | Normal integration and warning-free protected evidence; no suppression. |
| Catalog connection leases / TOCTOU | #1077 / #1080 | Separate owner lanes; no long DB lease across external/model work. | Causal RED->GREEN, short-transaction evidence, protected integration. |
| Governed translation delivery | #929 / #932 | Versioned translation-ledger owner lane. | ko/en/ja/zh/vi/es/de/fr plus state/responsive/keyboard/focus/screen-reader/CJK evidence. |
| MCP buyer-path latency | #1009 | Target p95 <= 20 ms where applicable. | Representative cold/authenticated measurements and causal profiling; Rust-first repair when warranted. |
| Release identity / immutable publication | #961 / #1056 | Protected main is not release-ready. | One protected SHA with version/CHANGELOG/tag/package/immutable release, SBOM/provenance, reproducibility and rollback evidence. |
