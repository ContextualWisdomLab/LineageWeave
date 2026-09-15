# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 21:34 KST.
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
prerequisites for the central review/runtime path. On #2170 exact
`c346b8324fa23e23d4007799d26ad3a8ac6ae4c3`, canonical CodeQL producer run
`34921233636` has passed `validate-dispatch` (`104229618015` SUCCESS) and is now
waiting in the actual scan job `104230163129`; coordinator success alone is not
analysis acceptance.

Historical `.github#2140` remains open while current-main successor `.github#2207`
is independently validated. #2207 is now exact
`2d61a668a0d7f0f4bb51c7805945db15e81f0bec` after two rounds of verified review
repair. Active streaming is protected from the idle-socket bound only within the
external job boundary; a job ceiling or separately classified runner-reclamation
event may still terminate the request without becoming a model-failure verdict or
route-ranking signal. First-response-byte silence is now classified only as a
transport-level no-progress observation: it does not prove provider/model failure
or distinguish long time-to-first-byte from transport stall, and occupancy expiry
must not penalise, circuit-break, or rank the route. The changelog carries the same
boundary. A separate review suggestion to replace `012beaac` was rejected after
verification because #2137 uses that value as the target vendored
contextual-orchestrator revision. All receipts from earlier #2207 heads are
historical; successor existence or repaired prose is not complete succession, so
#2140 stays open.

### Leftover-map singular/share and marker-identity stack

#867's production repair remains the foundation: `LeftoverMapPlot` uses
`leftoverMapComparePlotAxisBadge` for comparison-graphic captions, while the
comparison strip retains `leftoverMapCompareAxisBadge`. Both helpers consume only
persisted finite singular/share evidence and keep the two measurements independent.

The #867 branch then advanced non-destructively from `9e9e38da...` to exact
`a81297680bf1b0536227db41fd9596ee42519c0e`. The intervening delta was inspected
rather than treated as a race: it changes only
`frontend/src/leftoverMapAxisBadge.test.ts` (+53/-0) and adds direct Vitest coverage
for the graphic helper's empty, share-only, singular-only (including finite
`σ=0`), and combined states. It does not change production semantics. Current
#867 Tests include queued run `34967080332`; cancelled/skipped sibling attempts are
not acceptance evidence.

Because that parent movement invalidated descendant ancestry assumptions, the
active linear stack was adopted/converged without force-push or destructive
rebase. The current exact ancestry is:

`#867 a8129768... -> #868 d39343ab... -> #869 732ad3b6... ->
#870 fb1eb3cd... -> #871 78ce9469... -> #872 fc9bf9db... ->
#873 c8a5063c... -> #874 f2377692... -> #875 758da1e8...`.

The moved #868-#875 heads keep their own tick/share/singular product deltas while
inheriting the exact #867 executable test blob. Their PR authorities now name the
current parent/head pairs. No predecessor validation receipt transfers, and all
remain Draft pending fresh exact-head repository/security/rendered-accessibility/
performance/review evidence.

The current report/comparison marker stack below #875 was also repaired in the
same turn rather than left conflicted:

- #876 exact `347962092b5887580fce6d2d708d9ae7c950c2a2`: report criterion `ζ`
  consumes only persisted finite item-axis coordinates and fails closed for
  unusable pairs. The prior criterion product/test delta is preserved while the
  exact upstream Vitest blob is inherited. Fresh Tests run `34968725267` is queued.
- #1033 exact `ccf077cf503b4ce3169e44186a07b74ee30ec7f0`: comparison criterion `ζ`
  preserves the #876 boundary after semantic non-force convergence. Fresh Tests
  run `34968819345` is queued.
- #1034 exact `b9dec94a21e47b9ceeb30a3074b6978d17b00958`: comparison post `ξ`
  consumes only persisted finite person-axis coordinates. Fresh Tests run
  `34968872059` is queued.
- sibling #877 exact `ba9101f59743de37f999c3ccf5e0ad0a1a26980d`: comparison origin-tick
  identity remains exact canonical formatted zero while share/σ remain independent.
  Fresh Tests run `34968764771` is pending.

For #876/#877/#1033/#1034 the only upstream semantic movement was the executable
`leftoverMapAxisBadge.test.ts` coverage. Their local product/test files did not
overlap that delta, so convergence used explicit two-parent commits and copied the
exact upstream blob into the child tree before a non-force branch fast-forward.
No child product delta was replaced or force-rebased.

Historical #878/#879 remain open as delta carriers. Their full stale trees are not
replayed over repaired ancestry; #1033/#1034 are the current reconstruction
successors. They may close only after every valid product/test/fixture/contract/
evidence delta is demonstrably inherited and verified.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950...` | Authorization repair remains isolated from central review-runtime owner logic. `.github#2170` producer validation is GREEN but its actual CodeQL scan remains queued; `.github#2207` is now `2d61a668...` after verified ADR/changelog semantic repairs and requires entirely fresh evidence. | Canonical CodeQL producer/receiver settlement, authenticated OpenCode verdict, Strix/Noema owner-path revalidation, qualifying approval and normal protected merge. |
| Comparison-graphic axis σ/share identity | #867 `a8129768...` | Production uses graphic-specific helper rather than strip helper; direct Vitest state coverage now exercises empty/share-only/σ-only/combined states. Current Tests run `34967080332` is queued, not GREEN. | Focused contract + frontend/full repository tests, rendered a11y/i18n evidence, applicable Security/SAST/CodeQL/model review and qualifying approval. |
| Singular/share tick stack | #868 `d39343ab...` -> #875 `758da1e8...` | Descendants contain repaired #867 foundation plus the executable helper-state tests through non-force ancestry; PR authority names current parents/heads. | Settle each local RED and fresh exact-head repository/security/browser-a11y/performance/review evidence in parent order. |
| Report/comparison marker identity | #876 `34796209...` -> #1033 `ccf077cf...` -> #1034 `b9dec94a...` | ζ/ζ/ξ boundaries are preserved after current-parent convergence; new Tests `34968725267`, `34968819345`, `34968872059` are queued. Historical #878/#879 remain open delta carriers. | Focused contracts, frontend build/tests, full repository/PostgreSQL validation, rendered keyboard/focus/a11y evidence, applicable security/model review and qualifying approvals. |
| Comparison origin tick identity | #877 `ba9101f5...` | Exact-zero origin and independent share/σ composition are preserved while the upstream executable badge-state tests are inherited; Tests `34968764771` is pending. | Current-head executable contract, frontend build/tests, rendered keyboard/focus/a11y/i18n, applicable security/model review and qualifying approval. |
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
