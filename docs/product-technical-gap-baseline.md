# Product & Technical Gap Baseline

> Current mutable authority overlay: 2026-09-20. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, or documentation workflow is not acceptance for a moved product head.

> Live inventory at this read: 164 open PRs and 42 open issues. This count is
> operational metadata, not release evidence. This update was based on #1041
> parent head `9119775aa13ea7ea461a4c9aea914a85503ce670` against
> `main@83eba56149eb802cd63642c507c324c9976ec78e`; the PR remains Draft.
> Its full/frontend jobs are Draft-policy skipped, while admission and analysis
> checks are queued. None is product acceptance.

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

The comparison-coordinate reconstruction stack is also not GREEN. #876 exact `1dc3cec3c251a1cf4d4b53acfb8a21532c57f54b` has Tests `35449409685` failing in both frontend job `105913841595` (`Test` after lint) and full-suite job `105913841700` (`Run full test suite against PostgreSQL`). #1033 exact `dc9efcb0b16f8e9887e9d72ebef76fe28cf4b2ab` has Tests `35449469635`: PostgreSQL/full-suite job `105914000303` is GREEN, while frontend job `105914000414` fails its `Test` step after lint. #1034 exact `bb664b7aae733933c11b2fe056de2a7b16a02c15` has the same classification in Tests `35449496627`: PostgreSQL/full-suite job `105914068322` is GREEN, frontend job `105914068148` fails its `Test` step after lint. Historical #878/#879 remain delta carriers whose valid criterion/post-coordinate intent is reconstructed by #1033/#1034; neither historical PR nor its successor is closable merely by substitution while the successor heads remain RED. The exact frontend failing test node/output is still unavailable from the current Actions surface, so geometry, copy, and expectation changes must not be guessed.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`. Report lanes must consume that repair through protected integration or verified succession rather than duplicate telemetry source.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 306fc9dccf972c9fcb859b1379c32ec98649f137 → #1120 fb7b6c61fa5b552cc241e31bf8924cf5c63355d7 → #1117 dd060d315bf4666f60e802bfd68d88cc4b8f3985`.

Accumulated #1120 verifier/auth-fixture prerequisites remain in force: private or contradictory RSA/JWK metadata is rejected; `x5c` is canonical/parseable and consistent with JWK `n/e` and KeyUsage; unsupported `x5u` candidates fail closed because LineageWeave owns no remote-certificate retrieval/trust path; service-account subjects are derived from the checked-in realm fixture; service and human subjects are disjoint; required machine clients are unique, enabled OIDC confidential service-account clients with direct/browser/implicit grants disabled and the required REST/MCP access-token audiences. The public browser fixture remains Authorization Code + S256 PKCE with implicit flow disabled and exact local redirect origins.

Executable seed/bootstrap contract `fd3edd04d93714d152db31473850c10fe30b31d0` remains source-satisfied. The seed reads deterministic `demo.analyst` / `demo.admin` subjects from `docker/keycloak/realm-export.json`, fails closed on missing/disabled/shared subject identities, and no longer logs into master `admin-cli` or mints a human password-grant token. `scripts/warm_seeded_post_content.py` uses the validated confidential `lineageweave-test-automation` Client Credentials actor, and `make seed` orders deterministic human fixture seed → service-account authorization binding → machine warm-up while requiring only `KEYCLOAK_CLIENT_SECRET` for that OAuth step.

The final backend-integration ROPC finding remains executable rather than prose-only. `tests/test_backend_integration_oauth_contract.py` fails unless `backend/tests/test_api.py` stops requesting `grant_type=password` from public `lineageweave-frontend`, consumes distinct viewer/admin machine token helpers, and the public browser client has `directAccessGrantsEnabled=false` after migration. `backend/tests/integration_oauth_support.py` provides the existing `lineageweave-test-automation` viewer actor and `lineageweave-test-admin` admin actor and rejects token responses without a non-empty access token.

Review of that helper exposed a concrete pre-migration integration defect: its no-argument path used the hard-coded local default even when the suite had selected a different endpoint through `LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL`. Source RED `b7bb7a58ac72cd1a6974f1c4bf2375998c3ef2c7` pins the expected configured endpoint. Causal repair inherited by #1120 resolves the environment override at call time for both viewer and admin helpers while preserving explicit caller overrides and the existing secret sources.

A fresh #1118 dependency review closed a separate source-level security gap. `uv.lock` already resolved PyJWT 2.13.0, but `pyproject.toml` still admitted `pyjwt[crypto]>=2.8.0` in both `dev` and `backend`. RED `6ea095400a0b95fe586161dcfd0730d91ce9f96d` requires both declared floors to be `>=2.13.0`, requires every committed PyJWT lock entry to satisfy that floor, and requires owned JWT verifier algorithm allow-lists to remain RS256-only rather than mix symmetric and asymmetric families. Repair `990dfdf30517262afebc7c8202f2c9b8f301d392` raises both floors; `e8ad79da959eef8c628164a8651e53313313dcd8` records the security changelog; exact #1118 `306fc9dccf972c9fcb859b1379c32ec98649f137` adds `docs/doctoring/PYJWT_SECURITY_REFERENCES.md` with APA 7th traceability to GitHub Reviewed CVE-2026-48523/48524/48525/48526 advisories and the RS256-only defense-in-depth rationale. The lock was already compliant, so no generated-lock rewrite was needed. Exact #1118 Tests `35506460512` is Draft-policy skipped; this is source-repaired but not hosted GREEN.

