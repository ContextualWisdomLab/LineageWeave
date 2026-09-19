# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-20. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, or documentation workflow is not acceptance for a moved product head.

## Delivery authority

- Protected `main`, live PR heads/bases, `AGENTS.md` / `CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are authoritative.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, review-skipped, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence. Force push, destructive rebase, self-approval, gate weakening, synthetic status, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

Current protected references:

- LineageWeave `main@83eba56149eb802cd63642c507c324c9976ec78e`, protected and signature-valid on the latest read.
- Canonical reusable-workflow owner `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`, protected and signature-valid on the latest read.

Re-read both before merge or release; neither reference is a frozen dependency.

## Customer Master / translation

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Material UI / accessibility

#861 remains the earliest proven App integration acceptance root: #860 exact `2084d534cef027aacf515a0907e36a3aa600fa62` was hosted GREEN; #861 introduced persisted comparison-graphic σ+share semantics without updating inherited `App.test.tsx` expectations. Production semantics must not be rolled back merely to satisfy stale share-only assertions.

#861 also retains a distinct buyer-visible layout risk: comparison axis copy can grow through σ/share and translation expansion inside a fixed SVG. A rendered/browser bounding-box RED across responsive widths, keyboard/focus states, and text-expansion locales is required before changing layout; accessible σ/share semantics must remain intact.

## Report / comparison stack

Current ordinary/non-force report chain:

`#863 1bab89ac... → #865 3178713c... → #866 8d63271c... → #867 bbbb7f44... → #868 07558b5a... → #869 58e3eb52... → #870 5a8d9b27... → #871 abb24781... → #872 32a7da41... → #873 aefa45a3... → #874 164ec8e0... → #875 937415e2...`.

#875 children are #876 `1dc3cec3c251a1cf4d4b53acfb8a21532c57f54b` and #877 `34b5682bfbc093a253f6b500c66116354e78c5b4`; #876 continues through #1033 `dc9efcb0b16f8e9887e9d72ebef76fe28cf4b2ab` → #1034 `bb664b7aae733933c11b2fe056de2a7b16a02c15`.

The previous #868 head exposed three stale report contracts rooted at #863/#865/#866. Their causal repairs are already converged into the current chain while preserving stronger descendant semantics. Fresh read of current #868 Tests `35448971227` is terminal FAILURE, not queued: Full test suite/PostgreSQL job `105912690728` completed SUCCESS, while Frontend lint/test/build job `105912690894` failed at the `Test` step after lint succeeded; Build and Storybook were skipped. The exact #868 `App.test.tsx` still contains inherited share-only comparison-axis assertions while #861 production composes independently persisted σ and share, so that stale App acceptance remains a valid source finding even though the available Actions surface does not expose the failing Vitest node/output. Do not attribute this run to PostgreSQL or create a blind rerun.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`. Report lanes must consume that repair through protected integration or verified succession rather than duplicate telemetry source.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 04120daa95c709ed0b095e127e2fdbce055edc83 → #1120 8ec3f725ef15210dc75bc992f52d0bbca4b7b52e → #1117 1b301d28c73c71b4750cf0950ca5a3007b9f307d`.

The accumulated JWKS consumer repairs remain part of #1120: verification candidates reject private RSA members; `x5c` members must be canonical Base64 / parseable X.509, the leaf RSA key must match JWK `n/e`, KeyUsage cannot contradict signature verification, and `x5t` / `x5t#S256` must be canonical and match embedded leaf DER when available. These are LineageWeave verifier boundaries, not Keyverse/provider identity ownership.

Latest executable RED `97c99343fd188eeed8b011e5336b8784039cb331` found one remaining fail-open metadata path: the selector accepted RFC 7517 `x5u` without retrieving or validating the referenced certificate. RFC 7517 §4.6 requires the first certificate public key to match the other JWK members and requires integrity-protected retrieval with server identity validation. Because the shared selector owns no remote certificate retrieval or trust path, causal fix `334c5ad7ce8cd3c137c7ad12a2a6505ce76e482f` rejects every `x5u`-bearing candidate before key loading, including same-`kid` ambiguity poisoning. Follow-up `8ec3f725ef15210dc75bc992f52d0bbca4b7b52e` restores pre-existing rationale comments so the net production delta from predecessor `249d3fa2...` is five added lines plus the new contract. No remote fetch, SSRF surface, PKIX trust implementation, or Keyverse/provider source copy was introduced.

