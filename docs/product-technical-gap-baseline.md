# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15.
>
> Protected `main` is `83eba56149eb802cd63642c507c324c9976ec78e`.
> This file is a current projection of live PR/Issue/check authority, not a
> substitute for those sources. Historical overlays through 2026-09-13 are
> preserved in
> [`evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).
> When this projection differs from live GitHub state, protected refs, PRs,
> Issues, ADRs and exact-head check receipts win.

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head.

### Summary shared-catalog authorization

#1079 remains open, Ready and mechanically mergeable at exact
`c2923950e73c88a9f9fd932332ddd47682da124b` on protected
`main@83eba56149eb802cd63642c507c324c9976ec78e`. Reader materialization is
fail-closed for shared Customer Master catalog enrichment and explicit
`post_admin` retains the canonical create/upsert path. Exact-head repository,
authenticated PostgreSQL + Keycloak + Valkey integration, SAST and Required
Security evidence are GREEN. CodeRabbit's protected-base-to-head full-diff
review reported no actionable findings, but that is not a submitted qualifying
`APPROVED` review.

Required CodeQL remains fail-closed, not source-failed. Compatibility receivers
failed after finding no authenticated current-head producer verdict. Coordinator
`104180256379` completed the exact consumer-head dispatch successfully and created
canonical `.github` producer run `34922377994`; that producer is still queued at
the current sweep. Producer validation/execution, authenticated terminal verdict
publication and fresh compatibility settlement remain required. The CodeQL
control plane stays owned by the canonical `.github` lane.

OpenCode source-tree and coverage evidence are GREEN, while `opencode-review`
failed closed because no authenticated exact-head review verdict had materialized.
Strix produced zero findings but correctly failed closed after contextual-
orchestrator rejected concurrent sub-agent work with explicit
`concurrency_limit_exceeded`; incomplete provider execution is not GREEN. Noema
never reached a model verdict because contextual-orchestrator sidecar provisioning
occupied the runner until cancellation. These are canonical review-runtime /
provider-admission problems, not authorization-source findings in LineageWeave.

Foundation prerequisite `.github#2170` remains open/Ready/mergeable at exact
`c346b8324fa23e23d4007799d26ad3a8ac6ae4c3` on protected
`.github/main@91be6442906c7b6b4f600272c953699708394327`. Runtime Quality, SAST,
Python Security, Security, Noema, Strix, OpenCode bootstrap, OpenCode source-tree
and coverage evidence, latest queue scan, CodeQL language detection and the
CodeQL coordinator are GREEN, and a current-head Noema `APPROVED` review exists.
Canonical producer run `34921233636` is still at producer validation; OpenCode
review publication is also unsettled. Required ordering therefore remains
`.github#2170` normal protected integration -> ordinary/non-force `.github#1629`
reconciliation -> fresh #1629 acceptance. LineageWeave must not copy dependency
predicates, queue policy, provider/model routing, fallback or timeout semantics.

The stale `.github#2140` decision-record lane remains open while current-main Draft
successor `.github#2207` is independently revalidated. A replacement branch is
not complete succession by itself.

### Leftover-map identity and evidence stack

Parent #875 moved to exact
`b220dcb8d73f6bdc926c5d8cb1ae3f47df05100c` on current #874
`2b49e327b02a2b9f8b1449ae4b5a68648849e227`. The moved parent was not treated
as a race or rewritten. Direct children were read, their local deltas preserved,
and their ancestry converged through ordinary non-force two-parent commits.

#876 is now exact `2c12c30b54ca1cbb74a9ec8829dcb68314ccee6d` on current #875.
Semantic convergence PR #1081 was normally recognized as merged at that commit;
it was not simply closed. The branch preserves the report-criterion ζ contract:
`leftoverMapPlotCriterionBadge` consumes only persisted finite item axes, keeps
finite zero coordinates, fails closed for unusable pairs and does not infer ζ
from person ξ, geometry, distance, rank, coverage or neighboring evidence. It
also inherits #875's independent persisted comparison-axis singular evidence.
Fresh exact-head Tests run `34943676800` is queued. Predecessor validation does
not transfer.

#1033 is now exact `d69b339f71a5a3bca9fb84aae663e2aae0eda739` on current #876.
It preserves the report criterion boundary and adds the distinct comparison-
criterion ζ boundary through `leftoverMapComparePlotCriterionBadge`, again using
only persisted item axes. Comparison naming composes existing localized labels;
no competing static translation authority is introduced. Fresh exact-head Tests
run `34943827063` is queued. Historical #878 remains open as a delta carrier
until complete verified succession is demonstrated.

#1034 is now exact `4078f769dde0b4503325d37d61761967f137482e` on current #1033.
It preserves both criterion ζ boundaries and its comparison-post ξ repair.
`leftoverMapComparePlotPostBadge` consumes persisted finite person axes only;
criterion ζ, singular evidence, geometry, distance, rank and coverage do not
infer ξ. Fresh exact-head Tests run `34943967157` is queued. No open PR directly
targeted the #1034 branch in the current sweep. Historical #879 remains open until
complete verified succession is demonstrated.

Sibling #877 is now exact `cbb28027cfe0ea72651cb5bb03d809801ecc8068` on current #875.
Its one-file executable comparison-origin-tick RED was deliberately preserved
while ancestry converged. Fresh exact-head Tests run `34944016757` is queued.
The branch stays Draft until the local RED has a causal source repair and fresh
acceptance; ancestry movement is not permission to manufacture GREEN evidence.

The product stack therefore remains Draft and ordered. #876 -> #1033 -> #1034
must settle current-head evidence before promotion, while #877 follows its own
sibling lane. No descendant inherits parent or predecessor validation receipts.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950e73c88a9f9fd932332ddd47682da124b` | Authorization repair and repository/security tests are GREEN; independent full-diff review is clean. CodeQL producer, OpenCode verdict, Strix/Noema complete review evidence and qualifying approval remain unsettled. | Finish canonical current-head CodeQL settlement, authenticated OpenCode verdict, Strix/Noema owner-path repair/revalidation, qualifying approval and normal protected merge. |
| Report/comparison leftover-map marker identity | #876 `2c12c30...` -> #1033 `d69b339...` -> #1034 `4078f769...` | Report criterion ζ, comparison criterion ζ and comparison post ξ causal implementations are preserved after current-parent non-force convergence. Fresh exact-head Tests are newly queued; historical #878/#879 carriers remain open. | Settle focused/static contracts, frontend lint/tests/build, full repository/PostgreSQL validation, rendered keyboard/focus/a11y evidence, applicable Security/SAST/CodeQL/model review and qualifying approvals; integrate in parent order. |
| Comparison origin tick identity | #877 `cbb28027...` | Current #875 ancestry is converged while the executable origin-tick contract remains intentional RED. | Implement the minimum causal source repair, prove exact-head RED -> GREEN, then complete the ordinary security/browser/review gates. |
| Catalog connection leases and summary TOCTOU | #1077 and #1080 | Kept separate from #1079; external/provider work must not hold long database leases and post-provider persistence must revalidate authorization/visibility/source revision. | Causal RED -> GREEN in each owner lane, short-transaction evidence, current-head tests and protected integration. |
| Governed UI translation delivery | #929 and child #932 | Governed versioned translation-ledger work remains in its canonical owner lane; the leftover-map stack consumes existing localized labels instead of adding a competing store. | Complete reviewed `ko/en/ja/zh/vi/es/de/fr` resources and rendered normal/loading/empty/error/permission/responsive, keyboard/focus/screen-reader, CJK expansion and font-fallback evidence. |
| MCP buyer-path latency | #1009 | Existing measurements remain above the repository `p95 <= 20 ms` acceptance contract. | Representative uncontended measurements, causal query/I/O/runtime profiling, Rust-first hot-path repair where warranted and exact-head gates. |
| Release identity and immutable publication | #961 / #1056 | Candidate release identity work remains Draft; protected main is not release-ready. | Built/installed version proof, normal protected merge, immutable tag/package/release, SBOM/provenance, reproducibility and rollback evidence on one protected SHA. |

## Evidence and ownership rules

Queued, skipped, COMMENTED, rate-limited, status-only, predecessor-head or source-
neutral results are not GREEN evidence for a moved head. An exact-head full-diff
review with no actionable finding is positive independent review coverage but is
not equivalent to a submitted `APPROVED` review when approval is a gate.

A successful dispatch coordinator proves only exact-head handoff to the canonical
producer. It does not transfer producer acceptance. The producer must validate
its payload, execute the detected-language matrix, publish authenticated terminal
verdicts and drive fresh consumer settlement on the same exact head.

A moved parent invalidates descendant ancestry assumptions immediately. Repair is
non-force: inspect the intervening delta, preserve valid contract/test/product
evidence, then merge/reconstruct/retarget onto the moved parent without rewriting
shared history. Parent GREEN evidence does not transfer to the resulting descendant.

A stale or conflicted PR is not force-rebased or closed merely because a successor
exists. Closure requires complete verified succession of every valid product,
test, fixture, contract and evidence delta, or another explicitly allowed close
condition.

Canonical domain truth stays with its owner. LineageWeave consumes released
contracts/ACLs and does not copy contextual-orchestrator admission/routing,
central CI queue policy, psychometrics implementations, ranking, scheduling or
other owner functionality.

For database paths, external/model work occurs outside long-lived explicit
transactions and locks. Persistence reacquires the shortest necessary lease,
revalidates authorization/version state and uses idempotent/UPSERT semantics when
the domain contract requires them.

For material UI, repository/unit evidence does not replace rendered buyer-path
acceptance. Normal/loading/empty/error/permission/responsive behavior,
pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and
applicable p95 evidence remain part of release acceptance.

## Historical evidence

The former append-only baseline, including dated overlays through 2026-09-13, is
preserved unchanged at
[`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).
It is provenance, not current authority. Future refreshes should update this
projection rather than presenting superseded runtime/check state as live.
