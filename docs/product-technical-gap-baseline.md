# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, open PR/Issue state, ADRs and exact-head receipts are authoritative. The preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md); earlier history through 2026-09-13 remains separately preserved.

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve valid product, test, fixture, contract and evidence deltas, but checks and reviews never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A job with no runner assignment and zero executed steps is control-plane evidence, not executed product or security evidence.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming/status, locale expansion/font fallback and applicable performance evidence. Story/test source is evidence intent; static Storybook build alone is not interaction evidence.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` is `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` was last revalidated at `64aa08d7fa487deacd41c761c36277ca68cab6c9`; it must be refreshed before promotion. No LineageWeave-local CodeQL status shim, runner workaround, provider/model pin, copied queue implementation, synthetic status, no-op wake commit or lifecycle churn substitutes for owner evidence.

## Current foundations and buyer-visible gaps

### Customer Master authorization and translations

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. #929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative versioned UI translation ledger and 37-key × 8-locale Customer Master draft; direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` remains Draft. Publication still requires hosted PostgreSQL/full-suite and security/static GREEN, independent language/product review, immutable one-way publication, authenticated API/browser consumption, and CJK/text-expansion/font-fallback evidence. Ontology/concept labels remain separate canonical truth.

### Leftover-pair action accessibility

#977 remains Draft on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. Its intermediate head `cf3bc986b7838731e3ef056fa5c4cc9bb03597ca` exists only to run the purpose-bounded selector repair for five stale inherited `frontend/src/App.test.tsx` accessible-name expectations; it is not product acceptance. One-shot run `35316632816` remains queued before runner assignment. ADR 0049 was aligned on docs commit `91a66bf69e200615f890177b4cfd2a5a6686dd64`; that docs repair does not transfer acceptance to #977.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs; child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` remains ordinarily/non-force converged. Exact-head Tests `35267030859`, SAST `35267030789` and Security `35267030604` are GREEN, while CodeQL PR `35267030868` remains queued. Current-head producer/consumer CodeQL settlement and qualifying independent approval remain promotion blockers.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body JavaScript sanitization and frontend coverage. SAST is GREEN, but Tests/Security/CodeQL acceptance remains incomplete; fresh producer evidence must prove the recorded `js/incomplete-multi-character-sanitization` findings absent on the exact repair head.

### Embedded-image ingestion and commercial DB tooling

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns embedded-image ingestion only. Its product Tests/SAST/Security are GREEN; repository-baseline CodeQL findings remain #974/#983 owner work and must be consumed rather than copied. #911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps pg8000/libpq compatibility source-stable; central Dependency Review availability and baseline CodeQL still block promotion.

### Contextual-orchestrator boundary, local OIDC smoke and auth topology

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores contextual-orchestrator source-of-truth ownership and keeps ADR 0300 Proposed while unmerged. Provider/model discovery, routing, fallback and provider credentials remain contextual-orchestrator concerns.

#1118 exact `04120daa95c709ed0b095e127e2fdbce055edc83` is the local OIDC-smoke child. #1117 exact `fca2641f90ca0f2e331403848c05b2da7f31bb35` is its README-only child. #1118 limits `make smoke` evidence to the synthetic local Keycloak token/JWKS/claim compatibility probe and explicitly does not treat Resource Owner Password Credentials as browser Authorization Code acceptance.

Issue #1119 owns the root grant/test-actor migration. Draft #1120 is now exact `4ae239bdde9a0b956c2639d0fbdb20c702cc83fa`, directly on #1118 with `behind_by=0`; its effective delta is only `tests/test_oidc_security_contract.py`. Initial RED `d147db013...` requires the public `lineageweave-frontend` client to keep standard flow enabled while direct access and service accounts are disabled. Follow-up RED `44ab2f720...` also requires `attributes["pkce.code.challenge.method"] == "S256"` because RFC 9700 §2.1.1 requires PKCE for public Authorization Code clients and Keycloak otherwise leaves the client PKCE requirement optional.

Fresh review found that applying those realm settings before consumer migration would knowingly break repository-owned buyer/test paths. Protected source still issues `grant_type=password` from the smoke script, backend authenticated integration fixture, both k6 buyer paths, and seed/bootstrap script; RFC 9700 §2.4 forbids ROPC use. RED `13c080cff0faf4280eff939cd860baf7580c47fd` therefore adds an executable-actor inventory over `scripts/` and `backend/tests/` and requires those owned callers to stop consuming password grants before the public-client hardening can be considered causal GREEN. The generic form-encoding fixture `tests/test_http_client.py` remains outside this auth-actor scope.

