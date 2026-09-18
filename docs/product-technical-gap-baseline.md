# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, open PR/Issue state, ADRs and exact-head receipts are authoritative. The preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md); earlier history through 2026-09-13 remains separately preserved.

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve valid product, test, fixture, contract and evidence deltas, but checks and reviews never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A job with no runner assignment and zero executed steps is control-plane evidence, not executed product or security evidence.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming/status, locale expansion/font fallback and applicable performance evidence. Story/test source is evidence intent; static Storybook build alone is not interaction evidence.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` is `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` was last revalidated at `64aa08d7fa487deacd41c761c36277ca68cab6c9`; both must be refreshed immediately before promotion. No LineageWeave-local CodeQL status shim, runner workaround, provider/model pin, copied queue implementation, synthetic status, no-op wake commit or lifecycle churn substitutes for owner evidence.

## Current foundations and buyer-visible gaps

### Customer Master authorization and translations

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. #929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative versioned UI translation ledger and 37-key × 8-locale Customer Master draft; direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` remains Draft. Publication still requires hosted PostgreSQL/full-suite and security/static GREEN, independent language/product review, immutable one-way publication, authenticated API/browser consumption, and CJK/text-expansion/font-fallback evidence. Ontology/concept labels remain separate canonical truth.

### Leftover-pair action accessibility

#977 remains Draft on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. Intermediate head `cf3bc986b7838731e3ef056fa5c4cc9bb03597ca` exists only to execute the bounded selector repair for stale inherited App accessible-name expectations; one-shot run `35316632816` remains non-accepting until actual runner execution. ADR 0049 was aligned separately; documentation does not transfer product acceptance.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs; child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` remains ordinary/non-force converged. Tests/SAST/Security are GREEN, while CodeQL PR `35267030868` is still queued/non-accepting. Current-head producer/consumer CodeQL settlement and qualifying independent approval remain blockers.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body JavaScript sanitization and frontend coverage. SAST is GREEN, but Tests/Security/CodeQL acceptance remains incomplete; fresh producer evidence must prove the recorded JavaScript findings absent on the exact repair head.

### Embedded-image ingestion and commercial DB tooling

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns embedded-image ingestion only. Product Tests/SAST/Security are GREEN; repository-baseline CodeQL findings remain #974/#983 owner work and must be consumed rather than copied. #911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps pg8000/libpq compatibility source-stable; central Dependency Review availability and baseline CodeQL still block promotion.

### Contextual-orchestrator boundary, local OIDC and auth topology

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores contextual-orchestrator source-of-truth ownership and keeps ADR 0300 Proposed while unmerged. Provider/model discovery, routing, fallback and provider credentials remain contextual-orchestrator concerns.

#1118 exact `04120daa95c709ed0b095e127e2fdbce055edc83` owns only the local smoke dependency/evidence-semantics repair. Causal grant migration is issue #1119 / Draft #1120 exact `03b0d5d828c7b0d7ade046ff2c9b436f16656428`; identity/provider truth stays Keyverse/Keycloak-owned and #1057 separately owns hosted PostgreSQL + Keycloak + Valkey execution.

#1120's executable RED still requires the public `lineageweave-frontend` client to use standard flow with direct access/service accounts disabled, mandatory S256 PKCE, and repository-owned executable auth actors to stop consuming `grant_type=password`. A material subset is repaired: smoke plus HTTP/MCP k6 use a separate confidential `lineageweave-test-automation` service-account client with `client_credentials`; operator contracts require an explicit `KEYCLOAK_CLIENT_SECRET`; the realm fixture contains API/MCP audience mappers, S256, deterministic synthetic human subject IDs and environment placeholders. Keycloak startup import now installs the existing realm source as `/opt/keycloak/data/import/lineageweave-demo-realm.json` while `docker/keycloak/realm-export.json` remains the source of truth.

Fresh ADR-first review found normative drift: runtime/test auth topology had advanced beyond ADR 0028. Exact #1120 `03b0d5d...` changes only that ADR and keeps the production Keyverse decision Accepted while marking the local #1120 hardening amendment Proposed. The amendment now makes the actor boundary explicit: rendered browser Authorization Code + PKCE, machine `client_credentials`, distinct product-test subjects, normalized local authorization, and purpose-bound bootstrap. It also records a narrower causal seed repair exposed by current source: the two synthetic human `sub` values are deterministic in the repository-owned realm fixture, so `scripts/seed_demo_data.py` should consume that fixture truth rather than authenticate to Keycloak Admin REST solely to rediscover those same IDs. A privileged bootstrap client is required only if an actual Admin REST operation remains after that simplification.

