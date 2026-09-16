# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-16.
>
> Protected `main` observed at `83eba56149eb802cd63642c507c324c9976ec78e`.
> Protected refs, live PRs/Issues, ADRs, exact heads and exact-head receipts are authoritative.
> Historical overlays through 2026-09-13 remain in
> [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head. A moved parent invalidates descendant acceptance evidence. Ordinary/non-force convergence preserves valid deltas but never transfers predecessor validation receipts. Draft-skipped, queued, advisory/comment-only, predecessor-head, or source-neutral results are not GREEN evidence.

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

#974 exact `6911954363888d1e2d523ebbcf68f68d7217752a` owns the Python CodeQL findings. TLS minimum repair and the user-input polynomial-ReDoS repair are present test-first. Exact-head Tests `35033878120`, SAST `35033619322`, and Security `35033619472` are terminal GREEN; CodeQL PR `35033619584` remains queued. Child #979 is exact `2431fa8cde5927ca9e6afeb2652ff8b01f3f0a85` directly on #974 and inherits no acceptance receipt.

#983 is now exact `c3bb8a765fc34cc1f4c6facee1bb926c19bd53f2` and still owns frontend post-body parsing. The production parser repair itself remains at `63a72ef89f5a97aef1e0139430ee659efd8d9478`: deterministic quote-aware parsing covers tag recomposition, nested and outer quoted-`>` cases, embedded-image boundaries, and structural break/block/OOXML-indent handling. Its hosted Tests run `35050376521` then produced useful RED evidence: full PostgreSQL suite job `104649231509` was GREEN, while the frontend job failed only at the unchanged repository-wide 100% coverage gate; lint, build and Storybook were GREEN. Preserved artifact `frontend-coverage` id `10436364175`, digest `sha256:32a5707fa0aa584cd88d08d5def5893e6d2cd6b63a72f1eb011cd33117c76182`, measured lines 3300/3405 (96.91%), statements 3548/3729 (95.14%), functions 1008/1055 (95.54%), and branches 2741/3171 (86.43%). Test-only coverage commits `7881cb6ed8fe563e00821fa7d659bba8d15a993d` and `c3bb8a765fc34cc1f4c6facee1bb926c19bd53f2` cover the occupational-construct missing-placeholder fallback and evidence-layer focus edge states without changing runtime behavior. Current descendants are #984 `81957f047fed1d71ad06c5615f5e7609552ffdfb`, #992 `96b4d2025065ff81aa9d8960f1aaeab9370188ba`, and sibling #985 `283c0b89f99032ef50bdaad175547f691bb3d06a`, all ordinary/non-force and `behind_by=0` against their direct parent. Fresh exact-head Tests `35082024018`, SAST `35082024176`, Security `35082024171`, and CodeQL PR `35082023994` are nonterminal; predecessor receipts do not transfer.

### Backend embedded-image structural extraction

#1115 is exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` directly on protected main. It replaces tag-wide embedded-image matching with structural `HTMLParser` attribute handling while retaining the narrow `data:image/*;base64` allowlist, strict base64 decode, remote-image rejection, and provenance position. Review then exposed non-LF offset drift; RED `b2e29b6ade8fb651e27fa50d5580204bd641037c` and causal fix `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` align line starts with `HTMLParser.getpos()` using actual LF positions only. The review thread is resolved/outdated. Exact-head Tests `35065642195`, Security `35065642147`, SAST `35065642221`, and CodeQL PR `35065642188` remain queued, so the lane is validation-only and not merge-ready.

## Leftover-map report/comparison stack

#866 is exact `6935ac4d3850ae24d23fab76be70fe22102ef4ee` on #865 `0728f56ba66f16783685c84d9d3aa034eea9f143`. Its `App.tsx` buyer-path repair now consumes the aggregate four-state `leftoverMapAxisBadge(axis)` projection and omits the badge when persisted singular/share evidence is unusable. Exact-head Tests `35049868360` ended `action_required` without jobs and provide no GREEN receipt.

Current ordinary/non-force ancestry remains:

`#867 09ee432b... -> #868 fbd637f1... -> #869 0e57921f... -> #870 43260094... -> #871 3427b5e1... -> #872 02bb2393... -> #873 36ed7500... -> #874 a3eff4a5... -> #875 18448d39...`

Below #875:

- #876 `6ef9d151...`: report criterion `ζ`, persisted finite item-axis pair only.
- #1033 `86ea83ba...`: comparison criterion `ζ`, same item-coordinate boundary with distinct comparison identity.
- #1034 `bca51350...`: comparison post `ξ`, persisted finite person-axis pair only.
- sibling #877 `ddaa592ab2b3bbd6a50d267fee3e794f0925448e`: canonical formatted-zero origin identity with independent share/σ composition plus the comparison-tick i18n RED.

### Fresh hosted RED evidence

The queue finally admitted the current stack and produced useful source evidence rather than synthetic status.

#875 Tests run `35051514644` reached the real full suite and terminated RED: 13 failures, 1791 passed, 147 skipped, 1 warning. #877 Tests run `35051594411`, full-suite job `104652962912`, likewise ran in the committed Python 3.12 / uv 0.11.28 / Rust 1.97.1 environment and terminated RED: 12 failures, 1795 passed, 147 skipped, 1 warning.

One #877 failure is the intended buyer-visible i18n contract: eight regular/origin comparison-tick accessibility templates are absent from each ko/zh/ja/vi catalog, for 32 missing entries while preserving `{axis}`, `{value}`, `{share}`, and `{singular}`.

The remaining failures are inherited foundation/test-contract drift rather than evidence that the 32-entry i18n patch alone makes the stack GREEN. They include brittle whole-file/tail negative assertions that are invalid after later valid share composition and expected report/comparison tick helper/copy contracts that have not all reached a coherent parent-first GREEN state. Therefore the next product repair after the current #877 writer settles is foundation-first: classify each #868–#875 failure as stale executable contract versus missing product helper, repair at the owning parent, get focused/full GREEN, then immediately non-force converge #876/#1033/#1034 and sibling #877. No predecessor receipt transfers.

### #877 single-writer harness RCA

The existing single-writer run `35053146771`, job `104657654443`, eventually received a GitHub-hosted Ubuntu runner and checked out exact #877 `ddaa592a...`. It then exposed a repository-owned harness defect:

- the RED probe invoked system `python -m pytest` without installing the committed test environment;
- `/usr/bin/python: No module named pytest` was swallowed by `|| true`, so infrastructure failure masqueraded as expected RED;
- the 32-entry catalog patch existed only in the ephemeral checkout;
- focused GREEN failed for the same missing-pytest cause, so commit/push never ran and product head did not move.

The same lane was causally repaired, not duplicated. Auxiliary head `1b49077a8d26fe198dd23f8bd0eba2ba5cec30c5` now installs Python 3.12, uv 0.11.28, Rust 1.97.1, and `uv sync --frozen --extra dev --extra backend`; runs pytest through `uv run --frozen`; accepts RED only on pytest exit 1 plus the expected missing-translation assertion; fails closed on infrastructure/usage/internal/no-test statuses; retains the exact product-head guard; and removes the purpose-complete self-deleting automation-branch step. Current writer run `35079319154`, job `104739217183`, is queued. Do not add a competing writer, no-op wake commit, unchanged rerun, force rewrite, or predecessor receipt transfer.

Historical #878/#879 remain open delta/evidence carriers. Closure still requires complete verified successor inheritance of every valid product, test, fixture, contract, and evidence delta.

## Warning and operability ownership

Fresh hosted logs also re-proved warnings that must not be suppressed. Owner reconciliation found existing single repair lanes, so duplicate issue #1116 was closed only after its evidence was transferred:

- OpenTelemetry SDK `LoggingHandler` deprecation stays with #1036 / PR #973.
- PROV-O explicit-migration transaction warnings stay with #1035.
- person-projection migration transaction warnings stay with #1038 / PR #1040 exact `4d74c32a23cdc254cf5f4d4e72804fe54aa0f1af`.
- PostgreSQL Alpine locale bootstrap warnings stay with #1037 / PR #1039.
- newly re-observed `initdb: warning: enabling "trust" authentication for local connections` was transferred into #1037 comment `5695341589`; that owner must now prove an explicit supported initdb authentication contract and warning-free exact-head acceptance rather than filter stderr or weaken authentication.

Expected PostgreSQL constraint-violation `ERROR` records produced by negative contract tests are intentional and are not part of warning-cleanliness work.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1079 `c2923950...` | Product Tests/SAST/Security GREEN; canonical CodeQL RED is on repository-baseline owner findings outside #1079 diff. | Integrate/reconverge owner repairs, fresh exact-head canonical CodeQL GREEN/compatibility settlement, model-review settlement, qualifying approval, normal protected merge. |
| Commercial-safe synchronous PostgreSQL tooling | #911 `6030b295...` | Tests/PROV-O/Ontology/SAST GREEN; Dependency Review and CodeQL fail closed at canonical owner paths. | `.github` owner repairs, authoritative exact-head Security/CodeQL GREEN, qualifying approval. |
| Contextual-orchestrator ownership decision lifecycle | #899 `a2da5875...` | ADR 0300 is correctly Proposed; #902/#915/#919/#966 are exact non-force descendants; Draft Tests are skipped, not GREEN. | Normal prerequisite integration, fresh required evidence, qualifying approval; only then Accepted. |
| Ask HTTP/chat security baseline | #974 `69119543...` -> #979 `2431fa8c...` | TLS/ReDoS causal fixes; Tests/SAST/Security GREEN, CodeQL queued. | Fresh CodeQL GREEN and qualifying approval before parent-first integration. |
| Post-body parser hardening | #983 `c3bb8a76...` | Quote-aware source repair remains at `63a72ef8...`; predecessor hosted full suite GREEN, frontend failed only the unchanged 100% coverage gate. Artifact `10436364175` gives exact coverage RED and current head adds two targeted test-only slices. Descendants #984 `81957f04...`, #992 `96b4d202...`, #985 `283c0b89...` are converged. | Fresh current-head 100% frontend/full/rendered/security/CodeQL GREEN and qualifying approval. |
| Embedded-image ingestion structural parsing | #1115 `6545b5ff...` | Structural parser and LF-only position repair present; review resolved; required workflows queued. | Fresh repository/security/static-analysis GREEN and qualifying exact-head approval. |
| Dichotomous measurement policy | #902 `9487e029...` | Governed policy delta preserved; direct parent exact; Tests Draft-skipped. | Prerequisite integration, current-head repository/security/governance evidence, approval. |
| Dynamic-evaluation provenance | #915 `e2a00383...` | Projection delta preserved; direct parent exact; Tests Draft-skipped. | Current-head required checks, released-owner integration evidence, approval. |
| Semantic/operator naming | #966 `f93715af...` / #919 `d78390c5...` | Both direct #899 descendants exact and `behind_by=0`; Tests Draft-skipped. | Fresh hosted evidence and independent review after #899 integration/reconvergence. |
| Report-axis σ/share missingness | #866 `6935ac4d...` | Minimum App repair present; exact Tests action_required without jobs. | Fresh frontend/full/rendered/a11y/i18n/security evidence and approval. |
| Comparison-graphic axis σ/share identity | #867 `09ee432b...` | Product/helper delta retained on repaired #866 ancestry. | Fresh repository/rendered/security/review evidence. |
| Singular/share tick foundation | #868 `fbd637f1...` -> #875 `18448d39...` | Hosted #875 full suite is terminal RED with 13 failures; later valid composition exposed stale/brittle contracts and still-missing helper/copy obligations. | Classify and repair owning parent REDs in order, exact-head focused/full GREEN, then non-force descendant convergence and fresh browser/security/performance/review evidence. |
| Report/comparison marker identity | #876 `6ef9d151...` -> #1033 `86ea83ba...` -> #1034 `bca51350...` | ζ/ζ/ξ boundaries preserved, but parent foundation is RED. | Parent-first repair/convergence, then focused/full/rendered/security evidence and approval. |
| Comparison origin/a11y identity | #877 `ddaa592a...` | Product full suite terminal RED: intended 32-entry i18n failure plus 11 inherited foundation/test-contract failures. Old writer failed from missing pytest; repaired sole writer `35079319154` is queued. | Writer must prove focused RED→32-entry repair→focused GREEN→ordinary push; then foundation convergence and fresh full/rendered/a11y/security evidence plus approval. |
| Warning-clean acceptance harness | #1036/#973; #1035; #1038/#1040; #1037/#1039 | Existing single owner lanes cover telemetry deprecation, transaction ownership, locale, and now initdb local-auth warning. Duplicate #1116 closed after evidence transfer. | Normal integration of owner repairs and fresh protected-path warning-free acceptance; no filtering/suppression. |
| Catalog connection leases / summary TOCTOU | #1077 / #1080 | Separate owner lanes; external/model work must not hold long DB leases. | Causal RED→GREEN, short-transaction evidence, protected integration. |
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
