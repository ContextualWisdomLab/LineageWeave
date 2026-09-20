# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-21. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, queued workflow, or documentation-only workflow is not acceptance for a moved product head.

> This update starts from #1041 exact predecessor `85e3d743ad1fe430d5a21a8841159b8ab28101ba` against `main@83eba56149eb802cd63642c507c324c9976ec78e`; the PR is Ready. Open-PR/issue counts are operational metadata and are intentionally not treated as release evidence. New exact-head workflow receipts created by this edit remain authoritative for acceptance; predecessor receipts do not transfer.

## Delivery authority

- Protected `main`, live PR heads/bases, `AGENTS.md` / `CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are authoritative.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, review-skipped, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence, reconstruction, or safe retargeting. When an intermediate PR is normally merged into its parent, live descendants must not remain based on the closed branch when the merged parent is their verified ancestry.
- Force push, destructive rebase, self-approval, gate weakening, synthetic status, blind rerun, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

Current protected references on the latest read:

- LineageWeave `main@83eba56149eb802cd63642c507c324c9976ec78e`.
- Canonical reusable-workflow owner `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`.
- GitHub resolves the named ecosystem repositories as `ContextualWisdomLab/LineageWeave`, `ContextualWisdomLab/RankWeave`, `ContextualWisdomLab/ThreadWeave`, `ContextualWisdomLab/disksage`, and `ContextualWisdomLab/TEPP`; `DiskSage` is the product name, not the repository path casing.

Re-read both protected references before merge or release; neither is a frozen dependency.

## Customer Master / translation

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Material UI / accessibility

#861 remains the earliest proven App integration acceptance root. #860 exact `2084d534cef027aacf515a0907e36a3aa600fa62` was hosted GREEN; current #861 exact `9f3923c1d66ee56460e2660a3fbc6bfeacc3c2bd` introduces an executable RED that rejects inherited share-only App expectations and requires exact persisted σ+share accessible names. Production semantics must not be rolled back merely to satisfy stale assertions, and descendant-local duplicate/fuzzy repairs are not substitutes for the owner fix.

#861 also retains a separate buyer-visible layout risk: comparison axis copy can grow through σ/share and translation expansion inside a fixed SVG. A rendered/browser bounding-box RED across responsive widths, keyboard/focus states, and text-expansion locales is required before changing layout; accessible σ/share semantics must remain intact.

Fresh local Storybook inspection on #1041 predecessor `bb7cecf721d67be0f0ce32f77c642cff2f58e3be` covered the synthetic `Reports/LeftoverPairList/ClosestAndFarthest` story at the default desktop viewport and at 390 × 844. The pair actions wrap without horizontal page overflow at 390 px, preserving their exact values and next action. The plot's dense origin-adjacent tick labels still collide in both captures, and the fixed 480 px SVG intentionally requires horizontal scrolling on mobile. This is rendered local RED for the separate comparison-layout gap, not authenticated product acceptance and not authority to omit or approximate persisted ticks.

Exact #861 Tests `35514822818` is queued and is not acceptance evidence.

## Report / comparison stack

The report lineage has been converged ordinary/non-force through current #861. Exact active ancestry is:

`#861 9f3923c1... → #862 c05b155b... → #863 a9e10500... → #865 a51b0ec4...`

#866 final source `8d63271c4644b39d11d65263cc59e8fca8a548cd` was **normally merged** into #865. Its valid v2.82 product/test/ADR/CHANGELOG delta is materially present in #865 exact `a51b0ec4668fa4bef4cd45dfd777fe3df8871331`; #866 is closed/merged rather than merely closed or replaced by a successor. Exact compare from #863 to #865 has merge-base `a9e10500...`, `behind_by=0`, and retains both v2.81 and v2.82 deltas. Fresh #865 Tests `35517757738` is queued and is not acceptance evidence.

Because #866 is now a closed intermediate, #867 was retargeted from the closed #866 branch to active #865 without rewriting the #867 head. Current #867 exact `fc19017063aab7df438f2603959f78ddbb62b8e5` has #865 `a51b0ec...` as exact merge-base, `behind_by=0`, and only its four-file comparison-axis badge delta. Fresh #867 Tests `35517813171` is queued and is not acceptance evidence.

The active descendants continue:

`#867 fc190170... → #868 db281ce1... → #869 838dd8c0... → #870 a289ebd7... → #871 91cde2af... → #872 8bd9778a... → #873 050477cf... → #874 7192a978... → #875 b7e948ae...`

#875 has two current children:

- #876 `52542e26f6d602a3303859b39f173d57800135e6` → #1033 `ce4612557f26a2e0fd2fa62d520f5677d1cccbe7` → #1034 `53950a849c849b2e172234613ffd4c742cea393e`;
- #877 `f0a99af9e7962364a5f0f7ed96dc3b9a6d07fd32`.

Tests `35448971227` on predecessor #868 `07558b5a...`, Tests `35449409685` on predecessor #876 `1dc3cec3...`, Tests `35449469635` on predecessor #1033 `dc9efcb0...`, and Tests `35449496627` on predecessor #1034 `bb664b7a...` remain diagnostic evidence only. They do not transfer to the moved heads above.

