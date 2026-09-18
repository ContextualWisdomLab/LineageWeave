# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, open PR/Issue state, ADRs and exact-head receipts are authoritative. The preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md); earlier history through 2026-09-13 remains separately preserved.

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve valid product/test/fixture/contract/evidence deltas, but checks and reviews never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A job with no runner assignment and zero executed steps is control-plane/pre-execution evidence, not executed product/security evidence.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming/status, locale expansion/font fallback and applicable performance evidence. Story/test source is evidence intent; static Storybook build alone is not interaction evidence.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` is `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` is `64aa08d7fa487deacd41c761c36277ca68cab6c9`. No LineageWeave-local CodeQL status shim, runner workaround, provider/model pin, copied queue implementation, synthetic status, no-op wake commit or lifecycle churn is an acceptable substitute for owner evidence.

## Current foundations and buyer-visible gaps

### Customer Master authorization and translations

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. Product Tests/SAST/Security are GREEN on its recorded head, but CodeQL/model-review/control-plane evidence remains non-accepting. #1077 and #1080 retain connection-lease and summary application-service lease/TOCTOU responsibility; #996 owns hierarchy presentation rather than stored hierarchy truth.

#929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative versioned UI translation ledger and the 37-key × 8-locale Customer Master draft. Direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` is ordinarily/non-force stacked on that exact parent and remains Draft. #929 Tests `35236145547` are still pre-runner and #932 Tests `35236229290` are Draft-skipped, so neither has hosted exact-head acceptance. Publication requires PostgreSQL/full-suite and required security/static GREEN, independent language/product review, immutable one-way publication, authenticated API/browser consumption, and CJK/text-expansion/font-fallback evidence. Ontology/concept labels remain separate canonical truth.

### Leftover-pair action accessibility

#977 is Draft and mechanically mergeable on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. The last product/test tree before the current repair helper is `640ee39fef7a49cbe5d86468b203e5232c96724b`. The branch has advanced to intermediate exact head `cf3bc986b7838731e3ef056fa5c4cc9bb03597ca` only to run a purpose-bounded selector repair; that intermediate head is not product acceptance.

The product lane retains the WCAG 2.2 SC 2.5.3 visible-label-prefix repair, finite-evidence fail-closed naming, dense/mobile 44px target handling, keyboard/focus and explicit mouse/touch Storybook contracts, and the Playwright/Chromium rendered-Storybook lane. Production `LeftoverPairList` builds the accessible name from the exact localized visible label followed by localized action text and formatter-admitted finite persisted evidence; it does not synthesize psychometric values.

Hosted Tests `35293139866` on predecessor `d08cb70f498c3afa4e4a1d7b9318a131caa36b1d` isolated the remaining repository RED. `LeftoverPairList.test.tsx` and `LeftoverPairList.accessibleName.test.tsx` passed, while inherited `frontend/src/App.test.tsx` still queried historical `Open leftover closest/farthest pair: ...` names. Fresh source inspection narrows the causal edit to five expectations in two App integration cases: two closest selectors, two farthest selectors and one exact old closest accessible-name assertion. A prior whole-file candidate `d76f021caafc9d99afb01146810dd31897b6de36` was rejected because it mixed broad unrelated App-test churn; forward restore `640ee39f...` returned the product tree to the predecessor state.

Intermediate commit `cf3bc986...` adds a self-removing one-shot workflow which asserts those exact stale occurrence counts, edits only `frontend/src/App.test.tsx`, runs the App plus focused LeftoverPairList regressions and lint, verifies the staged file set, removes itself and then creates an ordinary forward commit. Run `35316632816`, job `105509597284`, is currently queued before runner assignment with `runner_id=0` and `steps=[]`; ordinary PR Tests `35316636604` are Draft-policy skipped. The sole executable repair path has been handed to canonical queue owner `ContextualWisdomLab/.github#712` in comment `5726354801`. No rerun, no-op wake commit, `runs-on` change, synthetic status or Draft/Ready churn is authorized.

