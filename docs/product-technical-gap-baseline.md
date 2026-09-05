# Product & Technical Gap Baseline

## Current evidence — 2026-09-05 KST

This is a supporting, point-in-time inventory. ADRs remain normative. Older
snapshots remain in this file's Git history and do not establish current
acceptance. The machine-readable snapshot is
[`development-loop-20260905-voice-visibility.json`](development-loop-20260905-voice-visibility.json).

Protected `main`: `83eba56149eb802cd63642c507c324c9976ec78e`.
The queue captured before this slice's PR registration contains **119 open PRs
and 16 open issues**, including 23 PRs targeting `main`. All 119 heads and
bases are recorded in the snapshot. Review-thread pagination was complete;
all 23 main-targeted PRs had zero unresolved threads, no current-head
independent approval, and `REVIEW_REQUIRED`. Checks for all 119 pre-registration PRs were read
from each exact commit, not inherited from a prior head or merge simulation.

PR #780 remains open at `1d8fa267b059289e77301a09985dfac70a439814`, targeting
`main`, with normal squash auto-merge enabled. Its exact-head check inventory
contains 8 successful, 8 skipped, and 11 cancelled checks. Skipped/cancelled
required workflows are not acceptance. The ruleset requires one independent
approval, dismissal of stale reviews after pushes, resolved review threads,
central required workflows, and non-fast-forward protection. No PR was
self-approved, force-pushed, or merged with bypass. No new merge SHA is claimed.

Existing auto-merge settings on #780, #907, #911, #914, and #929 were preserved.
The observed running Tests job belonged to open #802 at its current head
`32f1cda10a2a1a6cabd64a3ae6f59bd6f0b20fd6`; it was not cancelled. No stale run
was cancelled during this slice and no CI-stall remediation is claimed.

## Product priority and implementation

The selected gap is **additional perspectives remaining visible after their
supporting evidence becomes inaccessible**. This violates the explicit evidence
access boundary in PRD-FR-2/3 and VOC-TR-5, so it takes priority over additional
report decoration. This priority is a product trust requirement, not a
weighted score or a claim about prevalence in current data.

The implementation is committed as
`4210fe5fead389504f19f3d1c73657a44b3d4af4`, with atomic rejection follow-up
`629d23836b24fe25923c6566f0ee9ad7f3e21106`, in PR #937, stacked on #780. It:

- reauthorizes genuine derivation evidence in Post detail, list labels, filter
  options, and filtered membership/totals, including knowledge-cutoff reads;
- omits additional assignments backed by private, draft, deleted, or
  out-of-scope evidence, without substituting the carrying Post;
- retains the imported primary, atomic vocabulary, stored truth, assignment
  intervals, and PROV-O derivation, allowing the same assignment to reappear
  when access is restored;
- returns an actionable conflict if evidence disappears before a write's
  response is assembled, with assignment persistence and response
  reauthorization in one transaction so rejection rolls back the write.

The SQL uses the existing source eligibility and public-or-affiliated-scope
contract. No schema, migration, release number, numerical kernel, inference,
model selector, provider call, or new dependency was introduced.

| Evidence class | Current result | Acceptance boundary |
| --- | --- | --- |
| Reproduction | Real OIDC/JWKS plus a disposable, fully migrated PostgreSQL database reproduced the hidden-evidence disclosure before the fix | Synthetic only |
| Implementation regression | 63 selected backend, authorization, ontology, SHACL, and docstring tests pass | Includes live/cutoff visibility withdrawal, restoration, exact process scope, and a concurrent withdrawal response |
| Atomic rejection follow-up | 11 selected backend tests pass after the transaction change; 5 documentation checks pass | Real authenticated PostgreSQL test confirms a rejected additional Voice is absent after the 409; preserves another agent's atomicity regression from `1371a4ec1c4ac3206d108d9001c0179e2b8df370` |
| Frontend regression | 30 focused Voice/ontology/export tests pass using the thread pool | Full frontend run remains unverified: fork workers timed out before tests ran |
| Build and documentation | Frontend lint, production build, Storybook build, and 5 documentation-hygiene tests pass | Existing chunk-size warning is retained; no DeprecationWarning suppression added |
| Rendered evidence | Authenticated synthetic API payloads rendered with the existing component and global tokens at 1440 and 390 pixels; visible/withdrawn states show no document overflow | Component renders, not a deployed authenticated full-application journey |
| Protected delivery | Parent #780 and this stacked candidate remain unmerged | Parent first, then retarget child to `main`, recollect exact-head evidence and independent approval |

