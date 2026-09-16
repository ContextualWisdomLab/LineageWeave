# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-17.
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

#974 exact `6911954363888d1e2d523ebbcf68f68d7217752a` owns the Python CodeQL findings. TLS minimum repair and the user-input polynomial-ReDoS repair are present test-first. Exact-head Tests `35033878120`, SAST `35033619322`, and Security `35033619472` are terminal GREEN. CodeQL PR `35033619584` is terminal RED in the compatibility/verdict path: language detection succeeded; python/actions/javascript-typescript compatibility jobs read the current-head dispatch verdict successfully and then failed at `Release runner or enforce current-head CodeQL verdict`; the later `Dispatch current-head CodeQL scan` job succeeded. That record proves a fail-closed required-gate failure but does not by itself establish a new LineageWeave source finding, so reconciliation stays with the canonical central CodeQL owner path rather than a leaf gate bypass. Child #979 is exact `2431fa8cde5927ca9e6afeb2652ff8b01f3f0a85` directly on #974 and inherits no acceptance receipt.

#983 is exact `6519c8e30d261b5427e5db98392ca671eb07a643` and owns frontend post-body parsing plus the coverage closure of LineageWeave-owned buyer surfaces. The quote-aware scanner repair remains rooted at `63a72ef89f5a97aef1e0139430ee659efd8d9478`; hosted predecessor Tests `35082024018` proved that repair was incomplete because the full PostgreSQL suite, frontend lint/build and Storybook were GREEN while Vitest had one quoted-attribute `<br>` functional failure and the unchanged 100% coverage gate also failed. Causal product repair `4800c8180f44bb53feeff82c5d4d116e4c49ea3c` maps structurally parsed `<br>` to `\n\n`, preserving the existing two-segment break contract without changing scanner, list/indent, image allowlist, remote-image, auth, or runtime policy. Preserved coverage artifact `frontend-coverage` id `10449646541`, digest `sha256:8b6e9a23629358930c24cd62191b6d10216d83a4d6cf5f38470c41d6513e4481`, measured lines 3300/3405 (96.91%), statements 3548/3729 (95.14%), functions 1008/1055 (95.54%), and branches 2743/3171 (86.50%). Artifact-selected test-only commit `e5104121ab1f628cd717cf3474b45ca5c8d5a322` covers existing `postBodyDisplay.ts` scanner/script branches without production or gate changes. Test-only commit `6519c8e30d261b5427e5db98392ca671eb07a643` then covers existing OntologyExplorer extension/fallback branches: unknown node/truth codes remain visible, generic node styling is retained, missing callback directions fall back without dropping evidence, unknown evidence-post IDs remain actionable, keyboard edge selection is exercised, and an edge without direct evidence retains explicit provenance guidance. Earlier test-only `816423c46a4b27c42d1369d4d72c02d99eda5df6` covers the artifact-selected `i18n.ts` non-DOM `document` branch. Current descendants are #984 `f8bef6c4c4d49e32b1132eb970264c435ade6c9e`, #992 `7ffb5ca3dec0ebb8a48ac8113222b21576ffee22`, and sibling #985 `d711c5f1dc3bd782757f6bc2652c53c86b638481`, all ordinary/non-force and `behind_by=0` against their direct parent with their pre-existing deltas preserved. Fresh exact-head Tests `35124653513`, SAST `35124653583`, Security `35124653463`, and CodeQL PR `35124653475` are queued; the live boundary review thread remains unresolved and predecessor receipts do not transfer.

### Backend embedded-image structural extraction

#1115 is exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` directly on protected main. It replaces tag-wide embedded-image matching with structural `HTMLParser` attribute handling while retaining the narrow `data:image/*;base64` allowlist, strict base64 decode, remote-image rejection, and provenance position. Review then exposed non-LF offset drift; RED `b2e29b6ade8fb651e27fa50d5580204bd641037c` and causal fix `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` align line starts with `HTMLParser.getpos()` using actual LF positions only. The review thread is resolved/outdated. Exact-head Tests `35065642195` and SAST `35065642221` are terminal GREEN. Security `35065642147` and CodeQL PR `35065642188` remain queued. This is still not repository acceptance because the required security/static-analysis set is incomplete and there is no qualifying exact-head approval.

## Leftover-map report/comparison stack

