# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, open PR/Issue state, ADRs and exact-head receipts are authoritative. The preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md); earlier history through 2026-09-13 remains separately preserved.

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve valid product/test/fixture/contract/evidence deltas, but checks and reviews never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A terminal job with no runner assignment and zero executed steps is control-plane/pre-execution evidence, not executed product/security evidence.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming/status, locale expansion/font fallback and applicable performance evidence. Story/test source is evidence intent; static Storybook build alone is not interaction evidence.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` is `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` is `64aa08d7fa487deacd41c761c36277ca68cab6c9`. No LineageWeave-local CodeQL status shim, runner workaround, provider/model pin, copied queue implementation, synthetic status, no-op wake commit or lifecycle churn is an acceptable substitute for owner evidence.

## Current foundations and buyer-visible gaps

### Customer Master authorization and translations

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. Product Tests/SAST/Security are GREEN on its recorded head, but CodeQL/model-review/control-plane evidence remains non-accepting. #1077 and #1080 retain connection-lease and summary application-service lease/TOCTOU responsibility; #996 owns hierarchy presentation rather than stored hierarchy truth.

#929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative 37-key × 8-locale translation ledger; migration 0248 remains `draft`. Direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` remains Draft. Publication still requires independent language/product review, immutable one-way publication, authenticated API/browser consumption and CJK/text-expansion/font-fallback evidence. #929 Tests `35236145547` remained pre-runner, so no hosted GREEN is claimed.

### Leftover-pair action accessibility

#977 is now Draft at exact `640ee39fef7a49cbe5d86468b203e5232c96724b` on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. The product lane still contains the Label-in-Name/finite-evidence repair, dense/mobile 44px target handling, keyboard/focus and explicit mouse/touch Storybook contracts, plus the Playwright/Chromium rendered-Storybook lane.

Tests `35293139866` finally executed on predecessor product head `d08cb70f498c3afa4e4a1d7b9318a131caa36b1d`. Frontend `105440087005` failed in Vitest before build/Storybook/Chromium execution: dedicated `LeftoverPairList.test.tsx` and `LeftoverPairList.accessibleName.test.tsx` were GREEN, while two inherited `frontend/src/App.test.tsx` cases still queried the historical `Open leftover closest/farthest pair: ...` names instead of the repaired visible-label-prefix contract (`Closest leftover:` / `Farthest leftover:`). Full suite/PostgreSQL `105440086877` reached a hosted runner but was cancelled during the full-suite step and is not GREEN evidence.