Screenshots: [visible desktop](screenshots/voice-evidence-visible-desktop-20260905.png),
[visible mobile](screenshots/voice-evidence-visible-mobile-20260905.png),
[withdrawn desktop](screenshots/voice-evidence-hidden-desktop-20260905.png),
[withdrawn mobile](screenshots/voice-evidence-hidden-mobile-20260905.png).
`EvidenceNoLongerVisible` extends the existing Recorded perspectives Storybook
inventory. No new layout or style was designed.

## Authority, research, implementation, and runtime are separate

- **Authority read:** current LineageWeave `docs/product-requirements.md`,
  ADR 0246, ADR 0256, ADR 0252, and the Voice technical requirements. ADR 0246
  governs twelve atomic classifications and extensibility. In this checkout
  ADR 0251 is the I/O psychology taxonomy; Voice composition is ADR 0256.
  The #780 parent already corrects the historical Voice references.
- **Research checked:** [W3C PROV-O](https://www.w3.org/TR/prov-o/) supplies
  derivation semantics; [ISO stakeholder guidance](https://helpdesk-docs.iso.org/article/331-gd-stakeholders-categories)
  permits context-dependent categories. Neither authorizes fixed combinations,
  weights, evidence substitution, or a B2B2C-only taxonomy. ABAC admission is
  the repository's product contract, not a rule inferred from those standards.
- **Implementation:** #780 owns carrying/evidence export separation;
  #934 owns singleton JSON-LD page merging; #935 owns filtered JSON-LD/CSV
  parity; #936 owns additional-Voice correction history. These candidates
  were read and preserved; their tests and screenshots are not transferred
  to this candidate. Paged JSON-LD regressions on the #780-based slice pass,
  but its later stacked repairs still need parent-first protected delivery.
- **Current non-identifying census:** a read-only query on the formal
  `lineageweave-postgres-1` service found 43,189 source records, 43,189 current
  Voice assignments, zero current additional assignments, and zero closed
  assignment intervals. This is an exact table count, not evidence that any
  real user exercised this bug or that deployed API/UI acceptance passes.
- **Population inference:** unavailable. No declared probability sample,
  inclusion probabilities, membership digest, failure-inclusive denominator,
  or Rust-owned terminal estimator/variance/interval artifact was produced.

## Synthetic authenticated HTTP observations

The existing `scripts/k6_http_e2e.js` ran against a temporary API process using
real demo OIDC, the formal PostgreSQL service with an isolated two-record
synthetic database, an isolated Valkey service under Compose project
`lineageweave`, and the formal contextual-orchestrator gateway. The existing
asynchronous Ask path remained observable while Post/Lineage/status reads ran.

| VUs / duration | HTTP requests | Requests/s | HTTP p95 | HTTP failure rate | Enqueue duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 / 10s | 2,609 | 229.42 | 14.84 ms | 0% | 240.54 ms |
| 4 / 10s | 3,236 | 265.80 | 65.67 ms | 0% | 13.42 ms |

Samples observed running and succeeded Ask rows; the last sample still had a
running job. This does not establish successful completion of every answer or
its semantic validity. Sampled PostgreSQL CPU reached 113.69% across cores,
gateway CPU 24.98%, and the API process containing the workers 61.1%.
Valkey reported zero rejected connections; its three blocking stream readers
are not by themselves saturation evidence. The telemetry contains one explicit
Docker-statistics timeout. Shared-host CPU snapshots, sparse observations,
and this small synthetic workload do not establish a capacity/SLO, causal
bottleneck, or population claim. No performance implementation was changed.
The recorded load preceded the final write-response conflict guard; it is
not represented as exact released-head load evidence.

The temporary API process and synthetic database were removed. The exact
`lineageweave-voice-evidence-test-valkey-1` container was stopped, verified as
exited with the expected Compose labels, and removed. Formal data volumes and
other agents' containers were retained. Compose-rendered provider values were
never printed or persisted.

## Ecosystem authority and canonical repository identity

Remote metadata confirms `ContextualWisdomLab/LineageWeave`, `RankWeave`,
`ThreadWeave`, `TEPP`, `contextual-orchestrator`, and `fast-mlsirm`. The canonical
DiskSage repository path is **`ContextualWisdomLab/disksage`**.

Before selecting this change, the loop read ThreadWeave and fast-mlsirm PRDs,
RankWeave and TEPP architecture authorities, contextual-orchestrator's
architecture, and disksage's current README/product boundary. Their scope
remains separate: threading, score fusion, numerical measurement, model
orchestration, and storage lifecycle are not reimplemented here. Context7
reported quota exhaustion and DeepWiki reported an unindexed repository;
current repository authorities and official PostgreSQL/W3C/ISO pages were used
instead. Sequential Thinking and Memory graph tools were not callable in this
session; no missing tool output is represented as verified evidence.

## Cross-PR collision audit

The added ADR declarations relative to each PR's current base expose these
same-number/different-path conflicts. They need explicit owner reconciliation
before integration, not an automatic rename that changes authority.

| ADR number | Open PRs |
| --- | --- |
| 0355 | #920, #915 |
| 0301 | #902, #838 |
| 0300 | #899, #837 |
| 0279 | #888, #811 |
| 0335 | #877, #876 |
| 0305 | #844, #843 |
| 0304 | #842, #841 |
| 0293 | #828, #826 |
| 0290 | #823, #822 |
| 0289 | #821, #820 |

Repeated proposed release numbers are 2.92.0 (#877/#876), 2.62.0 (#844/#843),
2.61.0 (#842/#841), 2.50.0 (#828/#826), 2.47.0 (#823/#822), and 2.46.0
(#821/#820). Main metadata remains 2.28.0 while the package's public version
remains 2.20.0; release reconciliation is still unavailable. No new migration
identifier collision was found among added files in the observed PR diffs;
this is not proof of compatible schema semantics. The Voice and translation
stacks both modify the API module, so textual and behavioral merge validation
must be repeated after their parents land.

Issue #807 and PR #847 own duplicated occupational requirement/authority
identities. Their resolution must preserve pinned SOC/O*NET definitions and
relations, keep occupation observations with source scale/error/provenance,
and keep employer job-family/job-series imports distinct in the governed 3NF
contract. This Voice fix changes none of those contracts.

## Next protected loop

A later GraphQL review-thread refresh reached the account rate limit. No
review or merge eligibility is inferred while that refresh is unavailable.

1. Preserve auto-merge while independent approval and required workflows wait;
   inspect failed #907/#911 central workflows at their owning repository.
   Their named failures are recorded; run-log retrieval returned 404 and their
   root causes were not inferred from older runs.
2. PR #811 already carries another agent's caption-bound correction in
   `98c794fe1f94b8c5a49a8ecbeced0141e3900ffc`. Exact-head focused tests found
   51 passes and one obsolete midpoint-position expectation inherited from
   before that layout change. Commit
   `430077e24aca9a3643e66fa52bb8b7e21d0fb3b4` carries the exact parent
   caption-offset expectation into the child; all 55 tests in the four layout
   and rank suites pass. The production clipping fix is preserved. Its
   parent/ADR conflict still blocks protected integration; GitHub Checks and
   independent approval remain unverified. Informational notes are not defects.
3. Merge #780 only through its current ruleset, then retarget its children one
   at a time and recollect exact-head checks, threads, approval, and merge SHA.
4. Keep #277 receipt/completion, #272 public-claim evidence, #269 authenticated
   MCP, #271 cutoff, #280/#284 project history, #741 occupation evidence,
   #900 calendar authority, and #922 translation acceptance distinct. Open
   issue/PR presence is neither a shipped feature nor a missing implementation.
5. Repeat authenticated deployed PostgreSQL/API and full rendered-app evidence
   on the eventual protected release head before marking Voice acceptance
   complete. No unavailable authority is replaced by an invented signal.
