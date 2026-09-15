# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 19:04 KST.
>
> Protected `main` is `83eba56149eb802cd63642c507c324c9976ec78e` at this projection.
> This file summarizes live PR/Issue/check authority; protected refs, PRs, Issues,
> ADRs and exact-head receipts remain authoritative. Historical overlays through
> 2026-09-13 are preserved in
> [`evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head.

### Summary shared-catalog authorization

#1079 remains open and Ready at exact
`c2923950e73c88a9f9fd932332ddd47682da124b` on protected
`main@83eba56149eb802cd63642c507c324c9976ec78e`. Its reader materialization path
is fail-closed for shared Customer Master catalog enrichment, while explicit
`post_admin` retains the canonical create/upsert path. Repository, authenticated
PostgreSQL + Keycloak + Valkey, SAST and Required Security evidence are GREEN.

Required CodeQL remains a canonical control-plane wait rather than a LineageWeave
source failure. Coordinator `104180256379` dispatched `.github` producer run
`34922377994`, which remains nonterminal. OpenCode source-tree/coverage evidence
is GREEN but the authenticated exact-head review verdict is unsettled. Strix
failed closed after contextual-orchestrator returned
`concurrency_limit_exceeded`; Noema was cancelled during sidecar provisioning
before a model verdict. LineageWeave must not copy provider routing, queue,
timeout, retry or credential policy to work around those owner paths.

Foundation `.github#2170` and its `.github#1629` reconciliation remain ordered
prerequisites for the central review/runtime path. Historical `.github#2140`
remains open while current-main successor `.github#2207` is independently
validated; successor creation alone is not complete succession.

### Leftover-map singular/share and marker-identity stack

A fresh review found a real product RED in #867. Its executable contract required
comparison-graphic axis evidence to expose independent persisted `σ` and share
states through `leftoverMapComparePlotAxisBadge`, but the production helper was
missing. Exact #867 `6d5562411904ca1e945898fa70c2aad7eaed10f7`
now contains the causal repair: empty/share-only/σ-only/combined states are
composed from persisted values only; finite `σ=0` survives; no square root,
normalization, clamping or cross-inference is introduced. Fresh Tests run
`34954789975` is queued, so this is not yet GREEN release evidence.

Because #867 moved, every active descendant was immediately converged by ordinary
two-parent, non-force commits. The current linear ancestry is:

`#867 6d556241... -> #868 6c7897e9... -> #869 49637c03... ->
#870 6162dbdf... -> #871 2834dd5a... -> #872 beb425a2... ->
#873 7cae3683... -> #874 7dac5923... -> #875 73665d07...`.

No child was force-pushed or destructively rebased, and no predecessor receipt
transfers to a moved exact head. #868-#875 remain Draft because each retains its
own local tick/share/singular contract and requires fresh exact-head repository,
security, rendered accessibility and independent-review evidence before
promotion.

The current report/comparison marker stack below #875 is:

- #876 exact `4290b153db2ea50e78e3b2c4f5e4f37488688644`: report criterion `ζ`
  consumes only persisted finite item-axis coordinates and fails closed for
  unusable pairs.
- #1033 exact `2fb586e408114770e0a054b663002190439d5a5b`: comparison criterion `ζ`
  preserves the #876 boundary on the current repaired ancestry.
- #1034 exact `603e255bc11146495617c44ea7a329233be284e8`: comparison post `ξ`
  consumes only persisted finite person-axis coordinates. Fresh Tests run
  `34955527799` is queued.
- sibling #877 exact `2d859c90cf74c3a011e25b295d7a50a631007bdb`: comparison origin-tick
  identity remains exact canonical formatted zero; share and `σ` are independent,
  and the repaired comparison-axis badge is preserved. Fresh Tests run
  `34955402329` is queued.

Historical #878/#879 remain open as delta carriers. Their full stale trees are not
replayed over repaired ancestry; #1033/#1034 are the current reconstruction
successors. They may close only after every valid product/test/fixture/contract/
evidence delta is demonstrably inherited and verified.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950...` | Authorization repair plus repository/security evidence are GREEN; central CodeQL/model-review settlement is not complete. | Canonical CodeQL producer/receiver settlement, authenticated OpenCode verdict, Strix/Noema owner-path revalidation, qualifying approval and normal protected merge. |
| Comparison-graphic axis σ/share identity | #867 `6d556241...` | Missing production composition helper was repaired causally; fresh Tests `34954789975` is queued. | Focused contract + frontend/full repository tests, rendered a11y/i18n evidence, applicable Security/SAST/CodeQL/model review and qualifying approval. |
| Singular/share tick stack | #868 `6c7897e9...` -> #875 `73665d07...` | All descendants contain the repaired #867 foundation through ordinary non-force merge ancestry; PR bases now point to current parents. | Settle each local RED and fresh exact-head repository/security/browser-a11y/performance/review evidence in parent order. |
| Report/comparison marker identity | #876 `4290b153...` -> #1033 `2fb586e4...` -> #1034 `603e255b...` | ζ/ζ/ξ causal boundaries are preserved on current repaired ancestry; #1034 Tests are queued. Historical #878/#879 remain open delta carriers. | Focused/static contracts, frontend build/tests, full repository/PostgreSQL validation, rendered keyboard/focus/a11y evidence, applicable security/model review and qualifying approvals. |
| Comparison origin tick identity | #877 `2d859c90...` | Exact-zero origin rule and independent share/σ composition survive current-parent convergence; Tests are queued. | Current-head executable contract, frontend build/tests, rendered keyboard/focus/a11y/i18n, applicable security/model review and qualifying approval. |
| Catalog connection leases and summary TOCTOU | #1077 and #1080 | Kept separate from #1079; external/provider work must not hold long database leases and post-provider persistence must revalidate authorization/visibility/source revision. | Causal RED -> GREEN in each owner lane, short-transaction evidence, current-head tests and protected integration. |
| Governed UI translation delivery | #929 and child #932 | Governed versioned translation-ledger work remains in its canonical owner lane; leftover-map work consumes localized labels rather than adding a competing store. | Reviewed `ko/en/ja/zh/vi/es/de/fr` resources plus rendered normal/loading/empty/error/permission/responsive, keyboard/focus/screen-reader, CJK expansion and font-fallback evidence. |
| MCP buyer-path latency | #1009 | Existing measurements remain above the repository `p95 <= 20 ms` acceptance contract. | Representative uncontended measurements, causal query/I/O/runtime profiling, Rust-first hot-path repair where warranted and exact-head gates. |
| Release identity and immutable publication | #961 / #1056 | Candidate release identity work remains Draft; protected main is not release-ready. | Built/installed version proof, normal protected merge, immutable tag/package/release, SBOM/provenance, reproducibility and rollback evidence on one protected SHA. |

## Evidence and ownership rules

Queued, skipped, COMMENTED, rate-limited, status-only, predecessor-head or
source-neutral results are not GREEN evidence for a moved head. A successful
dispatch coordinator proves exact-head handoff only; authenticated producer
execution and consumer settlement must still complete on that same head.

A moved parent invalidates descendant ancestry assumptions immediately. Repair is
non-force: inspect intervening deltas, preserve valid product/contract/test
evidence, then merge/reconstruct/retarget onto the moved parent without rewriting
shared history. Parent GREEN evidence never transfers to the resulting child.

A stale or conflicted PR is not force-rebased or closed merely because a successor
exists. Closure requires complete verified succession of every valid product,
test, fixture, contract and evidence delta, or another explicitly allowed close
condition.

Canonical domain truth stays with its owner. LineageWeave consumes released
contracts/ACLs and does not copy contextual-orchestrator admission/routing,
central CI queue policy, psychometrics implementations, ranking, scheduling or
other owner functionality.

External/model work stays outside long-lived explicit database transactions and
locks. Persistence reacquires the shortest necessary lease, revalidates
authorization/version state and uses idempotent/UPSERT semantics where required.

Material UI requires rendered buyer-path acceptance in addition to unit/repository
evidence: normal/loading/empty/error/permission/responsive behavior,
pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and
applicable p95 evidence.

## Historical evidence

The former append-only baseline through 2026-09-13 remains unchanged at
[`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).
It is provenance, not current authority.