#866 is exact `6935ac4d3850ae24d23fab76be70fe22102ef4ee` on #865 `0728f56ba66f16783685c84d9d3aa034eea9f143`. Its `App.tsx` buyer-path repair consumes the aggregate four-state `leftoverMapAxisBadge(axis)` projection and omits the badge when persisted singular/share evidence is unusable. Exact-head Tests `35049868360` ended `action_required` without jobs and provide no GREEN receipt.

### Foundation repair and current ancestry

The hosted #875 RED was decomposed into owning-parent contracts and repaired causally without rewriting history.

- #868 `3cbed781b136f494556c4c31a6808f57b0571999` adds the report-graphic singular-tick projection and exact template, using persisted finite non-negative σ only.
- #869 `e395e3f8e988d77c10b1c48cd6f7cdd4d6454d1b` adds the comparison-graphic singular-tick projection, preserving finite `σ=0` and not deriving share.
- #870 `327518f86c647745c159dead5ef5bf18d044b463` adds the comparison-strip singular-tick projection.
- #871 `171355483c5852aac705886230fbc830f6418c29` adds the report-axis singular-tick projection.
- #872 `299bae80c1a961d16bf0213fb797c0fe9f805a17` makes comparison-graphic tick σ/share a four-state projection without deriving either field.
- #873 `052824158509a917d950855268b5e6c2dc236ffd` makes report-graphic tick σ/share a four-state projection. Fresh Tests `35093007592` are queued.
- #874 source repair `f8298afa68d31567818a510388ee82ca6cee9de4` makes comparison-strip tick σ/share four-state; exact branch head `adce3dd85ed645170e457d51924031e7edb9d879` is the ordinary two-parent convergence onto repaired #873. Fresh Tests `35093206837` are queued.
- #875 source repair `b771f634f0878a2bf4743ddedd88bc62f93517bf` makes report-axis tick σ/share four-state; exact branch head `c35287666fec08e533e138e503c407706873e01` is the ordinary two-parent convergence onto repaired #874. Fresh Tests `35093354671` are queued.

No current queued test is counted GREEN and no predecessor receipt transfers. Current ancestry is:

`#867 09ee432b... -> #868 3cbed781... -> #869 e395e3f8... -> #870 327518f8... -> #871 17135548... -> #872 299bae80... -> #873 05282415... -> #874 adce3dd8... -> #875 c3528b76...`

Below #875:

- #876 `88b6d22f...`: report criterion `ζ`, persisted finite item-axis pair only; reconverged ordinary/non-force.
- #1033 `faaaf4b9...`: comparison criterion `ζ`, same item-coordinate boundary with distinct comparison identity; reconverged ordinary/non-force.
- #1034 `c1ad80e4...`: comparison post `ξ`, persisted finite person-axis pair only; reconverged ordinary/non-force.
- sibling #877 `2b3363da9cf868cc1d8121a94e0cf8a357fe8f56`: formatted-zero origin identity with independent share/σ composition. It adopts the repaired report-graphic/comparison-strip/report-axis share foundations while preserving its richer origin-aware comparison-tick projection.

### Fresh hosted RED evidence

#875 predecessor Tests run `35051514644` terminated RED: 13 failures, 1791 passed, 147 skipped, 1 warning. #877 predecessor Tests run `35051594411`, full-suite job `104652962912`, likewise terminated RED: 12 failures, 1795 passed, 147 skipped, 1 warning. These receipts are diagnosis evidence only after later head movements.

The remaining known buyer-visible RED on this stack is #877 i18n/accessibility: eight regular/origin comparison-tick templates are absent from each ko/zh/ja/vi catalog, for 32 missing entries while preserving `{axis}`, `{value}`, `{share}`, and `{singular}`. Foundation source repairs #868 through #875 still require fresh exact-head full/rendered/security evidence before promotion.

### #877 single-writer harness RCA and current writer

The original writer exposed a repository-owned harness defect: system `python -m pytest` was used without the committed test environment, `/usr/bin/python: No module named pytest` was swallowed by `|| true`, and the ephemeral 32-entry patch never reached the product branch. The lane was repaired to use Python 3.12, uv 0.11.28, Rust 1.97.1, `uv sync --frozen --extra dev --extra backend`, fail-closed RED classification, and `uv run --frozen`; the purpose-complete self-deleting workflow step was removed.

