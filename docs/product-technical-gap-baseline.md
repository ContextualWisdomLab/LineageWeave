# Product & Technical Gap Baseline

> Dashboard delivery snapshot: 2026-08-27. Protected `main` was
> `ff7431bd1851c03e737808d22c6a2d43968582f9`. Dashboard PR #640 exact
> observed head is `b3befa8bec8dd2807994444299df7eafdd1c7781`; this branch is not
> protected-main release evidence. The queue contained 35 open PRs (23
> `BLOCKED`, six `UNSTABLE`, four `CLEAN`, and two `UNKNOWN`) and no exact-head
> approval. PR #715
> merged normally into #640 and repaired the four stale HTTP transport test
> doubles plus one Python-before-3.7 Semgrep false positive that contradicted
> the repository's Python >=3.12 contract. PR #722 also merged normally into
> #640, restoring semantic-query and opt-in public-verification factories in
> the dedicated Ask worker and the production-equivalent concurrent-migration
> fixture path. PR #727 merged normally as `353dfd01`, replacing general-reader
> implementation wording with evidence actions. Worker evidence PR #725's
> implementation exact is `40283c9b`; subsequent evidence-only refreshes do not
> change that code and its fresh hosted gates are pending. Storybook follow-up
> #730 merged normally at `b3befa8b` from exact head `c21cac5d`.
> Current #640 required checks are queued and independent approval remains
> absent, so the candidate stays blocked.

## Operations Dashboard PRD/TRD traceability

ADR 0224 reconciles the observed `lw*` test projects with the complete
`lineageweave` Compose boundary. A historical Dashboard candidate exercised
all eight declared services with 27 synthetic posts: live OIDC/JWKS
verification passed, the latest topic-coordinate migration tables were
present, Ask reached `succeeded`, and a 2-VU 20-second authenticated k6
observation completed 162 HTTP requests with zero failures. That run predates
the current #640 head. The canonical containers currently return HTTP 200 from
backend `/healthz` and the frontend root, but their Compose labels do not prove
the source commit; therefore neither the running stack nor the historical k6
run is exact-head authenticated acceptance. Exact-head desktop/mobile
screenshots and k6 remain required after #640 is rebuilt from its current
exact head. Historical test projects are retired only by their exact Compose
project label and without named-volume deletion. PR #678 implementation head
`da98de07` fixes the default project name; its follow-up exact-label audit also
removed the remaining identifiable isolated test containers while preserving
named volumes.