The remaining RED is concrete. `backend/tests/test_api.py` still uses two distinct public-client password-grant principals; collapsing those subjects would invalidate its cross-account authorization proof. `scripts/seed_demo_data.py` still has a password-grant `admin-cli` lookup and a separate password-grant post-content warm-up. The latter must migrate to a standards-compliant product actor without inheriting bootstrap privilege. The existing machine service-account `sub` also is not yet represented in seeded normalized authorization tables, so current k6 can prove token acquisition but not end-to-end RBAC/ABAC authorization. Public direct grants therefore remain enabled until these consumers move.

README #1117 follows the security migration. When #1120 moved to `03b0d5d...`, #1117 was immediately ordinary/non-force reconverged to exact `1260cd53579b406d7fb9386e9c8f95730bc164ca`, with prior #1117 `4f82a984...` first parent and exact #1120 second parent. Fresh compare from #1120 has merge-base exactly `03b0d5d...`, `behind_by=0`, and `README.md` as the only effective child delta. No predecessor validation receipt transfers to either moved head.

Required order remains: remove/replace backend and seed password-grant consumers while preserving distinct authorization subjects; provision machine/product actors with least privilege; disable public direct grants with S256 already present; prove focused/full exact-head GREEN; then prove rendered Authorization Code state/nonce/return-URL/product-session behavior. #1057 must consume the same standards-compliant fixture in hosted CI rather than duplicate it.

### Report/comparison stack

The serialized report stack remains parent-first: #873 → #874 → #875, with #876 → #1033 → #1034 and sibling #877. Persisted σ/share/ζ/ξ evidence remains distinct; moved-head receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession. Exact heads must be refreshed from live PR state before promotion or descendant rewrite.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` owns runtime/package/frontend version identity and #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` owns the Proposed supply-chain caller contract. No current protected head has verified immutable tag/package/release + SBOM/provenance/reproducibility/rollback evidence, so no commercial release is admitted.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 PostgreSQL draft exists; owner/consumer acceptance remains incomplete. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 `cf3bc986...` | Product contract repaired; inherited App selectors isolated; one-shot repair remains non-accepting. | Execute/self-remove current writer, verify narrow delta, then fresh frontend/full-suite + Chromium GREEN, security/CodeQL, locale/font-fallback and approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Tests/SAST/Security GREEN; CodeQL remains queued/non-accepting. | Current-head producer/consumer CodeQL proof + qualifying approval, then protected integration. |
| Post-body sanitizer / coverage | #983 `f48afbe...` | Quote-aware repair and coverage tests present; SAST GREEN, other acceptance incomplete. | Fresh full/coverage/rendered/security evidence + producer proof JS findings absent + review resolution. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; CodeQL baseline is owner-external. | Consume verified #974/#983 repairs, then unchanged-head CodeQL and approval. |
| CO ownership / local OIDC dependency semantics | #899 `a2da5875...` → #1118 `04120daa...` | Owner boundary Proposed/Draft; dependency/evidence semantics are separated from causal grant migration. | Promote parent-first only after exact-head repository/security/static-analysis GREEN and qualifying approval. |
| ROPC removal + public-client PKCE + browser Authorization Code acceptance | #1119 → #1120 `03b0d5d...` → README #1117 `1260cd53...` | Machine actors use a confidential client; PKCE S256, deterministic local human IDs and startup-import repair exist; ADR 0028 is code-current but the local amendment remains Proposed. Backend integration and seed/warm-up still use password grants and moved-head validation is absent. | Remove unnecessary admin subject rediscovery, migrate remaining backend/warm-up actors with distinct least-privilege subjects, seed local authorization, disable public direct grants, prove focused/full GREEN, then rendered state/nonce/return-URL/product-session evidence, security/static GREEN and approval. |
| Hosted authenticated API topology | #1057 | Existing suite can skip real bearer/JWKS/RBAC/ABAC when PostgreSQL/Keycloak/Valkey are absent. #1119 remains the token-path prerequisite. | Required bounded hosted service topology, fail-closed readiness/cleanup, real authenticated contracts, then full security/static/review acceptance. |
| Commercial DB tooling | #911 `6030b295...` | Functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement, fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas remain in non-force ancestry; moved-head acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version/source contract exists; immutable release evidence is absent. | Protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback and immutable tag/package/release. |

## Documentation and release boundary

This file is the mutable current overlay. Superseded detail belongs in immutable dated history rather than remaining as stale authority here. Release-ready means one exact protected head has required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery documentation, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.
