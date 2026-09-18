# Product & Technical Gap Baseline

> Current authority snapshot: 2026-09-18.
>
> Live protected refs, PRs/Issues, ADRs, exact heads and exact-head receipts remain authoritative. The immediately preceding full snapshot is preserved byte-for-byte in [`docs/evidence/product-technical-gap-baseline-history-through-20260918.md`](evidence/product-technical-gap-baseline-history-through-20260918.md). Earlier overlays through 2026-09-13 remain in [`docs/evidence/product-technical-gap-baseline-history-through-20260913.md`](evidence/product-technical-gap-baseline-history-through-20260913.md).

## Delivery rules

No release is admitted from the current protected head. Parent/head/base movement invalidates descendant acceptance evidence. Ordinary/non-force convergence must preserve every valid product/test/fixture/contract/evidence delta, but validation receipts never transfer across moved heads. Queued, skipped, cancelled, `action_required`, COMMENTED, predecessor-head, dispatcher-only, rate-limited or source-neutral results are not GREEN. A terminal workflow/job failure with no runner assignment and zero executed steps is control-plane/pre-execution evidence, not executed product/security evidence; it remains fail-closed.

LineageWeave owns lineage/evidence/customer-master/composition/read-model behavior. It consumes released canonical-owner contracts and ACLs rather than copying contextual-orchestrator routing/admission, `.github` queue/review policy, fast-mlsirm/TEPP psychometrics, RankWeave ranking, CalendarWeave/Naruon scheduling or other owner implementations. External/model work stays outside long-lived DB transactions and explicit application locks; persistence reacquires the shortest necessary lease, revalidates state and uses idempotent/UPSERT semantics where required.

Material UI acceptance requires current-head rendered buyer evidence in addition to repository checks: normal/loading/empty/error/permission/responsive states, pointer/touch/keyboard/focus, accessible naming and status, locale expansion/font fallback, and applicable performance evidence. Story/test source is evidence intent, not hosted execution evidence. A static Storybook build likewise proves bundling only; interaction claims require an executing browser lane.

## Canonical owner state

Protected `ContextualWisdomLab/LineageWeave/main` remains `83eba56149eb802cd63642c507c324c9976ec78e`. Protected `ContextualWisdomLab/.github/main` is `64aa08d7fa487deacd41c761c36277ca68cab6c9`; its terminal-preexecution/queued-job diagnostics do not retroactively turn LineageWeave receipts GREEN.

The central owner boundary remains fail closed: no LineageWeave-local CodeQL status shim, runner selector workaround, provider/model pin, queue implementation copy, synthetic status, no-op wake commit or repeated Draft/Ready lifecycle churn is acceptable.

## Current foundations and buyer-visible gaps

### Customer Master authorization and composition

#1079 exact `c2923950e73c88a9f9fd932332ddd47682da124b` remains the shared-catalog authorization candidate. Product Tests/SAST/Security are GREEN on its current recorded head, but required CodeQL/model-review/control-plane evidence remains non-accepting. #1077 and #1080 retain separate connection-lease and summary application-service lease/TOCTOU responsibility. Customer Master hierarchy presentation stays in #996; it must not rewrite stored hierarchy truth or duplicate authorization/translation ownership.

### Governed translation delivery

#929 exact `d4f42f579663e88a0c9af0cc492aa6ff7cae96ee` owns the PostgreSQL-authoritative Customer Master translation ledger and 37-key × 8-locale review candidate. Migration 0248 deliberately remains `draft`. The owner lane includes seed-ownership, TEMP-shadowing, replay-concurrency, reviewed-copy preservation, retirement, non-destructive upgrade and catalog-comment constraint-version repairs. Fresh Tests `35236145547` still has Full suite/PostgreSQL `105252445377` and Frontend `105252445197` pre-runner with no executed steps; no hosted GREEN or qualifying current-head approval exists.