| Requirement | Evidence contract | Delivery state |
|---|---|---|
| Claim cause delay: order, specification change, originating order, sales pool, Event/post counts | ADR 0206; contextual-orchestrator case classification and `claim_received` → `cause_confirmed` milestones with cited spans and observed source clocks | Stacked candidate reports open/resolved/evidence-missing counts and exact elapsed time only for paired observed endpoints; every required answer and endpoint is cited or explicitly missing. Historical synthetic runtime passed, while current exact-head authenticated acceptance and authorized-corpus re-analysis remain pending. |
| Rebid/handover: discussion, counterparties, our owner, decisions, Event/post counts | ADR 0206; normalized case facts plus separate rebid-response and handover milestone pairs | Stacked candidate reports open/resolved/evidence-missing rebid and handover lifecycles without a delay threshold or invented elapsed endpoint. Historical synthetic runtime passed, while current exact-head authenticated acceptance and authorized-corpus re-analysis remain pending. |
| External information count/rate and sales/project relation | ADR 0206; semantic `external_information` classification inside Dashboard GNB | Candidate GNB destination filters the Dashboard to external evidence; no separate Board by product decision. Historical synthetic runtime returned the honest zero-result state; current exact-head authenticated acceptance remains pending. |
| Project-specific journey | Explicit source/semantic project membership plus provenance-bearing TEPP TDT/CHRONOS predecessor, branch, and transition results | Candidate API preserves every explicit project membership, but its local event-time sort is only an observed-event list. It is no longer labeled as a Project Journey. Full journey delivery remains open until the accepted TEPP producer artifact is persisted and rendered; no fixed sales/order start or nearest-date edge is accepted. |
| Apple-Silicon mathematical acceleration | ADR 0226 macOS-native Rust owner service with authenticated MLX Metal execution receipts | Normative boundary applies to accepted TEPP and fast-mlsirm Rust kernels; their owner implementations and actual Metal parity receipts remain required before activation. RankWeave's current dependency-free Python retrieval-fusion/evaluation contract is not Rust acceleration evidence and is not required to adopt MLX; a future Rust vector-scoring owner remains a separately accepted contract gap. |
| Ask answer citation-to-event navigation | ADR 0225; authorized cited source, observed source clock, focused evidence layer, and full-post navigation | Stacked candidate renders numbered answer citations and chronologically ordered evidence cards with bidirectional focus. Event and record clocks stay distinct; this list does not claim a Project Journey. Storybook and component interaction evidence are included; authenticated runtime screenshots remain required at the exact candidate head. |
| Repeat issue to design improvement | `repeat_issue`, `issue_pattern`, and `improvement_action` cited facts | Candidate semantic contract; design-system connector acceptance pending |
| Natural-language Ask with evidence, report, alert, MCP | Persisted semantic-unit embeddings plus versioned delivery/resource contract | Candidate implementation uses whole-question embedding retrieval with no lexical fallback. Post-scoped evidence collection follows exact persisted `project_key` membership, and newly analyzed project evidence durably requeues completed sibling analyses that still have missing facts. Case-analysis reuse is bound to the exact ordered authorized evidence window and context, so the unchanged focal record re-analyzes when that window changes. Canonical acceptance completed one provider-backed 2,048-input batch and atomically persisted 2,048 semantic-unit vectors (6,291,456 dimension values) with zero duplicate units and post-scoped session mismatch count 0. The provider step was durable before persistence, while normalized dimension insertion required about four minutes, peaked near one CPU of PostgreSQL, and showed no database wait event or OOM. The remaining product gap is a measured storage-throughput boundary: preserve atomic replacement and normalized auditability while reducing dimension-write CPU and operator-memory cost through a separately reviewed database contract; do not weaken WAL durability or expose partially replaced vectors. |
| Similar VOC, customer cohort, prior action | Persisted repeat-issue candidate semantics plus orchestrator pair adjudication and extractive evidence | Candidate live post endpoint and post-detail UI implemented; authenticated runtime acceptance pending |
| TEPP independent Event Lineage anchor | Accepted, persisted TEPP criterion bound to exact snapshot/cutoff before fast-mlsirm activation | Consumer PR #606 is on protected main; TEPP producer PR #237 remains open, so no end-to-end accepted artifact is release evidence yet |
| Temporal Lineage topics and multilevel important posts | ADR 0210; TEPP posterior topic/plausible-value contract followed by fast-mlsirm observed-information case-deletion influence | This stacked candidate adds normalized persistence, exact run/snapshot/cutoff binding, pre-aggregation scope authorization, API diagnostics, and populated/unavailable Storybook surfaces. TEPP PR #247 remains open at `063f10f3`; stacked #251–#254 provide fail-closed input validation, full joint precision, deterministic joint plausible-value draws, and the canonical research register, while complete provenance assembly remains gated. fast-mlsirm PR #1418 validates the Rust consumer envelope but intentionally returns `EstimatorUnavailable` until the scientific estimator lands. Runtime therefore remains honestly unavailable with no local Python or fallback score. |
| PostgreSQL WAL/checkpoint and worker memory pressure | ADR 0227 and ADR 0247; aligned PostgreSQL counter deltas plus unchanged-container Docker/cgroup v2 evidence | Candidate PostgreSQL procedure emits a content-authenticated restart/rollback plan while retaining unmeasured settings and durability. The current cumulative counters establish sustained historical WAL/checkpoint pressure but do not replace a representative aligned apply window. A prior worker exit 137 is not attributable after container recreation: the current healthy worker has no configured service memory limit/reservation, and a one-second non-identifying observation showed an approximately 109 MiB cgroup lifetime peak with no new local pressure/OOM event. That idle window is not capacity acceptance. Capture the declared representative workload before recreation; do not add a limit or headroom multiplier until that evidence supports a separately accepted capacity boundary. |

