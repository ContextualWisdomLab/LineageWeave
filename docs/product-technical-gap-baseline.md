# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-21. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, queued workflow, or documentation-only workflow is not acceptance for a moved product head.

> This update starts from #1041 exact predecessor `44befb5974cdf65f97b94331bfe566c85075fc50` against `main@83eba56149eb802cd63642c507c324c9976ec78e`; the PR is Ready. New exact-head workflow receipts created by this edit are authoritative for acceptance; predecessor receipts do not transfer.

## Delivery authority

- Protected `main`, live PR heads/bases, `AGENTS.md` / `CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are authoritative.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, `action_required`, runnerless, review-skipped, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence, reconstruction, or safe retargeting. Closed intermediate branches must not remain live ancestry after verified normal merge into an active parent.
- Force push, destructive rebase, self-approval, gate weakening, synthetic status, blind rerun, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

Fresh protected references:

- LineageWeave `main@83eba56149eb802cd63642c507c324c9976ec78e`, protected, signature valid.
- Canonical reusable-workflow owner `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`, protected, signature valid.

Re-read both before merge or release; neither is a frozen dependency.

## Customer Master / translation

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Material UI / accessibility

#861 remains the earliest proven App integration acceptance root. #860 exact `2084d534cef027aacf515a0907e36a3aa600fa62` was hosted GREEN; current #861 exact `9f3923c1d66ee56460e2660a3fbc6bfeacc3c2bd` introduces an executable RED that rejects inherited share-only App expectations and requires exact persisted σ+share accessible names. Production semantics must not be rolled back to satisfy stale assertions, and descendant-local fuzzy repairs are not substitutes for the owner fix.

#861 also retains a distinct buyer-visible layout risk: comparison axis copy can grow through σ/share and translation expansion inside a fixed SVG. Existing local Storybook evidence at desktop and 390×844 shows dense origin-adjacent tick collision and a 480 px SVG requiring horizontal scroll on mobile. This is rendered local RED, not authenticated product acceptance and not authority to omit persisted ticks. A current-head bounding-box/browser RED across responsive widths, keyboard/focus states, and text-expansion locales is required before a bounded layout repair.

Exact #861 Tests `35514822818` remains non-acceptance while queued.

## Report / comparison stack

Active ancestry is code-current through the owner repair stack:

`#861 9f3923c1... → #862 c05b155b... → #863 a9e10500... → #865 a51b0ec4...`

#866 final source `8d63271c4644b39d11d65263cc59e8fca8a548cd` was normally merged into #865; its valid v2.82 product/test/ADR/CHANGELOG delta is materially present in #865 exact `a51b0ec4668fa4bef4cd45dfd777fe3df8871331`. #867 was safely retargeted from the closed #866 branch to active #865 without rewriting its head; exact #867 `fc19017063aab7df438f2603959f78ddbb62b8e5` has #865 as merge-base, `behind_by=0`, and only its four-file badge delta.

Descendants continue:

`#867 fc190170... → #868 db281ce1... → #869 838dd8c0... → #870 a289ebd7... → #871 91cde2af... → #872 8bd9778a... → #873 050477cf... → #874 7192a978... → #875 b7e948ae...`

#875 children are #876 `52542e26...` → #1033 `ce461255...` → #1034 `53950a84...`, and #877 `f0a99af9...`. Historical #878/#879 remain delta carriers until verified GREEN succession proves all valid deltas are inherited; predecessor workflow failures remain diagnostic only.

The recovered #1033 predecessor failure is still useful causal evidence: PostgreSQL/full-suite was GREEN while frontend failed `App > shows the synthetic sigma overlay data` because share-only `leftover map comparison axis 1 (82%)` contradicted rendered persisted `leftover map comparison axis 1 (σ 1.84, 82%)`. That validates #861 ownership but is not current-head evidence for moved descendants.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`; report lanes must consume that repair through protected integration or verified succession.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 306fc9dccf972c9fcb859b1379c32ec98649f137 → #1120 f597be93f29e330f97b294d4fb69795d333f8a7f → #1117 2a467401d65027aaa136a6b05a78968ac86b1c0f`.

Accumulated #1120 verifier/auth-fixture prerequisites remain in force: contradictory RSA/JWK metadata is rejected; `x5c` must be canonical/parseable and consistent with JWK `n/e` and KeyUsage; unsupported `x5u` candidates fail closed because LineageWeave owns no remote-certificate retrieval/trust path; service-account subjects come from the checked-in realm fixture and remain disjoint from human subjects; machine clients are unique enabled OIDC confidential service-account clients with direct/browser/implicit grants disabled and required REST/MCP audiences. The public browser fixture remains Authorization Code + S256 PKCE with implicit flow disabled and exact local redirect origins.

Seed/bootstrap ROPC is source-repaired. Human fixture subjects are read deterministically from `docker/keycloak/realm-export.json`; seed no longer logs into master `admin-cli` or mints a human password token. `scripts/warm_seeded_post_content.py` uses the validated confidential `lineageweave-test-automation` Client Credentials actor, and `make seed` orders human fixture seed → service-account authorization binding → machine warm-up. `scripts/smoke_test_oidc.py` and the k6 HTTP/MCP paths are already machine Client Credentials consumers and are not remaining public-client ROPC callers.