Direct consumer #932 exact `fb2422537216a19280860f710b55f4df963902db` remains Draft on that exact parent and inherits ledger semantics only through ancestry. Publication still requires independent language/product review, one-way immutable publication, authenticated API/browser consumption, CJK/text-expansion/font-fallback and material UI acceptance. #996 consumes that owner path rather than introducing static translation authority.

### Leftover-pair action accessibility

#977 exact `d08cb70f498c3afa4e4a1d7b9318a131caa36b1d` is based on serialized parent #830 exact `bebd77c03e5beae469f42361c20bccc80787ebb5`. Product repair `8d78f22567c200e926e811a3a419a6dab60905e2` makes the accessible name begin with the exact rendered localized label, mirrors only formatter-admitted finite persisted evidence (`R`, `Y/E`, rank, `U`, shares, `R̂`, `ξ/ζ`, `d`), and omits non-finite residual/distance rather than exposing `R —` or `d NaN`.

`ae071b203a73b89a211fa2bbf8a89d1d457fe624` adds Storybook visible-label/name parity plus Tab/Enter focus/selection. Dense/mobile RED `a73b7e8abeb4f5d55a8ce853ebd108e7eef53584` and scoped layout repair `b586ea945809bb60b68e32e17701684f29e9346c` + `b041ab7dfe5cea09071cdf5d36de2acafb7ae27b` require bounded wrapping and the existing 44px touch-target token without changing the shared post-list contract. Inherited test selectors were aligned at `55d69ebbf2c8b31a9544fef470cff099ecb83578`; `5a8deac88b4b8f8a25466b57b234f9e63b4d39c9` adds explicit `[MouseLeft]` and `[TouchA]` Storybook source assertions.

Fresh review then found the hosted frontend workflow only built Storybook; it never executed the interaction source. RED `1463c94ea2de51d12ec88a66be38242fbc4eb63f` requires the frontend lane to execute a Storybook browser test after the static build. The current repair reuses the existing pinned Playwright stack: `playwright.storybook.config.ts` serves `storybook-static`, Chromium executes computed accessible-name/focus/mobile/mouse/touch assertions in `storybook-e2e/leftover-pair-list.pw.ts`, `frontend/package.json` exposes `test:storybook:browser`, and `.github/workflows/tests.yml` runs it after `build-storybook`. The browser-only suffix and Playwright `testMatch` intentionally keep the spec out of the existing Vitest discovery path.

Fresh Tests `35293139866` for `d08cb70f...` has Full suite `105440086877` and Frontend `105440087005` queued pre-runner with no steps. The new browser lane therefore exists as an executable contract but is not hosted GREEN. No open PR targets #977, so this head movement creates no descendant-restack obligation.

### Python / JavaScript CodeQL owner lanes

#974 exact `4341080f6027d869acb08896e41d761c3f3b8e77` owns the repository-baseline Python TLS/ReDoS repairs. The TLS boundary constructs and configures the certifi-backed context before escape with an explicit TLS 1.2 minimum. Hosted predecessor Tests proved the production repair while exposing one stale implementation-shape regression assertion; the current head replaces that assertion with behavioral builder-floor evidence. Fresh Tests/SAST/Security/CodeQL remain nonterminal/non-accepting, so no merge or GREEN transfer is claimed. Direct child #979 exact `2dfd21110813f474d3068796d0733d96f28d6061` is ordinarily/non-force converged on this parent.

#983 exact `f48afbe373cdb6aa64abf0f7c4e69e897f820cd8` owns the post-body JavaScript sanitization path and frontend coverage closure. Its quote-aware linear scanner replaces the flagged multi-character deletion shape while preserving quoted attributes and `<br>` semantics. Current SAST is GREEN, but Tests were cancelled before runner assignment; Security is fail-closed at Dependency Review support and CodeQL compatibility/verdict settlement is non-accepting. Fresh producer evidence proving the four `js/incomplete-multi-character-sanitization` findings absent on this repaired exact head is still required. #984/#985/#992 inherit no acceptance receipt.