The recovered #1033 predecessor receipt remains useful causal evidence: PostgreSQL/full-suite was GREEN while frontend failed `App > shows the synthetic sigma overlay data` because a share-only expectation (`leftover map comparison axis 1 (82%)`) contradicted rendered persisted σ+share (`leftover map comparison axis 1 (σ 1.84, 82%)`). That validates #861 ownership; it is not current-head GREEN/RED evidence for moved #1033 or #1034.

Historical #878/#879 remain delta carriers whose valid criterion/post-coordinate intent is reconstructed by current #1033/#1034. Their live PR authority has been refreshed to the current #876/#1033/#1034 heads; they remain open until verified GREEN succession proves all valid deltas are inherited.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`. Report lanes must consume that repair through protected integration or verified succession rather than duplicate telemetry source.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 306fc9dccf972c9fcb859b1379c32ec98649f137 → #1120 fb7b6c61fa5b552cc241e31bf8924cf5c63355d7 → #1117 dd060d315bf4666f60e802bfd68d88cc4b8f3985`.

Accumulated #1120 verifier/auth-fixture prerequisites remain in force: private or contradictory RSA/JWK metadata is rejected; `x5c` is canonical/parseable and consistent with JWK `n/e` and KeyUsage; unsupported `x5u` candidates fail closed because LineageWeave owns no remote-certificate retrieval/trust path; service-account subjects are derived from the checked-in realm fixture; service and human subjects are disjoint; required machine clients are unique, enabled OIDC confidential service-account clients with direct/browser/implicit grants disabled and the required REST/MCP access-token audiences. The public browser fixture remains Authorization Code + S256 PKCE with implicit flow disabled and exact local redirect origins.

Executable seed/bootstrap contract `fd3edd04d93714d152db31473850c10fe30b31d0` remains source-satisfied. The seed reads deterministic `demo.analyst` / `demo.admin` subjects from `docker/keycloak/realm-export.json`, fails closed on missing/disabled/shared subject identities, and no longer logs into master `admin-cli` or mints a human password-grant token. `scripts/warm_seeded_post_content.py` uses the validated confidential `lineageweave-test-automation` Client Credentials actor, and `make seed` orders deterministic human fixture seed → service-account authorization binding → machine warm-up while requiring only `KEYCLOAK_CLIENT_SECRET` for that OAuth step.

The final backend-integration ROPC finding remains executable rather than prose-only. `tests/test_backend_integration_oauth_contract.py` fails unless `backend/tests/test_api.py` stops requesting `grant_type=password` from public `lineageweave-frontend`, consumes distinct viewer/admin machine token helpers, and the public browser client has `directAccessGrantsEnabled=false` after migration. `backend/tests/integration_oauth_support.py` provides the existing `lineageweave-test-automation` viewer actor and `lineageweave-test-admin` admin actor and rejects token responses without a non-empty access token.

Review of that helper exposed a concrete pre-migration integration defect: its no-argument path used the hard-coded local default even when the suite had selected a different endpoint through `LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL`. Source RED `b7bb7a58ac72cd1a6974f1c4bf2375998c3ef2c7` pins the expected configured endpoint. Causal repair inherited by #1120 resolves the environment override at call time for both viewer and admin helpers while preserving explicit caller overrides and the existing secret sources.

A #1118 dependency review closed a separate source-level security gap. `uv.lock` already resolved PyJWT 2.13.0, but `pyproject.toml` still admitted `pyjwt[crypto]>=2.8.0` in both `dev` and `backend`. RED `6ea095400a0b95fe586161dcfd0730d91ce9f96d` requires both declared floors to be `>=2.13.0`, every committed PyJWT lock entry to satisfy that floor, and owned JWT verifier algorithm allow-lists to remain RS256-only rather than mix symmetric and asymmetric families. Repair `990dfdf30517262afebc7c8202f2c9b8f301d392` raises both floors; `e8ad79da959eef8c628164a8651e53313313dcd8` records the security changelog; exact #1118 `306fc9dccf972c9fcb859b1379c32ec98649f137` adds `docs/doctoring/PYJWT_SECURITY_REFERENCES.md` with APA 7th traceability to GitHub Reviewed CVE-2026-48523/48524/48525/48526 advisories and the RS256-only defense-in-depth rationale. Exact #1118 Tests `35506460512` is Draft-policy skipped; this is source-repaired but not hosted GREEN.

Current exact #1120 inspection shows `scripts/smoke_test_oidc.py` is already a confidential-machine smoke: it requests `grant_type=client_credentials` for `lineageweave-test-automation`, validates live JWKS/RS256/issuer/audience/authorized-party/subject, and explicitly states that it is not browser OIDC acceptance. It is therefore **not** a remaining public-client ROPC consumer. The earlier baseline wording that put the smoke path in the ROPC removal scope was stale and has been removed.

