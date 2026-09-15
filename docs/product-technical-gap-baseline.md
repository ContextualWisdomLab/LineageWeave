# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-16.
>
> Protected `main` observed at `83eba56149eb802cd63642c507c324c9976ec78e`.
> Protected refs, live PRs/Issues, ADRs, exact heads and exact-head receipts are authoritative.
> Historical overlays through 2026-09-13 remain in
> [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head. A moved parent invalidates descendant acceptance evidence. A semantic/non-force convergence preserves valid deltas but never transfers predecessor validation receipts.

### Summary shared-catalog authorization

#1079 remains the Customer Master/shared-catalog authorization candidate at exact `c2923950e73c88a9f9fd932332ddd47682da124b`. Product Tests/SAST/Security are terminal GREEN, but required CodeQL is legitimately RED. Canonical producer run `34922377994` has now completed all actual scans: JavaScript/TypeScript and Python analyses succeeded, then the Medium+ SARIF gates failed; Actions produced no retained product finding. The findings are repository-baseline files outside #1079's 13-file authorization delta, so they are owner work rather than new summary-catalog authorization regressions. Python findings are owned by #974; frontend parser findings are owned by #983. Authority correction is recorded on #1079 as comment `5689248387`. Authenticated OpenCode verdict, complete Strix/Noema owner-path settlement and qualifying independent approval also remain outstanding. Canonical review/runtime queue, provider, timeout, retry and credential behavior stays in `.github` and contextual-orchestrator; LineageWeave does not copy it.

### Commercial-safe synchronous PostgreSQL boundary

#911 remains exact `6030b295aadc3ee76dc4d27f5713273f35888325`. Its test-first pg8000 compatibility repair preserves libpq-style integer `connect_timeout` semantics and treats non-positive values as no-deadline sentinels. Runtime persistence remains `asyncpg`. Exact-head Tests `34978833151`, PROV-O `34978832987`, Ontology Pages `34978833063`, and SAST `34977841093` are terminal GREEN. Security `34977841173` is now terminal `failure`: changed-scope, OSV, Trivy and Scorecard completed successfully, while dependency-review job `104497459473` passed exact checkout/verification, failed `Check dependency review support`, and skipped the pinned Dependency Review action. That is the intended fail-closed shape of the still-open canonical `.github#810` availability/configuration incident, not evidence of a new pg8000/libpq source regression. Fresh downstream owner evidence is recorded in `.github#810` comment `5689139333`. CodeQL PR `34977841115` remains queued, and there is still no qualifying independent exact-head `APPROVED` review. Ready state is validation admission, not merge acceptance.

### Owner-boundary and governed measurement stack

#899 remains the contextual-orchestrator consumer-boundary foundation at `d331d1f6b05d39385a652be6dbb8f279871a2e2e`. Descendant evaluation/measurement lanes remain separate from LineageWeave domain truth. Provider/model/routing behavior stays in contextual-orchestrator; psychometric truth stays in its canonical owners.

#902 is exact `e6e6fed13e8f9273772708167156f7ad16017df4` on #899. Its current causal delta is documentation/changelog-only: it narrows an overstated DRAFT/PILOT scoreless claim to the lifecycle contract the LineageWeave policy object actually enforces. LineageWeave owns the governed rubric/version/lifecycle/activation and observation-policy vocabulary; numerical IRT kernels remain in fast-mlsirm, temporal/event/multilevel measurement semantics in TEPP, and provider/judge execution in contextual-orchestrator. Current-head Tests `35016400830` are terminal `skipped` under Draft admission and are not product GREEN.

#915 was immediately converged after that parent movement. It is exact `e2cbacb775744c14103c3d3043b78ba5ff9bc7e2`, directly based on #902 `e6e6fed13e8f9273772708167156f7ad16017df4`, by an ordinary two-parent convergence preserving the dynamic-evaluation lineage delta. No fresh workflow run is registered for this exact head; predecessor skipped evidence does not transfer. Its projection keeps criterion, observation, adjudication, calibration, promotion, linking and supersession provenance distinct without absorbing contextual-orchestrator execution, fast-mlsirm psychometrics, or TEPP temporal truth.

#966 is mechanically mergeable and Draft at actual Git head `1be24cd923b89a64f41d05bea8534b552e1ee7bc` on current #899 `d331d1f6b05d39385a652be6dbb8f279871a2e2e`. The long-form PR body still opens with an older `e5711282...` / `24a3007...` historical snapshot, so authority correction comment `5687847837` records the live base/head without moving source or inheriting checks. This naming lane must not restore provider aliases or copy contextual-orchestrator source.

### CodeQL baseline security ownership

Canonical producer `34922377994` preserved three immutable SARIF artifacts. Python artifact `10398012754` exposed `py/insecure-protocol` in `lineageweave/http_client.py` and `py/polynomial-redos` in `lineageweave/post_chat.py`; both files belong to active #974 rather than #1079. #974 carried the TLS finding through executable RED `9177894c19339de137aed5fb71dcad9c6a725ec2` and causal fix `0ac8bd5dd85321d84d69782f72aab56e47e33b8b`, explicitly setting a TLS 1.2 minimum while retaining certifi chain and hostname verification. It then carried the user-input regex finding through RED `216e4e3c41161f49b65c48128e8c178790222e3d` and causal fix `6911954363888d1e2d523ebbcf68f68d7217752a`, replacing the end-anchored punctuation regex with linear whitespace normalization plus `.rstrip("?.!")`. These are source-level causal repairs, not current-head GREEN. #974 is Ready for validation admission only: Tests `35033878120`, CodeQL PR `35033619584`, SAST `35033619322`, and Security `35033619472` are all queued on the exact repaired head; earlier Tests `35033619342` was a Draft-event skip and is not acceptance.

#979 was immediately non-force converged after each #974 movement and is now exact `2431fa8cde5927ca9e6afeb2652ff8b01f3f0a85` directly on #974 `6911954363888d1e2d523ebbcf68f68d7217752a`. Its claim-generation/queue/schema delta remains distinct, the parent security files are adopted unchanged, and predecessor receipts do not transfer. There are no open descendants below #979 at this snapshot.

JavaScript artifact `10398331800` exposed four `js/incomplete-multi-character-sanitization` findings in `frontend/src/postBodyDisplay.ts`. #983 already owns that parser/rendering boundary; owner evidence is recorded in comment `5689242771`. The current React rendering path outputs text nodes and explicit `<sup>`/`<sub>` elements rather than `dangerouslySetInnerHTML`, so the SARIF alone does not establish exploitable browser XSS. The regex-as-sanitizer boundary is still a valid hard-gate robustness defect: #983 must add adversarial nested/repeated/encoded-script REDs and replace that boundary with one deterministic parser/tokenizer without breaking scientific script, OOXML indentation/footnote, embedded-image or table semantics. Query suppression or gate weakening is not accepted.

## Active leftover-map foundation finding

#866 remains the active report-axis buyer-path RED at exact `35f4b07fd91a01ce14c31059fa4d46ad3a9ca5a2`, based on #865 `0728f56ba66f16783685c84d9d3aa034eea9f143`. The helper `leftoverMapAxisBadge(axis)` already distinguishes combined, singular-only, share-only and empty evidence, preserves finite `σ=0`, and fails closed for unusable values. The live `frontend/src/App.tsx`, however, still composes `leftoverMapAxisBadgeSingular` and `leftoverMapAxisBadgeShare` directly. When neither persisted datum is usable, the report can still emit a badge shell instead of omitting evidence.

`tests/test_leftover_axis_report_singular_only_contract.py` remains the executable RED. It requires the report path to call `leftoverMapAxisBadge(axis)`, render only non-null projections, and stop importing the two primitive helpers. The minimal causal production fix remains confined to `App.tsx`; it does not alter SQL, persistence, psychometric estimation or a canonical-owner contract.

One-shot run `34997230462` eventually received a GitHub-hosted runner. It verified the exact RED head successfully, then failed in `Apply minimal causal fix` because the automation literal for the import block contained indentation that the real source does not contain. GREEN, commit and push steps were skipped. This is an automation-code RCA, not a product verdict. The workflow was repaired at auxiliary exact `468571288ba8ef45065c188c8d3a28ff2105cf7e` using line-joined exact source blocks and the current checkout action; replacement run `35016883619` / job `104542432409` remains pre-runner queued on `ubuntu-latest` with `runner_id=0` and `steps=[]`. Queued is not GREEN. Same-repository #911 required Security jobs did acquire concrete `ubuntu-24.04` runners during the overlapping interval, so this is not an absolute LineageWeave-wide hosted-runner blackout; it does not by itself distinguish label, concurrency/admission, priority, capacity partitioning, or another owner-plane cause. That narrowed diagnosis is recorded in canonical `.github#712` comment `5689143076`. Once #866 moves, every descendant must converge again from the resulting exact head.

## Current non-force ancestry

The previously stale #866→#867 parent convergence completed successfully in run `34997608532`. #867 is now exact `1d5e0d7aa86ab4d45e9834c5630ae2d9374f46ec`, directly based on current #866 `35f4b07fd91a01ce14c31059fa4d46ad3a9ca5a2`; its comparison-axis σ/share product delta remains intact. This convergence does not pre-adopt the still-pending #866 `App.tsx` repair and transfers no validation receipts.

The live descendant chain is:

`#867 1d5e0d7a... -> #868 de64a973... -> #869 dc3b9fc4... -> #870 0b6a21a0... -> #871 4448ffd1... -> #872 167f63f5... -> #873 41a755cc... -> #874 e75f5ff4... -> #875 8bfc9511...`

Below #875, current exact topology is:

- #876 `6a1c46546fc6b74564af8f7834a17ca6275a5e21`: report criterion `ζ`, persisted finite item-axis pair only.
- #1033 `a29e2979ff85aaee30ad906e577aafdc8dd8e5c2`: comparison criterion `ζ`, same item-coordinate boundary with distinct comparison identity.
- #1034 `f2982aba2e6e15969aa980d4d42b44f822f20ecf`: comparison post `ξ`, persisted finite person-axis pair only.
- sibling #877 `ef776547c3422904f3d1e5119037fad6fb63d3f0`: canonical formatted-zero origin identity with independent share/σ composition, plus a current executable i18n RED.

#877 first exposed a real executable-contract drift during convergence. Production already routed comparison tick accessibility copy through `leftoverMapPlotTickText` and `leftoverMapComparePlotTickAxisBadge`, preserving exact-origin/share/σ evidence, while `tests/test_grouping_comparison_graphic_tick_contract.py` still required the obsolete inline comparison-label ternary and prohibited the comparison tick template. The test was repaired at `8503b0f03d54ce0995e20e9c0149f097b5240e57`, then current #875 was adopted through ordinary two-parent commit `a61db0aa7870f287689b3b1a47f5b8be740ebb72`. Temporary convergence PR #1114 is therefore normally merged, not simply closed.

A fresh unresolved review finding on #877 was then verified against current source rather than accepted blindly. The eight comparison regular/origin tick accessibility templates are defined and passed directly to `tf`, but none is present in the current ko/zh/ja/vi translation catalogs. Existing ordinary leftover-axis tick keys are translated, so the comparison templates fall back to untranslated template strings in non-English accessibility names. This is a current product/a11y/i18n defect, not a cosmetic review note.

Executable RED `tests/test_grouping_comparison_graphic_tick_i18n_contract.py` was added at exact #877 head `ef776547c3422904f3d1e5119037fad6fb63d3f0`. It requires all eight comparison templates in each of the four currently implemented non-English catalogs and verifies every required placeholder is preserved. One-shot run `35019486346` / job `104551325828` remains pre-runner queued on `ubuntu-latest` with `runner_id=0` and `steps=[]` to add the 32 catalog entries and run the focused i18n/tick/origin contracts. The earlier Tests run `35018582871` belongs to predecessor `a61db0aa...` and is no longer acceptance evidence. The broader es/de/fr locale expansion remains governed by the translation-ledger owner lane; #877 only repairs the locales this frontend currently implements.

All current product lanes remain Draft except lanes explicitly promoted only for validation admission. They are converged only to their stated current foundations. When #866 acquires the causal `App.tsx` repair, the full leftover-map descendant chain must converge again. No current descendant receipt can be treated as acceptance for future heads.

Historical #878/#879 remain open delta/evidence carriers. Their succession authority is current with #876 `6a1c4654...`, #1033 `a29e2979...`, and #1034 `f2982aba...`; they are not closed merely because reconstructed successors preserve the intended product contracts. Closure still requires complete verified succession of every valid product, test, fixture, contract and evidence delta.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1079 `c2923950...` | Product Tests/SAST/Security are GREEN. Canonical CodeQL actual scans are terminal RED on repository-baseline Python/JS findings outside #1079's diff; owner repairs are in #974/#983 lanes. | Owner repairs integrated/reconverged, fresh exact-head canonical CodeQL GREEN/compatibility settlement, OpenCode/Strix/Noema settlement, qualifying approval, normal protected merge. |
| Commercial-safe synchronous PostgreSQL tooling | #911 `6030b295...` | Exact-head Tests/PROV-O/Ontology/SAST are GREEN. Security is terminal fail-closed because canonical Dependency Review support could not be established; independent Security jobs are green. | `.github#810` owner repair followed by authoritative exact-head Security GREEN, CodeQL terminal GREEN, and qualifying independent exact-head approval. |
| Ask HTTP/chat security baseline | #974 `69119543...` -> #979 `2431fa8c...` | CodeQL-derived TLS and polynomial-ReDoS REDs have test-first causal source fixes; child is immediately non-force converged. #974 current Tests/SAST/Security/CodeQL runs are queued after validation admission; no GREEN is inherited. | Fresh exact-head Tests/SAST/Security/CodeQL GREEN, provider-boundary regression evidence and qualifying approval before parent-first integration. |
| Post-body parser hardening | #983 `60d2f780...` | Four JS CodeQL multi-character-sanitization findings are assigned to the existing parser/rendering owner; React text sink lowers exploit claim but not the hard-gate defect. | Adversarial parser REDs, deterministic tokenizer/parser causal repair, rendered sup/sub/OOXML/image/table regressions, fresh CodeQL GREEN, descendants converged. |
| Dichotomous measurement-policy boundary | #902 `e6e6fed1...` | Causal docs/changelog repair matches the implemented DRAFT/PILOT/PUBLISHED lifecycle contract; parent #899 is exact. Draft Tests are skipped, not GREEN. | Normal prerequisite integration, fresh repository/security/governance evidence and qualifying exact-head approval. |
| Dynamic-evaluation provenance projection | #915 `e2cbacb7...` | Ordinary two-parent convergence adopts current #902 while preserving the 12-file dynamic-evaluation delta and owner boundaries. | Fresh current-head required checks, released-owner integration evidence and qualifying approval after prerequisites. |
| Semantic operator/API naming continuation | #966 `1be24cd9...` | Actual Git base/head are current with #899; stale opening body snapshot is explicitly superseded by authority comment `5687847837`. | Keep Draft; fresh exact-head hosted evidence and independent review after #899 integration/reconvergence. |
| Report-axis σ/share missingness | #866 `35f4b07...` | Four-state helper and executable RED exist. First repair run confirmed RED then failed in source-application automation; repaired run `35016883619` remains pre-runner queued. | Causal `App.tsx` GREEN, fresh frontend/full/rendered/a11y/i18n/security evidence and qualifying approval. |
| Comparison-graphic axis σ/share identity | #867 `1d5e0d7...` | Product/helper contract retained and current #866 ancestry is converged. | Re-converge after #866 moves, then fresh repository/rendered/security/review evidence. |
| Singular/share tick stack | #868 `de64a973...` -> #875 `8bfc9511...` | Child deltas preserved through ordinary non-force convergence on current #867. | Re-converge after #866 moves; fresh exact-head repository/browser/security/performance/review evidence in parent order. |
| Report/comparison marker identity | #876 `6a1c4654...` -> #1033 `a29e2979...` -> #1034 `f2982aba...` | ζ/ζ/ξ owner boundaries preserved on current ancestry. | Re-converge on foundation movement; focused/full/rendered/security evidence and qualifying approvals. |
| Comparison origin/a11y identity | #877 `ef776547...` | Stale tick-structure contract repaired and #1114 normally merged; new RED proves eight comparison accessibility templates are absent from ko/zh/ja/vi catalogs. Repair run `35019486346` remains pre-runner queued. | Current-head i18n GREEN, fresh executable/rendered/a11y/security evidence and qualifying approval; re-converge on foundation movement. |
| Catalog connection leases and summary TOCTOU | #1077 / #1080 | Separate owner lanes; external/model work must not hold long DB leases. | Causal RED→GREEN, short-transaction evidence and protected integration. |
| Governed UI translation delivery | #929 / #932 | Versioned translation-ledger work remains in its canonical owner lane. | `ko/en/ja/zh/vi/es/de/fr`, normal/loading/empty/error/permission/responsive, keyboard/focus/screen-reader, CJK expansion/font fallback. |
| MCP buyer-path latency | #1009 | Repository target remains p95 ≤ 20 ms where applicable. | Representative measurements and causal profiling; Rust-first hot-path repair if warranted. |
| Release identity and immutable publication | #961 / #1056 | Protected main is not release-ready. | One protected SHA with version/CHANGELOG/tag/package/release, SBOM/provenance, reproducibility and rollback evidence. |

## Evidence and ownership rules

Queued, skipped, COMMENTED, cancelled, rate-limited, status-only, predecessor-head or source-neutral results are not GREEN evidence for a moved head. A successful dispatcher or coordinator proves handoff only; producer execution and consumer settlement must complete on the same exact head.

A moved parent invalidates descendant ancestry immediately. Repair is ordinary/non-force: inspect intervening deltas, preserve valid product/test/fixture/contract evidence, then create a semantic two-parent convergence or safe reconstruction. Force-push, destructive rebase and receipt inheritance are not acceptable substitutes.

A conflicted or stale PR is repaired, not closed by convenience. Closure requires normal merge, complete verified successor inheritance, user direction, no valid delta, or another explicitly permitted condition.

Canonical domain truth stays with its owner. LineageWeave consumes released contracts/ACLs and does not copy contextual-orchestrator routing/admission, central CI queue policy, psychometrics implementations, ranking, scheduling or other owner functionality.

External/model work stays outside long-lived explicit database transactions and locks. Persistence reacquires the shortest necessary lease, revalidates authorization/version state, and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires rendered buyer-path evidence in addition to unit/repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and applicable performance evidence.
