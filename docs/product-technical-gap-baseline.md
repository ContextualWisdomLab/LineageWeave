# Product & Technical Gap Baseline

> Current exact-head overlay: 2026-09-01 KST. Protected `main` is
> `cb187cadee5fb6c46d8a944815ccc154a1e028d1`; PR #640 evidence is current
> through head `51ab4616b80ebb9fc5c3a6a596b79c209226e745`. The PR is
> blocked, still requires review, and has required checks queued; auto-merge is
> off. The repository has 98 open
> PRs and 11 open issues. This current overlay supersedes the older dated
> queue snapshots below; neither branch tests nor the running Compose stack
> are protected-main delivery evidence.
>
> Exact-head buyer acceptance: authenticated desktop and 390-pixel mobile
> Dashboard browser tests passed against the canonical Compose stack, including
> grounded-case evidence opening, responsive navigation, Korean/English
> switching, and zero browser, request, or HTTP errors on the Dashboard and idle
> Ask surface. The bounded 100-record page is terminal with no queued or running
> rows and no later page was admitted; failures remain retryable only after their
> typed root causes are repaired. contextual-orchestrator PR #970 is at
> `3f6fce20ec1a0475f36f775786979b9b7d808ecf`; required checks and
> independent review remain pending. Stacked upstream PR #990 merged normally
> into that base; its exact source head
> `c25712646bb25d0d30e4a5146ca9ea54669dfdf6` adds exact request-scoped endpoint
> routing, the OpenAI JSON probe contract, and single-copy caller prompt
> preservation. Its isolated LineageWeave candidate
> returned conforming Chat Completions and Responses objects through the configured
> endpoint. The isolated administrator readiness gate passed and canonical Compose
> now runs that exact revision; post-scoped Responses correlation also passed through
> OpenAI-compatible metadata without an unknown top-level field. This is runtime
> and stacked-base evidence, while protected-main upstream delivery remains pending.
> Org workflow PR #1507 merged normally; central Pingora policy PR #1466 is at
> `7ffc89d7f76f26535602ffd29dcb19f4af00a50f`, mergeable, and awaits fresh
> checks plus replacement of its stale changes-requested review.
> Terminal retry and unbounded continuation remain mutually exclusive, so each
> admitted page must settle before another page is selected.
>
> Current Dashboard performance evidence separates selected-path improvement
> from the unchanged all-read release gate. At exact image head `c4d13aaab`,
> the authenticated response negotiated `Content-Encoding: gzip`; the complete
> payload measured 96,415 bytes without compression and 10,282 bytes on the
> wire. A five-VU, ten-second k6 observation accepted all 3,207 responses and
> measured 14.75 ms average, 14.17 ms median, 20.50 ms p95, and 84.79 ms
> maximum. The negotiated path therefore improved transfer volume and
> throughput but still fails the 20 ms maximum; neither Dashboard nor all-read
> acceptance is claimed.
> Exact-head desktop and 390-pixel mobile screenshots were retained outside
> git and reviewed without exposing implementation terminology. After applying
> the shared 44-pixel touch-target
> token, every visible Dashboard/global control met that minimum; desktop and
> mobile authenticated browser flows and the production frontend build passed.
> The populated Dashboard Storybook scene now exposes cited actions for all eight
> required claim and rebid/handover questions; its missing-fact scene independently
> proves fail-closed Sales-pool guidance. The frontend suite passed 605 tests and the
> Storybook production build completed. Authenticated non-empty Ask citations,
> grounded runtime detail cards, authoritative journey reconciliation, and a manual
> screen-reader audit remain open acceptance evidence. Global Ask now has an
> independent durable consumer at this exact head. The exact-revision Ask worker
> reached healthy while the broad post-content worker stayed stopped, settled the
> one previously queued Ask job to succeeded, and persisted a non-empty answer with
> one cited Post and one cited Event. No identifying question, answer, citation id,
> or source record was retained in this baseline. Two pre-existing post-content
> stream entries remained unconsumed, proving that Ask availability did not restart
> or drain the stopped backfill path.
>
> PostgreSQL's measured state retains `read committed` isolation with `fsync`,
> full-page writes, and synchronous commit enabled. The evidence-bound tuning
> planner observed no WAL writes, requested checkpoints, waiting locks, or
> active transactions during its bounded sample. Its validated plan retained
> the 1 GiB WAL ceiling and proposed only the measured 4 MiB-to-16 MiB WAL
> buffer change. That plan was not applied because a zero-write sample is not
> sufficient deployment evidence; controlled apply remains plan-ID-gated and
> revalidates live isolation, durability, space, locks, and transaction state.
>
> PR #640 declares and SHACL-validates the operations-case JSON-LD
> vocabulary that its Dashboard emits, keeps the packaged fallback graph-isomorphic
> with the authoritative Turtle, and includes that fallback in built wheels. This is
> implemented branch evidence; protected-main ontology publication and authenticated
> installed-runtime acceptance remain unverified. No additional ontology class is
> missing for the current normalized case, fact, relation, and milestone-code
> projection. No screenshot or identifying runtime record is committed. The ontology
> current exact head passed 2,351 repository tests with 16 integration skips;
> those branch tests are not protected-main proof. Canonical Compose applied the
> replay-safe 0271/0272 schema and serves the new Voice/Product read contracts from
> exact PR #640 backend/frontend images. The broad worker remains stopped on its
> earlier image, while the consumer-selective Ask-only worker runs exact head
> `51ab4616b80ebb9fc5c3a6a596b79c209226e745`; therefore neither receipt-bearing
> Voice/Product producer is deployed. Derived Voice completions and active
> derived assertions are both zero. Historical Product analysis rows have no model
> receipt and expose zero Product evidence; they are retry candidates, not completed
> analyses or corpus prevalence. Worker replacement remains gated on stacked PR #895,
> whose process-epoch probe fix is open with required checks queued.
>
> Canonical project binding retains three normalized membership rows on one Post.
> Separately, the current Dashboard rollup has 24 project-bearing case-kind rows across
> 22 Posts, all from explicit source project fields; the earlier 23/21 rollup snapshot
> was not a normalized-membership count. An authenticated
> Dashboard page included 2 project-bound cases among 20 returned cases, and an
> exact-code project journey returned one matching event; desktop and mobile
> browser acceptance rendered the project groups without committing an identifier.
> PR #896 merged normally into #640's non-default branch as squash
> `1788082e5672232118443eda31b5dbe34c4947bf`. Its in-progress hosted backend and
> frontend jobs were cancelled by that merge and are not green evidence; fresh
> integrated #640 checks are queued. #896's aggregate runtime evidence proves only
> the selected Dashboard-to-Project-History path, not the all-read 20 ms contract or
> #888 activation. Protected-main delivery remains unverified. The earlier Global Ask
> semantic-retrieval gap is closed in the canonical candidate runtime: the pinned
> orchestrator accepts the configured endpoint contract, and the isolated Ask worker
> persisted a non-empty answer with one Post citation and one Event citation while
> the broad worker remained stopped. Protected-main upstream and LineageWeave
> delivery, source-reference attachment for that answer, and wider authorized-corpus
> acceptance remain unverified.

