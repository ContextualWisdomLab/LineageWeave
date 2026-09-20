# Product & Technical Gap Baseline

> Exact-head refresh: 2026-09-21 07:00 KST. Protected `main` remains
> `83eba56149eb802cd63642c507c324c9976ec78e`; the live aggregate inventory is
> 164 open pull requests and 42 open issues. Those counts describe the queue,
> not delivery. The largest current buyer-visible security gap is #1119:
> public-browser password grants plus missing rendered Authorization Code
> acceptance. Candidate #1120 now has the minimal source repair at
> `867e26175a90cd7c6048be6aa91983686cc8d897`: the two backend integration
> actors use distinct confidential viewer/admin identities and the public
> browser client disables direct grants while retaining Authorization Code +
> S256 PKCE. Focused source contracts pass locally (20 tests), but #1120 is
> still a Draft stacked on #1118. No authenticated PostgreSQL/browser render,
> protected exact-head Checks, independent approval, merge, or release is
> claimed. Parent #1118 must protectively merge first; only then may #1120 be
> retargeted to `main` and collect fresh exact-head evidence.

> Current mutable authority overlay: 2026-09-21. Historical implementation detail belongs in Git/PR history. A predecessor, sibling, descendant, focused harness, skipped workflow, queued workflow, cancelled workflow, or documentation-only workflow is not acceptance for a moved product head.

> This update adopts #1041 exact predecessor `4e3ca6b7e4dbd4c38085c11389824f869a3024b5` against `main@83eba56149eb802cd63642c507c324c9976ec78e`. The live inventory showed 164 open pull requests and 42 open issues. Those aggregate counts are operational metadata, not delivery evidence. This file intentionally does **not** hard-code its own newly-created #1041 head: writing this file creates a new commit, so the live PR API/body owns #1041's exact head and exact-head workflow receipts. Completed successful protected receipts on that live head are authoritative for acceptance; queued, skipped, cancelled, failed, runnerless, or predecessor receipts are non-accepting and do not transfer.

## Delivery authority

- Protected `main`, live PR heads/bases, `AGENTS.md` / `CLAUDE.md`, ADRs, PRD/TRD, and exact workflow receipts are authoritative.
- LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. Canonical-owner source is consumed only through released/versioned contracts; it is not copied here.
- Draft/skipped, queued, cancelled, `action_required`, runnerless, review-skipped, or owner-control-plane receipts are not product GREEN.
- Parent movement requires ordinary non-force descendant convergence, reconstruction, or safe retargeting. Closed intermediate branches must not remain live ancestry after verified normal merge into an active parent.
- Force push, destructive rebase, self-approval, gate weakening, synthetic status, blind rerun, and no-op wake commits are not acceptance tools.
- Release readiness requires one exact protected candidate with version/CHANGELOG/package/tag/release/SBOM/provenance/reproducibility/rollback evidence.

Fresh protected references:

- LineageWeave `main@83eba56149eb802cd63642c507c324c9976ec78e`, protected, signature valid.
- Canonical reusable-workflow owner `ContextualWisdomLab/.github@e6334e229581a918e2f22de18733b76fa65d7e71`, protected, signature valid.

Re-read both before merge or release; neither is a frozen dependency.

Ready review lanes at the predecessor snapshot were #911 `2d91db2e76849dead722b343fb5d816886114b81`, #983 `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8`, #1041 (this documentation branch; exact head must be read live), #1079 `c2923950e73c88a9f9fd932332ddd47682da124b`, #1115 `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4`, and #1121 `dbabff85c72801a1a72a33dc69f969e032dc17b2`. Readiness is not acceptance. #983 and #1115 retain `CHANGES_REQUESTED`; no predecessor approval or workflow result transfers to moved heads.

#1041 predecessor `ecc0c7916692d94fd6e092e42750a62751d4e588` had CodeQL PR `35530132994`, Tests `35530132918`, SAST `35530133109`, and Security `35530132977`; all four were cancelled when the branch advanced to `6fb0cb0d...`. Tests jobs `106129146183` and `106129146237` finished cancelled with `runner_id=0` and no steps, so they never executed repository code. The successor `6fb0cb0d...` then received Tests `35532215015`, SAST `35532214984`, CodeQL PR `35532214983`, and Security `35532214903`; at collection time those successor jobs were queued and runnerless. Both predecessor and successor receipts are diagnostic-only after this file moves the head again.

