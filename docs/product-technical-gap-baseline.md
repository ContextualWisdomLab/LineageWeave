# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-20. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, or documentation workflow is not acceptance for a moved product head.

## Delivery authority

- Protected `main`, live PR heads/bases, `AGENTS.md` / `CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are authoritative.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, review-skipped, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence. Force push, destructive rebase, self-approval, gate weakening, synthetic status, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

Current protected references on the latest read:

- LineageWeave `main@83eba56149eb802cd63642c507c324c9976ec78e`.
- Canonical reusable-workflow owner `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`.

Re-read both before merge or release; neither reference is a frozen dependency.

## Customer Master / translation

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Material UI / accessibility

#861 remains the earliest proven App integration acceptance root: #860 exact `2084d534cef027aacf515a0907e36a3aa600fa62` was hosted GREEN; #861 introduced persisted comparison-graphic σ+share semantics without updating inherited `App.test.tsx` expectations. Production semantics must not be rolled back merely to satisfy stale share-only assertions.

#861 also retains a separate buyer-visible layout risk: comparison axis copy can grow through σ/share and translation expansion inside a fixed SVG. A rendered/browser bounding-box RED across responsive widths, keyboard/focus states, and text-expansion locales is required before changing layout; accessible σ/share semantics must remain intact.

## Report / comparison stack

#868 Tests `35448971227` is terminal FAILURE in the frontend `Test` step. The full/PostgreSQL suite is GREEN. Exact #868 `App.test.tsx` still contains inherited share-only comparison-axis assertions while #861 production composes independently persisted σ and share. That stale App acceptance remains a valid source finding even though the available Actions surface does not expose the failing Vitest node/output. Do not attribute this run to PostgreSQL or create a blind rerun.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`. Report lanes must consume that repair through protected integration or verified succession rather than duplicate telemetry source.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 04120daa95c709ed0b095e127e2fdbce055edc83 → #1120 16bb3ab3b1325e1fce27a7564adf16ea50c6c719 → #1117 bd2e686da9140b15ae8272b428aa46cc508b374d`.

Accumulated #1120 verifier/auth-fixture prerequisites remain in force: private or contradictory RSA/JWK metadata is rejected; `x5c` is canonical/parseable and consistent with JWK `n/e` and KeyUsage; unsupported `x5u` candidates fail closed because LineageWeave owns no remote-certificate retrieval/trust path; service-account subjects are derived from the checked-in realm fixture; service and human subjects are disjoint; required machine clients are unique, enabled OIDC confidential service-account clients with direct/browser/implicit grants disabled and the required REST/MCP access-token audiences. The public browser fixture remains Authorization Code + S256 PKCE with implicit flow disabled and exact local redirect origins.

Executable seed/bootstrap contract `fd3edd04d93714d152db31473850c10fe30b31d0` is now source-satisfied. #1120 exact `16bb3ab3...` reads deterministic `demo.analyst` / `demo.admin` subjects from `docker/keycloak/realm-export.json`, fails closed on missing/disabled/shared subject identities, and no longer logs into master `admin-cli` or mints a human password-grant token. New `scripts/warm_seeded_post_content.py` uses the validated confidential `lineageweave-test-automation` Client Credentials actor, and `make seed` orders deterministic human fixture seed → service-account authorization binding → machine warm-up while requiring only `KEYCLOAK_CLIENT_SECRET` for the OAuth step.

Source inspection at the exact head finds no `admin-cli`, `grant_type=password`, or `KEYCLOAK_ADMIN_PASSWORD` in `scripts/seed_demo_data.py`. The machine warm-up posts only `grant_type=client_credentials`, `client_id=lineageweave-test-automation`, and its supplied client secret. This closes the seed/bootstrap ROPC finding at source level, but exact-head Tests run `35492733630` is Draft-policy skipped; Devin Review and CodeRabbit success statuses are not repository GREEN.

The earlier temporary exact-SHA-guarded self-modifying repair workflow remains removed. Its predecessor runnerless run is stale and cannot mutate the moved #1120 branch. Queue/runner acquisition evidence remains with canonical organization owner `.github#712`; no new source-neutral wake commit or blind rerun was introduced.

#1117 was immediately ordinary/non-force converged from exact #1120 plus a code-current README to `bd2e686da9140b15ae8272b428aa46cc508b374d`. Exact compare from `16bb3ab3...` has merge-base exactly `16bb3ab3...`, `behind_by=0`, and effective delta only `README.md`; predecessor child receipts do not transfer.

Remaining auth RED:

- `backend/tests/test_api.py` still obtains both `demo.analyst` and `demo.admin` access tokens from public `lineageweave-frontend` using `grant_type=password`; migrate that final local ROPC caller without collapsing its distinct viewer/admin authorization semantics;
- human browser product acceptance remains a rendered Authorization Code + S256 PKCE lane and must not be silently replaced by machine-only evidence;
- keep public frontend direct grants enabled until the final password-grant consumer migrates atomically, then set `directAccessGrantsEnabled=false` with a repository contract;
- move PyJWT dependency floor, lock, and security regression evidence together rather than through metadata-only edits;
- obtain exact-head hosted GREEN, rendered browser session/return-URL/tampered-state/permission acceptance, and qualifying independent review.

## Performance / immutable delivery

#995 `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains performance RED because durable exact-head cold buyer-path evidence is absent. #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` remains MCP latency RED until representative profiling and causal hot-path work demonstrate p95 ≤20 ms without sample shrinking, hidden I/O, or unrealistic cache warm-up.

#961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs source version identity but is not a release. Publication requires one protected exact candidate with required gates, installed/built package identity, CHANGELOG, immutable tag/release/package, SBOM/provenance, reproducibility, and rollback evidence.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 | RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 | RED | rendered clipping/bounds RED across responsive + text-expansion states, then bounded layout fix |
| Report contracts | #868 | frontend RED / PostgreSQL GREEN | recover or reproduce exact frontend failing acceptance; repair at causal owner, then converge descendants |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority; queue owner #712 active | refresh consumers/receipts against current released owner contracts; keep runner starvation separate from product source |
| Authentication | #899 → #1118 → #1120 `16bb3ab3...` → #1117 `bd2e686d...` | seed/bootstrap source repaired; exact Tests skipped; backend ROPC still RED | migrate backend analyst/admin ROPC preserving role semantics, then disable public direct grants and obtain hosted/browser proof |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge or release that protected-state evidence does not show.