> Current rebuild overlay: 2026-08-28 KST. Protected `main` is
> `ff7431bd1851c03e737808d22c6a2d43968582f9`; PR #640 is a ready-for-review
> current-main semantic rebuild at `f0bc98eef238b7a03d4227ab909c8de296041f36`.
> PR #778 is remotely published at
> `b87b186dd7213dc59d8e933e7d8c3f330598470f`; PR #781's last remote
> exact-head evidence before this overlay is
> `760d05896f96e5ce7fb9df0e4b62369448913fbd` and remains candidate-only.
> Its contextual-orchestrator runtime is pinned to open upstream replacement PR #970 exact
> `e6329db1b9d0fb59b23cf63b4e4b056743b8a5da`; this candidate is not
> protected-main evidence.
> The open queue has 14 PRs:
> #783, #782, #781, #780, #778, #774, #772, #771, #770, #702, #679, #672,
> #667, and #640; #702/#679/#672/#667 remain drafts. Local candidate tests do
> not transfer to the remote PR head or protected `main`. Exact-head Compose,
> browser, load, and backfill acceptance remains pending. This
> overlay supersedes every older queue count below while the dated historical
> snapshots remain supporting evidence only.
> Exact-head loop overlay: 2026-08-29 13:20 KST. Protected `main` is
> `fc13acaa20adca11968238e398d4aafcf62b6cee` (v2.23.0 leftover-map
> explained leftover share, #775). Open ready PRs still lack independent
> APPROVE. #782 leftover-map coordinates + graphic + axis share + ticks
> (v2.24.0–v2.27.0 / ADR 0267–0270) is on
> `2a203bf8b75b987ba899a0006a312d81259b9124` after #799 squash-merged
> into the unprotected leftover branch. Auto-merge squash remains armed
> on #782/#780/#774/#772/#771/#770. Independent APPROVE is still
> required for protected main. Drafts remain dirty against `main`. #96
> stays closed as a weaker duplicate of #91. GitHub writes through
> `gh`/MCP succeed. Copilot review is not independent APPROVE. Do not
> self-approve. Do not `gh pr merge` stacked leftover PRs onto an
> unprotected leftover base.
>
> Next buyer increment on this cycle: leftover-map distance on
> graphic-display pair segments (ADR 0271 / v2.28.0). Caption each
> closest/farthest segment with persisted leftover-map distance `d` so
> the pair-row badge matches the graphic line. UI-only; no new columns.
> Missing/non-finite `d` omits that segment caption. Do not invent `d`
> from plotted coordinates. Do not invent leftover scores. Stack onto
> leftover branch `feat/leftover-map-coordinates-v2240`; leave the PR
> open for independent review.

> Exact-head loop overlay: 2026-08-29 13:15 KST. Protected `main` is
> `fc13acaa20adca11968238e398d4aafcf62b6cee` (v2.23.0 leftover-map
> explained leftover share, #775). Open ready PRs still lack independent
> APPROVE. #782 leftover-map coordinates + graphic display + axis share
> (v2.24.0 / v2.25.0 / v2.26.0 / ADR 0267 / ADR 0268 / ADR 0269) is on
> `4a0afbf4804d9862bba58869db20ccdfb0a0b37e`; Strix fail-closed and no
> independent APPROVE. Auto-merge squash remains armed on
> #782/#780/#774/#772/#771/#770. Drafts remain dirty against `main`.
> #96 stays closed as a weaker duplicate of #91. GitHub writes through
> `gh`/MCP succeed (comment/create-branch/auto-merge). `git push` HTTPS
> still fails (empty `X-OAuth-Scopes`). Copilot review is not
> independent APPROVE. Do not self-approve.
>
> Next buyer increment on this cycle: leftover-map coordinate ticks
> (ADR 0270 / v2.27.0). Tick leftover-map axes at the origin and at each
> unique finite persisted `ξ` / `ζ` so pair-row `ξ (x, y) ζ (x, y)`
> matches the graphic. UI-only; no new columns. Rank-0 unused axes name
> only `0` and do not invent drawing-scale `−1` / `+1` ticks. Do not
> invent leftover scores. Do not mix into #782; stack onto leftover
> branch `feat/leftover-map-coordinates-v2240`.

> Exact-head loop overlay: 2026-08-28 19:15 KST. Protected `main` is
> `fc13acaa20adca11968238e398d4aafcf62b6cee` (v2.23.0 leftover-map
> explained leftover share, #775). Open ready PRs still lack independent
> APPROVE. #782 leftover-map coordinates + graphic display (v2.24.0 /
> v2.25.0 / ADR 0267 / ADR 0268) is on
> `2f7e9c8df695f12d03964d5caa68fa3355bdd923`; Strix fail-closed and no
> independent APPROVE. Drafts remain dirty against `main`. #96 stays
> closed as a weaker duplicate of #91. GitHub writes through MCP succeed
> (comment/create-branch/git push/auto-merge). Copilot review is not
> independent APPROVE. Do not self-approve.
>
> Next buyer increment on this cycle: leftover-map axis share on the
> graphic display (ADR 0269 / v2.26.0). Caption plot axes with persisted
> ADR 0148 `leftover_map_axes` inertia `σ_k² / Σ_j σ_j²`. UI-only; no
> new columns. Rank-0 zero-share axes still named. Missing/non-finite
> share omits that axis badge and keeps existing leftover-map axis
> text. Do not invent leftover scores. Do not mix into dashboard stacks
> #640/#778/#781.

> Exact-head loop overlay: 2026-08-28 16:05 KST. Protected `main` is
> `fc13acaa20adca11968238e398d4aafcf62b6cee` (v2.23.0 leftover-map
> explained leftover share, #775). Open ready PRs still lack independent
> APPROVE. #782 leftover-map coordinates (v2.24.0 / ADR 0267) is on
> `e2d13019004a5d8c019fecf7a39ceeef4093b8dd`; Strix fail-closed and no
> independent APPROVE. Drafts remain dirty against `main`. #96 stays
> closed as a weaker duplicate of #91. GitHub writes through MCP succeed.
>
> Next buyer increment on this cycle: leftover-map graphic display
> of already-persisted `ξ_{1:2}` / `ζ_{1:2}` (ADR 0268 / v2.25.0).
> UI-only; no new columns. `R̂` and `d` already are inner product and
> length. Do not invent leftover scores. Do not mix into dashboard
> stacks #640/#778/#781.

> Exact-head loop overlay: 2026-08-28 13:00 KST. Protected `main` is
> `fc13acaa20adca11968238e398d4aafcf62b6cee` (v2.23.0 leftover-map
> explained leftover share, #775). Open ready PRs still lack independent
> APPROVE. Drafts remain dirty against `main`. #96 stays closed as a
> weaker duplicate of #91. GitHub writes through `gh` succeed.
>
> Next buyer increment on this cycle: leftover-map coordinates
> `ξ_{1:2}` / `ζ_{1:2}` (ADR 0267 / migration 0245 / v2.24.0) so
> `R̂ = ξ · ζ` and `d = ‖ξ − ζ‖` are buyer-auditable. Do not name
> leftover-map inner product, cosine, or length as separate columns.

> Exact-head loop overlay: 2026-08-28 10:00 KST. Protected `main` was
> `edf22ee39aee2a8481f9bda8fff59801821e79c2` (#773 similar-VOC coverage).
> Open ready PRs: #772 (ask_time_axis coverage), #771 (fixtures/vision
> coverage), #770 (project-history empty-state). Auto-merge squash is
> enabled on all three; none has an independent APPROVE (only bot
> COMMENT). Drafts #702, #679, #672, #667, #640 remain dirty against
> `main`. #96 stays closed as a weaker duplicate of #91. Writes through
> the Grok GitHub App now succeed (comment/close/auto-merge/update-branch)
> despite empty `X-OAuth-Scopes`; git push is the remaining probe this
> cycle. This overlay supersedes every older queue count below.
>
> Next buyer increment on this cycle: leftover-map explained leftover
> share `e = R̂² / R²` (ADR 0266 / migration 0244 / v2.23.0) so
> `e + s + x = 1` is buyer-auditable. Do not persist leftover-map
> coordinates in this slice.

> Exact-head loop overlay: 2026-08-28 KST. Protected `main` was
> `bbb191924e9881a5201f1ecf63c854d92992cc1c`; seven PRs and nine issues were
> open. PR #763 was `b51d3bd8872b` and PR #762 was `e6ca33dba1b5`; both were
> mergeable, normal squash auto-merge was enabled, exact-head Checks were still
> running, and no qualifying independent approval existed. PRs #702
> (`93e7b81d096d`), #679 (`135dfe7c4266`), #672 (`a3e87a89185f`), #667
> (`0c0f4af572a9`), and #640 (`bd73e0a43ae1`) remained draft and dirty against
> `main`. Central ruleset 18156473 and repository no-force-push ruleset
> 21065108 remain active. This overlay supersedes every older queue count below.
> Checks from older heads, stacked bases, or merged PRs are not transferred.
>
> Current-runtime boundary: the official Compose project was healthy at the
> HTTP health route, but its PostgreSQL schema did not yet contain
> `source_post_voice`; therefore no current Voice-history aggregate,
> authenticated project-history API result, or rendered authenticated UI result
> is claimed. Older aggregate observations below remain dated supporting
> evidence, not confirmation of this exact head. The checked repository names
> are `ContextualWisdomLab/LineageWeave`, `RankWeave`, `ThreadWeave`, `TEPP`,
> and lowercase canonical `ContextualWisdomLab/disksage`.

> Voice-of-X delivery snapshot: 2026-08-27 KST. Protected `main` was
> `ff7431bd1851c03e737808d22c6a2d43968582f9`; PR #713 was
> `850494c3861703862a76cfe564381a41243c6c2d`; stacked PR #717 was
> audited at implementation head
> `d5fe4828e9005f0157c308e8ea3c3a590cdf465b`. This candidate and the
> historical evidence below are not protected-main release evidence.
> Loop snapshot: 2026-08-27. Protected `main` advanced through the
> I/O-Psychology job-family and occupational-classification delivery: PRs
> #709 (DOT/FJA worker functions, ADR 0232), #718 (evidence-bound construct
> classes, ADR 0248), +#726 (catalog-bound construct extraction, ADR 0253),
> #733 (construct evidence navigation, ADR 0255), #713 (Voice-of-X ADR 0246),
> #753 (FJA I/O-Psychology semantic layer, ADR 0251), #751 (SOC/O*NET/RIASEC
> taxonomy, ADR 0245), #749 (authorized job-family and job-series snapshot
> import, ADR 0263), #657 (TEPP lifecycle evidence), #704, #720, and #754 are
> now merged. The still-open queue is carried in section 1. No row below is
> release evidence until re-verified on a specific head.

## Voice-of-X product and technical gap

ADR 0246 and PR #713 add Supplier, Employee, Business, Regulator, Investor,
Society, and Process to the original Customer, Customer's Customer,
Competitor, Market, and Partner source-post vocabulary. The migration,
published SKOS concepts, product requirements, changelog, and ontology
round-trip tests agree on the twelve codes. The design is organization-type
neutral: public bodies, nonprofits, communities, and automated processes do
not need to be forced into a B2B2C customer chain.

The phrase "all Voice-of-X combinations" does not have a standards-backed
finite enumeration. ISO's own stakeholder-category guidance says that the
relevant category set varies by committee and subject; ISO 26000 requires
stakeholder identification and engagement across organizational contexts;
AA1000SES requires an inclusive, continuing identification process; and
Mitchell, Agle, and Wood (1997) model stakeholder salience from combinations
of power, legitimacy, and urgency rather than a fixed industry-role list.
Accordingly, ADR 0246 keeps the controlled vocabulary extensible and refuses
keyword inference, defaults, invented weights, or an asserted exhaustive
cross-product.

ADR 0256 and migration 0237 now define the persistence contract for
evidence-bearing composition. A post keeps one source-provided
`voc_type_code`, mirrored as its sole primary association, while every
additional voice requires a normalized PROV-O assertion and explicit truth
status. Half-open assignment intervals preserve a backfilled primary at
historical cutoffs, close a replaced primary without deleting it, and permit a
later return to the same Voice. The #717 candidate therefore addresses #748's
A → B → A storage root cause without adding Cartesian-product codes. Protected
delivery and synthetic PostgreSQL concurrency/cutoff evidence remain required.
The remaining acceptance boundary is:

1. preserve the imported primary voice without reclassification (implemented
   in the candidate migration; migration 0237 replayed twice successfully on
   an isolated PostgreSQL stack on 2026-08-27, including both primary-sync
   triggers; a synthetic real-OIDC PostgreSQL API write also proved that the
   imported primary remains unchanged);
2. record each additional voice with its own source/evidence and truth state
   (schema-enforced and candidate `post_admin` API plus live Post-popup
   authoring implemented; synthetic authenticated PostgreSQL integration
   proved denial before permission, the authorized write, and its normalized
   PROV-O derivation on 2026-08-27);
3. keeps post voice distinct from named-counterparty relationship, actor role,
   topic, channel, lifecycle, and stakeholder-salience attributes;
4. return only authorized associations through API, JSON-LD, CSV, filters,
   and UI (candidate API list/detail, filters, combined post-card labels,
   qualified JSON-LD, exact-value CSV, SHACL, and source-post evidence
   navigation implemented; the board re-filter matches every associated voice
   and all twelve governed atomic labels are localized across English, Korean,
   Chinese, Japanese, and Vietnamese; one bounded query projects assignments
   for every authorized Post even when another node type is the focus; post
   detail lists primary and evidence-connected perspectives separately and
   honors its knowledge cutoff; client-side JSON-LD filtering retains only
   exact canonical repository-case node and Voice-assignment IRIs rather than
   accepting cross-origin suffix matches; the exact-value row exposes distinct
   carrying-Post and authorized derivation-evidence actions, while hidden
   evidence emits neither an identifier nor a fabricated evidence count;
   paged JSON-LD merges properties for one subject and unions its multi-Voice
   relation rather than overwriting an earlier page); and
5. proves zero-, one-, and multi-voice states with synthetic fixtures,
   migration replay, ontology/SHACL, API, accessibility, and Storybook edge
   tests before any release claim. The candidate `CombinedVoiceEvidence` scene
   covers primary-plus-additional assignments; desktop and mobile screenshots
   were inspected on 2026-08-27. At 390 CSS pixels the document did not
   overflow, the named exact-value region remained horizontally scrollable,
   and the source-post evidence action remained visible and labeled. The
   `Post/Recorded perspectives` desktop and 390-pixel scenes were also inspected
   on 2026-08-27; both kept each complete Voice label paired with its imported
   or evidence-connected state without clipping or horizontal overflow. The
   `Post/Connect perspective` ready/success scenes were inspected at 1440 and
   390 CSS pixels on 2026-08-27: labels stay above controls, the mobile form is
   a single column, controls meet the 44-pixel touch target, and no horizontal
   overflow was visible.

At this snapshot the repository had 42 open PRs and 11 open issues. PR #713
head `850494c3` includes the review-driven localization of all twelve governed
Voice labels. Its frontend, ontology publication, static-analysis, dependency,
coverage, full-suite, CodeRabbit, Devin, and OpenCode checks passed. Strix
failed closed before producing a vulnerability report:
the primary NVIDIA NIM model returned HTTP 429, one configured fallback had
reached end of life, and the OpenAI fallback reported exhausted credits. A
same-head retry completed on 2026-08-27 with the explicit
`STRIX_PROVIDER_UNAVAILABLE` annotation and again produced no vulnerability
report. This
is provider/control-plane unavailability, not a vulnerability result or
permission to transfer an older success. Auto-merge remains enabled, while an
independent approval is still required. PR #717 implementation head
`d5fe4828` merges that
parent change without force-pushing and separates the complete governed Voice
catalog used for authoring from usage-derived Board filters, so an authorized
administrator can attach a Voice that no visible Post carries yet. It also
labels Voice exact-value navigation as opening the carrying Post rather than
misrepresenting that Post as the separately recorded derivation evidence. Its
CodeRabbit and hosted Frontend/Storybook checks passed at predecessor head
`ebb4ef1d`; refreshed checks for exact head `d5fe4828` were queued. Focused local
backend tests, frontend type checking/lint, and the new unused-Voice authoring
regression passed, and the exact-value navigation tests, lint, and type check
passed after the label repair. The paged JSON-LD union regression and Voice
evidence navigation suite passed 23 focused frontend tests; 48 focused backend
ontology/docstring tests also passed. The full backend suite at predecessor
head `ebb4ef1d` passed 1,366 tests with 148 environment-dependent skips. The
real-integration fixture now applies
the existing migration 0042 before the expanded taxonomy migrations instead
of seeding an incomplete or duplicate legacy catalog; the exact
`d5fe4828` authenticated post-list integration passed in 91.54 seconds. The
wider local frontend run had 400 passes and eight five-second timeouts under
concurrent backend-suite load; a later App-only run had 94 passes and five
five-second timeouts, while the hosted Frontend/Storybook job passed on
`ebb4ef1d`. Neither local timeout run is promoted to full-suite success. An initial
authenticated integration attempt was unavailable while Keycloak initialized;
a later retry against the shared synthetic stack succeeded in 56.18 seconds
and proved the permission, API, PostgreSQL,
PROV-O, and primary-preservation assertions; no identifying source data was
used or retained. No self-approval, admin bypass, or stale-head check transfer
is permitted.

Stacked PR #717 carries ADR 0256, migration 0237, qualified
ontology terms, persistence/API/UI tests, and the category-validation review
repairs plus a local candidate admin write path that creates its PROV-O
derivation from an authorized evidence Post. Its JSON-LD projection names that
evidence Post only when it is in the authorized visible set and omits the whole
additional assignment otherwise, preserving the SHACL evidence minimum without
substituting the assigned Post. It targets
#713's branch, not protected `main`;
its checks and review are candidate evidence only. After
#713 reaches protected main, #717 must be synchronized, retargeted to `main`,
and revalidated on its then-current head.

Downstream Dashboard repair PR #737 exact head `a837ee5d` is stacked on base
`7c7bb2cf`, which contains migration 0235 through a non-#713 composition but
does not contain #713's twelve-label locale update. Its added Voice labels are
therefore necessary on that exact base, yet overlap #713 and must be reconciled
when the stack is eventually rebuilt on protected `main`; neither branch is a
second taxonomy authority, and pre-parent Checks cannot transfer across that
restack.
The remaining user-visible gap is evidence-bearing composition. A post still
has one source-provided `voc_type_code`; the product cannot yet represent a
single record that intentionally carries multiple independently evidenced
voices, nor expose the combination in filters, exports, or the ontology
neighborhood. Do not solve this by adding every Cartesian-product code. The
acceptance boundary for a later ADR is a normalized, provenance-bearing
multi-voice association that:

1. preserves the imported primary voice without reclassification;
2. records each additional voice with its own source/evidence and truth state;
3. keeps post voice distinct from named-counterparty relationship, actor role,
   topic, channel, lifecycle, and stakeholder-salience attributes;
4. returns only authorized associations through API, JSON-LD, CSV, filters,
   and UI; and
5. proves zero-, one-, and multi-voice states with synthetic fixtures,
   migration replay, ontology/SHACL, API, accessibility, and Storybook edge
   tests before any release claim.

At this snapshot the repository had 23 open PRs and 10 open issues. PR #713
was `MERGEABLE` but policy-blocked: exact-head backend, frontend, CodeQL,
ontology-publication, Semgrep, OSV, Trivy, Scorecard, Noema, Devin, and
CodeRabbit checks were successful; `coverage-source-tree` was queued; Strix
failed closed with `STRIX_PROVIDER_UNAVAILABLE`; and an independent approval
was still required. Auto-merge remains enabled. No self-approval, admin bypass,
or stale-head check transfer is permitted.

References for this gap use the APA 7 entries in ADR 0246. Current supporting
standards pages were rechecked on 2026-08-27: ISO 26000:2010 remains applicable
to all organization types and AA1000SES v3 is under development for a planned
2027 release, so the repository continues to cite the published AA1000SES
(2015) contract rather than treating the draft as adopted policy.

> Current queue overlay: 2026-08-27 KST. Protected `main` was
> `ff7431bd1851c03e737808d22c6a2d43968582f9`; 26 PRs and 10 issues were
> open. This overlay supersedes the older queue count and exact-head table
> below, which remain historical evidence. Re-fetch the head, checks, reviews,
> threads, applicable rulesets, and merge SHA immediately before any lifecycle
> claim. No local branch or stacked-branch result is protected-main evidence.

## Current occupational semantic-layer gap

ADR 0245's candidate branch publishes only a provenance-safe classification
foundation: 23 2018 SOC major groups, four O*NET 31.0 Job Zone categories, six RIASEC interest
types and their published adjacency, six explicitly legacy work-value clusters, seven
revised work-style dimensions, and four ability domains. It asserts no
occupation-to-characteristic instance profile and therefore does **not** yet
satisfy the requested job-family, job-series, and occupation-level coverage of
work cognition, affect, behavior, or their empirical relations. This is an
explicit unavailable state, not a reason to infer mappings from labels.

| Gap | Current evidence | Acceptance requirement |
|---|---|---|
| Classification depth | ADR 0245 and `lineageweave/io_taxonomy.py` expose SOC major groups only; schemes now name versioned PROV source entities and the stable O*NET 31.0 Job Zone JSON digest | Import a versioned authoritative classification release with provenance-preserving major, minor, broad, and detailed occupation identifiers; add ISCO/ESCO crosswalks only where the publishing authority supplies them |
| Construct granularity | The candidate ontology exposes 23 high-level characteristic concepts | Publish source-versioned O*NET abilities, skills, knowledge, work activities, work context, interests, and work styles without collapsing cognition, affect, and behavior into one dimension; preserve removed Work Values only as versioned legacy content |
| Occupation-to-construct relations | ADR 0245 deliberately declares relation properties without instance assertions | Persist released source observations with source version, occupation code, element identifier, scale identifier, value, sample/error metadata when supplied, and provenance; never invent or locally normalize a weight |
| Job-family and job-series semantics | No authoritative employer-specific job architecture is present | Define an organization-neutral import contract that preserves the authorized source hierarchy and distinguishes standard occupation codes from employer job families/series; no label-based binding |
| Temporal and multilevel interpretation | Static vocabulary only; no person-level inference is asserted | Version valid and transaction time, preserve occupation/organization/unit nesting and multiple membership, and require TEPP or the owning Rust psychometric service before any calibrated temporal or multilevel result |
| Product consumption | The read model has no persisted semantic-layer consumer or authenticated UI evidence | Add a provenance-bearing API and accessible ontology exploration flow, then verify synthetic Storybook edge states plus authenticated aggregate runtime evidence without exposing identifying records |

### Current exact-head PR queue

| PR | Exact observed head | Base | Observed gate state |
|---:|---|---|---|
| #719 | `0cea830a` | `feat/fja-worker-function-ontology` | unstable; 1 pending check(s) |
| #718 | `a3fb32bb` | `feat/fja-worker-function-ontology` | clean; no non-passing check observed |
| #717 | `771a8edf` | `feat/voice-of-x-complete-taxonomy` | unstable; 1 pending check(s) |
| #716 | `8b54b2f7` | `fix/structured-workflow-exact-pin` | clean; no non-passing check observed |
| #714 | `aa93318f` | `main` | blocked; no non-passing check observed |
| #713 | `cc3dfc14` | `main` | blocked; review required; 13 pending check(s) |
| #711 | `8902e37f` | `feat/dashboard-case-metrics` | clean; no non-passing check observed |
| #710 | `8df04b68` | `main` | blocked; review required; no non-passing check observed |
| #709 | `8ef4090c` | `main` | blocked; review required; 11 pending check(s) |
| #704 | `027323cf` | `main` | blocked; review required; 2 failed check(s) |
| #702 | `5de66ab9` | `main` | blocked; review required; 2 pending check(s) |
| #701 | `cc3351a9` | `main` | blocked; review required; 1 failed check(s) |
| #700 | `1bc99eca` | `main` | blocked; review required; 1 failed check(s) |
| #680 | `efe864e5` | `main` | blocked; 1 failed check(s) |
| #679 | `13ecf41d` | `main` | blocked; no non-passing check observed |
| #672 | `a3e87a89` | `main` | blocked; review required; 1 failed check(s) |
| #668 | `1194f44d` | `main` | blocked; review required; 1 failed check(s) |
| #667 | `c2d11a8a` | `main` | blocked; review required; 2 pending check(s) |
| #658 | `15d670f0` | `main` | blocked; review required; 1 failed check(s) |
| #657 | `9f71681c` | `main` | blocked; review required; 1 failed check(s) |
| #644 | `f53dd28e` | `main` | blocked; review required; 1 failed check(s) |
| #643 | `8767de1b` | `main` | blocked; review required; 1 failed check(s); 1 pending check(s) |
| #640 | `5594029c` | `main` | blocked; no non-passing check observed |
| #639 | `2f4b1bff` | `main` | blocked; review required; 1 failed check(s) |
| #632 | `24262a99` | `main` | blocked; review required; 1 failed check(s) |
| #629 | `b721b0f2` | `main` | blocked; review required; 1 failed check(s) |

> Dashboard delivery snapshot: 2026-08-26 07:15 KST. Protected `main` was
> `494b54e2245040bcf02b45376f221c37cd437e76`. This local branch is not
> protected-main release evidence.

## Operations Dashboard PRD/TRD traceability

| Requirement | Evidence contract | Delivery state |
|---|---|---|
| Operations ontology runtime package | ADR 0206 governed OWL/JSON-LD projection; authoritative Turtle, SHACL, and installed fallback must agree | **Implemented on the PR branch:** the wheel declares the Turtle package data and tests graph isomorphism with the authoritative source. **Unverified:** protected-main Pages publication and authenticated installed-runtime acceptance. No speculative milestone classes are required because the normalized API contract governs milestones by closed codes. |
| Claim cause delay: order, specification change, originating order, sales pool, Event/post counts | ADR 0206; contextual-orchestrator case classification with cited spans; case-specific normalized milestones | Candidate implementation counts only cited claim milestones instead of duplicating every Post summary Event; authenticated runtime acceptance pending |
| Rebid/handover: discussion, counterparties, our owner, decisions, Event/post counts | ADR 0206; normalized case facts and case-specific normalized milestones | Candidate implementation counts only cited rebid/handover milestones; corpus backfill pending |
| External information count/rate and sales/project relation | ADR 0206; semantic `external_information` classification inside Dashboard GNB | Candidate implementation; no separate Board by product decision |
| Project-specific journey | Explicit source/semantic project membership plus event-time ordering | **Implemented on the PR branch and aggregate runtime-accepted:** canonical storage retains three normalized membership rows on one Post. Separately, 24 project-bearing Dashboard case-kind rollups across 22 Posts use explicit source project fields; these are case rows, not membership rows, and may change while the bounded page settles. An authenticated 20-case page included 2 project-bound cases and one exact-code journey returned one matching event. Desktop/mobile rendering passed without retaining identifiers. **Unverified:** protected-main delivery and authoritative lifecycle/handover reconciliation. |
| Repeat issue to design improvement | `repeat_issue`, `issue_pattern`, and `improvement_action` cited facts | Candidate semantic contract; design-system connector acceptance pending |
| Natural-language Ask with evidence, report, alert, MCP | Persisted semantic-unit embeddings plus versioned delivery/resource contract | Candidate implementation uses whole-question embedding retrieval with no lexical fallback. **Runtime-accepted on the PR head:** the exact `51ab4616` Ask-only worker became healthy while the broad worker stayed stopped, settled the one queued request, and persisted a non-empty answer with one cited Post and one cited Event. This closes the earlier configured-gateway admission and non-empty citation gap without exposing identifying records. **Open/unverified:** the latest answer attached no separate source-reference row, MCP authenticated E2E acceptance remains incomplete, and neither the upstream stack nor LineageWeave is protected-main delivery evidence. |
| Similar VOC, customer cohort, prior action | Persisted repeat-issue candidate semantics plus orchestrator pair adjudication and extractive evidence | Candidate live post endpoint and post-detail UI implemented; authenticated runtime acceptance pending |
| TEPP independent Event Lineage anchor | Accepted, persisted TEPP criterion bound to exact snapshot/cutoff before fast-mlsirm activation | Consumer PR #606 is on protected main; TEPP producer PR #237 remains open, so no end-to-end accepted artifact is release evidence yet |
| Temporal Lineage topics and multilevel important posts | ADR 0210; TEPP posterior topic/plausible-value contract followed by fast-mlsirm observed-information case-deletion influence | The stacked successor adds a durable, short-transaction producer request, exact accepted TEPP posterior run/snapshot/cutoff/artifact binding, four-level source-membership admission, complete-result validation, and normalized persistence. It does not misbind the older topic-lineage envelope or calibrated-measurement receipt to this scientifically distinct posterior projection. Incomplete evidence is stored until a new evidence event, expired work follows an operator-declared lease that strictly exceeds the request timeout, changed input automatically produces a fresh request, and exact request, membership, and result artifact bytes are digest-verified before parsing. The Dashboard remains unavailable until TEPP publishes the full posterior/membership artifact and fast-mlsirm publishes the domain-neutral continuous-posterior Rust result endpoint; the crossed weighted MAP binary kernel is not misapplied and no local Python substitute exists |

### Technical contract and flow

```mermaid
sequenceDiagram
  participant Source as Authorized source_post
  participant CO as contextual-orchestrator
  participant Case as operations_case_* (3NF)
  participant TEPP as TEPP criterion run
  participant MLS as fast-mlsirm
  participant API as Dashboard/Ask API
  Source->>CO: semantic units + lineage + ontology context
  CO-->>Case: cases, cited facts, session provenance
  Source->>TEPP: versioned snapshot and independent criterion
  TEPP-->>MLS: exact accepted anchor only
  MLS-->>API: anchored vector or unavailable
  Case-->>API: ABAC-filtered evidence and counts
```

Security/operability: every aggregation applies `post_read` plus row-level
corporate-entity visibility before counting; source-body digests invalidate
stale inference; provider errors persist no positive/negative result; PII
remains authorized at the UI boundary and is excluded from telemetry. The
tables use composite keys and bounded kind-first indexes; production hot-path
acceptance still requires `EXPLAIN (ANALYZE, BUFFERS)` on an anonymized runtime
snapshot.

### Historical UI audit evidence

The `f0b96029` Storybook build was rendered at 1440×1100 and 402×1200 with
synthetic evidence; `416fd19d` changes only post-navigation request isolation.
Desktop inspection showed all four case kinds, five non-conflated metrics,
project-journey ordering, cited facts, and evidence actions without horizontal
card overflow. Narrow inspection showed two-column metrics, readable cards and
44px-class actions; the project journey remains intentionally horizontally
scrollable. No identifying runtime record or screenshot is committed. The
`EvidenceReady`, `NarrowViewport`, `AnalysisPendingAndMissingEvidence`,
`AnalysisFailed`, and `LoadError` scenes cover the ADR 0206 state inventory.
Authenticated authorized-corpus acceptance remains separate and may return
only aggregate, non-identifying evidence to this repository.

### Exact open-PR boundary

At this snapshot there were 11 open PRs and 10 open issues. PRs #660 and #659
merged to protected `main`; PR #666 remains only non-default-branch stack
composition inside #663. Every remaining open head required refreshed hosted
gates and/or independent review after the base changed. These observations are
not merge readiness. Re-fetch exact heads, unresolved threads, checks,
approvals, rulesets, and merge SHA before any lifecycle claim.

> Audit snapshot: 2026-08-26 07:15 KST (refreshed by the autonomous merge
> loop). This repository records synthetic fixtures and aggregate,
> non-identifying runtime evidence only. Open PRs and local checks are not
> protected-default-branch release evidence. Identifying post identifiers,
> organization names, and production record keys must never appear in this
> file.

## 1. Exact-head and governance evidence

The protected default branch was `494b54e2245040bcf02b45376f221c37cd437e76`
when this baseline was refreshed. The live queue contained 11 open PRs and 10
open issues. The exact-head inventory below supersedes older per-PR snapshots
elsewhere in this document; those older rows remain useful historical delivery
context only.

| PR | Exact observed head | Merge/check state at this snapshot |
| ---: | --- | --- |
| #667 | `3bc662d7` | refreshes protected-main and open-queue documentation evidence; base conflict remains to be repaired |
| #663 | `6fd2f701` | combined Project ontology candidate plus #666's non-default-branch removal of sampled region-coverage arithmetic; base conflict remains to be repaired |
| #658 | `f007a5ed` | evidence-honest Global Ask cutoff; hosted checks and independent review required |
| #657 | `2d9b43b7` | TEPP asynchronous lifecycle persistence while unpublished producer work stays unavailable; hosted checks and independent review required |
| #644 | `ed8d97f3` | native frontend surface code splitting; hosted checks and independent review required |
| #643 | `7fb4d18c` | shared token-backed status notice; hosted checks and independent review required |
| #640 | `1788082e` | current integrated dashboard case metrics and project journeys head, including merged stack PR #896; blocked with required checks queued and independent review still required |
| #639 | `48065ad1` | restores Running action and Compose contracts; hosted checks and independent review required |
| #632 | `29aee18d` | graph-fact provenance, public verification, MCP admission, and k6 evidence; hosted checks and independent review required |
| #631 | `665046dc` (observed parent) | decomposes closed PR #490; this merge refresh advances its head and restarts hosted review evidence |
| #629 | `0138db5f` | provider-work release and bounded landing reads refreshed onto protected `main`; hosted checks and independent review restarted |

No row above is merge evidence. Immediately before any lifecycle action,
re-fetch the head, unresolved threads, formal reviews, rulesets, and same-head
check conclusions. In particular, queued checks are infrastructure state and
do not transfer evidence from an earlier SHA.

PR #607 first merged as `61fd631c7bb3c57113fd19763c2c43161eeb2824`
into #606's non-default branch. PR #606 subsequently passed the protected gate,
so the combined TEPP-consumer and operations-dashboard implementation is now
on `main`; the still-open TEPP producer PR #237 keeps end-to-end anchor
acceptance unavailable.

PR #604 was closed unmerged after its exact OIDC repair was composed into #605;
its green or pending checks are not delivery evidence. PR #482 merged as
protected-main commit `464ff25002044b9d933c8eefd36c8def7ca0ffd8`
with package conflict markers, identifying baseline records, and an OIDC
return-context regression. PR #603 repaired the package/privacy and
analysis-run transaction defects through protected main at `4f53190b`; the
OIDC defect remains delivered until #604 or the composed #605 passes the
protected gate. Protected main is therefore not yet a release candidate.

PR #592 first merged as `3b3af3b4fe9c439354433a43444e05f37ab24ea3`
into #590's non-default stack base at `2f033ba3`. The complete stack then
passed the protected gate and #590 merged to `main` as
`1d1379fc59d9dac6e9c8bfa4812313e3b9e8f3c8`.

PR #521 merged through protected `main` as
`3797f063b1a7396972a749aa81f23745acccbee1`; it is release evidence and no
longer part of the open queue. That merge also left a standalone conflict
marker and duplicated stale tail in `CLAUDE.md`; #594 repaired it through
protected `main` as `241be2dddf657f854cb8be54fe11d4ef48d37976`.

Protected main now contains the ADR 0109 OIDC return restoration from #605,
including fragment preservation and storage fallback. The #606 dashboard
landing must additionally route `?post=` deep links to the Board; that focused
regression is part of the current candidate and is not delivery evidence yet.

Three systemic gates currently dominate the queue:

1. **Strix visibility lookup failure (org control plane).** PR #600 exact head
   `7580bdc9` failed before scanning because the required-workflow token could
   not resolve this public repository after six API retries. The root repair is
   ContextualWisdomLab/.github#1320 at `3b9b2380`: ordinary PR, push, and
   schedule runs use trusted event visibility; cross-repository dispatch keeps
   authoritative public/private/internal visibility; private and internal
   repositories remain on private-capable providers. The exact head also
   composes the executable fallback contract and classifies bounded NVIDIA
   `ServiceUnavailableError` overload evidence as retryable across configured
   distinct models without weakening exhaustion or vulnerability fail-close.
   A hosted fallback then completed with zero vulnerabilities but was rejected
   because the generic warning gate treated Strix's fallback-model banner and
   a Hugging Face unauthenticated-download notice as provider failures. The
   current head removes only those two exact scanner notices before the
   existing general warning and explicit 429/provider failure checks. The
   current head also clears a foreign NVIDIA/OpenRouter endpoint before a
   direct-OpenAI fallback while retaining an explicitly configured
   direct-OpenAI primary endpoint. The prior full quick-gate harness, overload
   path, 12 visibility-contract tests, and the focused cross-provider endpoint
   contract passed; exact-head hosted revalidation remains pending. It is blocked on
   hosted exact-head gates and independent review, so no repaired
   protected-main Strix runtime evidence exists yet.
2. **Strix provider unavailability (org control plane).** The central required
   Strix scan on .github#1320 failed when NVIDIA returned `Service temporarily
   overloaded`; the gate correctly failed closed but did not try its configured
   distinct fallbacks because the service-unavailable classifier excluded the
   NVIDIA provider. Exact head `3b9b2380` composes that execution repair and the
   two exact non-fatal scanner-notice exclusions while keeping
   incomplete exhaustion non-passing. This is still an unmerged control-plane
   proposal, not protected-main or downstream runtime evidence.
3. **Current-head independent approval.** The org merge scheduler requires
   `reviewDecision == APPROVED` plus complete Strix evidence on the exact
   head. Bot review evidence regenerates per push, so any repair push resets
   the review clock by design; this is expected and not a bypass target.

Recent protected-default-branch delivery evidence (squash merges onto
`main`, newest first):

| PR | Merged (UTC) | Delivered |
| ---: | --- | --- |
| #628 | 2026-08-25 12:39 | one-round-trip authorized post filter options without narrowing the complete ABAC-visible set |
| #627 | 2026-08-25 12:35 | preserved valid k6 lifecycle evidence across setup, scenario execution, and teardown |
| #468 | 2026-08-25 08:44 | fast-mlsirm, Keyverse, contextual-orchestrator, and TEPP integration boundaries |
| #493 | 2026-08-25 08:44 | evidence-grounded Event Lineage isolation reasons |
| #600 | 2026-08-25 08:44 | then-current exact-head product/technical baseline |
| #605 | 2026-08-25 08:44 | dialog focus order, evidence readability, and OIDC return-context restoration |
| #608 | 2026-08-25 08:43 | Naruon projection consumed by Workspace Calendar |
| #603 | 2026-08-25 07:24 | short analysis-run transactions, session advisory locking, package-marker/privacy repair, and provider-work lease release |
| #602 | 2026-08-25 07:24 | post-detail modal semantics, Escape close, initial focus, and opener restoration; navigation-refocus edge case continues on #605 |
| #582 | 2026-08-25 07:24 | bounded batched cited-lineage graph fetch |
| #588 | 2026-08-25 07:23 | named two-axis leftover-map reconstruction and raw-residual identity |
| #482 | 2026-08-25 07:03 | corroborated SKOS companion organization chips; regressions subsequently tracked above |
| #601 | 2026-08-25 06:38 | APA 7th PROV-O and PROV-DM references for ADRs 0011 and 0065 |
| #595 | 2026-08-25 04:39 | audited no-draft import door, nullable updated-at fallback, and event-time import |
| #484 | 2026-08-25 04:39 | Allen interval relations with deferred FK validation |
| #383 | 2026-08-25 04:39 | reader-safe OTel diagnostics and service-peer-bounded session metadata |
| #599 | 2026-08-25 04:28 | raw-residual leftover-map cross-share identity aligned without arbitrary weighting |
| #598 | 2026-08-25 03:32 | 5W1H roles/events remain readable across a stale summary contract version |
| #597 | 2026-08-25 03:32 | related posts open Customer Master detail in place without stale graph state |
| #591 | 2026-08-25 03:32 | prior exact-head product-gap baseline snapshot |
| #584 | 2026-08-25 03:32 | TEPP topic-lineage consumption boundary grounded in cited temporal models |
| #581 | 2026-08-25 03:32 | relative-time Ask filtering bound to event time |
| #596 | 2026-08-25 03:27 | hierarchy/name-resolution deep-work timeouts aligned at 600 seconds |
| #585 | 2026-08-25 03:27 | raw Global Ask transport exceptions replaced by bounded client-safe detail |
| #355 | 2026-08-25 02:38 | Naruon calendar projection contract and conformance fixture |
| #562 | 2026-08-24 02:05 | parameter-free classic RRF; deleted the last hand-picked fused score |
| #561 | 2026-08-24 01:47 | knowledge-graph precedence/hierarchy relation classification and layout order |
| #555 | 2026-08-24 01:29 | per-channel score breakdown persisted on `post_lineage_edge.channel_scores` (ADR 0195) |
| #559 | 2026-08-24 01:26 | deleted `DEFAULT_CHANNEL_WEIGHTS` hand-picked fallback |
| #549 | 2026-08-24 00:43 | clamped embedding cosine into `[0, 1]` instead of remapping from `[-1, 1]` (ADR 0190) |
| #548 | 2026-08-24 00:37 | mid-reconstruction provider failure maps to an explicit unavailable state |
| #544 | 2026-08-24 00:27 | fusion weights accepted only via fast-mlsirm estimation |
| #538 | 2026-08-23 23:39 | real embeddings wired into the Event Lineage text channel |

This documentation is owned by protected `main` again: the #426 stack landed,
so hidden-stack merges (#494, #497, #499, #505, #509 into unprotected parent
branches) are historical context only and no longer gate anything.

The current protected-`main` and exact #507 trees are clean of the private
runtime source-table identifier present in the closed #506 head and older
public history. Do not reproduce or hint at its value. Historical remediation
requires the ADR 0001 incident process and security/privacy-owner coordination;
never force-push or delete evidence ad hoc.

The former central caller PRs ContextualWisdomLab/.github#1259 and #1288 both
closed without merge and therefore are not scheduler evidence. PR #1380 merged
normally at head `9ffd7bec`: its `4 * * * *` caller performs one bounded
OpenCode/contextual-orchestrator PR review-and-repair dispatch without
`COPILOT_GITHUB_TOKEN`, and the two-hour unchanged-head retry prevents overlap
with multi-hour workers. It does not discover or implement product gaps.
LineageWeave still lacks the explicit commercial-development entrypoint marker,
and the latest central coordinator failed closed before repository inventory
because `PR_REVIEW_MERGE_TOKEN` was absent. Autonomous hourly product
development therefore remains unavailable; no credential or repository opt-in
is inferred or added here.
ContextualWisdomLab/.github#1258 merged at exact head `897819c4` to
repair the pnpm/coverage-evidence workflow; newly created exact PR heads must
still prove the runtime behavior because merged workflow source alone is not
check evidence.

Figma design-system boundary (ADR 0002): File ID `1Su3lDRmiZdcUs47t1QwIX`.
The sanitized file now contains synthetic Event Lineage desktop (`5:14`) and
mobile (`5:15`) frames with graph direction, event dates, an inference
boundary, and exact fused-score evidence. Do not copy source-organization
content into this repository. Storybook remains the executable scene and
edge-case inventory for repeated web objects; rendered code-to-Figma parity
still requires same-viewport browser comparison on an exact candidate head.

## 2. User-visible capability baseline

Substantially present on protected `main`:

- PostgreSQL-backed import, normalized provenance, cutoff-aware analysis runs,
  source revisions, lineage reconstruction, and explicit unavailable states.
- Authenticated workspace navigation, post detail, localized summaries, 5W1H,
  R&R/Keyman, evidence citations, chat, organization hierarchy, and lineage DAG
  (`frontend/src/LineageDag.tsx` is on `main`; the old “DAG view missing”
  baseline entry is stale).
- Semantic paragraph/list/table/image-region units that preserve the source
  representation and provenance instead of flattening it into one body string.
- FJA→I/O-Psychology semantic layer (ADR 0251): the published DOT/FJA
  Data/People/Things worker functions (ADR 0232) project into disjoint
  cognitive, affective, and behavioral constructs with APA 7th anchors,
  SHACL validation, and a deterministic typed read model
  (`lineageweave/iopsy_taxonomy.py`); no fitted weight or O*NET/ADR 0248
  crosswalk is asserted (ADR 0145).
- Contextual-orchestrator boundaries for adjudication, extraction, summaries,
  chat, embeddings, and VISION; null channels remain unavailable and are
  dropped from score fusion.
- W3C PROV-O projection through normalized provenance tables, with the
  knowledge graph retained as an explicit navigation projection.
- Keyverse/Keycloak OIDC, RankWeave fusion port, TEPP measurement client,
  ThreadWeave tree assembly.

These statements describe source capability, not authenticated production
corpus acceptance or protected release.

## 3. Historical open-PR inventory (superseded by §1)

Heads below are queue evidence captured at snapshot time; recheck SHA,
checks, unresolved threads, and independent approval immediately before any
merge claim. Do not self-approve, force-push, or transfer stale review
evidence across heads. The org merge scheduler merges only when
`reviewDecision == APPROVED` on the exact head and Strix evidence is complete.

### 3.0 Shared systemic gate

| Gate | Evidence | Durable repair |
| --- | --- | --- |
| Strix provider unavailability | `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` and `openai-direct/gpt-5.6-luna` failed authoritatively across unrelated heads | ContextualWisdomLab/.github#1263 at `ab3d7645` proposes executable Azure/cross-provider fallbacks but remains open/conflicting; repair that branch without weakening the required gate |
| ADR 0109 login repair debt | Eight branches cut from the pre-repair base carried the unauthenticated `AdminPanel` + unused-OIDC-helper `tsc -b` failure | Same verified two-line repair applied to #521, #522, #552, #553, #554, #556, #558, #560 during this loop; frontend lint/test/build verified locally |

### 3.1 Workspace root and product surfaces

| PR | Head | Intent | Notes |
| ---: | --- | --- | --- |
| #258 | `f0b5234d` | Workspace evidence board and source-grounded ontology surface (root stack) | Largest surface; historical CHANGES_REQUESTED is stale relative to current head |
| #349 | `bef4a858` | Bounded ontology and provenance explorer (v2.13.0) | Issue #341 |
| #355 | `2f3f308c` | Naruon event projection contract | Issues #336/#338 |
| #387 | `5ef0f2e6` | Persist and explain Event Lineage channel evidence | Issue #274 |
| #405 | `ec62d9f0` | Persisted image-region locations (v2.12.8) | VISION region provenance |
| #484 | `878c4a87` | Allen interval relations on Event Lineage edges (v2.15.0) | Temporal modeling; Allen (1983) |
| #490 | `d0cad030` | Wire remaining ADR 0133–0137 surfaces | Consolidated product stack incl. Knowledge Graph token repair |
| #493 | `499c8b1b` | Name Event Lineage isolation reasons (v2.16.0) | Honest unavailable/failed states |

### 3.2 SKOS organization aliases and leftover-map family (stacked)

| PR | Head | Intent |
| ---: | --- | --- |
| #480 | `f18b421d` | Bind corroborated SKOS org aliases to one catalog row |
| #482 | `c38c08d6` | Corroborated SKOS companion caption on organization chips (v2.14.0) |
| #481 | `32944979` | Persist leftover interaction-map coordinates (v2.12.7) |
| #485 | `dcaa6320` | Leftover pair clicks land on the named Post quality criterion (v2.12.8) |
| #518 | `3117823f` | Name leftover complete-case coverage (v2.12.17) |
| #519 | `31c150c8` | Persist leftover-map axis share on period reports (v2.12.16) |
| #521 | `40677c75` | Leftover pairs on the grouping comparison strip (v2.12.17) |
| #522 | `9be3712e` | Leftover-map distances on two Gabriel axes (v2.12.18) |
| #535 | `1fb5d69a` | Name leftover-map unexplained leftover (v2.12.26) |
| #537 | `9a639554` | Name leftover-map unexplained share (v2.12.27) |
| #539 | `740629d0` | Name leftover-map explained share (v2.12.28) |
| #563 | `740d50f3` | Name leftover-map cross share (v2.12.29) |
| #564 | `ac5de72a` | Name leftover-map reconstruction share (v2.12.30) |

The leftover-map naming series (#518–#564) is a stacked ladder of honest
leftover-pair labeling increments; merge in ascending order once each exact
head clears gates.

### 3.3 Repairs and operability

| PR | Head | Intent |
| ---: | --- | --- |
| #393 | `4ddd3a83` | Detach provider parse error context (honest orchestrator failure) |
| #394 | `cf9505b7` | Preserve source indentation evidence for adjudication |
| #434 | `01d6cca5` | Wire adjudication client into corpus-wide rebuild (issue #289) |
| #541 | `3d93ea9b` | Bootstrap repo-root sys.path in operator scripts |
| #546 | `d210c20c` | Strip Keycloak OIDC callback params from post share links |
| #547 | `fb7fe2db` | Shorten orchestrator healthcheck retry budget |
| #552 | `89000280` | Footer text contrast passes WCAG 1.4.3 AA |
| #553 | `e5152f5c` | `.post-meta` contrast in both themes |
| #554 | `689e42e4` | Event Lineage DAG node marks get a 24×24 px hit target |
| #556 | `21cf9991` | Citation chip grows to a 24px touch target |
| #558 | `91dd1bfc` | Bare loading text exposed as live regions |
| #560 | `59b769e3` | Secondary details/summary toggles sized to `--size-control-min` |

### 3.4 Integration and measurement boundary

| PR | Head | Intent |
| ---: | --- | --- |
| #417 | `cb08377c` | TEPP topic-lineage consumption boundary (TRSL-TM + CHRONOS/TDT) ADR |
| #468 | `228f13dd` | Bind fast-mlsirm, Keyverse, orchestrator, and TEPP integration tests |
| #258-family measurement note | — | GRM/GPCM/CAT/FIPC parameter recovery (#451–#454) landed earlier; true-parameter RMSE remains the acceptance bar |

### 3.5 Documentation

| PR | Intent |
| ---: | --- |
| #565 | Sync AGENTS.md / CLAUDE.md with accepted ADR boundaries |
| this file | Non-identifying gap baseline refresh (ADR 0001) |

Closed as superseded during this loop: #368 (baseline rewrite superseded by
this file per §3.5 of the prior snapshot).

## 4. Open issues (complete live queue; product acceptance remaining on `main`)

| Issue | User-visible gap | Active PR |
| ---: | --- | --- |
| #79 | Milestone 2: port verified direct-PostgreSQL analysis into the protected architecture | analysis-run registry on `main`; remaining runtime bridge |
| #87 | Milestone 2.1 normalized runtime-analysis schema bridge | related analysis-run work |
| #269 | Authenticated Global Ask MCP browser-safe and admission-bounded | Ask stack |
| #271 | Evidence-honest knowledge-cutoff scope on Global Ask | #658; still open and not protected-main evidence |
| #272 | Verify Global Ask KG/ontology/semantic claims with public SearXNG evidence | #632 preserves internal provenance; public verification acceptance remains open |
| #277 | TEPP: persist accepted receipts, poll completed results, keep measurement authority distinct | #657 consumer lifecycle; executable producer route remains unavailable |
| #280 | Full project-lifecycle history and handover intervals | #640 adds case/project journeys and #663 adds evidence-backed Project exploration; authoritative lifecycle reconciliation remains #284 |
| #284 | Authoritative lifecycle ingestion and idempotent reconciliation | No active delivery PR confirmed |
| #338 | Evidence-bounded email/project lineage contract for Naruon consumption | #704 recreates the provider-side contract on current `main` without arbitrary fusion weights; #343 remains only a non-default-stack merge and #355 is a distinct calendar contract |
| #611 | Decompose closed PR #490 ADR 0133–0137 evidence without transferring stale branch state | #631 supplies the current-main inventory only; focused implementation PRs and tests for every unmet criterion are still required |

## 5. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | 12 open PRs at snapshot, all targeting `main` with normal auto-merge enabled. None has the required independent approval, and running checks on #631/#632/#663 are not treated as blockers for safe work on other PRs. #666's merge into the non-default #663 branch is not protected-main delivery | Terminal exact-head checks, no unresolved threads, two independent approvals including last-push approval, protected squash-merge SHA |
| Orchestrator admission and readiness | The pinned `c2571264` orchestrator is healthy and contains the configured-endpoint contract plus the corrected JSON-object discovery probe. The exact `51ab4616` Ask worker used that boundary to persist a non-empty answer with Post/Event citations; no local provider selection or retry heuristic was added. | Complete the upstream protected gate, repin the eventual protected commit without changing the endpoint-neutral LineageWeave contract, and repeat MCP plus wider authorized-corpus acceptance. |
| CI queue release latency | Two Tests runs for already merged PRs occupied the available runner slots while 54 newer runs remained queued. Manual cancellation released the stale work, but the central close workflow was itself queued behind those runs. #634 merged into #631's non-default branch and reuses the repository's existing per-PR concurrency group so a jobless close event can cancel obsolete Tests work before runner allocation; this is not protected-main delivery | Merge #631 through its refreshed protected gate; close a synthetic PR while its Tests run is active and verify the old run becomes cancelled, the close-event jobs remain skipped, and a newer exact-head run starts without manual intervention |
| Evidence-grounded operations workspace | Protected-main #614 delivers governed semantic Ask, live Similar VOC, disjoint pending/failed analysis metrics, full Storybook state inventory, and current desktop/mobile screenshot evidence. Authorized-corpus backfill acceptance remains unavailable | Perform authenticated authorized-corpus acceptance with aggregate evidence and retain fail-closed no-match behavior |
| Shared frontend gate | The ADR 0109 login repair is on protected `main`; eight older branches carried the defect and received the same verified repair this loop (#521–#560) | Keep every future branch cut from post-repair bases; re-verify with frontend lint/test/build before push |
| Identifying baseline regression | `main` gap file listed real post identifiers; separately, closed #506 and pre-existing public history contain a private runtime source-table identifier, while current `main` and #507 trees are clean | Land this non-identifying rewrite, then coordinate ADR 0001 history remediation with security/privacy owners; do not reproduce the value, force-push, or delete evidence ad hoc |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Concurrent web responsiveness | ADR 0204 releases pooled transactions during provider work, and the synthetic Compose boundary has an authenticated k6 E2E harness for Ask enqueue, concurrent reads, and job polling. PR #633's measured landing-query and event-loop work merged into open parent #629 rather than protected `main`; its aggregate observation improved 25-VU throughput but did not establish a latency SLO. The current exact #629 also persists each completed relation verification before propagating a later provider failure | Land #629 through its refreshed protected gate, rebuild that exact-head application image, and repeat `make load-http` with declared environment concurrency/window and retained raw distributions/resource configuration; set no SLO until representative capacity evidence is approved |
| Test broker isolation | Backend integration tests use Valkey database 15 and clear only that database at session boundaries. At the current exact-head runtime check, canonical database 0 retained two pre-existing post-content stream entries while the broad worker stayed stopped; the Ask-only worker neither consumed nor expanded that stream. | Keep runtime and test broker databases distinct; record pre/post stream length for integration acceptance and never restart or drain a production backfill as part of a test. Existing production work is not test debris and must not be deleted to manufacture an empty assertion. |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419), but current runtime acceptance has not yet proved table-image structure, complete region coverage, or summary/image readiness together | Orchestrator-backed rendered workflow, original/derived asset provenance, region-before-OCR processing, and honest unsupported states; reconcile ADR 0052's image-bearing summary readiness with ADR 0098 before changing sequencing |
| Semantic source rendering | Paragraph, table, list, formula, and indentation work exists across stacks (#394, #427, #448–#450); #515 adds synthetic backend/frontend parity for deterministic rows/cells, footnote boundaries, and encoded scripts | Land the #427 → #515 stack, then gather authenticated browser evidence that list nesting, continuation alignment, and formula units render without authoring-layout artifacts |
| Event and project semantics | #663 is the largest current user-visible gap slice: evidence-backed Project nodes, bounded traversal, cutoff/snapshot fencing, exact-value table parity, and localized graph labels. Focus visibility, label-bound, and temporal test-double regressions are repaired. #666's heuristic removal is composed into this parent but is not separately protected-main evidence. #640 now has aggregate authenticated proof that explicit source project fields produce project-bearing case rollups and render one matching journey event. Three normalized membership rows exist separately; rollup rows are not relabeled as memberships, and no authoritative lifecycle status is claimed. | Combined #663 must pass exact-head checks and independent approval before protected merge. Authenticated acceptance must still prove handover intervals and authoritative lifecycle reconciliation without promoting co-occurrence. |
| Voice primary history | Protected `main` `bbb19192` includes ADR 0252 / #761 (migration 0243, GiST primary-period exclusion, `clock_timestamp()` after the source-row lock, API/ontology half-open cutoff SQL). v2.22.1 adds synthetic PostgreSQL integration tests for A → B → A at before/between/after cutoffs, concurrent primary updates, additional-assignment close, and 0237→0243 trigger replay. This is not yet protected-main evidence | Land the live-test slice through the protected gate with independent exact-head APPROVE; close #748 only after that protected delivery |
| Knowledge Graph readability | #659 recreates the token-backed node-type repair on current `main`, including regression coverage; it is open and therefore not protected-main evidence | Merge #659 normally, then verify light/dark contrast, keyboard graph navigation, full labels, and evidence tables in the authenticated rendered surface |
| Product semantic identity | ADR 0228 and migration 0251 define normalized product group/model/variant/trade-item identities, scoped GTIN/MPN keys, and fail-closed unique/tie/missing/unavailable resolution. The governed provisioning candidate adds an add-only admin contract with explicit product code/label, authorized source-system record, server-calculated digest, and alias-level source evidence; `CatalogProductShape` validates stable code/label/level/parent projection, and unique Post results expose the same catalog id/code/IRI. It never creates identity from model output, keywords, fuzzy similarity, or `기타`. **Implemented and runtime-verified read foundation:** replay-safe migration 0272 is applied in canonical Compose, and the Post API hides every historical unreceipted analysis row; the current authorized read returned zero Product evidence. **Missing/unverified production:** the canonical worker predates the independent receipt-bearing Product stage, receipt-bearing completions remain zero, and the admitted bounded page is unsettled. Existing unreceipted rows are retry eligibility evidence, not completed analyses or corpus prevalence. Exact upstream `기타` category presence remains unavailable because no SOURCE DSN was configured in the observed runtime. Protected delivery, bounded retry settlement, aggregate relation coverage, and authenticated non-empty rendered acceptance remain unproven. | Pass #895's worker probe gate and PR #640's protected checks/review, deploy the exact worker only after the active page settles, then run a separately authorized bounded retry and retain only aggregate unique/missing/tie/unavailable and relation coverage plus authenticated desktop/mobile evidence. |
| Voice semantic taxonomy | ADRs 0244/0246 and migrations 0230/0235 preserve the twelve-value source-post scheme separately from the six-value post-scoped organization relationship scheme, retain source/derived disagreement and multi-membership, and provide authorized overlap-aware aggregate filters. **Implemented and runtime-verified read foundation:** PR #640's replay-safe migration 0271 is applied in canonical Compose; the authenticated summary admitted 43,162 source-classified Posts and reported zero derived completions, assertions, disagreements, or unavailable rows. **Missing/unverified production:** the canonical worker predates the strict receipt-bearing Voice stage, so the producer is not deployed and no private-corpus accuracy or derived-coverage result is claimed. The branch producer accepts only exact focal-body spans, requires an orchestrator response receipt, records successful empty analysis separately, and runs independently of operations-case failure. | Pass #895's worker probe gate and PR #640's protected checks/review, deploy the exact worker only after the active page settles, then run a separately authorized bounded retry and verify aggregate-only source/derived/disagreement/unavailable counts at one declared cutoff without exposing record identities. |
| Source-code lookup UX | Source state/detail codes remain evidence-bearing machine values and current detail presentation is dense | Catalog-backed display labels with raw-code provenance, compact 5W1H/source-detail hierarchy, keyboard access, and no unsupported customer/project binding |
| Calendar / Naruon | #355 delivered the projection contract; v2.17.0 wires operator consumption without forwarding the end-user token. Naruon producer, provider/consumer fixtures, and protected merge remain open (#336) | Verify observed events against the published schema without invented events; keep commitments available when the channel is unwired |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | Durable accepted TEPP receipts and LineageWeave #614's exact accepted snapshot/cutoff/run/pair-count consumer are protected; TEPP #237 remains open, so no registered producer artifact exists yet. #387 removes inferred/default persistence weights, but several older reconstruction tests still pass hand-authored numeric dictionaries that are not estimator evidence | Land TEPP #237 through its protected gate, then replace remaining reconstruction-test constants with provenance-bearing fast-mlsirm estimates over synthetic fixtures. Retain true-parameter RMSE recovery as the acceptance bar |
| Asynchronous authorization | Protected `main` rebuilds Global Ask worker scope after the bearer token leaves the request; #468 now persists exact Keyverse organization/process-unit scope in 3NF child tables and intersects it with current affiliations | Land #468 through the protected gate; prove a second affiliation and a revoked process unit cannot widen delayed-job evidence |
| Planned-facility intent | Planned-facility relationship intent remains only on closed, unmerged #490; earlier stack-only merges were not protected delivery | Recreate the evidence-backed slice on a current base and land through protected `main` before a release claim |
| Accessibility and responsive UX | #602 delivered base post-detail modal semantics; #605 adds selected-post refocus, collapsed/hidden/inert/CSS-invisible focus exclusion across both modal types, readable evidence separators, focused tests, and desktop/mobile Storybook screenshots | Land #605 through the protected gate, then complete screen-reader and authenticated Playwright acceptance on the exact release head |
| Design tokens and repeated objects | Token extraction started; sanitized Figma Event Lineage desktop/mobile frames exist, while other repeated product surfaces remain incomplete | Tokens in CSS + Storybook stories for board, popup, DAG, Ask, calendar, forms, charts; same-viewport Figma/runtime visual comparison before release |
| Frontend delivery performance | #644 implements a native dynamic-import boundary for conditional workspace surfaces and retains accessible loading/error states; exact-head checks passed but the PR is not protected-main evidence | Merge #644 normally, rebuild the protected-main production bundle, and retain the measured chunk inventory rather than raising the warning limit |
| Authenticated read latency | ADR 0272 sets a product-owner-approved 20 ms maximum for every REST `GET` and MCP read, including authorization, database work, projection, serialization, and negotiated transfer. The Dashboard candidate separates exact authorized summary/lifecycle rollups from a stable keyset page of evidence-rich cases. On the 43,189-record runtime, the default 20-Post database page measured 2.736–3.094 ms warm, and an unrelated locale write now refreshes zero authored projections in 2.240 ms. PR #640 splits six broad-search signals into independently indexed branches while preserving exact membership and ranking: the aggregate database benchmark improved from 169.072 ms to 21.059 ms. An ID-only deduplication alternative regressed to 2,968.787 ms cold and 389.114–410.306 ms warm and was rejected. Sequential warm authenticated reads reached 4.707–13.374 ms, but the exact `e339e543` k6 harness now gates search separately and still fails under one VU's concurrent read batch: Post search averaged 102.74 ms (max 213.60), Dashboard 46.75 ms (max 93.60), Posts 51.40 ms (max 97.01), and Lineage 22.58 ms (max 31.88). PR #888 remains deliberately inactive and fail-closed: its five-way authenticated k6 observations recorded maxima from 48.280 to 127.320 ms across measured CPU profiles, disproving rather than satisfying the unchanged 20 ms gate. A later isolated full-snapshot profile verified that the native request path already uses Uvicorn 0.52.1 with uvloop 0.22.1 and httptools 0.8.0. The first cold Post search spent 87.24 ms of 89.20 ms in database work and then warmed to 11.89 ms total. Under five VUs, an approximately 78 ms cyclic-GC pause coincided with approximately 78 ms of event-loop lag, but a profiler-free GC-off authenticated k6 still failed every route maximum: 146.83 ms Posts, 216.23 ms Post search, 146.97 ms Lineage, 164.01 ms Dashboard, and 73.15 ms Ask poll across 6,875 accepted reads with no response failure. GC-off remained a discarded experiment; no production runtime or configuration changed. A later exact Dashboard-to-Project-History candidate, run in a host process against the same authorized aggregate runtime, kept every response accepted and the selected focus intact but still failed the unchanged threshold: the first accepted Dashboard/Project History reads measured 9.59/79.70 ms, and a warm five-VU, 25-journey run measured maxima of 38.05/173.52 ms across 50 accepted reads. Its Project History event-candidate plan rejected 43,188 rows in a corpus scan; the exact NFKC identity-indexed union retained ordered-row parity and reduced that statement from 24.267 ms average / 37.322 ms maximum to 0.761 / 2.495 ms. After that root fix, three independent fresh-backend five-VU series kept all 303 authenticated Dashboard and Project History reads accepted with focus intact: Dashboard maxima were 12.36, 11.86, and 12.62 ms; Project History maxima were 11.44, 11.28, and 13.87 ms. Review then removed display-name candidates so only explicit source/semantic keys admit an event; a fourth fresh five-VU series kept its 101 authenticated reads accepted and measured 13.41 ms Dashboard / 12.91 ms Project History maxima. This proves the selected Dashboard-to-History path only, not every REST/MCP read or #888 activation. Exact image head `c4d13aaab` then negotiated gzip from 96,415 to 10,282 complete wire bytes; five VUs accepted 3,207 Dashboard reads at 14.75 ms average and 84.79 ms maximum. That transfer optimization does not satisfy the unchanged maximum. Migration replay dropped from 60.70 s to 41.25 s after existing trigger-maintained projections stopped being rewritten; other replay work remains. The 20 ms contract is not met for Dashboard or all reads. | Keep #888 inactive and the all-read SLO gap open. Retain the exact indexed Project History candidate path and negotiated-compression assertion; treat native-parser replacement, cyclic-GC disablement, and extra worker processes as rejected fixes. Profile and remove the remaining route tails, then rerun authenticated k6 across every REST/MCP read without raising the limit or weakening exact results. |
| External integrations | Search, Zotero, calendar, Keyverse, orchestrator, RankWeave, ThreadWeave, TEPP, DiskSage, wardnet | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| Naruon email/project lineage | #704 provides a strict store-agnostic v1 contract, opaque evidence references, observed/inferred truth separation, knowledge-cutoff admission, and explicit unavailable states. Inferred edges require an injected provenance-bearing fast-mlsirm estimate; no local default weight exists | Merge #704 through protected `main`, publish an immutable attested artifact, then enable the Naruon consumer only against that released version and its contract fixtures |
| MSA / modular reuse | LineageWeave must run standalone and as a consumer of org packages | Do not reimplement RankWeave/TEPP/orchestrator/ThreadWeave/Keyverse; fix upstream and PR there |
| Accelerator runtime ownership | ADR 0076/0208 already prohibit local model and mathematical ownership; ADR 0237 now defines MLX as a native orchestrator-side service and TEPP/fast-mlsirm CUDA/OpenCL/CPU profiles as scientific-compute-owner deployments, so LineageWeave Compose remains device-neutral. RankWeave remains the dependency-free Python retrieval-fusion/evaluation owner behind its published contract | TEPP and fast-mlsirm must publish deterministic CPU recovery plus conformance evidence for every advertised CUDA/OpenCL profile; contextual-orchestrator must prove native MLX availability through its provider-neutral health/contract boundary. LineageWeave accepts only versioned, provenance-bearing envelopes and fails closed when the owner is unavailable |
| Product contract authority | The current LineageWeave PRD records exact-case ecosystem authorities. TEPP, fast-mlsirm, keyverse, ThreadWeave, and RankWeave PR #41 have standalone PRDs; RankWeave's remains unmerged. contextual-orchestrator, disksage, and wardnet still rely on product/architecture documents, and naruon has only a scoped Topic Intelligence PRD | Keep ADRs normative, preserve canonical repository case in machine references, land the pending PRDs, and add standalone PRDs in each remaining owning repository before cross-product release claims exceed its documented boundary |
| Release quality | PR #660 is now on protected `main`; its pre-merge full Python suite passed 1,352 tests with 17 skips, but release-wide frontend, Storybook, security, browser, and runtime acceptance remain unproven on one exact protected head | Repository-wide coverage, docstrings, Storybook, security, browser, and release evidence on one exact head |
| PII | Masking would paralyze the product; ADR 0001 forbids identifying artifacts in git | ABAC + authorized runtime; synthetic fixtures in git; no mask-in-place that drops names the operator must read |
| Database | PostgreSQL, 3NF, snake_case ≥ two words, hot-partition and lock policy | No file DBs; read/write split if lock management fails; whitelist every migration |

### 5.1 Closed PR #490 decomposition (issue #611)

Protected `main` at `04e6b610` and the three open PRs present during the initial
decomposition were rechecked; the later audit snapshot above includes #631
itself as the fourth open PR. Protected `main` contains none of PR #490. That PR remains
closed, unmerged branch evidence; its ADR 0133–0137 files are not normative and
its 321-file tree must not be replayed. Current-main code and schema searches
give this delivery matrix:

| Closed-branch decision | Current-main classification | Smallest remaining delivery |
| --- | --- | --- |
| ADR 0133 source-reference research | Partial foundation: protected `main` has the self-hosted SearXNG relation-verification client and fail-closed configuration, but it verifies an already extracted relation. It has no source-unit/image-region lead, cited-resource retrieval, claim judgment, or normalized research citation workflow | One post-scoped lead-to-citation slice that reuses the self-hosted SearXNG search boundary, adds public-target SSRF/redirect rejection for result retrieval, and judges through contextual-orchestrator with explicit unavailable outcomes |
| ADR 0134 token-backed exception messages | Partial: sanitized next-action failures exist, but no shared token-backed exception component or complete Storybook error inventory exists | Migrate one existing unavailable flow to one shared accessible alert and verify its success, unavailable, and retry states |
| ADR 0135 kind/status-exact analysis actions | Partial: protected `main` has kind-aware start/retry controls plus normative analysis-run, TEPP, cutoff-body, and channel-evidence contracts; it does not contain the closed branch's unified guidance component or its full kind × status interaction inventory | Test the current run-kind/status matrix first, then add only a proven missing state/control pair rather than copying the closed-branch function |
| ADR 0136 per-post Ask history | Partial: `post_chat_result` / `post_chat_citation`, the authorized post Chat API, and its linear exchange history are on protected `main`. Account-and-post-scoped sessions, ordered turns, list/select/new controls, and batched citation reauthorization are not | Define the 3NF account/post session boundary, bounded batch reauthorization, and one authorized list/load/write path before adding the conversation picker |
| ADR 0137 cross-post customer identity | Partial foundation: protected `main` preserves source customer hints and has corporate-catalog unique/miss/tie safeguards, but it has no normalized cross-post customer-identity judgment, supporting-post binding, or corporate-name-history workflow | Add only after external corroboration, orchestrator judgment, TEPP ordering, and unique-catalog fail-close can be verified together; never promote a one-post hint |

This matrix satisfies only #611's current-main inventory step. Issue #611
remains open: every unmet criterion above still needs a focused regression test
and exact-head current-main implementation PR before its acceptance criteria
are satisfied. No stale check, review, or implementation is transferred from
#490.

## 6. UI-UX acceptance inventory (must be defined, reviewed, applied, audited)

Each item needs a Storybook scene, an edge-case story, and an automated check
before a commercial release claim. Figma File ID `1Su3lDRmiZdcUs47t1QwIX`.

| Dimension | Current | Gap |
| --- | --- | --- |
| Accessibility | Partial labels/roles on board, popup, login | WCAG 2.2 AA on login, board, popup, Ask, calendar, admin; focus order; live regions |
| Touch & Interaction | Click-first popup and lists | 44px targets, swipe/escape to dismiss popup, no hover-only actions |
| Performance | Board caps and hint render limits exist | Interaction-to-next-paint on board search, DAG, Ask; no N+1 (#358) |
| Style Selection | Korean UI standards merged (#347) | Tokenized light/dark; Anti-Slop-UI density; no decorative noise |
| Layout & Responsive | Desktop popup shell | 402px-class phone layout; stacked GNB; readable DAG |
| Typography & Color | Badge tokens extracted | Contrast on badges, links, error/status; no raw hex in components |
| Animation | Minimal | Reduced-motion; no blocking animation on evidence open |
| Forms & Feedback | Login, Ask, tickets, admin brand | Inline validation, next-action copy, unavailable vs failed distinction |
| Navigation Patterns | Board / customers / calendar / Ask / admin | Deep-link post + OIDC return URL (#426); bookmarkable Ask |
| Charts & Data | Period reports, leftover pairs, Rankings, DAG | Honest empty/unavailable; no invented theta; Storybook chart states |

## 7. Ecosystem leverage order

Reuse before rebuild. Consume these ContextualWisdomLab packages in this order
of leverage; open connector PRs there when the defect is upstream:

1. **contextual-orchestrator** — every LLM/VISION/embedding call (Fugu / Conductor / TRINITY routing). Never a raw provider SDK.
2. **Keyverse** — OIDC issuer, JWKS, tenant principals.
3. **RankWeave** — fused scores and rankings; never invent a fused score or theta.
4. **TEPP** — calibrated measurement; persist receipts; no local reimplementation.
5. **fast-mlsirm** — GRM/GPCM/CAT/FIPC recovery tests (#451–#454) must stay true-parameter RMSE.
6. **ThreadWeave** — tree assembly.
7. **Naruon** — calendar and email/project lineage projection (#336, #338, #355).
8. **DiskSage / wardnet** — storage and network policy as needed.
9. **ContextualWisdomLab/.github** — required review workflows (OpenCode, Strix, Noema) and merged bounded hourly PR review/repair (#1380). This does not replace a commercial product-gap coordinator. If stacked PRs miss central review or coverage-evidence fails on pnpm 9 (`--trust-lockfile` is pnpm 11.3) or a missing Vitest coverage provider, fix the org workflow (#1258), not a local bypass.

## 8. Public ontology publication boundary

- PR #426 publishes fragment-addressable HTML, byte-identical Turtle,
  isomorphic JSON-LD and N-Triples, the PROV-O support profile, and a
  source-digest manifest from the authoritative ontology.
- Pull requests validate only. Only protected `main` may publish, and the
  generated-directory marker, linked-IRI, duplicate-fragment, symlink, and
  source-overlap checks fail closed.
- The lowercase knowledge-graph namespace and repository-case support-profile
  namespace remain distinct until issue #372 delivers a versioned migration
  and compatibility decision; this publication PR rewrites neither identity.
- Until the protected deployment and exact URL checks succeed, the public
  ontology endpoint remains unavailable and must not be represented as live.

## 9. Evidence boundaries

- Never add a real record, title, name, identifier, screenshot, log, benchmark
  artifact, or documentation example to this repository.
- Attendance or co-occurrence is not responsibility, project, customer, or
  affiliation evidence. Preserve uncertainty and provenance.
- Missing transport, model capability, accepted envelope, or persistence is
  unavailable or failed evidence, never a placeholder result.
- Local green tests, bot statuses, auto-merge, and warning-only checks do not
  prove a protected merge.
- Re-fetch base/head SHAs, checks, review threads, approvals, rulesets, and the
  merge SHA immediately before any lifecycle claim.
- Do not self-approve. Independent OpenCode / Strix / Noema review is required.
- Do not force-push. Do not treat GitHub Checks duration as a blocker; repair
  the failing check instead.
- `COPILOT_GITHUB_TOKEN` is not used.

## 10. Next acceptance loop (autonomous merge order)

Process every open PR in ascending number order, considering leverage; for
each: check reviews → repair → re-verify Checks → merge → continue. Checks and
review latency are never blockers — keep working while they settle.

1. Revalidate Strix after merged ContextualWisdomLab/.github#1320, reconcile
   open .github#1263, and verify open .github#1380 only as bounded hourly PR
   review/repair through its protected gates. Keep commercial product-gap
   development unavailable until a local manual opt-in entrypoint and the
   central coordinator's maintainer mutation credential are independently
   verified; closed-unmerged #1259/#1288 provide no delivery evidence.
2. Process main-targeted PRs #629, #631, #632, #639, #640, #643, #644, #657,
   #658, #659, #660, and #663 only after each exact head shows terminal green
   required checks plus current-head independent approval. Treat #666's
   non-default-branch merge only as part of #663's combined candidate and
   collect all protected evidence on #663's exact head.
3. While hosted checks or independent reviews wait, resume user-visible gaps
   from §5 in leverage order:
   external semantic verification (#272), Naruon calendar (#355/#336), and
   authenticated operations/ontology publication acceptance. Event Lineage
   evidence shipped in merged PR #387 and closed issue #274 is not an open gap.
4. Rename remaining `[Buyer Gap]` issue titles to neutral product-object
   naming per repository convention (no "Buyer" for internal objects).
5. Keep psychometric tests as true-parameter recovery (RMSE); never fixture
   tautologies, invented theta, or hand-authored numeric weights. Remove
   weights from tests that do not exercise fusion; fusion tests must consume
   provenance-bearing fast-mlsirm estimates over synthetic fixtures.
6. Run frontend lint/test/build/Storybook, backend tests, and authenticated
   browser/accessibility checks on the exact candidate release head.
7. Fix only evidence-backed failures and repeat the protected merge gate.
8. Refresh this file each loop with the exact queue state.

## 11. Spec pointers (derive, do not fork)

- Product/architecture: `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`
- Research grounding: ADR 0084, `docs/lineage-bi-research-notes.md`
- Demo identity: ADR 0001
- Figma boundary: ADR 0002 (File ID `1Su3lDRmiZdcUs47t1QwIX`)
- Orchestrator / paper-grounded models: ADR 0015, ADR 0076 (Fugu, TRINITY, Conductor)
- Ontology / PROV-O / SKOS: ADR 0004, ADR 0011, issue #372
- Analysis runs / TEPP: ADR 0013–0023, issue #79 / #277
- Calendar / Naruon: issues #336 / #338, PR #355, operator consumption v2.17.0
- Ask Agent: issues #269–#272, #358–#363

Citations in doctoring and ADRs use APA 7th. Do not invent a heuristic where
the papers leave the decision undecided.

## 12. Delivery snapshot (2026-08-27)

Fresh merges on protected `main`, verified from PR lifecycle state and
post-merge reruns (not transferable evidence for later heads):

| PR | Delivery | Governing ADR / reference |
| ---: | --- | --- |
| #643 | Shared StatusNotice (ADR 0220): success/unavailable/retry states, WorkspaceCalendar auth-unavailable copy, 5-locale i18n; CI Full suite 22m54s green | ADR 0220 |
| #644 | Native workspace surface split: 9 conditionally rendered components as lazy() dynamic imports behind a SurfaceBoundary error boundary; build emits 9 chunks (1.5-37 kB), main bundle 543 kB; 470 frontend tests, tsc, Storybook green | — |
| #762 | Evidence-bound project history (ADR 0243): /api/projects/{key}/history endpoint, project_history.py projection, fetchProjectHistory client, standalone ProjectHistoryTimeline component; supersedes #668 (3-way merge kept only the additive +2279/-0, dropping the branch's 8k shared-file reverts; popup UI hookup deferred as a scoped follow-up). ADR 0276 successor work admits digest-bound interval evidence only for existing lineage edges; it does not promote time order to a business transition. | ADR 0243, ADR 0276 |
| #763 | Live-PostgreSQL A→B→A Voice history validation (ADR 0252) proving effective_from/effective_to interval replacement across repeated primary-Voice imports | ADR 0252 |
| #764 | Test-only coverage lift: observability 78%→96%, post_summary 77%→89%, claim_verification 86%→99%; package line coverage 93.5%→95% (484→371 missing); 1651 Python tests green | — |
| #761 | Temporal imported-primary Voice history (ADR 0252): migration 0243 (`effective_to` + GiST primary-period exclusion + synchronize trigger), refined 0237 `least()` effective_from backfill, `effective_from/effective_to` dataclass/export + `coalesce($2,$3)` cutoff predicate. Completes the half-shipped main layer that queried `voice.effective_to` against a missing column. CI Full suite 19m13s green | ADR 0252 |
| #629 | Provider work released before embedding pool bound; landing reads bounded (k6-verified concurrency); merged with strix-only infra timeout (Full suite + all other gates green) | — |
| #750 | Leftover-map unexplained leftover share persisted (`report_leftover_map_unexplained_share`, share `s = U² / R²`) | ADR 0233 |
| #749 | Authorized job-family/job-series import snapshots (`0223_authorized_job_architecture`) | ADR 0263 |
| #759 | ***Promoted** the ONET rating-store stack to `main`: migrations 0222/0223, authenticated rating/rating-sources/rating-occupations endpoints, `OccupationRatingProfile` UI + stories, rating client functions, import scripts, ADR 0252–0263 references. Semgrep SQLi nullified by PL/pgSQL `format(%I/%L)` DDL + documented `nosemgrep`; 1583 Python + 447 frontend tests green | ADR 0257–0263 |
| #747 | Current product and MCP manuals (`docs/manuals/*`, contract tests) | ADR 0118-family |
| #754 | Customer-actionable copy and ADR 0237 accelerator runtime boundary; share/bookmark/verification call sites reworded and ko/zh/ja/vi translations completed after review | ADR 0237 |
| #700 | Source conversation-turn evidence ingestion (`0233_source_conversation_turn_evidence`, choke/adjacency resilience) | ADR 0238 |
| #658 | Optional Global Ask knowledge cutoff honoring `source_post_revision` cover | ADR 0216 |
| #632 | Graph-fact source provenance preserved through MCP streaming + verified psql-parity migration fixture | ADR 0166 |
| #742 | Evidence-bound product-operations relations (stack base) | ADR 0235 |
| #743 | Imported occupation-rating source catalog (stack base) | ADR 0260 |
| #745 | Occupation catalog title filter (stack base) | ADR 0262 |
| #746 | Rating-source occupation selector (stack base) | ADR 0261 |
| #740 | Occupation rating evidence view (stack base) | ADR 0259 |
| #720 | Cancel stale test runs on PR close | — |
| #716 | Prioritized evidence-bound operations backfill | — |
| #711 | Pinned validated structured-workflow runtime | — |
| #704 | Current-main external lineage contract publication | — |

The ONET rows stacked into base branches (#743/#745/#746/#740/#732) reached
`main` together through the #759 promotion; their per-base merge records are
historical evidence only. The job-architecture artifact ship originally via
#749 is now re-verified on `main` from the promotion.
