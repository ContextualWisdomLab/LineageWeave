# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-19. Historical detail belongs in Git/PR history. A successful predecessor, sibling, descendant, isolated harness, or documentation workflow is not acceptance for a moved product head.

## Delivery rules

- Protected `main`, live PR heads/bases, repository `AGENTS.md`/`CLAUDE.md`, ADRs, PRD/TRD and exact workflow receipts are the authority.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence. Force push, destructive rebase, self-approval, gate weakening, synthetic status, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

## Protected and canonical owner references

- LineageWeave protected base: `main@83eba56149eb802cd63642c507c324c9976ec78e`.
- Canonical reusable-workflow owner observed in the current maintenance lane: `ContextualWisdomLab/.github@64aa08d7fa487deacd41c761c36277ca68cab6c9`.
- These references are re-read at delivery time; this file does not freeze future protected movement.

## Customer Master / translation authority

The versioned PostgreSQL translation-ledger owner remains #929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee`, Draft. Its exact Tests run `35236145547` is terminal RED in the real PostgreSQL suite while frontend lint/test/build/Storybook is GREEN. Required Security is terminal RED at fail-closed Dependency Review availability and is handed to canonical `.github#810`; required CodeQL is terminal RED at current-head verdict publication/consumption and is handed to `.github#1929`. Scorecard/OSV/Trivy, Ontology Pages, PROV-O and SAST success do not substitute for those failures.

Customer Master presentation consumer #932 remains exact `fb2422537216a19280860f710b55f4df963902db`, Draft on #929. Its exact Tests are Draft-skipped. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource is still a draft; independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence remain release gates.

Malformed hierarchy presentation remains #996 exact `a640df40839ed7e2a15b9ab95a7f86faa050a248`, Draft. It must preserve stored hierarchy truth while repairing only presentation edges and remains gated by the translation/read-model prerequisite and separate Customer Master authorization work.

## Accessibility / material UI

#977 exact `c614d683414b0af1af006c96ed53169ab5b21ee2` causally repaired the stale App selectors after the hosted one-shot proved the narrow LeftoverPairList accessibility edit. Dedicated component/focused regressions and lint were GREEN. Final-head Tests `35340400072` completed `action_required` with zero jobs, so current-head repository/browser acceptance remains absent. The PR stays Draft pending full current-head repository, Chromium Storybook, keyboard/focus/touch/mobile, security/static-analysis and independent-review evidence.

## Central CodeQL baseline / owner settlement

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` has current-head Tests/SAST/Security GREEN, including the causal TLS contract repair. Required CodeQL `35267030868` is terminal RED only at the canonical dispatch-verdict settlement boundary: language detection and compatibility jobs ran, read `verdict=pending`, then failed closed while the dispatch coordinator succeeded. The specimen is owned by `.github#1929`; no LineageWeave-local CodeQL fork/status synthesis is permitted. Child #979 remains exact `2dfd21110813f474d3068796d0733d96f28d6061`, Draft.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` remains the JavaScript post-body parser/coverage owner for protected-baseline `js/incomplete-multi-character-sanitization` findings. It requires a fresh repaired-head canonical CodeQL producer receipt rather than a scanner exemption.

## Authentication / authorization stack

Current stack authority is #899 `a2da5875525cd0950999487ff8fe7d439284dbd2` → #1118 `04120daa95c709ed0b095e127e2fdbce055edc83` → #1120 `b70b82b03edd17b7384bdb1a2c82bc599cfc9dde` → README child #1117 `740a13fa1bf1d4c2d9f7b244f29aa5f3999a33b4`.

#1120 now closes the previously missing normalized local machine/admin authorization prerequisite at source level. Test-first contract `d6d01091ae7a07542821f4af7c517ee320e2e01e` preceded implementation `929095f18c62b0ef82dacf2cff1096a9407a01c1`; `1eb70c0c6a9f8e14f92852c76d7c2dd224c095a9` wires provisioning after the Demo Corp domain seed; `f6d788d5c4e7b255667a5137825ebf2e75a8da12` cross-checks the bindings against the realm fixture; ADR 0028 is code-current at `b70b82b0...`.

The PostgreSQL-only provisioner maps the realm fixture's automation subject `33333333-3333-4333-8333-333333333333` to `DEMO-PU-A` + `viewer` and the distinct admin-test subject `44444444-4444-4444-8444-444444444444` to `DEMO-PU-HQ` + `admin`. It replaces only those deterministic fixture actors' affiliation/role mappings in one short transaction and does not authenticate to Keycloak or mint tokens. This is source repair, not hosted acceptance: exact-head Tests `35423625310` is terminal `skipped` by Draft admission.

Remaining auth RED is narrower and explicit:

