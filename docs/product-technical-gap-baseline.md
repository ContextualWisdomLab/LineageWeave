# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, open PR/Issue state, ADRs and exact-head receipts are authoritative. The preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md); earlier history through 2026-09-13 remains separately preserved.

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve valid product, test, fixture, contract and evidence deltas, but checks and reviews never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A job with no runner assignment and zero executed steps is control-plane evidence, not executed product or security evidence.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming/status, locale expansion/font fallback and applicable performance evidence. Story/test source is evidence intent; static Storybook build alone is not interaction evidence.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` is `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` was last revalidated at `64aa08d7fa487deacd41c761c36277ca68cab6c9`; both must be refreshed again immediately before any promotion. No LineageWeave-local CodeQL status shim, runner workaround, provider/model pin, copied queue implementation, synthetic status, no-op wake commit or lifecycle churn substitutes for owner evidence.

## Current foundations and buyer-visible gaps

### Customer Master authorization and translations

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. #929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative versioned UI translation ledger and 37-key × 8-locale Customer Master draft; direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` remains Draft. Publication still requires hosted PostgreSQL/full-suite and security/static GREEN, independent language/product review, immutable one-way publication, authenticated API/browser consumption, and CJK/text-expansion/font-fallback evidence. Ontology/concept labels remain separate canonical truth.

### Leftover-pair action accessibility

#977 remains Draft on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. Its intermediate head `cf3bc986b7838731e3ef056fa5c4cc9bb03597ca` exists only to run the purpose-bounded selector repair for five stale inherited `frontend/src/App.test.tsx` accessible-name expectations; it is not product acceptance. One-shot run `35316632816` remains non-accepting until runner execution. ADR 0049 was aligned on docs commit `91a66bf69e200615f890177b4cfd2a5a6686dd64`; that docs repair does not transfer acceptance to #977.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs; child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` remains ordinarily/non-force converged. Exact-head Tests `35267030859`, SAST `35267030789` and Security `35267030604` are GREEN, while CodeQL PR `35267030868` remains non-accepting. Current-head producer/consumer CodeQL settlement and qualifying independent approval remain promotion blockers.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body JavaScript sanitization and frontend coverage. SAST is GREEN, but Tests/Security/CodeQL acceptance remains incomplete; fresh producer evidence must prove the recorded `js/incomplete-multi-character-sanitization` findings absent on the exact repair head.

### Embedded-image ingestion and commercial DB tooling

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns embedded-image ingestion only. Its product Tests/SAST/Security are GREEN; repository-baseline CodeQL findings remain #974/#983 owner work and must be consumed rather than copied. #911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps pg8000/libpq compatibility source-stable; central Dependency Review availability and baseline CodeQL still block promotion.

### Contextual-orchestrator boundary, local OIDC smoke and auth topology

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores contextual-orchestrator source-of-truth ownership and keeps ADR 0300 Proposed while unmerged. Provider/model discovery, routing, fallback and provider credentials remain contextual-orchestrator concerns.

#1118 exact `04120daa95c709ed0b095e127e2fdbce055edc83` is the local OIDC-smoke dependency/evidence-semantics child. Causal grant migration is issue #1119 / Draft #1120 exact `de4fc1d0e604fb03c336b0d9d1d0ac57c74c467f`; identity/provider truth stays Keyverse/Keycloak-owned and #1057 separately owns hosted PostgreSQL + Keycloak + Valkey acceptance.

#1120's RED lineage still requires the public `lineageweave-frontend` client to keep standard flow while direct access/service accounts are disabled, mandatory PKCE S256, and repository-owned executable auth actors to stop consuming `grant_type=password` before hardening can be called causal GREEN.

A material subset is now repaired rather than merely specified. `scripts/smoke_test_oidc.py`, `scripts/k6_http_e2e.js` and `scripts/k6_mcp_e2e.js` use a separate confidential `lineageweave-test-automation` service-account client with `client_credentials`; Makefile and static contracts require an explicit `KEYCLOAK_CLIENT_SECRET` and keep machine evidence distinct from rendered browser login. The realm fixture contains that confidential client with exact API and MCP audience mappers, uses env-placeholder local fixture credentials, and requires S256 on the public frontend client. Compose and `.env.example` supply explicit synthetic local defaults for realm import. The public client intentionally still has direct grants enabled while the final repository consumers move.