## Customer Master / translation

#929 `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` remains the PostgreSQL translation-ledger prerequisite for #932. The 37-key × 8-locale (`ko/en/ja/zh/vi/es/de/fr`) resource still needs independent language/product review, immutable one-way publication, authenticated browser consumption, permission/error/empty/loading states, CJK/text-expansion/font fallback, and current performance evidence. #996 remains gated by translation/read-model and Customer Master authorization prerequisites.

## Material UI / accessibility

#1041 carries one bounded buyer-visible accessibility repair in its own delta: closest/farthest pair buttons start their accessible names with the exact visible localized label, append finite persisted evidence, and wrap the existing token-backed title/evidence content on narrow screens. Focused component and Storybook evidence are local candidate evidence only; protected exact-head Checks, independent approval, authenticated PostgreSQL API evidence, and protected-main delivery remain outstanding.

The same mobile render still clips plot labels at the fixed SVG boundary. That observation belongs to the existing #861 comparison-layout RED below; #1041 does not hide ticks, fabricate coordinates, or claim that separate gap complete.

#861 remains the earliest App integration acceptance root. Parent #860 candidate `13b838a3ea4d23b3d358d2f0adecec9c21cb0a8f` must merge through its protected gate before the child is retargeted to `main`. That parent candidate repairs a valid review finding by deduplicating ticks on exact persisted coordinate values instead of their rounded labels; nearby coordinates that both display `+0.50` therefore remain separate plotted ticks, and React keys use the same exact value identity. Its 118 focused frontend tests, lint, and production build passed locally. Hosted Checks are queued and independent current-head approval is absent, so #860 remains Draft on #859 and these receipts do not authorize promotion.

Current #861 candidate `d572f65187f1148c3c7ebcdcbad3361d0c19fd9f` replaces inherited share-only App expectations with exact persisted σ+share names, makes the singular-only and rank-0 states exact, and right-bounds both axis captions inside the SVG. It does not derive σ from share or hide either persisted value. The focused contract passed 3 tests; the frontend suite passed 867 tests, followed by lint and production build. These are local candidate receipts, not protected delivery.

#860 and #861 retain dense origin-adjacent tick collisions as a separate buyer-visible risk. Current-head Storybook screenshots at 1440×1100 and 390×844 verify that #860 preserves the comparison plot on desktop and within the mobile horizontal-scroll viewport; #861 screenshots verify that the repaired σ+share captions stay inside the SVG. The screenshots are rendered local evidence, not authenticated PostgreSQL/API acceptance. Text-expansion locale and authenticated product acceptance remain unavailable.

Fresh hosted Checks and independent approval for #861 candidate `d572f651...` remain authoritative and unverified. The PR stays Draft on its parent base; no predecessor receipt transfers.

## Report / comparison stack

Active ancestry is code-current through the owner repair stack:

`#861 9f3923c1... → #862 c05b155b... → #863 a9e10500... → #865 a51b0ec4...`

#866 final source `8d63271c4644b39d11d65263cc59e8fca8a548cd` was normally merged into #865; its valid v2.82 product/test/ADR/CHANGELOG delta is materially present in #865 exact `a51b0ec4668fa4bef4cd45dfd777fe3df8871331`. #867 was safely retargeted from the closed #866 branch to active #865 without rewriting its head; exact #867 `fc19017063aab7df438f2603959f78ddbb62b8e5` has #865 as merge-base, `behind_by=0`, and only its four-file badge delta.

Descendants continue:

`#867 fc190170... → #868 db281ce1... → #869 838dd8c0... → #870 a289ebd7... → #871 91cde2af... → #872 8bd9778a... → #873 050477cf... → #874 7192a978... → #875 b7e948ae...`

#875 children are #876 `52542e26...` → #1033 `ce461255...` → #1034 `53950a84...`, and #877 `f0a99af9...`. Historical #878/#879 remain delta carriers until verified GREEN succession proves all valid deltas are inherited; predecessor workflow failures remain diagnostic only.