### Embedded-image ingestion

#1115 exact `6545b5ff7ed88d98daad74ca3ba8f8606dad3fc4` owns backend embedded-image ingestion only. Repository Tests/SAST/Security are GREEN on its recorded head. Canonical producer evidence is terminal RED only on #974/#983-owned repository-baseline Python/JavaScript findings outside the image parser delta. #1115 must consume verified owner integration and then revalidate; it must not copy those repairs.

### Commercial PostgreSQL tooling

#911 exact `6030b295aadc3ee76dc4d27f5713273f35888325` keeps the pg8000/libpq compatibility boundary source-stable. Tests/PROV-O/Ontology/SAST are GREEN; Security remains fail-closed at canonical Dependency Review availability and CodeQL baseline findings are owned by #974/#983. Promotion requires owner integration followed by fresh exact-head validation rather than duplicated HTTP/chat/frontend repairs.

### Contextual-orchestrator ownership boundary and public package README

#899 exact `a2da5875525cd0950999487ff8fe7d439284dbd2` restores the contextual-orchestrator source-of-truth boundary and correctly leaves ADR 0300 `Proposed` while unmerged. Current descendants #902 `9487e0299a148a10bfcf7b02110508078843d3ef`, #915 `e2a0038382c7fb4f75f66cad473afef4b9a8353a`, #919 `d78390c56c9d9abcf4a97d2ffa5477704dcbb465`, and #966 `f93715af6cbab2a39c22d7c170df2dc32bcd7456` remain Draft and preserve the parent lifecycle repair through ordinary/non-force ancestry. Provider/model discovery, routing and fallback remain contextual-orchestrator concerns.

New public/package README child #1117 was originally based directly on protected `main`, so its registry-facing absolute-link change also carried the stale pre-#899 README text that still described LineageWeave-local provider/gateway configuration. That is a wrong-owner/base composition problem, not a reason to copy #899's repair into another source lane. #1117 is now Draft and retargeted to exact #899. Ordinary two-parent/non-force convergence anchor `c69575c320b1749fc553089513c4ebdd8a392aea` preserved prior #1117 history while adopting exact #899; exact child `7accb384866254e50f65e449d929947dc0b93b6f` reapplies only the registry-safe README link/OIDC-smoke delta. Compare from #899 is behind 0 with only `README.md` modified. Predecessor #1117 checks/reviews do not transfer after both base and head movement. Exact-child Tests `35296950964` is Draft-policy skipped; an overlapping predecessor Tests run `35296938692` was cancelled on lifecycle change, while Security `35296938670`, SAST `35296938690`, and CodeQL `35296938707` remain non-accepting. Keep #1117 behind #899 rather than republishing stale owner-boundary prose from `main`.

### Report/comparison stack

The serialized report stack remains parent-first. #873 `262700d3936d7e783817f4c6fd008afe119d0b23` → #874 `3a191487420fd9d06b4fb35fef5d407e078f152a` → #875 `1ac7ddd0637a126c59d0102dcd75a051b059e9f4`, with #876 `4be3c382ce18ce6be272efbcdedfdaa66dc334ff` → #1033 `38967642e1efbd299dfcd68514c289716edfb597` → #1034 `825f47a268c5c31fecaef3537c24b78511823f4d`, plus sibling #877 `edcf5baa051046be448a0b356d01c3543b69408a`, preserve persisted σ/share/ζ/ξ evidence without deriving one quantity from another. Moved-head queued/skipped receipts are not GREEN. Historical #878/#879 remain delta carriers until verified successors prove complete succession.

### Immutable release path

#961 exact `3bdec0504a65e63f44bd49ba15de37182a1672cc` remains the single LineageWeave source lane for runtime/package/frontend version identity; #925 exact `8cbaad528c9aaa8d4e356db1577b932fa85ac686` remains the Proposed supply-chain caller-contract lane. The repository currently exposes neither a GitHub Release nor a Git tag, so no protected head can be treated as an immutable public release from repository evidence alone. This does not prove that no artifact was ever published elsewhere.

