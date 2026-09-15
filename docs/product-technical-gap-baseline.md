# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 22:04 KST.
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

### Owner-boundary and governed measurement stack

#899 is the canonical LineageWeave consumer-boundary foundation at exact
`d331d1f6b05d39385a652be6dbb8f279871a2e2e` on protected
`main@83eba56149eb802cd63642c507c324c9976ec78e`. Its latest parent delta is a
single `docs/ubiquitous-language.md` Markdown/trailing-whitespace cleanup; the
contextual-orchestrator ownership semantics remain unchanged. #966 has already
converged onto that exact parent at `1be24cd923b89a64f41d05bea8534b552e1ee7bc`.

#902 was still based on predecessor #899 `e5711282...` and GitHub reported it
non-mergeable after the parent moved. The parent delta and #902 both touched the
ubiquitous-language file, so the repair did not choose one side wholesale. Two-parent
non-force convergence `8b5cc45dbb2d6ef7bb3b49a10c33cdfb93b483cc`
retains #899's current Markdown structure and #902's substantive 2PLM
intended-use/recovery-contract wording. Fresh compare now has merge-base exactly
`d331d1f6...`, `behind_by=0`, with the same seven measurement-policy files; #902 is
open / Draft / mergeable / clean. Exact-head Tests `34971343143` is terminal
`skipped` under Draft admission, so it is not product GREEN. Status contexts from
CodeRabbit/Devin are not substituted for a qualifying submitted approval.

#915 depended on the moved #902 and also owned the same ubiquitous-language file.
Two-parent non-force convergence `6540acebbb3ecef4736ebeefa6c0c4486b002b79`
retains the newly converged #902 glossary formatting/2PLM wording plus #915's
dynamic-evaluation vocabulary and adjudication boundary. Fresh compare has
merge-base exactly `8b5cc45...`, `behind_by=0`, and the same 12 dynamic-evaluation
files; #915 is open / Draft / mergeable / clean. Exact-head Tests `34971580315` is
terminal `skipped` under Draft admission, and no qualifying current-head submitted
approval is claimed. No open PR currently targets #915's head branch, so this
ancestry movement has no further active descendant to converge in that lane.

#919 was the remaining direct #899 child one commit behind `d331d1f6...`. Its 14
bounded-operator/test/ADR/changelog files are disjoint from #899's intervening
glossary-only delta. Two-parent non-force convergence
`53dca4bda5dee5d1f4dceb75ea3c53d85bbc8e62` adopts the exact current parent
glossary blob while preserving all local #919 deltas. Fresh compare now has
merge-base exactly `d331d1f6...`, `behind_by=0`, and the same 14 local files; #919
is open / Draft / mergeable. Exact-head Tests `34972516997` is terminal `skipped`
under Draft admission, not GREEN. No open PR currently targets #919's branch.

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
| Contextual-orchestrator consumer boundary and governed measurement/evaluation/operator lineage | #899 `d331d1f6...`; children #902 `8b5cc45d...` -> #915 `6540aceb...`, #919 `53dca4bd...`, and #966 `1be24cd9...` | #902/#915 semantic glossary overlap and disjoint #919 operator delta were converged non-force onto the exact current parent. All are now mergeable Drafts. #902/#915/#919 exact-head Tests are Draft-skipped, not GREEN. | #899 normal integration first, then fresh full repository/security/governance evidence and qualifying independent approvals on unchanged descendant heads; no predecessor receipt transfer. |
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