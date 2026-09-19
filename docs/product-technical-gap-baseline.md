# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-19. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, or documentation workflow is not acceptance for a moved product head.

## Delivery rules

- Protected `main`, live PR heads/bases, repository `AGENTS.md`/`CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are the authority.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence. Force push, destructive rebase, self-approval, gate weakening, synthetic status, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

## Protected and canonical-owner references

- LineageWeave protected base: `main@83eba56149eb802cd63642c507c324c9976ec78e`; the commit is signature-valid.
- Canonical reusable-workflow owner: `ContextualWisdomLab/.github@64aa08d7fa487deacd41c761c36277ca68cab6c9`; the commit is signature-valid and the branch remains protected.
- These references are re-read at delivery time; this file does not freeze future protected movement.

## Customer Master / translation authority

The PostgreSQL translation-ledger owner remains #929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee`, Draft. Its known exact Tests receipt is terminal RED in the PostgreSQL suite while frontend lint/test/build/Storybook is GREEN. Required Dependency Review and CodeQL remain canonical `.github` owner-path failures rather than LineageWeave-local scanner exceptions.

Customer Master presentation #932 remains stacked on #929. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource is still a draft pending independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. Malformed-hierarchy presentation #996 remains gated by that translation/read-model prerequisite and separate Customer Master authorization work.

## Accessibility / material UI

#977 exact `c614d683414b0af1af006c96ed53169ab5b21ee2` repaired stale App selectors after focused hosted validation of the LeftoverPairList accessibility edit. Its final-head repository/browser acceptance is still absent because the final Tests receipt completed without executable jobs. Component-level evidence is not a substitute for current-head Chromium/keyboard/focus/touch/mobile/security acceptance.

## Central CodeQL owner settlement

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` retains current-head Tests/SAST/Security GREEN but required CodeQL is terminal RED at canonical dispatch-verdict settlement. The specimen remains an owner-path issue for `.github`; no LineageWeave-local CodeQL fork, status synthesis, or gate weakening is permitted. Child #979 remains dependent on that settlement.

## Authentication / authorization stack

Current stack authority is #899 `a2da5875525cd0950999487ff8fe7d439284dbd2` → #1118 `04120daa95c709ed0b095e127e2fdbce055edc83` → #1120 `c8da74f3b231b61f04cc040fed1c8e96f36ae66c` → README child #1117 `ca69b521bc862bbf686c721f274ac44b33229e6b`.

#1120 retains the normalized local service-account prerequisite. The realm fixture gives automation subject `33333333-3333-4333-8333-333333333333` `DEMO-PU-A` + `viewer` and a distinct admin-test subject `44444444-4444-4444-8444-444444444444` `DEMO-PU-HQ` + `admin`. The PostgreSQL-only provisioner replaces only those deterministic actors' affiliations/roles and does not authenticate to Keycloak or mint tokens.

Local authorization review already repaired two representation hazards. PU affiliations dropped by local account resolution were restored (`87d52c4c...` → `405b7ed8...` → edge proof `87e9aceb...`). The unrepresentable mixed `{corp-wide,NULL}` plus `{corp-scoped,pu}` shape now fails closed instead of widening a scoped corporation (`bca160c7...` → `801687f7...`).

The shared JWT/JWK selector closes candidate-admission classes before loader/candidate counting: unsupported `crit`; malformed/noncanonical Base64urlUInt; RSA modulus below 2048 bits; invalid exponent encoding/range; `e >= n`; even modulus; nonconformant RFC 7517 `key_ops`; explicitly null optional metadata; and now noncanonical nonzero Base64url terminal pad bits.

The earlier `key_ops` repair rejected duplicate operation values, non-string members, and unrelated `verify` + `encrypt` combinations. Test-first `6e9ca95a...` / `29d394b9...` produced `4 failed, 1 passed` against predecessor `81b8de43...`; causal fix `fbed153f...` produced `5 passed` in the focused set under PyJWT 2.13.0.

RFC 7517 review then found that predecessor `fbed153f...` used `.get()` semantics for optional `alg`, `use`, and `key_ops`, so explicit JSON `null` was indistinguishable from member absence. Those members are optional by absence but have defined JSON types when present. A malformed same-`kid` null-valued key could therefore enter candidate counting and manufacture false ambiguity.

Test-first `68af99be64e18ab4e07c28a2440b4e0420df5844` adds direct rejection and same-`kid` ambiguity cases for explicit-null `alg`, `use`, and `key_ops`. Causal fix `234d5c05aedd573cd6bbf37dfe1019afd0a67c40` distinguishes absent members from present values: optional strings must be exact strings when present, and present `key_ops` must be a conformant list.

Fresh RFC 4648 §3.5 review found one more canonical-encoding gap on `234d5c05...`: Python's Base64 decoder accepts strings whose unused terminal pad bits are nonzero, so distinct Base64url spellings can decode to the same RSA `n` or `e` octets. Because candidate uniqueness is decided before the JWK loader, an equivalent-but-noncanonical same-`kid` modulus could also manufacture false ambiguity. Test-first `1ee1c470934c859f493e81bfd489a51dfa646fd5` covers both `n` and a one-octet exponent plus same-`kid` poisoning. Causal fix `c8da74f3b231b61f04cc040fed1c8e96f36ae66c` round-trips decoded bytes through canonical unpadded Base64url before admitting the key, while retaining the separate RFC 7518 minimum-octet check.

#1117 was immediately ordinary/non-force converged by rebuilding from exact parent `c8da74f3...` plus its existing README blob. Exact parent→child compare has merge-base `c8da74f3...`, `behind_by=0`, and only `README.md` as effective child delta; child head is `ca69b521bc862bbf686c721f274ac44b33229e6b`.

These are source/focused repairs, not hosted repository acceptance. #1120 exact-head Tests `35431238139` is terminal `skipped` by Draft admission.

Remaining auth RED is explicit:

- `backend/tests/test_api.py` still uses public `lineageweave-frontend` password grants for distinct analyst/admin authorization evidence.
- `scripts/seed_demo_data.py` still uses `admin-cli` password grant to rediscover deterministic human fixture subjects and `demo.analyst` password grant for post-content warm-up.
- The public realm client therefore still has `directAccessGrantsEnabled=true`; disabling it before consumer migration would break current evidence paths rather than complete the OAuth repair.
- Project metadata still admits `pyjwt[crypto]>=2.8.0` while the lock resolves 2.13.0.
- Required order remains: migrate remaining password-grant consumers while preserving distinct authorization semantics → disable public direct grants → align dependency metadata/lock → prove one exact-head hosted repository/security/static-analysis GREEN set → prove rendered Authorization Code + PKCE state/nonce/return-URL/session behavior.

## Report / comparison stack

The current recorded report-axis chain is #874 `02eeb4b396de4d8077512d30d9492c31ab64155b` → #875 `d1f96f97eb79a5498f312293217191c45611ef45`, with direct children #876 `a8ba471ffedfb0f6007706d758ee4a8bd5b37464` and #877 `0f1adc5b6468e1e7b3d06d822402358ce5783505`; #876 continues through #1033 `c8e6b6f55e65f270a77c43cae6e9f74a918e628a` → #1034 `4fb7122c01d6883f090d4f11794f5140f030700c`.

#875 repaired stale source-shape sentinels by directly executing combined/singular-only-zero/share-only/invalid report-axis evidence states while retaining non-derivation of singular/share. Descendants preserve their isolated coordinate/origin/accessibility deltas. Moved-head hosted acceptance remains incomplete; predecessor receipts do not transfer.

## Buyer-path performance

#995 exact `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains RED because durable exact-head cold buyer-path evidence is absent. Bundle splitting is not a substitute for measured transfer, parse/compile, main-thread/DOM, representative p95, method/environment, and limitations evidence.

