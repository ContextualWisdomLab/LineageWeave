# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-20. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, or documentation workflow is not acceptance for a moved product head.

## Delivery rules

- Protected `main`, live PR heads/bases, repository `AGENTS.md`/`CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are the authority.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence. Force push, destructive rebase, self-approval, gate weakening, synthetic status, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

## Protected and canonical-owner references

- LineageWeave protected base: `main@83eba56149eb802cd63642c507c324c9976ec78e`; signature is verified and the branch remains protected.
- Canonical reusable-workflow owner: `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`, protected and signature-verified. This supersedes the previously recorded `64aa08d7...` after `.github` PR #2279 merged on 2026-09-19.
- Re-read both before merge/release; neither reference is a frozen dependency.

## Customer Master / translation authority

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Accessibility / material UI

#861 remains the earliest proven App integration acceptance root: #860 exact `2084d534cef027aacf515a0907e36a3aa600fa62` was hosted GREEN; #861 introduced persisted comparison-graphic σ+share semantics without updating inherited `App.test.tsx` expectations. Production semantics must not be rolled back merely to satisfy the stale share-only assertions.

#861 also retains a separate buyer-visible layout risk: comparison axis 2 starts near `layout.originX + 8` in a fixed SVG while visible copy may include σ and share. A rendered/browser bounding-box RED across responsive and translation-expansion states is required before changing layout; full accessible σ/share semantics must be retained.

## Report / comparison stack

The old #868 exact head `208079ab70a84477331d567cd1e70b439c67056c` Tests run `35435905529` is terminal RED. PostgreSQL produced **3 failed / 1805 passed / 147 skipped / 1 warning**. Hosted ancestry and source review separated those failures into three stale contracts:

1. #863: a whole-module `leftover_share` prohibition incorrectly treated legitimate sibling σ+share composition as derivation. Causal repair: `1bab89ac47b60df2107e31dcace00e2423fd2521`, scoping independence to `formatLeftoverMapPlotAxisSingular` and requiring independent formatter delegation.
2. #865: report-graphic copy was semantically correct but the test demanded a one-line constant declaration source shape. Causal repair plus parent convergence: `3178713cb294e930c2bb1e3b7fe04227f7d16e47`.
3. #866: production correctly moved share into an independently formatted optional suffix and added singular-only copy, while the test still required `%` inside the template. Causal repair plus ancestry convergence: `8d63271c4644b39d11d65263cc59e8fca8a548cd`.

Current ordinary/non-force report chain:

`#863 1bab89ac... → #865 3178713c... → #866 8d63271c... → #867 bbbb7f44... → #868 07558b5a... → #869 58e3eb52... → #870 5a8d9b27... → #871 abb24781... → #872 32a7da41... → #873 aefa45a3... → #874 164ec8e0... → #875 937415e2...`.

#875 children are #876 `1dc3cec3c251a1cf4d4b53acfb8a21532c57f54b` and #877 `34b5682bfbc093a253f6b500c66116354e78c5b4`; #876 continues through #1033 `dc9efcb0b16f8e9887e9d72ebef76fe28cf4b2ab` → #1034 `bb664b7aae733933c11b2fe056de2a7b16a02c15`.

#873 already carried stronger semantic versions of overlapping contracts, so its convergence deliberately preserved the stronger child tree rather than overwriting it with weaker ancestor blobs. #877 preserves its origin/i18n contract; #1033 preserves stronger criterion/tick-evidence contracts; #1034 retains its post-coordinate/accessibility delta.

Current exact-head acceptance is still RED/unknown, not GREEN: #863 Tests `35448677571`, #865 `35448826477`, #866 `35448866551`, and #868 `35448971227` were queued at the latest read. No historical receipt transfers to these moved heads.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`. Report lanes must consume that repair through normal protected integration or verified succession rather than duplicate telemetry code.

## Authentication / authorization stack

Current auth authority is #899 `a2da5875525cd0950999487ff8fe7d439284dbd2` → #1118 `04120daa95c709ed0b095e127e2fdbce055edc83` → #1120 `b87cdbdc362a35e82445e0b46908441b012a383a` → #1117 `524c55481d458ca706afabf47d124067cbfcda43`.

The earlier public-only JWKS repair remains in force: RED `b1f55e20edcbfe1d832aee6b4763d929bf20cf44` showed that RFC 7518 §6.3.2 RSA private-key members (`d`, `p`, `q`, `dp`, `dq`, `qi`, `oth`) could enter verification candidate counting and poison same-`kid` uniqueness; causal fix `c1b1841f1dfd7f014f78c82eac474b22806fdc58` rejects those members before counting.