The remaining RED is narrower and concrete: `backend/tests/test_api.py` still obtains its authenticated integration token through the public client's password grant, while `scripts/seed_demo_data.py` still uses password grants for Keycloak-admin bootstrap and for post-content warm-up. The machine service-account subject also still needs least-privilege representation in the seeded local authorization tables before k6 can exercise RBAC/ABAC rather than merely mint a valid machine token. Turning public direct grants off before these repairs would recreate the broken intermediate topology already rejected in review.

README #1117 is no longer a sibling of this security migration because #1120 changes the exact `make smoke` semantics that README exposes. Ordinary two-parent/non-force convergence `fdbb8b85eddc7bc59b0487a06719acf2e81635ed` preserved prior README history while adopting exact #1120; current README-only head is `e0a3018a25d7d134ab8d9150e7b33d5dbe67b530`. It now documents the machine client/explicit secret boundary, the still-open ROPC callers, realm-import placeholders, and Keycloak startup-import recovery caveat without implementing runtime behavior.

The former temporary self-removing realm writer is absent from the current tree; its predecessor run `35333568575` is historical. #1120 exact-head Tests `35341877001` are Draft-admission `skipped`, so none of the current source movement is hosted GREEN. Required order is: migrate backend/seed/bootstrap actors and seed the machine subject; disable public direct grants with S256 already present; prove focused/full exact-head GREEN; then prove rendered Authorization Code state/nonce/return-URL/product-session behavior. #1057 must consume that same fixture/token path in hosted CI rather than duplicate it.

### Report/comparison stack

The serialized report stack remains parent-first: #873 → #874 → #875, with #876 → #1033 → #1034 and sibling #877. Persisted σ/share/ζ/ξ evidence remains distinct; moved-head receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession. Exact heads must be refreshed from live PR state before promotion or descendant rewrite.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` owns runtime/package/frontend version identity and #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` owns the Proposed supply-chain caller contract. No current protected head has verified immutable tag/package/release + SBOM/provenance/reproducibility/rollback evidence, so no commercial release is admitted.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 PostgreSQL draft exists; owner/consumer acceptance remains incomplete. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 `cf3bc986...` | Product contract repaired; inherited App selectors isolated; one-shot repair remains non-accepting. | Execute/self-remove current writer, verify App-only delta, then fresh frontend/full-suite + Chromium GREEN, security/CodeQL, locale/font-fallback and approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Tests/SAST/Security GREEN; CodeQL remains non-accepting. | Current-head producer/consumer CodeQL proof + qualifying approval, then protected integration. |
| Post-body sanitizer / coverage | #983 `f48afbe...` | Quote-aware repair and coverage tests present; SAST GREEN, other acceptance incomplete. | Fresh full/coverage/rendered/security evidence + producer proof JS findings absent + review resolution. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; CodeQL baseline is owner-external. | Consume verified #974/#983 repairs, then unchanged-head CodeQL and approval. |
| CO ownership / local OIDC dependency semantics | #899 `a2da5875...` → #1118 `04120daa...` | Owner boundary Proposed/Draft; dependency/evidence semantics are separated from causal grant migration. | Promote parent-first only after exact-head repository/security/static-analysis GREEN and qualifying approval. |
| ROPC removal + public-client PKCE + browser Authorization Code acceptance | #1119 → #1120 `de4fc1d...` → README #1117 `e0a3018a...` | Smoke + HTTP/MCP k6 machine actors use a separate confidential client and client credentials; PKCE S256 and credential placeholders are in the realm; README follows this exact stack. Public direct grants remain on because backend integration + seed/bootstrap still use password grants; exact-head Tests are skipped. | Migrate backend/seed/bootstrap, seed least-privilege machine subject, switch public direct grants off, prove focused/full GREEN, then rendered state/nonce/return-URL/product-session evidence, security/static GREEN and approval. |
| Hosted authenticated API topology | #1057 | Existing suite can skip real bearer/JWKS/RBAC/ABAC when PostgreSQL/Keycloak/Valkey are absent. #1119 remains the token-path prerequisite. | Required bounded hosted service topology, fail-closed readiness/cleanup, real authenticated contracts, then full security/static/review acceptance. |
| Commercial DB tooling | #911 `6030b295...` | Functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement, fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas remain in non-force ancestry; moved-head acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version/source contract exists; immutable release evidence is absent. | Protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback and immutable tag/package/release. |

## Documentation and release boundary

This file is the mutable current overlay. Superseded detail belongs in immutable dated history rather than remaining as stale authority here. Release-ready means one exact protected head has required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery documentation, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.