The larger ROPC migration is still RED. Exact source inspection still finds the two analyst/admin password-grant calls in `backend/tests/test_api.py`, and `docker/keycloak/realm-export.json` still has `lineageweave-frontend.directAccessGrantsEnabled=true`. Those two source changes must move atomically so the final local ROPC consumer is removed before the browser client is disabled.

Human browser product acceptance remains a rendered Authorization Code + S256 PKCE lane and must not be silently replaced by machine-only integration evidence. The two confidential helper actors are appropriate for a test suite that exercises API authorization as a machine caller; they do not prove login redirect/callback/session semantics.

#1120 ordinary/non-force adopted the complete exact #1118 dependency/test/changelog/doctoring parent at `fb7b6c61fa5b552cc241e31bf8924cf5c63355d7`. Exact compare from #1118 `306fc9dc...` has merge-base exactly `306fc9dc...` and `behind_by=0`, with the parent files inherited rather than removed. Exact #1120 Tests `35506471984` is Draft-skipped. #1117 is converged on exact #1120 at `dd060d315bf4666f60e802bfd68d88cc4b8f3985`; exact compare has merge-base `fb7b6c61...`, `behind_by=0`, and effective child delta only `README.md`. Exact #1117 Tests `35506484694` is Draft-skipped.

Remaining auth RED:

- wire `backend/tests/test_api.py` to the viewer/admin Client Credentials helpers and remove both public-client password-grant calls;
- atomically set `lineageweave-frontend.directAccessGrantsEnabled=false` while preserving Authorization Code + S256 PKCE browser configuration;
- human browser product acceptance remains a rendered Authorization Code + S256 PKCE lane and must not be silently replaced by machine-only evidence;
- obtain exact-head hosted GREEN, rendered browser session/return-URL/tampered-state/permission acceptance, and qualifying independent review.

## Voice-of-X acceptance boundary

Accepted ADR 0246 remains the vocabulary authority: twelve atomic Voice codes,
an extensible scheme, and no Cartesian-product combination codes. The current
implementation preserves one imported primary Voice and normalized additional
assignments with explicit truth status and PROV-O derivation. API, exact-value
CSV, and JSON-LD tests cover carrying-Post/evidence separation and paged
multi-Voice union. These source contracts do not prove the live product.

Current protected `main@83eba56149eb802cd63642c507c324c9976ec78e`
has no newly collected, exact-head authenticated PostgreSQL API receipt or
desktop/mobile rendered acceptance in this cycle. Voice delivery therefore
remains **unverified at runtime**. A hidden evidence Post must omit the
additional assignment rather than substitute the carrying Post, and a cutoff
read must use the assignment interval effective at that cutoff. Completion
requires synthetic authenticated PostgreSQL evidence plus rendered desktop and
mobile evidence for zero-, one-, and multi-Voice states on the same candidate
head.

There is also a documentation identity collision that must not be resolved by
intuition: ADR 0251 is the accepted I/O-Psychology semantic-layer decision,
while ADR 0252 currently says it “extends ADR 0251” for temporal primary-Voice
history. The Voice implementation authority is ADR 0246 plus the accepted
temporal/persistence decisions and executable schema; the mismatched prose
reference is unresolved until its owning ADR is corrected with an explicit
amendment. No API, schema, release-number, or migration identity is changed by
this baseline note.

## Performance / immutable delivery

#995 `dbe5ac54228162e3ad5a9c92460006fb5e49e935` remains performance RED because durable exact-head cold buyer-path evidence is absent. #1009 `4fff982a96b0ad6e791aa8c463925388d036f08f` remains MCP latency RED until representative profiling and causal hot-path work demonstrate p95 ≤20 ms without sample shrinking, hidden I/O, or unrealistic cache warm-up.

#961 `3bdec0504a65e63f44bd49ba15de37182a1672cc` repairs source version identity but is not a release. Publication requires one protected exact candidate with required gates, installed/built package identity, CHANGELOG, immutable tag/release/package, SBOM/provenance, reproducibility, and rollback evidence.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 | RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 | RED | rendered clipping/bounds RED across responsive + text-expansion states, then bounded layout fix |
| Report contracts | #868; #876 → #1033 → #1034; historical #878/#879 | frontend RED; #876 PostgreSQL RED; #1033/#1034 PostgreSQL GREEN | recover exact frontend failing node/output; repair causal owner without guessing; converge descendants; keep historical delta carriers until verified GREEN succession |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority; queue owner #712 active | refresh consumers/receipts against current released owner contracts; keep runner starvation separate from product source |
| Authentication | #899 → #1118 `306fc9dc...` → #1120 `fb7b6c61...` → #1117 `dd060d31...` | seed/bootstrap repaired; helper endpoint drift repaired; PyJWT floor/lock/verifier + APA 7th advisory trace source-repaired; backend ROPC still executable RED | wire distinct viewer/admin machine helpers into backend integration, disable public direct grants atomically, then obtain hosted/browser proof |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge or release that protected-state evidence does not show.
