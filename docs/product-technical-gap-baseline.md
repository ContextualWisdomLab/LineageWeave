# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 10:50 KST.
>
> Protected `main` is `83eba56149eb802cd63642c507c324c9976ec78e`;
> the commit is signature-verified and no protected-main movement was observed in
> the fresh pre-write sweep. This document is a current projection of live
> PR/Issue/check authority, not a replacement for those sources. Historical
> overlays through 2026-09-13 are preserved byte-for-byte in
> [`evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).
> When this snapshot and live GitHub state differ, live protected refs, PRs,
> Issues, ADRs and check receipts win.

## Protected delivery baseline

No LineageWeave release is admitted from the current protected head.

- Summary shared-catalog authorization repair #1079 remains open and Ready at
  exact `c2923950e73c88a9f9fd932332ddd47682da124b` on protected
  `main@83eba56149eb802cd63642c507c324c9976ec78e`. Reader materialization is
  fail-closed for shared-catalog enrichment; explicit `post_admin` retains the
  canonical enrichment path. Exact-head Tests `34815479029` are GREEN: Frontend
  `103885140448`, Full suite `103885140559`, and authenticated PostgreSQL +
  Keycloak + Valkey Summary authorization integration `103885140632` all passed.
  SAST `34815434313` and Required Security Scan `34815434486` are GREEN; changed-
  source GHAS CodeQL, Trivy, Scorecard and Semgrep report no new alerts.
- Required CodeQL language detection `103965453105` is GREEN. Compatibility
  receivers Python `104064547176`, JavaScript/TypeScript `104064547154`, and
  Actions `104064547137` are terminal FAIL-CLOSED after reading an absent
  current-head producer verdict; they are not product-analysis failures. The
  coordinator `Dispatch current-head CodeQL scan` `104180256379` remains queued
  with no runner. Canonical bootstrap/cutover ownership remains `.github#2106 ->
  #2040`; LineageWeave must not manufacture a wake commit or duplicate that
  control plane.
- Required OpenCode coverage is partly terminal GREEN: `coverage-source-tree`
  `104070870386` and `coverage-evidence` `104070870162` succeeded on exact
  `c2923950e...`. `opencode-review` `104070870170` successfully dispatched a
  current-head request, then correctly failed because no authenticated
  `opencode-agent` `APPROVED`/`CHANGES_REQUESTED` verdict had materialized on the
  exact head. The central dispatch path owns the eventual verdict/rerun.
- Required Strix `103970045852` is terminal FAILURE but not a LineageWeave
  security finding. Trusted-source validation, contextual-orchestrator sidecar
  provisioning and Strix installation succeeded. Artifact `strix-reports`
  `10371857268` (digest
  `sha256:b0d69ccbdf5b4fa52c99e118a9d76e6d4251d34d7deb9341131b9ce8270dd13b`)
  contains a terminal report/SARIF with zero findings, while concurrent sub-agent
  requests received explicit CO `503 concurrency_limit_exceeded` / `too many
  concurrent orchestration runs`. The Strix gate correctly refused to promote a
  partial provider execution to GREEN. CO deliberately rejects saturated inference
  rather than queueing it; the repair therefore belongs to canonical review-runtime
  admission/backpressure, not to a leaf provider/model override or gate weakening.
  Fresh consumer evidence remains on `.github#2139`. The decision-record lane
  `.github#2140` was found stale/non-mergeable against current protected `.github`
  `main@91be6442906c7b6b4f600272c953699708394327`; current-main reconstruction
  `.github#2207` now carries the same ADR blob (`1c133061cccb6bca9c3552cb8bdbca43b17d19f1`)
  plus the original changelog evidence via the repository's existing `CHANGELOG.d/`
  convention. #2140 remains open/Draft until complete succession is proved.
- Required Noema `103965387845` is terminal CANCELLED and likewise is not a
  product finding. Exact-head admission, credential selection, GitHub App token,
  current-head validation and visibility checks succeeded. `Provision contextual-
  orchestrator review sidecar` started at `2026-09-14T16:50:39Z`, logged the
  sidecar starting at `16:52:41Z`, never emitted readiness, and GitHub cancelled
  the operation at `22:51:33Z` after about six hours; no model-verdict step ran.
  This is startup/provisioning occupancy evidence, not an elapsed-model-time
  verdict. `.github#1629` retains sidecar admission/preflight ownership and
  `.github#2139` retains progress/idle/runner-reclamation evidence. Proposed
  ADR-0030 authority is being reconstructed on current protected `.github` main
  in Draft `.github#2207`; no total elapsed model deadline is introduced.
- CodeRabbit completed an independent full protected-base-to-exact-head review of
  all 13 changed files with no actionable comments and `Merge Risk: Minimal`; both
  inline threads are resolved. This is positive independent review coverage but
  not a submitted qualifying `APPROVED` review.
- Canonical organization queue observation remains owned by
  `ContextualWisdomLab/.github#1150` with LineageWeave enrollment child
  `.github#2200`; LineageWeave does not copy queue policy or runner controls.
- Review-sidecar admission/preflight remains owned by `.github#1629`, exact
  `db3d648c905d283f03fc16fbc9891ba76edd56b8`, on `.github` protected
  `main@91be6442906c7b6b4f600272c953699708394327`. Its provider-default source
  contract is repaired but its exact-head Runtime Quality RED is blocked by the
  missing Noema document dependency during review-repair collection. Canonical
  prerequisite `.github#2170`, exact
  `c346b8324fa23e23d4007799d26ad3a8ac6ae4c3`, owns that dependency predicate and
  remains Ready/mergeable with Runtime Quality, SAST, Python Security, Security,
  Noema, Strix, OpenCode bootstrap, `coverage-source-tree`, `coverage-evidence`,
  latest `scan-pr-queue`, and CodeQL language detection GREEN plus a current-head
  Noema APPROVED review. Its CodeQL Actions/Python compatibility receivers are
  fail-closed and coordinator `104179015295` remains queued with no runner.
  Required OpenCode `opencode-review` `104142935844` is terminal FAILURE after
  dispatch succeeded because no authenticated exact-head OpenCode verdict existed;
  the sibling coverage jobs are GREEN, so this is review publication/settlement
  evidence rather than a coverage or #2170 source failure. Correct sequencing
  stays #2170 normal protected integration -> ordinary/non-force #1629
  reconciliation -> fresh #1629 acceptance. Final provider
  admission/routing/TTC remains owned by released contextual-orchestrator, not
  central CI or LineageWeave.
- `.github#2207` remains a Draft reconstruction of stale/non-mergeable #2140 on
  current protected `.github/main`; exact head is
  `36a6755a5b699d8f43269805b6fccd5c5d75eae5`. Current-head
  `required-workflow-bootstrap` `104210566507` and `admit-current-head`
  `104210566437` remain queued and there is no submitted review, so complete
  succession is not yet proven and #2140 must remain open.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950e73c88a9f9fd932332ddd47682da124b` | Reader path is lookup/reuse-only; explicit admin retains mutation authority. Full PostgreSQL and authenticated PostgreSQL + Keycloak + Valkey materialization/fallback regressions, SAST and Required Security are GREEN. CodeRabbit full-diff review is clean. OpenCode coverage tree/evidence are GREEN. Strix produced zero SARIF findings but failed closed on CO saturation; Noema never reached a verdict because sidecar provisioning occupied the runner until cancellation. Canonical occupancy decision evidence is on `.github#2139`, with stale `.github#2140` reconstructed as current-main Draft `.github#2207`. | Finish current-head CodeQL producer/compatibility acceptance, obtain authenticated OpenCode verdict, repair/revalidate Strix and Noema through canonical owner lanes, prove the #2140 -> #2207 decision-record succession, obtain qualifying submitted approval, then normal protected merge. |
| Catalog connection leases and summary TOCTOU | #1077 and #1080 | Kept separate from #1079: provider work must not hold long DB leases; post-provider persistence must revalidate authorization/visibility and source revision. | Causal RED->GREEN in each owner lane, short-transaction evidence, current-head tests and protected integration. |
| Governed UI translation delivery | #929 `f898399c5ff9ab89fe440d2e66985860e141620c` and child #932 | PostgreSQL-authoritative versioned ledger is implemented and repository tests are GREEN, but complete reviewed `ko/en/ja/zh/vi/es/de/fr` Customer Master publication is not demonstrated and central Security/CodeQL gates remain non-GREEN. | Complete eight-locale resource publication, authenticated API/browser normal/loading/empty/error/permission/responsive states, keyboard/focus/screen-reader, CJK/text expansion/font fallback and current security/governance receipts. |
| MCP buyer-path latency | #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` | Modern/legacy protocol repair is Draft. Recorded modern submit/read and legacy read measurements remain far above the repository `p95 <= 20 ms` acceptance contract; CodeQL is also non-GREEN. | Representative uncontended cold/realistic measurements without sample removal or artificial warm-up, profile owned query/I/O/runtime bottlenecks, Rust-first hot-path repair where causal, then exact-head gates. |
| Release identity and immutable publication | #961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` / #1056 | Candidate aligns runtime/package/frontend at 2.28.0 and has repository/Security/SAST GREEN, but Required CodeQL and independent review remain incomplete. Protected main still carries the pre-repair runtime identity. | Built/installed version proof, normal protected merge, immutable tag/package/release, SBOM/provenance, reproducibility and rollback evidence bound to one exact protected SHA. |
| Material Customer Master / lineage UI | #929/#932 plus the live Customer Master and lineage presentation owner PRs | Translation authority, authorization repairs, responsive/a11y states and browser evidence are distributed across their existing owner lanes; no competing inline translation or authorization implementation is permitted. | Converged owner prerequisites plus current-head normal/loading/empty/error/permission/responsive, pointer/touch/keyboard/focus/screen-reader, deterministic identity/layout and applicable performance evidence. |

## Evidence and ownership rules

A queued, skipped, COMMENTED, rate-limited, status-only, predecessor-head or
source-neutral result is not GREEN evidence for a moved current head. An exact-head
full-diff review with no actionable findings is positive independent review
coverage, but it is not equivalent to a submitted `APPROVED` review when approval
is an explicit merge gate. A compatibility receiver that fails because its
current-head producer has not yet materialized is fail-closed control-plane
evidence, not a source-analysis failure. A clean SARIF/report from a review scan
whose provider execution was incomplete is likewise not promoted to GREEN.

A stale/conflicted owner PR is not silently force-rebased and is not closed merely
because a replacement exists. Reconstruction is acceptable only from the current
protected owner base with every still-valid decision/test/fixture/contract/evidence
delta carried forward and independently revalidated. `.github#2207` is therefore a
candidate successor to #2140, not yet proof that #2140 may close.

Valid findings are repaired in their canonical owner lane and consumed through
released contracts/ACLs; domain truth is not copied across repositories. In
particular, CO's explicit `concurrency_limit_exceeded` overload contract must not
be weakened from a LineageWeave leaf. Review callers must respect the released
capacity/admission boundary, while progress/idle/runner-reclamation semantics stay
separate from total model elapsed time.

For database paths, external/model work must execute outside long-lived explicit
transactions and locks. Persistence reacquires the shortest necessary lease,
revalidates authorization/version state, and uses idempotent/UPSERT semantics
where the domain contract requires them.

For material UI, repository/unit evidence does not replace rendered buyer-path
acceptance. Normal/loading/empty/error/permission/responsive behavior,
pointer/touch/keyboard/focus, accessibility, locale expansion/font fallback and
applicable p95 evidence remain part of release acceptance.

## Historical evidence

The former append-only baseline, including every dated overlay through
2026-09-13 20:27 KST, is preserved unchanged at
[`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).
It is provenance, not current authority. Future refreshes should update this
current projection and preserve superseded snapshots without presenting old
runtime/check state as live.