Customer-copy audit began at #640 exact `c142c4ea` and was delivered by #727
at merge `353dfd01`; it retained the ADR-required
measurement-administrator terms and explicit ontology/provenance inspection
labels. Two general-reader gaps were isolated: Customer Master explained the
ontology/semantic implementation boundary instead of the evidence action, and
Global Ask called authorized workspace evidence "internal" posts. The stacked
copy repair tells the reader to compare the source identifier with related
posts and organization evidence, and reuses the authorized-citation action.
Five-locale consistency, rendered component tests, and desktop/narrow
Storybook scenes cover the Customer Master repair. Follow-up #730 renders the
Global Ask no-public-claim result and its next action in desktop and narrow
scenes delivered at merge `b3befa8b`. `프로젝트별 관측 Event` and ADR 0210's exact
`model influence` estimand name remain unchanged.

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
tables use composite keys and bounded kind-first indexes. Production hot-path
acceptance uses `scripts/explain_post_content_backfill.py` on an anonymized
runtime snapshot; the exact candidate SQL runs in a rolled-back transaction
and emits aggregate plan/buffer metrics only. A deployment-specific
capacity/SLO remains separate from this query-shape evidence.

On an isolated exact-schema synthetic snapshot based on #716 `c01de078`
(20,000 eligible posts and jobs, 9,927 ontology-backed project mentions, and
4,951 current operations analyses), a consecutive rolled-back comparison
returned the same 200-row priority page in 2,056.629 ms before and 1,327.868 ms
after the change. Root shared-hit blocks fell from 275,642 to 100,514; both
plans recorded zero shared reads and zero temporary reads/writes. The former
plan made 20,000 correlated project probes and 9,927 correlated
operations-analysis probes, while the semantics-equivalent two-tier query
removes the corpus-wide priority `CASE` and its extra correlated priority
subplans. The reproducible summary includes both relation plan-node counts and
actual scan-loop totals so a single nested-loop node cannot be mislabeled as a
single execution.
The plan remains `Limit -> LockRows -> Sort`; `SKIP LOCKED` and the transaction
boundary therefore remain intact, and the remaining tier runs only when the
priority tier cannot fill the requested page. A separate remaining-tier
observation returned 200 rows in 12,649.654 ms with 241,317 root shared-hit
blocks and no reads or temporary spill; it is retained as the next
distribution-specific optimization target, not hidden by the priority-path
improvement. These observations establish query shape only, not a deployment
capacity or latency SLO.

### Historical UI audit evidence

The `f0b96029` Storybook build was rendered at 1440×1100 and 402×1200 with
synthetic evidence; `416fd19d` changes only post-navigation request isolation.
Desktop inspection showed all four case kinds, five non-conflated metrics,
project-observed-event ordering, cited facts, and evidence actions without horizontal
card overflow. Narrow inspection showed two-column metrics, readable cards and
44px-class actions; the project event list remains intentionally horizontally
scrollable. No identifying runtime record or screenshot is committed. The
`EvidenceReady`, `NarrowViewport`, `AnalysisPendingAndMissingEvidence`,
`AnalysisFailed`, and `LoadError` scenes cover the ADR 0206 state inventory.
The current #640 candidate adds `ExternalInformationEmpty`; its Storybook
build was inspected at 1440×1000 and 390×844 and exposes neither corpus-wide
total/pending/failed counts nor a misleading corpus failure alert in that scoped
destination. Screenshots remain local synthetic audit evidence and are not
committed.
The stacked topic-context consumer adds `TopicInfluenceAccepted` and the
unavailable topic section in `EvidenceReady`. Synthetic screenshots were
inspected at 1440×1200 and 390×844. At 390px the page had zero document-level
horizontal overflow while each exact-value table retained its named,
keyboard-focusable 332px viewport over 784px of table content. The new source
actions measured 54px high; sampled heading, caption, and table-header contrast
was 20.15:1, 5.73:1, and 18.62:1. Authenticated runtime evidence remains
required before protected delivery can be claimed.
Authenticated authorized-corpus acceptance remains separate and may return
only aggregate, non-identifying evidence to this repository.

The 2026-08-26 canonical runtime audit found the Ask composer visually
compressed even though its asynchronous enqueue path remained responsive. The
current stacked candidate replaces that loose control row with a labeled form,
a stable submit action, and a separate live status. Component screenshot
acceptance remains pending until the candidate image is rebuilt. This is not
protected-main delivery evidence.

