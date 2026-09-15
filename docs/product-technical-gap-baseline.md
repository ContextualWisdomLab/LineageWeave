# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 21:03 KST.
>
> Protected `main` is `83eba56149eb802cd63642c507c324c9976ec78e` at this projection.
> This file summarizes live PR/Issue/check authority; protected refs, PRs, Issues,
> ADRs and exact-head receipts remain authoritative. Historical overlays through
> 2026-09-13 are preserved in
> [`evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head.

### Summary shared-catalog authorization

#1079 remains open at exact `c2923950e73c88a9f9fd932332ddd47682da124b`
on protected `main@83eba56149eb802cd63642c507c324c9976ec78e`. Its reader
materialization path remains fail-closed for shared Customer Master catalog
enrichment, while explicit `post_admin` retains the canonical create/upsert
path. Central CodeQL/OpenCode/Strix/Noema settlement is still owned outside this
product stack; LineageWeave must not copy provider routing, queue, timeout, retry
or credential policy to work around those owner paths.

Foundation `.github#2170` and its `.github#1629` reconciliation remain ordered
prerequisites for the central review/runtime path. Historical `.github#2140`
remains open while current-main successor `.github#2207` is independently
validated; successor creation alone is not complete succession.

### Leftover-map singular/share and marker-identity stack

A current-head review on #867 found that the newly introduced
`leftoverMapComparePlotAxisBadge` helper was not actually wired to the comparison
graphic. The component still mapped axis evidence through
`leftoverMapCompareAxisBadge`, which is comparison-strip copy. A realistic source
contract was first added at `e4670959cca60a94bc0ebf54a503f3b4d38d535d` to
require graphic-specific wiring, making the predecessor implementation RED.
Production head `9e9e38dab1120585d41cb4f2ee81778689b0256a` then switched
`LeftoverMapPlot` to `leftoverMapComparePlotAxisBadge` and documented the touched
production helpers. The graphic and strip surfaces therefore keep distinct copy
while both consume only persisted finite singular/share evidence.

Fresh #867 Tests are not GREEN yet: run `34965610236` is queued, a newer attempt
was cancelled, and another attempt was skipped. Neither cancellation nor skip is
acceptance evidence.

Because #867 moved, the active descendant stack was reconverged immediately by
normal merge PRs, without force-push or destructive rebase. The current linear
ancestry is:

`#867 9e9e38da... -> #868 933d4627... -> #869 26b9ce48... ->
#870 4d7e6404... -> #871 ddcba830... -> #872 ea26581b... ->
#873 bc03c627... -> #874 c5abdfc2... -> #875 4e90d973...`.

Convergence PRs #1085 through #1092 were normally merged in parent order. No
predecessor validation receipt transfers to any moved exact head. #868-#875 stay
Draft because each retains its own local tick/share/singular contract and still
requires fresh exact-head repository, security, rendered accessibility and
independent-review evidence before promotion.

The current report/comparison marker stack below #875 is:

- #876 exact `a9cefd596d0a4eb94281eccbadd1b24ce3ff6a1f`: report criterion `ζ`
  consumes only persisted finite item-axis coordinates and fails closed for
  unusable pairs. It adopted #875 through normal convergence PR #1093.
- #1033 exact `549db716caf71f3581bfa8cd96768212665feb6b`: comparison criterion `ζ`
  preserves the #876 boundary after normal convergence PR #1094.
- #1034 exact `0171755fc42dd30842a0245eb13430981426bd10`: comparison post `ξ`
  consumes only persisted finite person-axis coordinates after normal convergence
  PR #1095. Fresh Tests run `34966164590` is queued.
- sibling #877 exact `a0a2b6f7fa3a5b905e31a7fae21a26dcc1aead5d`: comparison origin-tick
  identity remains exact canonical formatted zero. Because #877 and #867 both
  touch `LeftoverMapPlot`, the parent change required semantic conflict repair:
  the graphic-specific axis-badge wiring and executable wiring contract were
  applied without removing the origin-tick delta, then a two-parent non-force
  merge commit completed convergence PR #1096. Fresh Tests run `34966416325` is
  queued.

Historical #878/#879 remain open as delta carriers. Their full stale trees are not
replayed over repaired ancestry; #1033/#1034 are the current reconstruction
successors. They may close only after every valid product/test/fixture/contract/
evidence delta is demonstrably inherited and verified.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950...` | Authorization repair remains isolated from central review-runtime owner logic. | Canonical CodeQL producer/receiver settlement, authenticated OpenCode verdict, Strix/Noema owner-path revalidation, qualifying approval and normal protected merge. |
| Comparison-graphic axis σ/share identity | #867 `9e9e38da...` | Review finding reproduced by source contract, production now uses graphic-specific helper rather than strip helper; current Tests are queued/skipped/cancelled, not GREEN. | Focused contract + frontend/full repository tests, rendered a11y/i18n evidence, applicable Security/SAST/CodeQL/model review and qualifying approval. |
| Singular/share tick stack | #868 `933d4627...` -> #875 `4e90d973...` | Descendants contain repaired #867 foundation through normal non-force merge ancestry and PR authority now names current parents/heads. | Settle each local RED and fresh exact-head repository/security/browser-a11y/performance/review evidence in parent order. |
| Report/comparison marker identity | #876 `a9cefd59...` -> #1033 `549db716...` -> #1034 `0171755f...` | ζ/ζ/ξ boundaries are preserved on repaired ancestry; #1034 Tests `34966164590` are queued. Historical #878/#879 remain open delta carriers. | Focused contracts, frontend build/tests, full repository/PostgreSQL validation, rendered keyboard/focus/a11y evidence, applicable security/model review and qualifying approvals. |
| Comparison origin tick identity | #877 `a0a2b6f7...` | Semantic conflict repair preserves exact-zero origin, independent share/σ composition, graphic-specific axis badge copy and its executable wiring contract; Tests `34966416325` are queued. | Current-head executable contract, frontend build/tests, rendered keyboard/focus/a11y/i18n, applicable security/model review and qualifying approval. |
| Catalog connection leases and summary TOCTOU | #1077 and #1080 | Kept separate from #1079; external/provider work must not hold long database leases and post-provider persistence must revalidate authorization/visibility/source revision. | Causal RED -> GREEN in each owner lane, short-transaction evidence, current-head tests and protected integration. |
| Governed UI translation delivery | #929 and child #932 | Governed versioned translation-ledger work remains in its canonical owner lane; leftover-map work consumes localized labels rather than adding a competing store. | Reviewed `ko/en/ja/zh/vi/es/de/fr` resources plus rendered normal/loading/empty/error/permission/responsive, keyboard/focus/screen-reader, CJK expansion and font-fallback evidence. |
| MCP buyer-path latency | #1009 | Existing measurements remain above the repository `p95 <= 20 ms` acceptance contract. | Representative uncontended measurements, causal query/I/O/runtime profiling, Rust-first hot-path repair where warranted and exact-head gates. |
| Release identity and immutable publication | #961 / #1056 | Candidate release identity work remains Draft; protected main is not release-ready. | Built/installed version proof, normal protected merge, immutable tag/package/release, SBOM/provenance, reproducibility and rollback evidence on one protected SHA. |

## Evidence and ownership rules

Queued, skipped, COMMENTED, cancelled, rate-limited, status-only,
predecessor-head or source-neutral results are not GREEN evidence for a moved
head. A successful dispatch coordinator proves exact-head handoff only;
authenticated producer execution and consumer settlement must still complete on
that same head.

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