The RFC 7517 `x5c` repairs also remain in force. RED `aa7b768e0f80b861ea2a87c47e52d528fc1f0630` plus coverage extension `7c97e6d7d42d019129e2c49befbce4869dc146c8` proved that contradictory/malformed leaf certificate metadata could enter candidate counting; causal fix `8296bf1ae92b05d85303598115b4c25bde18d74f` validates the leaf, and `66b0c7b648e7cfac0c9e2e7dee362791f0b600c7` closes remaining leaf type/Unicode edges. RED `3d9fb8f220347686243dc8d341d7a55af14fc6cc` then proved malformed trailing chain members could still enter candidate counting; causal fix `04e042f021fc4749bd2835116ae5cb247f2c90c7` requires every advertised chain member to be canonical ordinary Base64 and parseable X.509 DER while retaining exact RSA `n`/`e` equality for the leaf.

Fresh standards review found one narrower semantic inconsistency after that syntax/DER repair. RFC 7517 §4.7 requires certificate-related usage metadata to be semantically consistent with the first certificate, and RFC 5280 §4.2.1.3 makes X.509 KeyUsage restrictive when present. Predecessor `04e042f0...` accepted a matching RSA leaf restricted to encryption-only use, allowing an RS256-incompatible same-`kid` JWK to enter candidate counting. Test-first commit `761fb9981d2e7f1acc09008ac372e7bd01978cc9` adds acceptance for absent/signature-capable KeyUsage, rejects encryption-only leaves before loading, and covers same-`kid` ambiguity poisoning. Causal fix `b87cdbdc362a35e82445e0b46908441b012a383a` requires `digitalSignature` or `contentCommitment` when the first certificate carries KeyUsage; absence remains compatible. It does not add `x5u` retrieval, external trust-anchor validation, provider topology, or Keyverse source ownership.

RED-head Tests `35459249747` and exact-fix-head Tests `35459281228` are both terminal skipped under Draft admission, so this is executable/source repair rather than repository-wide GREEN. #1117 was immediately ordinary/non-force reconstructed from the exact new #1120 tree plus its existing README blob and advanced to `524c55481d458ca706afabf47d124067cbfcda43`; fresh parent→child compare has merge-base exactly `b87cdbdc...`, `behind_by=0`, and README-only effective delta. Child Tests `35459324866` is Draft-policy skipped. No predecessor child workflow receipt transfers.

Remaining auth RED: public-client password-grant consumers in backend/seed paths, public direct grants not yet safely disabled, metadata still admits `pyjwt[crypto]>=2.8.0` while the lock resolves 2.13.0, and full browser Authorization Code + PKCE/session evidence is absent.

## Central CodeQL / owner workflows

Canonical `.github/main` remains `e6334e229581a918e2f22de18733b76fa65d7e71` after the GitHub API URL authority repair. Required owner checks remain centralized; LineageWeave must not fork provider-group or CodeQL owner logic locally. Any PR body or document still naming `64aa08d7...` as current canonical head is stale and must be refreshed before relying on owner receipts.

## Performance and immutable delivery

#995 `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains performance RED because durable exact-head cold buyer-path evidence is absent. #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` remains MCP latency RED until representative profiling and causal hot-path work demonstrate p95 ≤20 ms without sample shrinking, hidden I/O, or unrealistic cache warm-up.

#961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs source version identity but is not a release. Publication requires one protected exact candidate with required gates, installed/built package identity, CHANGELOG, immutable tag/release/package, SBOM/provenance, reproducibility, and rollback evidence.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 | RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 | RED | rendered clipping/bounds RED across responsive + text-expansion states, then bounded layout fix |
| Report contracts | #863 → #875 → #876/#877 → #1033/#1034 | source repaired / hosted pending | wait for fresh exact-head receipts; RCA/fix any new terminal RED; no stale-receipt transfer |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority | refresh consumers/receipts against current released owner contracts |
| Authentication | #899 → #1118 → #1120 `b87cdbdc...` → #1117 `524c5548...` | migration RED / JWKS source repair | remove password-grant consumers, disable public direct grants, align PyJWT floor, full/browser proof; retain public-only, full-x5c syntax/DER/leaf consistency, and X.509 KeyUsage invariants |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge or release that protected-state evidence does not show.