The current candidate was also re-rendered from the isolated synthetic stack
at 1440×1100 and 402×1200 after the touch-target repair. Both viewports had
document width equal to viewport width, no browser console/page errors, and no
visible button or link below the shared 24px WCAG 2.2 minimum target token.
The screenshots remain local `/tmp` audit artifacts and are not committed.

At the repaired dashboard head, the `EvidenceReady` and `NarrowViewport`
stories were re-rendered locally with synthetic data at desktop and iPhone
13 viewports. The desktop shows separate Event/post values and evidence
actions; the narrow view preserves readable cards and 44px-class actions while
keeping the multi-step project event list horizontally scrollable. These images
remain local audit evidence and are not committed.
An authenticated synthetic OIDC audit then found that the mobile breakpoint
hid the entire GNB despite having no drawer implementation. Candidate
`6b195171` keeps the same semantic navigation in a keyboard-accessible
horizontal viewport. The 390×844 rerender showed the GNB, one `main`, zero
unnamed controls, no document-level horizontal overflow, and visible keyboard
focus. Candidate `1fb65c2e` fixed the root cause of the isolated 401: Compose
passed canonical `VITE_KEYVERSE_*` build arguments while the frontend image
consumed different names and silently compiled the default issuer. A fresh OIDC
browser context then rendered the authenticated synthetic Dashboard at
1440×1000 and 390×844 with 27 total posts, one classified Event/post, 24
pending analyses, zero failures, and honest unavailable TEPP/fast-mlsirm
producer contracts. Both viewports had one `main`, one navigation landmark,
zero unnamed controls, visible first-tab focus, no document horizontal
overflow, no console errors, and no HTTP 4xx/5xx. Screenshots remain local and
uncommitted.
The same candidate then ran the complete Python/backend suite with
`DeprecationWarning` promoted to an error: 1,372 tests passed and 17 declared
integration/provider tests skipped. The run exposed one stale async-queue test
that implicitly depended on unavailable semantic retrieval; the repaired test
injects the queue computation boundary, while dedicated retrieval tests retain
the no-keyword, fail-closed embedding contract. Starlette's maintained
`httpx2` TestClient dependency and FastAPI's RFC 9110 422 constant remove the
observed deprecations without suppression. This remains local exact-head
regression evidence, not hosted-gate or protected-main evidence.

### Exact open-PR boundary

At this snapshot there were 11 open PRs and 10 open issues. PRs #660 and #659
merged to protected `main`; PR #666 remains only non-default-branch stack
composition inside #663. Every remaining open head required refreshed hosted
gates and/or independent review after the base changed. These observations are
not merge readiness. Re-fetch exact heads, unresolved threads, checks,
approvals, rulesets, and merge SHA before any lifecycle claim.