The recovered #1033 predecessor failure is still useful causal evidence: PostgreSQL/full-suite was GREEN while frontend failed `App > shows the synthetic sigma overlay data` because share-only `leftover map comparison axis 1 (82%)` contradicted rendered persisted `leftover map comparison axis 1 (σ 1.84, 82%)`. That validates #861 ownership but is not current-head evidence for moved descendants.

The OpenTelemetry `LoggingHandler` deprecation remains separately owned by #973 `182d3c9d4c5f2a8ab2d63e77b8a9ced663a183f6`; report lanes must consume that repair through protected integration or verified succession.

## Summary-read catalog authorization

#1078 remains a separate critical authorization/integrity owner from #1077/#1080. A `post_read`-authorized `GET /api/posts/{post_id}/summary` may derive and persist its summary projection, but it must not gain the capability to create or mutate the shared `corporate_entity` catalog or hierarchy. The causal repair must keep summary-read behavior intact while admitting live hierarchy-inference/relation-verification catalog mutation only for an explicit `post_admin` authority; exact-match consumption of already-known catalog identities may remain read-only. #1077/#1080 continue to own connection-lease/TOCTOU lifetime rather than this permission boundary.

#1078 remains RED until executable real-service evidence proves a `post_read` account leaves global catalog rows/content invariant, a `post_admin` account retains the intended enrichment path, provider/network mutation capability is absent from the low-privilege path, and exact-head security evidence clears the original finding.

## Authentication / authorization stack

Current authority:

`#899 a2da5875525cd0950999487ff8fe7d439284dbd2 → #1118 306fc9dccf972c9fcb859b1379c32ec98649f137 → #1120 867e26175a90cd7c6048be6aa91983686cc8d897`.

Accumulated #1120 verifier/auth-fixture prerequisites remain in force: contradictory RSA/JWK metadata is rejected; `x5c` must be canonical/parseable and consistent with JWK `n/e` and KeyUsage; unsupported `x5u` candidates fail closed because LineageWeave owns no remote-certificate retrieval/trust path; service-account subjects come from the checked-in realm fixture and remain disjoint from human subjects; machine clients are unique enabled OIDC confidential service-account clients with direct/browser/implicit grants disabled and required REST/MCP audiences. The public browser fixture remains Authorization Code + S256 PKCE with implicit flow disabled and exact local redirect origins.

Seed/bootstrap ROPC is source-repaired. Human fixture subjects are read deterministically from `docker/keycloak/realm-export.json`; seed no longer logs into master `admin-cli` or mints a human password token. `scripts/warm_seeded_post_content.py` uses the validated confidential `lineageweave-test-automation` Client Credentials actor, and `make seed` orders human fixture seed → service-account authorization binding → machine warm-up. `scripts/smoke_test_oidc.py` and the k6 HTTP/MCP paths are already machine Client Credentials consumers and are not remaining public-client ROPC callers.

The final backend-integration ROPC finding is source-repaired at #1120 exact
`867e26175a90cd7c6048be6aa91983686cc8d897`: `backend/tests/test_api.py`
uses distinct confidential viewer/admin helpers, and the public browser client
sets `directAccessGrantsEnabled=false` in the same causal migration. The
focused OAuth, documentation, and public-docstring contracts pass locally (20
tests). This is candidate evidence only. Rendered browser Authorization Code +
S256 PKCE, callback/session restoration, return-path restoration, a protected
buyer API call, invalid-state rejection, authenticated PostgreSQL execution,
hosted exact-head Checks, and independent approval remain unavailable.

The pre-migration machine helper now carries four causal repairs:

- endpoint override RED `b7bb7a58ac72cd1a6974f1c4bf2375998c3ef2c7`: no-argument viewer/admin helpers honor `LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL`;
- Compose empty/unset parity RED `3633a0d115d854adc3f33f8a3d0412c49667351a` / repair `ec2481dda8ed75fa17c31eae0c2e5974b39a75e3`: local loopback helpers mirror `${VAR:-dev_default}` semantics rather than sending an empty client secret;
- remote-fallback RED `3ba75a6ee8ead09cbb5fa4547c2b4378d7736205` / repair `f597be93f29e330f97b294d4fb69795d333f8a7f`: repository-known synthetic dev secrets are allowed only for `localhost`, `127.0.0.1`, or `::1`; a non-loopback Keycloak endpoint with an absent or empty secret fails before token I/O;
- remote-cleartext RED `76b1884a5b64056f02cdb60c13610b02fd4b70d6` / repair `db3dda0c84b5bc9adefe16d6d462a0e56c7af2d7`: an explicit confidential-client secret is also rejected before token I/O when a non-loopback token endpoint is cleartext HTTP. Loopback HTTP remains a disposable local-fixture exception. Exact #1120 `0038f57f...` makes ADR 0028 code-current with RFC 6749 §§3.2, 10.8, and 10.9 plus the existing RFC 9700 / RFC 10017 references.