After the final parent convergence moved #877 to `2b3363da9cf868cc1d8121a94e0cf8a357fe8f56`, the same single-writer branch was retargeted in place to auxiliary head `2534956fc3a9e4211a8f79364b25c8d3412e4c94`. Current run `35093668549`, job `104785690763`, is queued with `runner_id=0` and `steps=[]`; both exact-head guards target current #877. Older queued runs target predecessor heads and are stale fail-closed evidence only. No competing writer, no-op wake commit, force rewrite, or predecessor receipt transfer was created.

Historical #878/#879 remain open delta/evidence carriers. Their current successor authority is #876 `88b6d22f...` -> #1033 `faaaf4b9...` -> #1034 `c1ad80e4...`; closure still requires complete verified successor inheritance of every valid product, test, fixture, contract, and evidence delta.

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
| Post-body parser and frontend evidence coverage | #983 `6519c8e3...` | Quoted-attribute `<br>` causal source repair remains at `4800c818...`; predecessor artifact `10449646541` measured 96.91% lines / 95.14% statements / 95.54% functions / 86.50% branches. Test-only `e5104121...` covers scanner/script branches and `6519c8e3...` covers OntologyExplorer extension/fallback branches without production/gate changes. Descendants #984 `f8bef6c4...`, #992 `7ffb5ca3...`, #985 `d711c5f1...` are converged `behind_by=0`. Current required workflows are queued and the live review thread remains unresolved. | Fresh exact-head functional regression/full suite, new coverage artifact and continued closure to 100%, rendered/security/CodeQL GREEN and qualifying approval; no denominator/gate weakening. |
| Embedded-image ingestion structural parsing | #1115 `6545b5ff...` | Structural parser and LF-only position repair present; review resolved; exact-head Tests and SAST GREEN; Security and CodeQL queued. | Terminal Security/CodeQL GREEN and qualifying exact-head approval. |
| Dichotomous measurement policy | #902 `9487e029...` | Governed policy delta preserved; direct parent exact; Tests Draft-skipped. | Prerequisite integration, current-head repository/security/governance evidence, approval. |
| Dynamic-evaluation provenance | #915 `e2a00383...` | Projection delta preserved; direct parent exact; Tests Draft-skipped. | Current-head required checks, released-owner integration evidence, approval. |
| Semantic/operator naming | #966 `f93715af...` / #919 `d78390c5...` | Both direct #899 descendants exact and `behind_by=0`; Tests Draft-skipped. | Fresh hosted evidence and independent review after #899 integration/reconvergence. |
| Report-axis σ/share missingness | #866 `6935ac4d...` | Minimum App repair present; exact Tests action_required without jobs. | Fresh frontend/full/rendered/a11y/i18n/security evidence and approval. |
| Comparison-graphic axis σ/share identity | #867 `09ee432b...` | Product/helper delta retained on repaired #866 ancestry. | Fresh repository/rendered/security/review evidence. |
| Singular/share tick foundation | #868 `3cbed781...` -> #869 `e395e3f8...` -> #870 `327518f8...` -> #871 `17135548...` -> #872 `299bae80...` -> #873 `05282415...` -> #874 `adce3dd8...` -> #875 `c3528b76...` | Owning-parent singular/share contracts now have causal source repairs; current #873/#874/#875 Tests are queued, not GREEN. | Fresh exact-head focused/full GREEN for repaired heads, then rendered/browser/a11y/security/performance evidence and qualifying review. |
| Report/comparison marker identity | #876 `88b6d22f...` -> #1033 `faaaf4b9...` -> #1034 `c1ad80e4...` | ζ/ζ/ξ boundaries preserved on current ordinary/non-force ancestry; parent acceptance remains incomplete. | Parent-first exact-head GREEN, then focused/full/rendered/security evidence and approval. |
| Comparison origin/a11y identity | #877 `2b3363da...` | Product origin/share/σ delta preserved on current repaired ancestry; intended 32-entry i18n RED remains. Same single-writer branch is retargeted at `2534956f...`; run `35093668549` / job `104785690763` is queued before source execution. | Prove focused RED -> 32-entry repair -> focused GREEN -> ordinary push on this exact head, then fresh full/rendered/a11y/security evidence plus approval. |
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