The local service-account prerequisite remains fail closed across identity, client topology, authentication usability, and consumer-resource audience compatibility:

- realm service-account `sub` values are derived from `docker/keycloak/realm-export.json` instead of copied into Python;
- required service subjects are unique and disjoint from non-service resource-owner subjects;
- each bound client must exist exactly once and be enabled OIDC, confidential, service-account enabled, direct-grant disabled, and browser-standard-flow disabled;
- a bound service-account user must be enabled and the current checked-in secret-based confidential client must carry a non-empty local secret;
- automation requires `lineageweave-api` plus `http://localhost:18001/mcp` access-token audiences, while admin requires `lineageweave-api`, through direct OIDC audience mappers with `access.token.claim == "true"`.

These conditions are intentionally local-fixture/consumer specific. They prove that the checked-in confidential actors are structurally capable of authenticating to the LineageWeave resources they are intended to exercise; they do not claim runtime secret resolution, provider availability, or Keyverse identity ownership.

#1120 exact-head Tests `35474448024` is terminal skipped under Draft admission. No repository GREEN is claimed. #1117 was immediately ordinary/non-force reconstructed from exact #1120 plus its existing README blob. Exact compare has merge-base `8ec3f725...`, `behind_by=0`, and README-only effective delta. #1117 exact-head Tests `35474459424` is also Draft-skipped.

Remaining auth RED:

- `backend/tests/test_api.py` still mints analyst/admin tokens through public `lineageweave-frontend` Resource Owner Password Credentials.
- `scripts/seed_demo_data.py` still uses master `admin-cli` password authentication for human-subject lookup and public-client analyst ROPC for content warm-up.
- Human browser demo users remain product-form actors and must continue through redirect-based Authorization Code + PKCE. Machine integration/bootstrap consumers should migrate to the validated confidential automation/admin actors without collapsing viewer/admin or cross-account evidence.
- Public frontend direct grants stay enabled until those consumers are migrated atomically.
- Dependency metadata remains stale and must move with the lock and security regression evidence rather than through a metadata-only edit.
- Exact-head hosted GREEN, rendered browser/session acceptance, and independent review remain outstanding.

## Central CI / CodeQL

Canonical `.github/main` is `e6334e229581a918e2f22de18733b76fa65d7e71` on the latest fresh read. Required owner checks stay centralized; LineageWeave must not fork provider-group or CodeQL owner logic locally. Any evidence naming another `.github` head as current must be refreshed before reliance.

## Performance / immutable delivery

#995 `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains performance RED because durable exact-head cold buyer-path evidence is absent. #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` remains MCP latency RED until representative profiling and causal hot-path work demonstrate p95 ≤20 ms without sample shrinking, hidden I/O, or unrealistic cache warm-up.

#961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs source version identity but is not a release. Publication requires one protected exact candidate with required gates, installed/built package identity, CHANGELOG, immutable tag/release/package, SBOM/provenance, reproducibility, and rollback evidence.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 | RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 | RED | rendered clipping/bounds RED across responsive + text-expansion states, then bounded layout fix |
| Report contracts | #863 → #875 → #876/#877 → #1033/#1034 | backend GREEN / frontend RED at #868 | recover or reproduce the exact frontend failing acceptance; repair at the causal owner, then converge descendants without stale-receipt transfer |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority | refresh consumers/receipts against current released owner contracts |
| Authentication | #899 → #1118 → #1120 `8ec3f725...` → #1117 `1b301d28...` | migration RED / verifier+machine fixture prerequisite repaired | migrate backend/seed password grants to validated confidential service actors; then disable public direct grants, align dependency floor+lock, and obtain hosted/browser proof |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge or release that protected-state evidence does not show.