The predecessor #1120 Tests `35529880681` is Draft-policy skipped and does not
transfer to `867e2617...`. #1117 still targets the predecessor #1120 head and
must not be treated as converged on the moved parent until ordinary ancestry
and effective delta are rechecked. Neither candidate has protected GREEN or
rendered-browser acceptance.

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

## Cross-PR identity and contract audit

Open stacked work still has two release-identity collisions that must be resolved by parent-first protected integration rather than parallel publication: #843 and #844 both claim `v2.62.0`, while sibling #876 and #877 both claim `v2.92.0`. Their distinct API/UI deltas may remain separate review units, but one integrated release identity cannot name two divergent heads. Retarget descendants only after the selected parent merges, then refresh ADR, API, CHANGELOG, package, and exact-head evidence.

Migration ordinal uniqueness remains separately owned by #1049 `5322971193d1ff4e0ae13c054d8f99615934d4dc`; the baseline does not infer a schema repair before that exact head is reviewed and protected-integrated. PRD/ADR identity reconciliation remains open in #997 and Voice authority in #1121. No current evidence supports renumbering another PR's ADR or migration from this documentation branch.

## Buyer-gap register

| Area | Current authority | State | Required causal next step |
| --- | --- | --- | --- |
| Translation / Customer Master | #929 → #932 → #996 | RED/Draft | PostgreSQL + canonical-owner checks, language review, browser/auth/performance acceptance |
| App comparison acceptance | #861 `9f3923c1...` | executable RED | repair exact σ+share App integration expectations, then ordinary descendant convergence |
| App comparison layout | #861 `9f3923c1...` | rendered RED / owner repair pending | bounded layout repair retaining full evidence semantics; re-run responsive/text-expansion browser evidence |
| Report contracts | #862 → #863 → #865; merged #866; #867 → … → #875 → (#876 → #1033 → #1034, #877); historical #878/#879 | converged / fresh acceptance pending | finish #861 owner repair, then exact-head validation; predecessor failures stay diagnostic only |
| Catalog connection leases / TOCTOU | #1077 / #1080 | separate owner lanes | prove short transactions around external work, then obtain protected integration evidence |
| Summary-read shared corporate catalog mutation | #1078 | separate owner lane / RED | enforce the `post_read`/`post_admin` mutation boundary, preserve summary-read behavior, then obtain exact-head security evidence |
| Telemetry deprecation | #973 | source repaired / integration pending | consume through protected integration or verified succession |
| Canonical CI/CodeQL | `.github@e6334e22...` | live owner authority; queue owner #712 active | refresh consumers/receipts against current released owner contracts; keep runner starvation separate from product source |
| Authentication | #899 → #1118 `306fc9dc...` → #1120 `0038f57f...` → #1117 `f1f5637c...` | seed/bootstrap repaired; machine smoke/k6 already Client Credentials; helper endpoint + empty-secret + remote-fallback + remote-cleartext defects source-repaired; PyJWT floor/lock/verifier + APA 7th advisory trace source-repaired; backend-integration ROPC still executable RED | move backend integration to distinct machine helpers, disable public direct grants atomically, then obtain hosted/browser proof |
| Voice ADR authority | #1121 `dbabff85...` | source repaired / hosted checks queued | exact-head GREEN + independent review + normal merge, then protected-main runtime evidence |
| Frontend performance | #995 | RED | representative cold buyer-path measurement and causal repair if over budget |
| MCP latency | #1009 | RED | representative profile and hot-path repair to p95 ≤20 ms |
| Release identity | #961 | release RED | required gates + immutable release/SBOM/provenance/reproducibility/rollback |

This baseline records unresolved authority; it must not be used to infer a merge, approval, release, or GREEN state that exact protected evidence does not show.
