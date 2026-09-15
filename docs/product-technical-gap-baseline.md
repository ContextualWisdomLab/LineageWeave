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

Parent #875 is exact `9303d67219071d76b59d4b85a49dac11023dcab1` on its current
base `eb051da92758e7bf84138e034b2049868c0fb487`. Its moved ancestry was read and
adopted without force-push or destructive rebase. Latest Tests attempts on this
exact head include queued run `34947735003`; newer Draft-policy attempts were
skipped and therefore are not GREEN evidence.

#876 is exact `f461f5023cdd658b4b37813a8bb3df6ee06dde72` on current #875.
It preserves the report-criterion ζ contract: `leftoverMapPlotCriterionBadge`
consumes only persisted finite item axes, keeps finite zero coordinates, fails
closed for unusable pairs and does not infer ζ from person ξ, geometry, distance,
rank, coverage or neighboring evidence. Current-head Tests run `34947822715`
remains queued; newer Draft-policy run `34949321710` was skipped. Predecessor
validation does not transfer.

#1033 is now exact `84b927f37471e3969f071520875eb40e5576877c` on current #876.
A semantic two-parent, non-force merge adopted the moved #876 ancestry while
preserving only the intended three-file comparison-criterion delta. Convergence
PR #1084 is normally recognized as merged at this exact commit. The comparison
ζ helper consumes only persisted finite item axes and keeps report criterion
behavior separate. Fresh exact-head Tests run `34949322503` is queued; no prior
receipt transfers.

#1034 is now exact `708e435d4c975696f4f78a5e9b81969b5895f31e` on current #1033.
A second semantic two-parent, non-force merge preserved the comparison-post ξ
delta while adopting the converged report/comparison criterion and singular-axis
foundation. `leftoverMapComparePlotPostBadge` consumes persisted finite person axes
only; criterion ζ, singular/share evidence, geometry, distance, rank and coverage
do not infer ξ. Fresh exact-head Tests run `34949510341` is queued. Historical
#879 remains open until complete verified succession is demonstrated.

Sibling #877 is now exact `73f8bf898a8eafc162850dae0b8dbc4955760fdb` on current #875.
A semantic two-parent, non-force merge adopted current #875 while preserving the
three-file comparison-origin-tick repair. Convergence PR #1083 is normally
recognized as merged at this exact commit. Origin identity is exact canonical
formatted zero; share and σ are projected independently and never define origin.
Fresh exact-head Tests run `34949897498` is queued. The branch remains Draft until
its current-head rendered and repository evidence settles.

The product stack therefore remains Draft and ordered. #876 -> #1033 -> #1034
must settle current-head evidence before promotion, while #877 follows its own
sibling lane. No descendant inherits parent or predecessor validation receipts.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950e73c88a9f9fd932332ddd47682da124b` | Authorization repair and repository/security tests are GREEN; independent full-diff review is clean. CodeQL producer, OpenCode verdict, Strix/Noema complete review evidence and qualifying approval remain unsettled. | Finish canonical current-head CodeQL settlement, authenticated OpenCode verdict, Strix/Noema owner-path repair/revalidation, qualifying approval and normal protected merge. |
| Report/comparison leftover-map marker identity | #876 `f461f502...` -> #1033 `84b927f3...` -> #1034 `708e435d...` | Report criterion ζ, comparison criterion ζ and comparison post ξ causal implementations are preserved after semantic current-parent non-force convergence. Fresh exact-head Tests are queued; historical #878/#879 carriers remain open. | Settle focused/static contracts, frontend lint/tests/build, full repository/PostgreSQL validation, rendered keyboard/focus/a11y evidence, applicable Security/SAST/CodeQL/model review and qualifying approvals; integrate in parent order. |
| Comparison origin tick identity | #877 `73f8bf89...` | Causal production repair is preserved after semantic convergence onto current #875. Exact formatted zero defines origin; share and σ remain independent. Fresh Tests `34949897498` is queued. | Prove current-head executable contract and frontend build/tests, rendered keyboard/focus/a11y/i18n evidence, applicable security/model review and qualifying approval before promotion. |
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