Release acceptance still requires a built/installed package identity, one exact protected SHA shared by version/CHANGELOG/package filenames/tag/release/SBOM/provenance predicates, reproducibility evidence, rollback evidence, and the thinnest exact-SHA consumer of the released canonical `.github` SBOM/attestation workflow. Do not create a competing release writer or retag/mutate an already-published version if external publication history later proves one exists.

## Buyer-gap register

| Gap | Current owner / exact head | Current evidence | Required next acceptance |
| --- | --- | --- | --- |
| Customer Master governed translations | #929 `d4f42f57...` → #932 `fb242253...` | 37×8 draft and migration lifecycle repairs exist; owner Tests remain pre-runner. | Hosted PostgreSQL/full-suite + security/static GREEN, independent language/product review, immutable publication, authenticated eight-locale browser acceptance. |
| Leftover-pair accessible action | #830 `bebd77c...` → #977 `d08cb70f...` | Label-in-Name/finite-evidence/dense-mobile contracts plus a real Chromium acceptance lane now exist; fresh Tests `35293139866` remains pre-runner. | Executed frontend/full-suite with Storybook browser GREEN, Security/CodeQL settlement, locale/font-fallback evidence, qualifying independent approval. |
| Python CodeQL baseline | #974 `4341080f...` → #979 `2dfd2111...` | Source repair + behavioral TLS regression contract present; fresh required workflows non-accepting. | Exact-head Tests/SAST/Security GREEN and producer/consumer CodeQL proof that Python findings are absent, then approval/integration. |
| Post-body sanitizer / frontend coverage | #983 `f48afbe...` | Quote-aware scanner and coverage tests present; SAST GREEN, Tests pre-execution cancelled, Security/CodeQL non-accepting. | Fresh executed full/coverage/rendered/security evidence + producer proof four JS findings absent + review resolution/approval. |
| Embedded image parser | #1115 `6545b5ff...` | Product Tests/SAST/Security GREEN; current CodeQL RED belongs to #974/#983 baseline. | Verified owner repairs integrate, unchanged-head CodeQL settles, independent approval. |
| CO ownership boundary | #899 `a2da5875...` → #1117 `7accb384...` | #899 boundary repair remains Proposed/Draft; registry README child is now non-force stacked and only README differs from the exact owner head. | Promote/integrate #899 first, then fresh #1117 exact-head checks and independent approval before public/package README integration. |
| Commercial DB tooling | #911 `6030b295...` | Local functional/static evidence mostly GREEN; central Dependency Review and baseline CodeQL block promotion. | Canonical owner settlement then fresh license-delta validation and qualifying approval. |
| Report/comparison evidence stack | #873/#874/#875/#876/#877/#1033/#1034 | Valid deltas are preserved through non-force ancestry; moved-head hosted acceptance incomplete. | Parent-first executed repository/rendered/a11y/i18n/security/performance evidence and independent review. |
| Immutable commercial release | #961 `3bdec050...` + #925 `8cbaad52...` | Version-identity/source contract exists, but GitHub release/tag inventory is empty and immutable artifact evidence is absent. | Normal protected integration, built-package identity, exact-SHA SBOM/provenance/reproducibility/rollback, immutable tag/package/release and approval. |

## Documentation and release boundary

This file is the mutable current overlay only. The prior full overlay is preserved byte-for-byte in the 2026-09-18 history file before this compaction; no historical RED/fix/fixture/contract/evidence is discarded. Future updates should keep this current overlay focused on live owner paths and exact acceptance gaps, moving superseded detail to immutable dated history instead of accumulating stale authority in place.

Release-ready means one exact protected head has the required repository/security/model-review evidence, no unresolved valid finding, code-current ADR/architecture/operability/recovery docs, version/CHANGELOG alignment, immutable tag/package/release, SBOM/provenance/reproducibility and rollback evidence. No current LineageWeave head meets that boundary.