The remaining ROPC migration is the backend integration lane. Exact source/contract authority still requires the two analyst/admin password-grant calls in `backend/tests/test_api.py` to move to the distinct confidential viewer/admin helpers before `lineageweave-frontend.directAccessGrantsEnabled` becomes `false`.

Human browser product acceptance remains a rendered Authorization Code + S256 PKCE lane and must not be silently replaced by machine-only integration evidence. The confidential integration and smoke actors are machine evidence only; they do not prove login redirect/callback/session semantics.

#1120 ordinary/non-force adopted the complete exact #1118 dependency/test/changelog/doctoring parent at `fb7b6c61fa5b552cc241e31bf8924cf5c63355d7`. Exact compare from #1118 `306fc9dc...` has merge-base exactly `306fc9dc...` and `behind_by=0`, with the parent files inherited rather than removed. Exact #1120 Tests `35506471984` is Draft-skipped. #1117 is converged on exact #1120 at `dd060d315bf4666f60e802bfd68d88cc4b8f3985`; exact compare has merge-base `fb7b6c61...`, `behind_by=0`, and effective child delta only `README.md`. Exact #1117 Tests `35506484694` is Draft-skipped.

Remaining auth RED:

- wire `backend/tests/test_api.py` to the viewer/admin Client Credentials helpers and remove both public-client password-grant calls;
- atomically set `lineageweave-frontend.directAccessGrantsEnabled=false` while preserving Authorization Code + S256 PKCE browser configuration;
- obtain exact-head hosted GREEN, rendered browser session/return-URL/tampered-state/permission acceptance, and qualifying independent review.

## Voice-of-X acceptance boundary

Accepted ADR 0246 remains the vocabulary authority: twelve atomic Voice codes, an extensible scheme, and no Cartesian-product combination codes. The implementation preserves one imported primary Voice and normalized additional assignments with explicit truth status and PROV-O derivation. API, exact-value CSV, and JSON-LD tests cover carrying-Post/evidence separation and paged multi-Voice union. These source contracts do not prove the live product.

Current protected `main@83eba56149eb802cd63642c507c324c9976ec78e` has no newly collected, exact-head authenticated PostgreSQL API receipt or desktop/mobile rendered acceptance in this cycle. Voice delivery therefore remains **unverified at runtime**. A hidden evidence Post must omit the additional assignment rather than substitute the carrying Post, and a cutoff read must use the assignment interval effective at that cutoff. Completion requires synthetic authenticated PostgreSQL evidence plus rendered desktop and mobile evidence for zero-, one-, and multi-Voice states on the same candidate head.

#1121 current exact head is `dbabff85c72801a1a72a33dc69f969e032dc17b2`. It repairs ADR 0252 so Status/Context authority and the ADR index point to evidence-bearing ADR 0256 rather than unrelated I/O-Psychology ADR 0251. Local documentation hygiene is source-GREEN, but hosted CodeQL `35514992028`, Tests `35514992029`, SAST `35514992064`, and Security `35514992065` are queued. #1121 is source-repaired, not protected delivery. This documentation repair does not substitute for runtime PostgreSQL/browser Voice-history acceptance.

## Performance / immutable delivery

#995 `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains performance RED because durable exact-head cold buyer-path evidence is absent. #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` remains MCP latency RED until representative profiling and causal hot-path work demonstrate p95 ≤20 ms without sample shrinking, hidden I/O, or unrealistic cache warm-up.

#961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs source version identity but is not a release. Publication requires one protected exact candidate with required gates, installed/built package identity, CHANGELOG, immutable tag/release/package, SBOM/provenance, reproducibility, and rollback evidence.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical-owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 `9f3923c1...` | executable RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 `9f3923c1...` | rendered RED / owner repair pending | bounded layout repair retaining full evidence semantics; re-run responsive/text-expansion browser evidence |
| Report contracts | #862 → #863 → #865; merged #866; #867 → … → #875 → (#876 → #1033 → #1034, #877); historical #878/#879 | converged / fresh acceptance pending | finish #861 owner repair, then exact-head validation; predecessor failures stay diagnostic only |
| Catalog connection leases / TOCTOU | #1077 / #1080 | separate owner lanes | prove short transactions around external work, then obtain protected integration evidence |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority; queue owner #712 active | refresh consumers/receipts against current released owner contracts; keep runner starvation separate from product source |
| Authentication | #899 → #1118 `306fc9dc...` → #1120 `fb7b6c61...` → #1117 `dd060d31...` | seed/bootstrap repaired; machine smoke already Client Credentials; helper endpoint drift repaired; PyJWT floor/lock/verifier + APA 7th advisory trace source-repaired; backend-integration ROPC still executable RED | move backend integration to distinct machine helpers, disable public direct grants atomically, then obtain hosted/browser proof |
| Voice ADR authority | #1121 `dbabff85...` | source repaired / hosted checks queued | exact-head GREEN + independent review + normal merge, then protected-main runtime evidence |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge, approval, release, or GREEN state that exact protected evidence does not show.