- `backend/tests/test_api.py` still uses the public browser client password grant for distinct analyst/admin authorization evidence.
- `scripts/seed_demo_data.py` still uses `admin-cli` password grant only to rediscover deterministic human fixture subjects and uses `demo.analyst` password grant for post-content warm-up.
- Therefore the public `lineageweave-frontend` fixture still has `directAccessGrantsEnabled=true`; disabling it before consumer migration would break current evidence paths rather than complete the OAuth repair.
- Project metadata still admits `pyjwt[crypto]>=2.8.0` while the lock resolves 2.13.0; the safe declared floor/lock must be reconciled before release.
- Required order: migrate remaining password-grant consumers while keeping distinct human authorization semantics → disable public direct grants → align dependency metadata/lock → prove one exact-head hosted repository/security/static-analysis GREEN set → prove rendered Authorization Code + PKCE state/nonce/return-URL/session behavior.

README child #1117 is ordinary/non-force converged on the exact #1120 parent. Fresh parent→child comparison at the repair point has merge-base exactly #1120, `behind_by=0`, with `README.md` as the sole effective child delta. Child receipts do not transfer to #1120.

## Report / comparison stack

The current report-axis chain is #874 `02eeb4b396de4d8077512d30d9492c31ab64155b` → #875 `d1f96f97eb79a5498f312293217191c45611ef45`, with direct children #876 `a8ba471ffedfb0f6007706d758ee4a8bd5b37464` and #877 `0f1adc5b6468e1e7b3d06d822402358ce5783505`; #876 continues through #1033 `c8e6b6f55e65f270a77c43cae6e9f74a918e628a` → #1034 `4fb7122c01d6883f090d4f11794f5140f030700c`.

#875 repaired stale source-shape sentinels by directly executing combined/singular-only-zero/share-only/invalid report-axis evidence states and retaining non-derivation of singular/share. Descendants were ordinarily/non-force converged and preserve their isolated coordinate/origin/accessibility deltas. Their moved-head hosted Tests remain non-accepting until terminal exact-head evidence exists; no predecessor receipt transfers.

## Buyer-path performance

#995 exact `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains intentionally RED because the durable exact-head cold buyer-path evidence file required by #994 is absent. Headline bundle splitting is not a substitute for measured transfer, parse/compile, main-thread/DOM, representative p95, method/environment and limitations evidence.

#1009 exact `4fff982a96b0ad6e791aa8c463925388d036f08f` retains the modern stateless MCP protocol repair but remains performance RED. Previously recorded buyer-path observations exceed the repository p95 ≤20 ms contract by a wide margin. Do not reduce samples, hide I/O, rely on unrealistic cache warm-up, or relabel contention as GREEN; profile the representative synchronous path and repair the owned hot path if the representative baseline still exceeds the contract.

## Release identity and immutable delivery

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs the protected runtime/package/frontend version mismatch to 2.28.0 and has repository Tests/SAST/Security GREEN, but required CodeQL and independent approval remain absent. Source-version coherence is not an immutable release.

Before publication, one protected exact candidate must prove built/installed package identity, CHANGELOG/release notes, immutable tag/release/package filename, SBOM/provenance predicates, exact source SHA, reproducibility and rollback consistency through the canonical released `.github` attestation contract. Existing GitHub Release absence does not prove no historical publication elsewhere.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation ledger | #929 `d4f42f57...` → #932 `fb242253...` | RED | recover/fix exact PostgreSQL failure; canonical Dependency Review + CodeQL settlement; independent 37×8 review/publication |
| Customer Master hierarchy | #996 `a640df40...` | Draft | satisfy translation/auth prerequisites, then current-head browser/a11y/performance acceptance |
| Pair-list accessibility | #977 `c614d683...` | source repaired / acceptance RED | obtain final-head repository + Chromium + security evidence |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd211...` | owner-control RED | canonical `.github#1929` verdict publication/consumer settlement |
| Local OIDC topology | #1120 `b70b82b0...` | normalized machine/admin source repair complete; migration still RED | remove remaining human/admin password-grant consumers, disable public direct grants, full/browser proof |
| Report axis/comparison | #875 `d1f96f97...` → #876/#877 → #1033/#1034 | source-repaired stack / hosted acceptance incomplete | terminal exact-head hosted validation without receipt transfer |
| Frontend delivery performance | #995 `dbe5ac54...` | RED | commit exact-head representative cold buyer-path evidence and repair if over budget |
| MCP buyer latency | #1009 `4fff982a...` | RED | representative uncontended profile and causal hot-path repair to p95 ≤20 ms |
| Release identity | #961 `3bdec050...` | source repaired / release RED | current required gates + immutable build/tag/release/SBOM/provenance/reproducibility/rollback |

This baseline intentionally records unresolved authority. It must not be used to infer a merge or release that GitHub protected-state evidence does not show.