ADR 0049's historical `Open leftover closest/farthest pair: {title}` screen-reader contract has been repaired on the docs owner branch in commit `91a66bf69e200615f890177b4cfd2a5a6686dd64`. The ADR now states that the exact localized rendered pair label is the accessible-name prefix, localized action/evidence context follows it, and missing or non-finite evidence is omitted rather than announced as a placeholder. This is a documentation-currentness repair only: #977's product head and queued selector writer were not touched, and the docs commit is not product acceptance.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs; child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` remains ordinarily/non-force converged on that parent. Exact-head Tests `35267030859`, SAST `35267030789` and Security `35267030604` are GREEN. CodeQL PR `35267030868` remains nonterminal: language detection executed GREEN while actions/python/javascript-typescript compatibility jobs remain queued pre-runner. Current-head CodeQL settlement and qualifying independent approval remain promotion blockers.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body JavaScript sanitization and frontend coverage. SAST is GREEN, but Tests/Security/CodeQL acceptance remains incomplete. Fresh producer evidence proving the recorded `js/incomplete-multi-character-sanitization` findings absent on its exact repair head is still required.

### Embedded-image ingestion and commercial DB tooling

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns embedded-image ingestion only. Its product Tests/SAST/Security are GREEN on the recorded head; repository-baseline CodeQL findings remain #974/#983 owner work and must be consumed rather than copied.

#911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps pg8000/libpq compatibility source-stable. Tests/PROV-O/Ontology/SAST are GREEN; central Dependency Review availability and baseline CodeQL still block promotion.

### Contextual-orchestrator boundary, local OIDC smoke and auth topology

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores contextual-orchestrator source-of-truth ownership and keeps ADR 0300 Proposed while unmerged. Provider/model discovery, routing, fallback and provider credentials remain contextual-orchestrator concerns. #1118 exact `04120daa95c709ed0b095e127e2fdbce055edc83` is the direct local OIDC-smoke child; #1117 exact `fca2641f90ca0f2e331403848c05b2da7f31bb35` is its README-only descendant.

#1118 now describes `make smoke` narrowly as a synthetic local Keycloak token/JWKS/claim compatibility probe and does not call the Resource Owner Password Credentials/direct-access path browser OIDC acceptance. The broader topology remains non-compliant: the public `lineageweave-frontend` client still enables direct access and smoke/backend/k6/seed paths still contain password-grant acquisition. Issue #1119 owns that grant/test-actor migration and rendered Authorization Code acceptance. #1057 separately owns making PostgreSQL + Keycloak + Valkey authenticated FastAPI bearer/JWKS/RBAC/ABAC topology required in hosted CI; it must consume #1119's standards-compliant fixture/token path rather than duplicate its grant migration. Identity/provider truth remains with Keyverse/Keycloak.

### Report/comparison stack

The serialized report stack remains parent-first: #873 → #874 → #875, with #876 → #1033 → #1034 and sibling #877. Persisted σ/share/ζ/ξ evidence remains distinct; moved-head receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession. Exact heads must be refreshed from live PR state before any promotion or descendant rewrite.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` owns runtime/package/frontend version identity and #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` owns the Proposed supply-chain caller contract. No current protected head has verified immutable tag/package/release + SBOM/provenance/reproducibility/rollback evidence, so no commercial release is admitted.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 PostgreSQL draft exists; owner Tests are pre-runner and consumer Tests Draft-skipped. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 intermediate `cf3bc986...` | Product contract is repaired; inherited App integration selectors remain the isolated hosted RED. One-shot causal repair is queued pre-runner. ADR 0049 is aligned on docs commit `91a66bf...`. | Let the sole current-head writer execute/self-remove; verify exact App-only selector delta; then fresh frontend/full-suite + Chromium GREEN, Security/CodeQL settlement, locale/font-fallback evidence and qualifying approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Exact-head repository Tests/SAST/Security GREEN; CodeQL compatibility queued pre-runner. | Current-head producer/consumer CodeQL proof that Python findings are absent + qualifying approval, then protected integration. |
| Post-body sanitizer / coverage | #983 `f48afbe...` | Quote-aware repair and coverage tests present; SAST GREEN, other acceptance incomplete. | Fresh full/coverage/rendered/security evidence + producer proof JS findings absent + review resolution. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; CodeQL baseline is owner-external. | Consume verified #974/#983 repairs, then unchanged-head CodeQL and approval. |
| CO ownership / local OIDC smoke / package docs | #899 `a2da5875...` → #1118 `04120daa...` → #1117 `fca2641f...` | Owner boundary remains Proposed/Draft. Local smoke evidence is explicitly limited to synthetic ROPC token/JWKS/claim compatibility. | Promote parent-first with exact-head repository/security/static-analysis GREEN and qualifying approval; evidence wording is not root ROPC removal. |
| ROPC removal + browser Authorization Code acceptance | #1119 | Public frontend client still enables direct access; smoke/backend/k6/seed paths use password grants. | RED for direct-access disablement; standards-compliant browser/machine/bootstrap fixture separation; rendered Authorization Code session/return-URL/protected-API evidence; repository/security GREEN and qualifying approval. |
| Hosted authenticated API topology | #1057 | Existing ordinary suite can skip real bearer/JWKS/RBAC/ABAC module when PostgreSQL/Keycloak/Valkey are absent. #1119 is prerequisite for token-path migration. | Required bounded hosted service topology, fail-closed readiness/cleanup, real authenticated contracts, then full security/static/review acceptance. |
| Commercial DB tooling | #911 `6030b295...` | Functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement, fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas remain in non-force ancestry; moved-head acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version/source contract exists; immutable release evidence is absent. | Protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback and immutable tag/package/release. |

## Documentation and release boundary

This file is the mutable current overlay. Superseded detail belongs in immutable dated history rather than remaining as stale authority here. Release-ready means one exact protected head has required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery documentation, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.