> Audit snapshot: 2026-08-26 07:26 KST (refreshed by the autonomous merge
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
| #681 | `3e0fa644` | stacked fast-mlsirm pair-posterior contract pin; exact-head checks queued and independent review required |
| #667 | `425de329` | current governance/gap evidence refresh; exact-head checks and independent review required |
| #663 | `e65fd29c` | consolidates project ontology traversal and #632 content; exact-head checks and independent review required |
| #658 | `f497a6e8` | evidence-honest Global Ask cutoff with revision-interval live-after semantics |
| #657 | `a59a2023` | fail-closed TEPP asynchronous lifecycle persistence; executable producer evidence remains required |
| #644 | `ed8d97f3` | native-surface code splitting with modal-focus regression coverage |
| #643 | `7fb4d18c` | accessible status-notice surfaces |
| #640 | `d314855c` | operations-dashboard contract alignment; exact-head checks queued and independent review required |
| #639 | `8da485d3` | exact-head checks and independent review required |
| #632 | `cad4debf` | semantic provenance repair structurally included by #663 |
| #631 | `e6b4f0c4` | documentation-only queue snapshot requires current-main refresh or closure |
| #629 | `c95f931d` | exact-head checks and independent review required |

No row above is merge evidence. Immediately before any lifecycle action,
re-fetch the head, unresolved threads, formal reviews, rulesets, and same-head
check conclusions. In particular, queued checks are infrastructure state and
do not transfer evidence from an earlier SHA.

PR #664 merged as `b2e48d5b0db59f5aa434e2a293cd182ee810c019`
into #660's non-default branch. Its semantic-unit implementation is therefore
stack evidence only until #660 passed protected `main` through merge
`7e9030c9a8ee2684e680c63013b304b435ba646e`; the subsequent ontology
readability stack reached protected `main` as `494b54e2245040bcf02b45376f221c37cd437e76`.

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

The Grok durable hourly loop and the central thin GitHub Actions caller
ContextualWisdomLab/.github#1259 (minute 4, `pr-review-fix-scheduler.yml`)
both target this repository. Do not add a LineageWeave-local duplicate
workflow. ContextualWisdomLab/.github#1258 merged at exact head `897819c4` to
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
| #271 | Evidence-honest knowledge-cutoff scope on Global Ask | Ask stack |
| #272 | Verify Global Ask KG/ontology/semantic claims with public SearXNG evidence | Ask stack |
| #274 | Persist and explain Event Lineage channel evidence | #387 |
| #277 | TEPP: persist accepted receipts, poll completed results, keep measurement authority distinct | #468, #417 |
| #280 | Full project-lifecycle history and handover intervals | The current stacked candidate covers observed claim, rebid-response, and handover endpoint pairs; cross-record business-case identity remains unavailable unless an explicit source identifier is persisted, so project/similarity proximity is not used as a substitute |
| #284 | Authoritative lifecycle ingestion and idempotent reconciliation | No active delivery PR confirmed |
| #338 | Evidence-bounded email/project lineage contract for Naruon consumption | Missing on protected `main`; #343 merged only into a non-default stack, while #355 is a distinct calendar-consumer contract and is not delivery evidence for email/project lineage |
| #611 | Decompose closed PR #490 ADR 0133–0137 evidence without transferring stale branch state | #631 supplies the current-main inventory only; focused implementation PRs and tests for every unmet criterion are still required |

## 5. Open product and technical gaps

| Gap | Current evidence | Acceptance requirement |
| --- | --- | --- |
| Protected release | 11 open PRs at the 07:26 KST snapshot; the exact-head inventory in section 1 records their current evidence boundaries | Terminal exact-head checks, no unresolved threads, independent exact-head approvals, protected squash-merge SHA |
| Evidence-grounded operations workspace | Protected-main #614 delivers governed semantic Ask, live Similar VOC, disjoint pending/failed analysis metrics, full Storybook state inventory, and current desktop/mobile screenshot evidence. The current Dashboard stack adds a candidate `post_admin`-gated, 1--200-row durable semantic-backfill enqueue path that reuses PostgreSQL recovery, includes successful records completed before operations extraction, and never runs providers in HTTP; authorized-corpus acceptance remains unavailable | Land the candidate, then perform authenticated authorized-corpus acceptance with aggregate queued/published/recovery and derived-evidence counts while retaining fail-closed no-match behavior |
| Shared frontend gate | The ADR 0109 login repair is on protected `main`; eight older branches carried the defect and received the same verified repair this loop (#521–#560) | Keep every future branch cut from post-repair bases; re-verify with frontend lint/test/build before push |
| Identifying baseline regression | `main` gap file listed real post identifiers; separately, closed #506 and pre-existing public history contain a private runtime source-table identifier, while current `main` and #507 trees are clean | Land this non-identifying rewrite, then coordinate ADR 0001 history remediation with security/privacy owners; do not reproduce the value, force-push, or delete evidence ad hoc |
| Authorized-corpus runtime | Repository tests use synthetic fixtures; private records remain outside git | Authenticated runtime validation returning only aggregate, non-identifying evidence |
| Concurrent web responsiveness | ADR 0204 releases pooled transactions during provider work. Candidate `361641ec` completed a freshly built, isolated, authenticated 4-VU/30-second k6 run over 27 synthetic posts: 3,898 requests, 0 failures, HTTP p95 194.70 ms, reader p95 204.06 ms, and Ask enqueue 104.90 ms. Earlier candidate observations remain in the operability record. These are local correctness/concurrency observations, not a product guarantee | Repeat on the protected merge SHA and a representative deployment/corpus with declared CPU, memory, database pool, worker concurrency, and raw output; approve an SLO only from that capacity evidence |
| Image understanding | Region, OCR, and description work exists across active heads (#405, #419), but current runtime acceptance has not yet proved table-image structure, complete region coverage, or summary/image readiness together | Orchestrator-backed rendered workflow, original/derived asset provenance, region-before-OCR processing, and honest unsupported states; reconcile ADR 0052's image-bearing summary readiness with ADR 0098 before changing sequencing |
| Semantic source rendering | ADR 0223 and migration 0221 give new paragraph, list, table, MathML formula, and caller-parsed conversation-turn units explicit persisted kinds without rewriting historical rows; image regions remain ordered normalized children under ADR 0091. This branch is candidate evidence, not protected-main delivery | Land the exact-head candidate, then prove an authorized semantic-only query retrieves each persisted unit kind and gather authenticated browser evidence that nesting, continuation alignment, formula units, and image regions retain source order |
| Event and project semantics | Multi-project mentions, project-bound actions, 5W1H, requester/processor, and semantic relations exist in ADR 0036/0052/0100/0111/0129 and active stacks | Aggregate authenticated evidence must show distinct projects and events, explicit requester/processor and real R&R, normalized relative time, and product/entity relations without promoting attendance or co-occurrence |
| Product semantic identity | ADR 0228 and migration 0228 define normalized product group/model/variant/trade-item identities, scoped GTIN/MPN keys, exact-span provenance, fail-closed unique/tie/missing/unavailable resolution, and foreign-key relations to existing project and operations facts. The worker candidate reuses the durable post-content queue and skips an unchanged authorized input digest. No authorized-corpus product counts or rendered acceptance evidence are recorded | Land the stack, add authorization-filtered Post/Dashboard relationship reads and SHACL projection, then verify aggregate-only backfill outcomes plus desktop/mobile Storybook screenshots without exposing identifying runtime rows |
| Voice semantic taxonomy | ADRs 0244/0246 and migrations 0230/0235 preserve the twelve-value source-post scheme separately from the six-value post-scoped organization relationship scheme, retain source/derived disagreement and multi-membership, and provide authorized overlap-aware aggregate filters. The Dashboard API returns every persisted category dynamically; PR #736 exact `2f5d9ee8` still typed and labeled only `voc`/`vocc`/`voco`/`vom`/`vop`, so `vos`/`voe`/`vob`/`vor`/`voi`/`voso`/`vops` could not render. This stacked repair covers all twelve with locale and component tests. Candidate Storybook evidence remains synthetic; no private-corpus derived assertion count is recorded | Land the stack, run bounded orchestrator backfill, and verify aggregate-only source/derived/disagreement/unavailable counts at one declared cutoff without exposing record identities |
| Knowledge Graph readability | The black evidence-node root cause is an undefined-token fallback; the design-token repair and long-label/evidence-table coverage remain only on closed, unmerged #490, not protected `main` | Recreate the token repair on a current base and deliver it through protected `main`, then verify light/dark contrast, keyboard graph navigation, full labels, and evidence tables in the authenticated rendered surface |
| Source-code lookup UX | Source state/detail codes remain evidence-bearing machine values and current detail presentation is dense | Catalog-backed display labels with raw-code provenance, compact 5W1H/source-detail hierarchy, keyboard access, and no unsupported customer/project binding |
| Calendar / Naruon | #355 delivered the projection contract; v2.17.0 wires operator consumption without forwarding the end-user token. Naruon producer, provider/consumer fixtures, and protected merge remain open (#336) | Verify observed events against the published schema without invented events; keep commitments available when the channel is unwired |
| SKOS organization aliases | Catalog binding and chip caption live on #480 / #482 | One catalog row per corroborated org; companion caption is hint-only until bound |
| Event Lineage evidence | Channel evidence and Allen relations live on #387 / #484 | Persist channel scores, explain them in the popup, never invent a fused score |
| Scientific measurement | Durable accepted TEPP receipts and LineageWeave #614's exact accepted snapshot/cutoff/run/pair-count consumer are protected; TEPP #237 remains open, so no registered producer artifact exists yet. #387 removes inferred/default persistence weights, but several older reconstruction tests still pass hand-authored numeric dictionaries that are not estimator evidence | Land TEPP #237 through its protected gate, then replace remaining reconstruction-test constants with provenance-bearing fast-mlsirm estimates over synthetic fixtures. Retain true-parameter RMSE recovery as the acceptance bar |
| Python mathematical-compute boundary | ADR 0208's first deletion slice consumes fast-mlsirm protected-main Rust `residual_interaction_map` and `polytomous_expected_response`; local Gabriel SVD, distance, reconstruction, shares, expected-category and duplicate likelihood formulas are deleted. This stack also removes local RRF contribution arithmetic and corrects the invalid all-ones call to RankWeave's convex API through RankWeave #47 (`f92c3a2c`), but RankWeave #47 remains Python and is not the final Rust CPU/GPU execution contract. The backend pins fast-mlsirm protected-main `09f762ded35786dd1078222a4577ff09d649816f`; TEPP-specific fast-mlsirm PR #1423 closed unmerged and is not a valid owner contract. The stacked deletion slice removes production-unused Python cosine/max-pooling helpers and freezes the one active direct-vector path with an AST inventory. Global Ask cosine remains Python migration debt because no accepted versioned Rust retrieval-scoring contract exists; embedding backfill performs only exact request-envelope sizing, advertised-ceiling validation, vector-shape validation, and persistence, not token estimation, model selection, or vector algebra. contextual-orchestrator owns automatic model discovery, selection, tokenization, packing, and provider execution. The doctoring inventory still names period calibration, channel weighting, time-decay and string similarity, cosine, graph ranking, and fusion debt. | Land the contextual-orchestrator owner changes through their protected gates and advance LineageWeave's immutable pin only to a protected owner commit. Land a versioned Rust RankWeave envelope for authorization-visible semantic-unit scoring with model/version provenance, input digest, deterministic CPU/GPU parity, finite dimensions, ranked evidence, and explicit failure. Then switch Global Ask to strict envelope validation, prove authorized semantic retrieval and zero-provider fail-closed behavior, and delete `KNOWN_LOCAL_DIRECT_VECTOR_ARITHMETIC`. Separately land the domain-neutral anchored-weight contract before deleting frozen channel-weight code. |
| Asynchronous authorization | Protected `main` rebuilds Global Ask worker scope after the bearer token leaves the request; #468 now persists exact Keyverse organization/process-unit scope in 3NF child tables and intersects it with current affiliations | Land #468 through the protected gate; prove a second affiliation and a revoked process unit cannot widen delayed-job evidence |
| Planned-facility intent | Planned-facility relationship intent remains only on closed, unmerged #490; earlier stack-only merges were not protected delivery | Recreate the evidence-backed slice on a current base and land through protected `main` before a release claim |
| Accessibility and responsive UX | #602 delivered base post-detail modal semantics; #605 adds selected-post refocus, collapsed/hidden/inert/CSS-invisible focus exclusion across both modal types, readable evidence separators, focused tests, and desktop/mobile Storybook screenshots | Land #605 through the protected gate, then complete screen-reader and authenticated Playwright acceptance on the exact release head |
| Design tokens and repeated objects | Token extraction started; sanitized Figma Event Lineage desktop/mobile frames exist, while other repeated product surfaces remain incomplete | Tokens in CSS + Storybook stories for board, popup, DAG, Ask, calendar, forms, charts; same-viewport Figma/runtime visual comparison before release |
| Frontend delivery performance | #644 implements a native dynamic-import boundary for conditional workspace surfaces and retains accessible loading/error states; exact-head checks passed but the PR is not protected-main evidence | Merge #644 normally, rebuild the protected-main production bundle, and retain the measured chunk inventory rather than raising the warning limit |
| External integrations | Search, Zotero, calendar, Keyverse, orchestrator, RankWeave, ThreadWeave, TEPP, DiskSage, wardnet | Provider conformance, failure/reconciliation behavior, and provenance-bearing integration evidence |
| MSA / modular reuse | LineageWeave must run standalone and as a consumer of org packages | Do not reimplement RankWeave/TEPP/orchestrator/ThreadWeave/Keyverse; fix upstream and PR there |
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
9. **ContextualWisdomLab/.github** — required review workflows (OpenCode, Strix, Noema) and the LineageWeave hourly caller (#1259). If stacked PRs miss central review or coverage-evidence fails on pnpm 9 (`--trust-lockfile` is pnpm 11.3) or a missing Vitest coverage provider, fix the org workflow (#1258), not a local bypass.

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
   open .github#1263, and land the atomic hourly LineageWeave caller in open
   .github#1288 only through their protected gates.
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