The final backend-integration ROPC finding remains executable in `tests/test_backend_integration_oauth_contract.py`: `backend/tests/test_api.py` must stop requesting `grant_type=password` from public `lineageweave-frontend`, use distinct viewer/admin machine helpers, and the browser client must move to `directAccessGrantsEnabled=false` in the same causal migration. Current source still has the two password-grant callers and current realm fixture still has public direct grants enabled, so this gap remains RED.

The pre-migration machine helper now carries three causal repairs:

- endpoint override RED `b7bb7a58ac72cd1a6974f1c4bf2375998c3ef2c7`: no-argument viewer/admin helpers honor `LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL`;
- Compose empty/unset parity RED `3633a0d115d854adc3f33f8a3d0412c49667351a` / repair `ec2481dda8ed75fa17c31eae0c2e5974b39a75e3`: local loopback helpers mirror `${VAR:-dev_default}` semantics rather than sending an empty client secret;
- remote-fallback RED `3ba75a6ee8ead09cbb5fa4547c2b4378d7736205` / repair `f597be93f29e330f97b294d4fb69795d333f8a7f`: repository-known synthetic dev secrets are allowed only for `localhost`, `127.0.0.1`, or `::1`. A non-loopback Keycloak endpoint with an absent or empty relevant secret now fails before token I/O instead of receiving a local fallback secret. Explicit non-empty operator secrets retain their prior behavior.

Exact #1120 Tests `35528397368` is Draft-policy skipped, so the latest helper repair is source-repaired rather than hosted GREEN. #1117 was immediately reconstructed ordinary/non-force on exact #1120 at `2a467401d65027aaa136a6b05a78968ac86b1c0f`; exact compare has merge-base `f597be93...`, `behind_by=0`, and effective child delta only `README.md`. Exact #1117 Tests `35528461243` is Draft-skipped.

#1118 separately owns the PyJWT declared-floor repair: both install surfaces require `pyjwt[crypto]>=2.13.0`, the committed lock already resolves 2.13.0, owned JWT verification remains RS256-only, and `docs/doctoring/PYJWT_SECURITY_REFERENCES.md` records APA 7th traceability for CVE-2026-48523/48524/48525/48526. Exact #1118 Tests `35506460512` is Draft-skipped; this remains source-repaired, not hosted GREEN.

Human browser acceptance remains a rendered Authorization Code + S256 PKCE lane. Machine integration/smoke/performance actors do not prove redirect, callback, session restoration, return URL, tampered state, MFA/SSO, or buyer permission rendering.

Remaining auth RED:

- wire `backend/tests/test_api.py` to the distinct viewer/admin Client Credentials helpers and remove both public-client password-grant calls;
- atomically set `lineageweave-frontend.directAccessGrantsEnabled=false` while preserving Authorization Code + S256 PKCE browser configuration;
- obtain exact-head hosted GREEN, rendered browser session/return-URL/tampered-state/permission acceptance, and qualifying independent review.

## Voice-of-X acceptance boundary

Accepted ADR 0246 remains vocabulary authority: twelve atomic Voice codes, extensible scheme, no Cartesian-product combination codes. Implementation preserves one imported primary Voice and normalized additional assignments with explicit truth status and PROV-O derivation. API, exact-value CSV, and JSON-LD tests cover carrying-Post/evidence separation and paged multi-Voice union, but these source contracts do not prove live delivery.

Protected `main@83eba56149eb802cd63642c507c324c9976ec78e` has no newly collected exact-head authenticated PostgreSQL API receipt or desktop/mobile rendered acceptance for Voice history. A hidden evidence Post must omit the additional assignment rather than substitute the carrying Post, and cutoff reads must use the assignment interval effective at the cutoff.

#1121 exact `dbabff85c72801a1a72a33dc69f969e032dc17b2` repairs ADR 0252 so Status/Context and the ADR index point to evidence-bearing ADR 0256 rather than unrelated ADR 0251. Local documentation hygiene is source-GREEN, while hosted CodeQL `35514992028`, Tests `35514992029`, SAST `35514992064`, and Security `35514992065` remain queued before repository execution. Canonical runner-owner issue `.github#712` owns the first-runner acquisition / organization throughput incident; no LineageWeave wake commit substitutes for that owner repair.

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
| Authentication | #899 → #1118 `306fc9dc...` → #1120 `f597be93...` → #1117 `2a467401...` | seed/bootstrap repaired; machine smoke/k6 already Client Credentials; helper endpoint + empty-secret + remote-fallback defects source-repaired; PyJWT floor/lock/verifier + APA 7th advisory trace source-repaired; backend-integration ROPC still executable RED | move backend integration to distinct machine helpers, disable public direct grants atomically, then obtain hosted/browser proof |
| Voice ADR authority | #1121 `dbabff85...` | source repaired / hosted checks queued | exact-head GREEN + independent review + normal merge, then protected-main runtime evidence |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge, approval, release, or GREEN state that exact protected evidence does not show.
