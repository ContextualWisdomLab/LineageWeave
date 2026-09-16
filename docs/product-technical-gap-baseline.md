# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-17.
>
> Protected `main` observed at `83eba56149eb802cd63642c507c324c9976ec78e` before the final protected-ref sweeps for this maintenance turn.
> Protected refs, live PRs/Issues, ADRs, exact heads and exact-head receipts are authoritative.
> Historical overlays through 2026-09-13 remain in
> [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head. A moved parent invalidates descendant acceptance evidence. Ordinary/non-force convergence preserves valid deltas but never transfers predecessor validation receipts. Draft-skipped, queued, cancelled, advisory/comment-only, predecessor-head, or source-neutral results are not GREEN evidence.

## Current owner and security foundations

### Summary shared-catalog authorization

#1079 remains the Customer Master/shared-catalog authorization candidate at exact `c2923950e73c88a9f9fd932332ddd47682da124b`. Product Tests/SAST/Security are terminal GREEN, but required CodeQL is legitimately RED on repository-baseline files outside #1079's authorization delta. Python findings are owned by #974; frontend parser findings are owned by #983. LineageWeave does not copy canonical review/runtime queue, provider, timeout, retry, credential, or model-routing behavior from `.github` or contextual-orchestrator.

### Commercial-safe synchronous PostgreSQL boundary

#911 remains exact `6030b295aadc3ee76dc4d27f5713273f35888325`. Exact-head Tests, PROV-O, Ontology Pages, and SAST are GREEN. Security is terminal fail-closed because canonical Dependency Review support could not be established, and CodeQL is terminal fail-closed at the canonical compatibility/publication boundary. These are owner-path failures, not a new pg8000/libpq source regression. Ready state is validation admission only.

### Contextual-orchestrator owner boundary and governed measurement stack

#899 is exact `a2da5875525cd0950999487ff8fe7d439284dbd2` on protected main. ADR 0300 is correctly `Proposed`, not prematurely `Accepted`, while the owner-boundary change remains unmerged. Exact-head Tests `35076460845` are Draft-skipped; SAST `35076460791`, Security `35076460767`, and CodeQL PR `35076460779` remain non-accepting.

Current non-force descendants are exact and `behind_by=0` against their direct parents:

- #902 `9487e0299a148a10bfcf7b02110508078843d3ef` on #899, governed dichotomous measurement-policy vocabulary only; numerical IRT remains in fast-mlsirm, temporal/multilevel measurement in TEPP, provider/judge execution in contextual-orchestrator.
- #915 `e2a0038382c7fb4f75f66cad473afef4b9a8353a` on #902, dynamic-evaluation provenance/read-model projection only.
- #919 `d78390c56c9d9abcf4a97d2ffa5477704dcbb465` on #899, bounded Keyman/channel-weight/thread-group/Vision operator policy only.
- #966 `f93715af6cbab2a39c22d7c170df2dc32bcd7456` on #899, semantic operator/API naming continuation only.

Their current Tests receipts are Draft-skipped and do not transfer as product GREEN. No foreign scoring, provider, routing, or psychometric implementation is copied into LineageWeave.

### CodeQL baseline security ownership

#974 exact `6911954363888d1e2d523ebbcf68f68d7217752a` owns the Python CodeQL findings. TLS minimum repair and the user-input polynomial-ReDoS repair are present test-first. Exact-head Tests `35033878120`, SAST `35033619322`, and Security `35033619472` are terminal GREEN. CodeQL PR `35033619584` is terminal RED in the compatibility/verdict path: language detection succeeded; python/actions/javascript-typescript compatibility jobs read the current-head dispatch verdict successfully and then failed at `Release runner or enforce current-head CodeQL verdict`; the later `Dispatch current-head CodeQL scan` job succeeded. That record proves a fail-closed required-gate failure but does not by itself establish a new LineageWeave source finding, so reconciliation stays with the canonical central CodeQL owner path rather than a leaf gate bypass. Child #979 is exact `2431fa8cde5927ca9e6afeb2652ff8b01f3f0a85` directly on #974 and inherits no acceptance receipt.

#983 is exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` and owns frontend post-body parsing plus the coverage closure of LineageWeave-owned buyer surfaces. The quote-aware scanner repair remains rooted at `63a72ef89f5a97aef1e0139430ee659efd8d9478`; hosted predecessor Tests `35082024018` proved that repair was incomplete because the full PostgreSQL suite, frontend lint/build and Storybook were GREEN while Vitest had one quoted-attribute `<br>` functional failure and the unchanged 100% coverage gate also failed. Causal product repair `4800c8180f44bb53feeff82c5d4d116e4c49ea3c` maps structurally parsed `<br>` to `\n\n`, preserving the existing two-segment break contract without changing scanner, list/indent, image allowlist, remote-image, auth, or runtime policy. Preserved coverage artifact `frontend-coverage` id `10449646541`, digest `sha256:8b6e9a23629358930c24cd62191b6d10216d83a4d6cf5f38470c41d6513e4481`, measured lines 3300/3405 (96.91%), statements 3548/3729 (95.14%), functions 1008/1055 (95.54%), and branches 2743/3171 (86.50%). Artifact-selected test-only commits `e5104121ab1f628cd717cf3474b45ca5c8d5a322`, `6519c8e30d261b5427e5db98392ca671eb07a643`, `816423c46a4b27c42d1369d4d72c02d99eda5df6`, and exact head `f48afbe...` exercise measured scanner/script, OntologyExplorer fallback, i18n non-DOM, and catalog initialization/auth-continuation branches without production or gate changes.

#983 Tests `35130878136` is now terminal `cancelled`, not queued. Both required jobs (`104911285691` frontend and `104911285836` full suite) have `steps=[]`; the frontend job has no downloadable log. The run existed from 2026-09-16T17:52:36Z to 21:01:22Z and therefore ended before any runner step executed. This is incomplete infrastructure evidence, not a product-test result. Exact evidence was handed to canonical queue owner `.github#712` in comment `5704726190`. SAST `35130877960`, Security `35130878012`, and CodeQL PR `35130878009` remain queued. The live boundary review thread remains unresolved and predecessor receipts do not transfer. Current descendants remain #984 `0d3079879a96b57c5f0f2849a35eb2542fd251d2`, #992 `538d323786247895fa9ca7cee1fe614dce5ac1e8`, and sibling #985 `d7016b4a1efcee901b22eda58f8682c2bab83fce`, all ordinary/non-force on their direct parents.

### Backend embedded-image structural extraction

#1115 is exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` directly on protected main. It replaces tag-wide embedded-image matching with structural `HTMLParser` attribute handling while retaining the narrow `data:image/*;base64` allowlist, strict base64 decode, remote-image rejection, and provenance position. Review then exposed non-LF offset drift; RED `b2e29b6ade8fb651e27fa50d5580204bd641037c` and causal fix `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` align line starts with `HTMLParser.getpos()` using actual LF positions only. The review thread is resolved/outdated. Exact-head Tests `35065642195`, SAST `35065642221`, and Security `35065642147` are terminal GREEN. CodeQL PR `35065642188` remains queued. This is still not repository acceptance because required CodeQL and qualifying exact-head approval remain outstanding.

## Leftover-map report/comparison stack

#866 is exact `6935ac4d3850ae24d23fab76be70fe22102ef4ee` on #865 `0728f56ba66f16783685c84d9d3aa034eea9f143`. Its `App.tsx` buyer-path repair consumes the aggregate four-state `leftoverMapAxisBadge(axis)` projection and omits the badge when persisted singular/share evidence is unusable. Exact-head Tests `35049868360` ended `action_required` without jobs and provide no GREEN receipt.

### Foundation repair and current ancestry

The hosted #874 RED is now causally classified and repaired without changing product semantics. Tests run `35093206837` had six source-text contract failures because predecessor assertions encoded the obsolete rule that persisted share must be absent from the same helper/source as persisted σ. The current product contract permits four states (empty/share/σ/σ+share) while deriving neither measurement from the other.

Concurrent work was adopted rather than overwritten:

- #873 exact `a27c2485a3354214e47bd96eefbb9d97810eea09` retains the report-graphic four-state product repair and changes five shared stale singular/share contract tests only. Fresh Tests `35150049852` are queued.
- #874 exact `d749cdbe57954e62ccad0f317c95e02e48a36c5e` retains source repair `f8298afa68d31567818a510388ee82ca6cee9de4`, adopts repaired #873 by ordinary two-parent convergence `6ddde3d89fbd71e31c90b99bdeb15f68ac45aff9`, and changes only the sixth comparison-strip-specific stale test at the final head. Fresh Tests `35150644199` are queued.
- #875 exact `582491effefbbe47ad4e32d497117794fef9a887` retains report-axis source repair `b771f634f0878a2bf4743ddedd88bc62f93517bf` and ordinary/non-force adopts repaired #874. Fresh Tests `35151212618` are queued.

Current ancestry is:

`#867 09ee432b... -> #868 3cbed781... -> #869 e395e3f8... -> #870 327518f8... -> #871 17135548... -> #872 299bae80... -> #873 a27c2485... -> #874 d749cdbe... -> #875 582491ef...`

Below #875:

- #876 `ac19cbcc19590fa132c469f250a8f0c729bfac84`: report criterion `ζ`, persisted finite item-axis pair only; ordinary/non-force convergence; Tests `35151293427` queued.
- #1033 `a5538f5f92bc6105e546b3595c7d32e710a95010`: comparison criterion `ζ`, same item-coordinate boundary with distinct comparison identity; ordinary/non-force convergence; Tests `35151386184` queued.
- #1034 `f5b46202080e21e2fa49e79bec280c00ec68ca2d`: comparison post `ξ`, persisted finite person-axis pair only; ordinary/non-force convergence; Tests `35151439831` queued. A valid current accessibility/i18n finding remains open: missing ξ does not yet use the intended localized title-only open action, and the new comparison-post action lacks its own non-English catalog contract. This finding blocks promotion until an executable RED -> causal fix -> GREEN receipt exists.
- sibling #877 `19856fa60690fdfb9b76c4132923f4d8fd2f4335`: formatted-zero origin identity with independent share/σ composition plus the completed i18n repair. Writer commit `d08dafb8bd0a20f9a0c443d2264582cf1ba350c3` changed only `frontend/src/i18n.ts`, +32/-0, adding eight regular/origin templates to each ko/zh/ja/vi catalog with placeholders preserved. The original single-writer run `35093668549` / job `104785690763` completed SUCCESS. Ordinary convergence `19856fa6...` adopts moved #875 without rewriting that delta. Fresh Tests `35151334447` are queued. Predecessor Tests `35135308646` ended `action_required` with zero jobs; that distinct admission failure is recorded in canonical `.github#712` comment `5702844081` and does not authorize the moved head.

Historical #878/#879 remain open delta/evidence carriers. Their current successor authority is #876 `ac19cbcc...` -> #1033 `a5538f5f...` -> #1034 `f5b46202...`; closure still requires complete verified successor inheritance of every valid product, test, fixture, contract, and evidence delta.

No queued or cancelled test is counted GREEN, and no predecessor receipt transfers. Fresh hosted/rendered/a11y/security evidence remains required before this stack can promote.

## Warning and operability ownership

Fresh hosted logs also re-proved warnings that must not be suppressed. Owner reconciliation found existing single repair lanes, so duplicate issue #1116 was closed only after its evidence was transferred:

- OpenTelemetry SDK `LoggingHandler` deprecation stays with #1036 / PR #973.
- PROV-O explicit-migration transaction warnings stay with #1035.
- person-projection migration transaction warnings stay with #1038 / PR #1040 exact `4d74c32a23cdc254cf5f4d4e72804fe54aa0f1af`.
- PostgreSQL Alpine locale bootstrap warnings stay with #1037 / PR #1039.
- `initdb: warning: enabling "trust" authentication for local connections` was transferred into #1037 comment `5695341589`; that owner must prove an explicit supported initdb authentication contract and warning-free exact-head acceptance rather than filter stderr or weaken authentication.

Expected PostgreSQL constraint-violation `ERROR` records produced by negative contract tests are intentional and are not part of warning-cleanliness work.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1079 `c2923950...` | Product Tests/SAST/Security GREEN; canonical CodeQL RED is on repository-baseline owner findings outside #1079 diff. | Integrate/reconverge owner repairs, fresh exact-head canonical CodeQL GREEN/compatibility settlement, model-review settlement, qualifying approval, normal protected merge. |
| Commercial-safe synchronous PostgreSQL tooling | #911 `6030b295...` | Tests/PROV-O/Ontology/SAST GREEN; Dependency Review and CodeQL fail closed at canonical owner paths. | `.github` owner repairs, authoritative exact-head Security/CodeQL GREEN, qualifying approval. |
| Contextual-orchestrator ownership decision lifecycle | #899 `a2da5875...` | ADR 0300 is correctly Proposed; #902/#915/#919/#966 are exact non-force descendants; Draft Tests are skipped, not GREEN. | Normal prerequisite integration, fresh required evidence, qualifying approval; only then Accepted. |
| Ask HTTP/chat security baseline | #974 `69119543...` -> #979 `2431fa8c...` | TLS/ReDoS causal fixes; Tests/SAST/Security GREEN. CodeQL `35033619584` is terminal RED in central compatibility/verdict enforcement after successful verdict read; dispatch handoff job succeeded, so no new leaf source finding is inferred from the job record alone. | Canonical central CodeQL settlement plus fresh exact-head CodeQL GREEN and qualifying approval before parent-first integration. |
| Post-body parser and frontend evidence coverage | #983 `f48afbe...` | Causal `<br>` source repair at `4800c818...`; predecessor coverage artifact measured 96.91/95.14/95.54/86.50%. Current Tests `35130878136` cancelled pre-runner with both jobs `steps=[]`; owner evidence is `.github#712` comment `5704726190`. Other required lanes remain queued. | Restore exact-head Tests evidence through canonical queue owner path, fresh functional/full run and coverage artifact, closure to 100%, rendered/security/CodeQL GREEN and qualifying approval; no denominator/gate weakening. |
| Embedded-image ingestion structural parsing | #1115 `6545b5ff...` | Structural parser and LF-only position repair present; review resolved; exact-head Tests, SAST, and Security GREEN; CodeQL queued. | Terminal CodeQL GREEN and qualifying exact-head approval. |
| Dichotomous measurement policy | #902 `9487e029...` | Governed policy delta preserved; direct parent exact; Tests Draft-skipped. | Prerequisite integration, current-head repository/security/governance evidence, approval. |
| Dynamic-evaluation provenance | #915 `e2a00383...` | Projection delta preserved; direct parent exact; Tests Draft-skipped. | Current-head required checks, released-owner integration evidence, approval. |
| Semantic/operator naming | #966 `f93715af...` / #919 `d78390c5...` | Both direct #899 descendants exact and `behind_by=0`; Tests Draft-skipped. | Fresh hosted evidence and independent review after #899 integration/reconvergence. |
| Report-axis σ/share missingness | #866 `6935ac4d...` | Minimum App repair present; exact Tests action_required without jobs. | Fresh frontend/full/rendered/a11y/i18n/security evidence and approval. |
| Singular/share tick foundation | #873 `a27c2485...` -> #874 `d749cdbe...` -> #875 `582491ef...` | Six stale source-text contracts are repaired without product/gate changes; current Tests are queued. | Exact-head Tests GREEN for repaired heads, then rendered/browser/a11y/security/performance evidence and qualifying review. |
| Report/comparison marker identity | #876 `ac19cbcc...` -> #1033 `a5538f5f...` -> #1034 `f5b46202...` | ζ/ζ/ξ boundaries preserved on current ordinary/non-force ancestry; #1034 still has a valid localized title-only fallback finding. | Repair #1034 accessibility/i18n RED, parent-first exact-head GREEN, then full/rendered/security evidence and approval. |
| Comparison origin/a11y identity | #877 `19856fa6...` | 32-entry ko/zh/ja/vi writer repair landed at `d08dafb8...` and was preserved through non-force parent convergence; fresh Tests queued. | Fresh exact-head full/rendered/a11y/security evidence and qualifying approval; central Actions admission evidence must settle normally. |
| Warning-clean acceptance harness | #1036/#973; #1035; #1038/#1040; #1037/#1039 | Existing single owner lanes cover telemetry deprecation, transaction ownership, locale, and initdb local-auth warning. Duplicate #1116 closed after evidence transfer. | Normal integration of owner repairs and fresh protected-path warning-free acceptance; no filtering/suppression. |
| Catalog connection leases / summary TOCTOU | #1077 / #1080 | Separate owner lanes; external/model work must not hold long DB leases. | Causal RED->GREEN, short-transaction evidence, protected integration. |
| Governed UI translation delivery | #929 / #932 | Versioned translation-ledger work remains in its canonical owner lane. | ko/en/ja/zh/vi/es/de/fr plus state/responsive/keyboard/focus/screen-reader/CJK evidence. |
| MCP buyer-path latency | #1009 | Target remains p95 <= 20 ms where applicable. | Representative cold/authenticated measurements and causal profiling; Rust-first hot-path repair if warranted. |
| Release identity / immutable publication | #961 / #1056 | Protected main is not release-ready. | One protected SHA with version/CHANGELOG/tag/package/immutable release, SBOM/provenance, reproducibility, rollback evidence. |

## Evidence and ownership rules

Queued, skipped, COMMENTED, cancelled, rate-limited, status-only, predecessor-head, or source-neutral results are not GREEN evidence for a moved head. A successful dispatcher proves handoff only; producer execution and consumer settlement must complete on the same exact head.

A moved parent invalidates descendant ancestry immediately. Repair is ordinary/non-force: inspect intervening deltas, preserve valid product/test/fixture/contract evidence, then create semantic two-parent convergence or safe reconstruction. Force-push, destructive rebase, and receipt inheritance are not substitutes.

A conflicted or stale PR is repaired, not closed by convenience. Closure requires normal merge, complete verified successor inheritance, user direction, no valid delta, malicious change, or another explicitly permitted condition.

Canonical domain truth stays with its owner. LineageWeave consumes released contracts/ACLs and does not copy contextual-orchestrator routing/admission, central CI queue policy, psychometrics implementations, ranking, scheduling, or other owner functionality.

External/model work stays outside long-lived explicit database transactions and locks. Persistence reacquires the shortest necessary lease, revalidates authorization/version state, and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires rendered buyer-path evidence in addition to unit/repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback, and applicable performance evidence.