A candidate whole-file writer commit `d76f021caafc9d99afb01146810dd31897b6de36` attempted the focused App selector correction but compare exposed unrelated broad App-test churn (+273/-1135), so that delta was rejected. Forward-only restore `640ee39fef7a49cbe5d86468b203e5232c96724b` restores the exact predecessor `App.test.tsx` blob; `d08cb70f...` → `640ee39f...` is tree-identical. The remaining causal repair is deliberately narrow: update only the stale App integration selectors/accessible-name expectation to the visible-label-prefix contract, then obtain fresh frontend/full-suite/Chromium evidence. Exact-head Tests `35313073233` materialized on the restored head but is not acceptance evidence for the known unfixed selector RED.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs; child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` remains ordinarily/non-force converged on that parent. Fresh exact-head Tests `35267030859` are GREEN: Full suite/PostgreSQL `105356637935` and Frontend lint/test/build/Storybook `105356638142` both executed successfully on hosted runners. SAST `35267030789` is GREEN. Security `35267030604` is now also GREEN: exact-head scope detection, Scorecard `105432724807`, and Trivy filesystem `105432724858` executed successfully; inapplicable jobs were scope-skipped rather than substituted. CodeQL `35267030868` remains nonterminal: language detection executed GREEN, while actions/python/javascript-typescript compatibility jobs remain queued pre-runner. The stale TLS-test implementation-shape RED is closed; current-head CodeQL settlement and qualifying approval remain the promotion blockers.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns post-body JavaScript sanitization and frontend coverage. SAST is GREEN, but Tests were cancelled before runner assignment; Security and CodeQL remain non-accepting. Fresh producer evidence proving the four `js/incomplete-multi-character-sanitization` findings absent on this exact repair head is still required.

### Embedded-image ingestion and commercial DB tooling

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns embedded-image ingestion only. Its product Tests/SAST/Security are GREEN on the recorded head; repository-baseline CodeQL findings remain #974/#983 owner work and must be consumed rather than copied.

#911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps pg8000/libpq compatibility source-stable. Tests/PROV-O/Ontology/SAST are GREEN; central Dependency Review availability and baseline CodeQL still block promotion.

### Contextual-orchestrator boundary, OIDC smoke and package README

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores contextual-orchestrator source-of-truth ownership and keeps ADR 0300 `Proposed` while unmerged. Provider/model discovery, routing, fallback and provider credentials remain contextual-orchestrator concerns. Direct descendants #902 `9487e0299a148a10bfcf7b02110508078843d3ef`, #919 `d78390c56c9d9abcf4a97d2ffa5477704dcbb465`, #966 `f93715af6cbab2a39c22d7c170df2dc32bcd7456` and #1118 `6f3b1eded99a0cbf053cef944d2b292b6559c952` remain Draft; #915 remains below #902.

#1118 owns the LineageWeave-local OIDC smoke operator contract. RED `53fe0ac34d8504bd48a0f90f73879135471370db` requires `make smoke` to activate the locked `dev` extra supplying PyJWT; `d6b5f67a642bf4892d92bd908dce35e99aaa4bbe` applies that Makefile repair. Follow-up RED `93b9e2169d393eda83751b7b9f0472ffb5007500` rejects stale direct-`python3` usage guidance. Exact head `6f3b1eded99a0cbf053cef944d2b292b6559c952` names `make smoke` as canonical usage and documents the direct equivalent as `uv run --locked --extra dev ...`, without changing OIDC/JWT runtime semantics. Compare from #899 is `behind_by=0` and changes exactly `Makefile`, `scripts/smoke_test_oidc.py` and `tests/test_makefile_contract.py`. Tests `35304655655` are Draft-policy skipped; no submitted review or inline thread supplies acceptance.

#1117's README explicitly advertises `make smoke`, so leaving it as a sibling of #1118 would permit documentation to integrate before the executable prerequisite it describes. Ordinary two-parent/non-force convergence `6218b2be1a2df88484db02b6a95170765718472b` preserves prior #1117 `7accb384866254e50f65e449d929947dc0b93b6f` as first parent and exact #1118 as second parent, using the #1118 tree plus only the validated README blob. #1117 is retargeted to #1118; compare from #1118 is `behind_by=0` and the effective delta is only `README.md`. Tests `35304930419` are Draft-policy skipped. The prerequisite chain is now #899 → #1118 → #1117.

### Report/comparison stack

The serialized report stack remains parent-first: #873 `262700d3936d7e783817f4c6fd008afe119d0b23` → #874 `3a191487420fd9d06b4fb35fef5d407e078f152a` → #875 `1ac7ddd0637a126c59d0102dcd75a051b059e9f4`, with #876 `4be3c382ce18ce6be272efbcdedfdaa66dc334ff` → #1033 `38967642e1efbd299dfcd68514c289716edfb597` → #1034 `825f47a268c5c31fecaef3537c24b78511823f4d`, plus sibling #877 `edcf5baa051046be448a0b356d01c3543b69408a`. Persisted σ/share/ζ/ξ evidence remains distinct; moved-head receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` owns runtime/package/frontend version identity and #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` owns the Proposed supply-chain caller contract. No current protected head has verified immutable tag/package/release + SBOM/provenance/reproducibility/rollback evidence, so no commercial release is admitted.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 draft ledger exists; owner Tests remain pre-runner. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 `640ee39f...` | Hosted predecessor frontend RED isolates two stale App integration selectors; focused component accessibility suites passed. Rejected broad writer delta was forward-restored, leaving current tree product-equivalent to `d08cb70f...`. | Apply only the stale App selector/name expectation repair, then fresh frontend/full-suite + Chromium browser GREEN, Security/CodeQL settlement, locale/font-fallback evidence, qualifying approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Exact-head repository Tests, SAST, and Security are GREEN; CodeQL compatibility remains queued pre-runner. | Current-head producer/consumer CodeQL proof that Python findings are absent + qualifying approval, then protected integration. |
| Post-body sanitizer / coverage | #983 `f48afbe...` | Quote-aware repair and coverage tests present; SAST GREEN, other acceptance incomplete. | Fresh full/coverage/rendered/security evidence + producer proof four JS findings absent + review resolution. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; CodeQL baseline is owner-external. | Consume verified #974/#983 repairs, then unchanged-head CodeQL and approval. |
| CO ownership / OIDC smoke / package docs | #899 `a2da5875...` → #1118 `6f3b1ede...` → #1117 `6218b2be...` | Owner boundary remains Proposed/Draft; smoke command and usage declare the locked PyJWT environment; README is stacked above that prerequisite and differs only by README. | Promote parent-first, with executed exact-head repository/security/static-analysis GREEN and qualifying approval at each step. |
| Commercial DB tooling | #911 `6030b295...` | Functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement, fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas remain in non-force ancestry; moved-head acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version/source contract exists; immutable release evidence is absent. | Protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback and immutable tag/package/release. |

## Documentation and release boundary

This file is the mutable current overlay. Superseded detail belongs in immutable dated history rather than remaining as stale authority here. Release-ready means one exact protected head has required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery documentation, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.
