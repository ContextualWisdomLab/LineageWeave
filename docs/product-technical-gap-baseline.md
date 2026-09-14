# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-15 02:47 KST.
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

- Summary shared-catalog authorization repair #1079 is open, Ready and mergeable
  at `c2923950e73c88a9f9fd932332ddd47682da124b` on protected
  `main@83eba56149eb802cd63642c507c324c9976ec78e`. Reader materialization is
  fail-closed for catalog enrichment; explicit `post_admin` retains the canonical
  enrichment path. Exact-head Tests `34815479029` are GREEN: Frontend
  `103885140448`, Full suite `103885140559`, and authenticated PostgreSQL +
  Keycloak + Valkey Summary authorization integration `103885140632` all passed
  on this unchanged head. SAST `34815434313` is GREEN. Required Security Scan
  `34815434486` is terminal GREEN, including `trivy-fs` `103964168812` and
  `scorecard` `103964168871`; GitHub Advanced Security CodeQL, Trivy, Scorecard,
  and Semgrep changed-source checks report no new alerts. Required CodeQL language
  detection `103965453105` is GREEN while compatibility analyses remain queued
  without a runner (`python` `104064547176`, `javascript-typescript`
  `104064547154`, `actions` `104064547137`). OpenCode exact-head admission
  `103974955239` is now GREEN; its `opencode-review` `104070870170`,
  `coverage-evidence` `104070870162`, and `coverage-source-tree` `104070870386`
  jobs remain queued without a runner. Strix `103970045852` and Noema
  `103965387845` have both received GitHub-hosted runners and are now actively
  executing on the unchanged exact head: Strix reached `Run Strix (quick)` after
  successful sidecar provisioning/install, while Noema is provisioning its
  contextual-orchestrator review sidecar. Neither is terminal review evidence,
  and no qualifying independent APPROVED review exists.
- Canonical organization queue observation remains owned by
  `ContextualWisdomLab/.github#1150`, exact
  `42bb922f03bf75aed1bc1931d9fbaf04a5433e20`. On that unchanged owner head,
  SAST `34831634664` and Agent Review Runtime Quality CI `34831634694` are
  terminal GREEN; Python Security `34831634654`, Security Scan `34831634718`, and
  CodeQL PR `34831634674` remain queued/nonterminal. LineageWeave enrollment child
  `.github#2200` remains Draft at exact
  `c4054eef3fc3cd84c87ea830b2e94d4145aa34e8`, stacked directly on #1150; its
  focused allowlist contract is GREEN while its own hosted Security/SAST/CodeQL
  acceptance remains queued. LineageWeave must not copy queue policy or runner
  controls locally.
- Review-sidecar admission/preflight remains owned by
  `ContextualWisdomLab/.github#1629`, exact
  `db3d648c905d283f03fc16fbc9891ba76edd56b8` on `.github` protected
  `main@91be6442906c7b6b4f600272c953699708394327`. Its provider-default source
  contract is repaired, but exact-head Runtime Quality `34826203993` is a real
  hosted RED: review-repair pytest collection ran without the Noema document
  dependency and eleven Noema-related modules failed import because
  `defusedxml` was absent. Canonical prerequisite `.github#2170`, exact
  `c346b8324fa23e23d4007799d26ad3a8ac6ae4c3`, owns that dependency-install
  predicate and is Ready/mergeable. On that unchanged exact head, Agent Review
  Runtime Quality CI `34826735972` and SAST `34826735939` are GREEN; Security
  `34826736000`, Python Security `34826735889`, and CodeQL `34826735991` remain
  queued. Correct order is #2170 normal protected integration, then ordinary
  non-force #1629 reconciliation and fresh acceptance. Provider/model/timeout/
  retry policy must not be reimplemented in LineageWeave.

## Buyer-visible gap register

| Gap | Canonical owner / exact candidate | Current evidence | Acceptance still required |
| --- | --- | --- | --- |
| Summary reads must not mutate Customer Master shared catalogs | #1078 / #1079 `c2923950e73c88a9f9fd932332ddd47682da124b` | Reader path is lookup/reuse-only; explicit admin retains mutation authority. Full PostgreSQL and authenticated PostgreSQL + Keycloak + Valkey materialization/fallback regressions, SAST, and Required Security Scan are GREEN on the unchanged head; GHAS CodeQL/Trivy/Scorecard/Semgrep report no new changed-source alerts; Required CodeQL language detection and OpenCode current-head admission are GREEN; Strix and Noema have entered actual exact-head execution. | Finish Required CodeQL compatibility analyses and OpenCode review/coverage jobs, obtain terminal exact-head Strix/Noema and qualifying approval evidence, then normal protected merge. |
| Catalog connection leases and summary TOCTOU | #1077 and #1080 | Kept separate from #1079: provider work must not hold long DB leases; post-provider persistence must revalidate authorization/visibility and source revision. | Causal RED→GREEN in each owner lane, short-transaction evidence, current-head tests and protected integration. |
| Governed UI translation delivery | #929 `f898399c5ff9ab89fe440d2e66985860e141620c` and child #932 | PostgreSQL-authoritative versioned ledger is implemented and repository tests are GREEN, but complete reviewed `ko/en/ja/zh/vi/es/de/fr` Customer Master publication is not demonstrated and central Security/CodeQL gates remain non-GREEN. | Complete eight-locale resource publication, authenticated API/browser normal/loading/empty/error/permission/responsive states, keyboard/focus/screen-reader, CJK/text expansion/font fallback, current security/governance receipts. |
| MCP buyer-path latency | #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` | Modern/legacy protocol repair is Draft. Recorded modern submit/read and legacy read measurements remain far above the repository `p95 <= 20 ms` acceptance contract; CodeQL is also non-GREEN. | Representative uncontended cold/realistic measurements without sample removal or artificial warm-up, profile owned query/I/O/runtime bottlenecks, Rust-first hot-path repair where causal, then exact-head gates. |
| Release identity and immutable publication | #961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` / #1056 | Candidate aligns runtime/package/frontend at 2.28.0 and has repository/Security/SAST GREEN, but Required CodeQL and independent review remain incomplete. Protected main still carries the pre-repair runtime identity. | Built/installed version proof, normal protected merge, immutable tag/package/release, SBOM/provenance, reproducibility and rollback evidence bound to one exact protected SHA. |
| Material Customer Master / lineage UI | #929/#932 plus the live Customer Master and lineage presentation owner PRs | Translation authority, authorization repairs, responsive/a11y states and browser evidence are distributed across their existing owner lanes; no competing inline translation or authorization implementation is permitted. | Converged owner prerequisites plus current-head normal/loading/empty/error/permission/responsive, pointer/touch/keyboard/focus/screen-reader, deterministic identity/layout and applicable performance evidence. |

## Evidence and ownership rules

A queued, skipped, COMMENTED, rate-limited, status-only, predecessor-head or
source-neutral result is not GREEN evidence for a moved current head. Valid
findings are repaired in their canonical owner lane and consumed through released
contracts/ACLs; domain truth is not copied across repositories.

The #1079 same-head progression from pre-checkout queue to successful repository,
authenticated integration, Security, CodeQL language-detect and OpenCode-admission
execution—and now actual Strix/Noema runner allocation—remains positive owner-path
evidence: runner admission latency must not be converted into leaf source churn,
manual reruns, selector changes or synthetic passing status. In-progress and
queued final review/compatibility jobs are still incomplete evidence and stay
fail-closed.

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