The former temporary self-removing realm writer at predecessor `630fae8d...` was removed at current exact `4ae239bd...` because settings-only mutation would have created a broken intermediate topology. Its predecessor push run `35333568575` is historical after the head move; if admitted later, the workflow's ancestry guard checks out the current branch and fails closed rather than mutating the realm. No cancellation, rerun, wake/no-op commit, runner-label workaround or lifecycle churn is required. The current tree contains no self-modifying repair workflow and the realm fixture remains RED (`directAccessGrantsEnabled=true`, PKCE requirement absent).

The required order is now explicit: migrate browser/machine/bootstrap actors away from ROPC; then disable direct grants and require PKCE S256 on the public client; then prove rendered Authorization Code state/nonce/return-URL/product-session behavior. #1057 separately owns making PostgreSQL + Keycloak + Valkey authenticated FastAPI bearer/JWKS/RBAC/ABAC execution mandatory in hosted CI and must consume #1119's standards-compliant fixture/token path rather than duplicate it. Identity/provider truth remains Keyverse/Keycloak-owned.

### Report/comparison stack

The serialized report stack remains parent-first: #873 → #874 → #875, with #876 → #1033 → #1034 and sibling #877. Persisted σ/share/ζ/ξ evidence remains distinct; moved-head receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession. Exact heads must be refreshed from live PR state before promotion or descendant rewrite.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` owns runtime/package/frontend version identity and #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` owns the Proposed supply-chain caller contract. No current protected head has verified immutable tag/package/release + SBOM/provenance/reproducibility/rollback evidence, so no commercial release is admitted.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 PostgreSQL draft exists; owner/consumer acceptance remains incomplete. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 `cf3bc986...` | Product contract repaired; inherited App selectors isolated; one-shot repair remains pre-runner queued. | Execute/self-remove current writer, verify App-only delta, then fresh frontend/full-suite + Chromium GREEN, security/CodeQL, locale/font-fallback and approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Tests/SAST/Security GREEN; CodeQL remains queued. | Current-head producer/consumer CodeQL proof + qualifying approval, then protected integration. |
| Post-body sanitizer / coverage | #983 `f48afbe...` | Quote-aware repair and coverage tests present; SAST GREEN, other acceptance incomplete. | Fresh full/coverage/rendered/security evidence + producer proof JS findings absent + review resolution. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; CodeQL baseline is owner-external. | Consume verified #974/#983 repairs, then unchanged-head CodeQL and approval. |
| CO ownership / local OIDC smoke / package docs | #899 `a2da5875...` → #1118 `04120daa...`; README sibling #1117 `fca2641f...` | Owner boundary Proposed/Draft. Smoke evidence is correctly bounded but still uses local ROPC. | Promote parent-first only after exact-head repository/security/static-analysis GREEN and qualifying approval; wording repair is not root grant removal. |
| ROPC removal + public-client PKCE + browser Authorization Code acceptance | #1119 → Draft #1120 `4ae239bd...` | RED now covers both the public-client direct-grant/PKCE configuration and the repository executable actors still consuming `grant_type=password`; the premature self-modifying realm writer is removed. | Migrate smoke/backend/k6/seed/bootstrap actors to standards-compliant browser/machine/bootstrap evidence, then disable public direct grants + require S256, prove focused/full exact-head GREEN, add rendered state/nonce/return-URL/product-session evidence, security/static GREEN and approval. |
| Hosted authenticated API topology | #1057 | Existing suite can skip real bearer/JWKS/RBAC/ABAC when PostgreSQL/Keycloak/Valkey are absent. #1119 is token-path prerequisite. | Required bounded hosted service topology, fail-closed readiness/cleanup, real authenticated contracts, then full security/static/review acceptance. |
| Commercial DB tooling | #911 `6030b295...` | Functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement, fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas remain in non-force ancestry; moved-head acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version/source contract exists; immutable release evidence is absent. | Protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback and immutable tag/package/release. |

## Documentation and release boundary

This file is the mutable current overlay. Superseded detail belongs in immutable dated history rather than remaining as stale authority here. Release-ready means one exact protected head has required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery documentation, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.