#1009 exact `4fff982a96b0ad6e791aa8c463925388d036f08f` retains the stateless MCP protocol repair but remains performance RED. Previously recorded buyer-path observations exceed the repository p95 ≤20 ms contract. Do not shrink samples, hide I/O, rely on unrealistic cache warm-up, or relabel contention as GREEN; profile the representative path and repair the owned hot path if the baseline still exceeds budget.

## Release identity and immutable delivery

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs protected runtime/package/frontend version mismatch to 2.28.0 and has repository Tests/SAST/Security GREEN, but required CodeQL and independent approval remain absent. Source-version coherence is not an immutable release.

Before publication, one protected exact candidate must prove built/installed package identity, CHANGELOG/release notes, immutable tag/release/package filename, SBOM/provenance predicates, exact source SHA, reproducibility, and rollback consistency through the canonical released `.github` attestation contract.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation ledger | #929 `d4f42f57...` → #932 | RED | recover/fix exact PostgreSQL failure; canonical Dependency Review + CodeQL settlement; independent 37×8 review/publication |
| Customer Master hierarchy | #996 | Draft | satisfy translation/auth prerequisites, then current-head browser/a11y/performance acceptance |
| Pair-list accessibility | #977 `c614d683...` | source repaired / acceptance RED | obtain final-head repository + Chromium + security evidence |
| Python CodeQL baseline | #974 `4341080f...` → #979 | owner-control RED | canonical `.github` verdict publication/consumer settlement |
| Local OIDC topology | #1120 `c8da74f3...` → #1117 `ca69b521...` | machine/admin + local scope + RSA/JWK canonical-admission source prerequisites repaired; migration still RED | remove remaining password-grant consumers, disable public direct grants, align PyJWT floor, full/browser proof |
| Report axis/comparison | #875 `d1f96f97...` → #876/#877 → #1033/#1034 | source-repaired stack / hosted acceptance incomplete | terminal exact-head hosted validation without receipt transfer |
| Frontend delivery performance | #995 `dbe5ac54...` | RED | commit exact-head representative cold buyer-path evidence and repair if over budget |
| MCP buyer latency | #1009 `4fff982a...` | RED | representative uncontended profile and causal hot-path repair to p95 ≤20 ms |
| Release identity | #961 `3bdec050...` | source repaired / release RED | current required gates + immutable build/tag/release/SBOM/provenance/reproducibility/rollback |

This baseline intentionally records unresolved authority. It must not be used to infer a merge or release that GitHub protected-state evidence does not show.
