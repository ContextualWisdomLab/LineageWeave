# Product, technical, and gap baseline

**Snapshot:** 2026-08-21 05:46 (Asia/Seoul)
**Protected-main baseline:** `origin/main`, product version `2.12.5`
**Audited PR head:** #258 at `b83be708a9dc705df7485e1b18e779439bfb7b71` (current exact branch head; protected-main runtime evidence remains pending)
**Active PR update:** Hosted Full test, frontend, PROV-O, CodeQL, SAST, supply-chain,
and security Checks are successful on the current #258 head; Devin Review is
failed and the OpenCode coverage check remains pending. Formal approval and
protected-main acceptance are still required.
**Purpose:** connect the normative ADRs and research evidence to product
requirements, technical contracts, implementation evidence, and active PRs.
An active PR is proposed work, not shipped behavior.

## PRD

### Problem and outcome

Buyers need to turn scattered, timestamped records into reviewable branching
histories without confusing a plausible relation with a proven fact. The
product succeeds when an authorized buyer can move from an aggregate signal or
answer to its source post, lineage neighborhood, channel evidence, actor and
project context, while every derived claim retains provenance and an explicit
availability boundary.

### Users and jobs

| User | Job | Success evidence |
|---|---|---|
| Buyer | Find a relevant customer, project, event, commitment, or Keyman and inspect its history | Browser navigation reaches an authorized source-backed post and focused lineage |
| Analyst | Reconstruct a cutoff-bounded lineage and inspect why edges were selected | Persisted run, digest, edge scores, channel breakdown, and status history |
| Operator | Import, rebuild, retry, and diagnose without inventing unavailable results | Durable ledger/outbox state and explicit failed/unavailable status |
| Retention admin | Purge run-bearing evidence only under a deliberate grant | Database role plus unrevoked retention grant; no public purge route |

### Scope

In scope: authorized source import, semantic units and visual regions,
multi-channel lineage reconstruction, source-grounded ontology/provenance,
period reports, Board/Global Ask/Calendar/Customer/Keyman navigation, TEPP and
contextual-orchestrator integration, and buyer-visible evidence.

Out of scope: TEPP model reimplementation, raw provider calls, locally chosen
models, forced links for missing channels, public real-data fixtures, and
claims that an unmerged PR or historical runtime observation is live behavior.

### Product measures

- Every displayed derived claim can navigate to authorized evidence or is
  labeled unavailable.
- No relation crosses the analysis cutoff or caller ABAC boundary.
- Missing model, embedding, TEPP, Vision, or verification channels are dropped
  and weights renormalized; no placeholder score or actor is invented.
- A real-stack acceptance run covers login, PostgreSQL-backed API behavior,
  buyer navigation, and aggregate non-identifying evidence.

## Functional specification

| ID | Requirement and acceptance criterion | Normative source | Current evidence |
|---|---|---|---|
| FR-01 | Import authorized records while preserving immutable source identity, raw state, publication state, and revisions. No real record enters git. | ADR 0001, 0040, 0046, 0056-0059, 0068, 0089 | Import/reconciliation modules and migrations; private runtime evidence only |
| FR-02 | Derive paragraph/list/table/image-region semantic units without replacing the source representation. | ADR 0061, 0062, 0066, 0067, 0077, 0087, 0091 | Chunking, image-content, visual-region and embedding paths |
| FR-03 | Reconstruct backward-only candidate edges from available channels, fuse through RankWeave, apply a minimum floor, persist scores, and assemble trees through ThreadWeave. | ADR 0024, 0064, 0084 | `lineageweave/reconstruct.py`, channel clients, reconstruction tables/tests |
| FR-04 | Create, start, observe, and retain analysis runs with cutoff snapshots, append-only status, outbox delivery, authorization, and explicit failure. | ADR 0013-0023, 0025 | Backend analysis-run modules, migrations, API tests |
| FR-05 | Keep TEPP as a versioned external measurement boundary; failed or unused responses never become invented theta. | ADR 0003, 0022 | `tepp_client.py`, report and start contracts |
| FR-06 | Resolve actors, organizations, projects, roles, and relationships without collapsing ties or same-name mentions; preserve catalog identifiers on role rows. | ADR 0004-0012, 0018-0019, 0026-0027, 0036 | Summary, entity-resolution, KG and report paths/tests |
| FR-07 | Global Ask and buyer surfaces retrieve only authorized evidence and let cited results open the relevant post/lineage context. | ADR 0032, 0037, 0039, 0041-0044, 0047, 0053-0055, 0075, 0078, 0090 | Main has the earlier surfaces; PR stack #258-#301 proposes the integrated navigation/evidence flow |
| FR-08 | LLM, structured output, embedding, and Vision work crosses contextual-orchestrator with one post session and bounded provenance; provider/model/protocol selection stays upstream. | ADR 0030, 0045, 0052, 0070-0077, 0079, 0081-0088 | Orchestrator clients, Compose boundary, historical gateway observations |
| FR-09 | Period reports use real fast-mlsirm results; missing cells remain missing and leftover pairs are residual-derived and navigable. | ADR 0003, 0034-0035, 0048-0050 | Historical authenticated report rebuilds; report tests and schema |
| FR-10 | Standard provenance uses normalized PROV-O relations; qualified influence implies its unqualified relation and KG edges remain a navigation projection. | ADR 0011, 0065 | PROV-O implementation matrices, ontology, CI contract |
| FR-11 | Post summaries expose evidence-bearing events and R&R. Requester/processor actions are nullable and may only name actors already bound to the same post summary. | ADR 0052, ADR 0100 | Commit `15e1a378` is on PR #258; one authorized target refresh stored three action rows, while corpus-wide buyer-data acceptance remains unproven |
| FR-12 | A hierarchy-enrichment timeout leaves the source-grounded summary readable and the actor unbound; it never creates a guessed catalog identity. | ADR 0101, ADR 0010, ADR 0026 | Commit `1c260f20` contains the boundary, ADR, and focused test; independent review, protected-main merge, and fresh runtime evidence remain pending |

## TRD

### Runtime components and trust boundaries

```mermaid
flowchart LR
  B[Authenticated buyer] -->|OIDC token| F[React buyer UI]
  F -->|bounded JSON| A[FastAPI]
  A -->|ABAC-scoped SQL| P[(PostgreSQL)]
  A -->|durable ledger| P
  A -->|wake-up only| V[(Valkey)]
  A -->|provider-neutral contract| O[contextual-orchestrator]
  A -->|published wire contract| T[TEPP]
  O --> X[LLM / Vision / embedding providers]
  P -->|authorized source boundary| S[(Private source)]
```

- PostgreSQL is authoritative for normalized product state, run snapshots,
  provenance, status, and durable work ledgers. Valkey is not the source of
  truth.
- FastAPI applies authentication and ABAC before projecting records or edge
  endpoints. The browser receives bounded projections, not raw source bags.
- contextual-orchestrator owns provider capability discovery, reasoning
  effort, structured synthesis/repair, sessions, and cost lineage.
- ThreadWeave, RankWeave, TEPP, and fast-mlsirm are reused at their published
  boundaries; LineageWeave does not clone their algorithms.

### Analysis-run lifecycle UML

```mermaid
stateDiagram-v2
  [*] --> Pending: authorized lineage request + frozen cutoff
  Pending --> Running: start + durable outbox claim
  Running --> Succeeded: result persisted + digest recorded
  Running --> Failed: explicit failure code
  Failed --> [*]
  Succeeded --> [*]
  note right of Pending
    TEPP creation is not a fake Pending lineage run.
    Retention purge has a separate DB-only grant boundary.
  end note
```

### Evidence sequence UML

```mermaid
sequenceDiagram
  actor Buyer
  participant UI
  participant API
  participant DB as PostgreSQL
  participant Orch as contextual-orchestrator
  Buyer->>UI: open source-backed feature
  UI->>API: authenticated bounded request
  API->>DB: load ABAC-visible cutoff evidence
  opt semantic adjudication is available
    API->>Orch: bounded units + provenance + session id
    Orch-->>API: validated result + usage/verification metadata
  end
  API->>DB: persist result or explicit unavailable/failure state
  API-->>UI: evidence-bearing projection
  UI-->>Buyer: claim, provenance, and source navigation
```

### Non-functional requirements

| ID | Contract | Verification |
|---|---|---|
| NFR-01 | OIDC authentication, endpoint ABAC, no public retention purge, no repository secrets | authorization-specific API tests and Compose identity-boundary check |
| NFR-02 | Bounded row, batch, browser, image, and MCP payloads | boundary unit tests plus real-stack response-size observation |
| NFR-03 | Third-normal-form identities and provenance; database constraints enforce integrity | migration/schema tests against PostgreSQL |
| NFR-04 | Python 3.12+ project-local environment; pinned Node/pnpm and Rust toolchain; checked lockfiles | clean-environment backend/frontend builds |
| NFR-05 | Synthetic fixtures only; runtime validation returns aggregate, non-identifying evidence | repository scan and evidence-document review |
| NFR-06 | ADR-first architectural change and paper-grounded model policy | ADR link check and review; unsupported policies remain unavailable |

## Current aggregate data and runtime evidence

Observed from the running local Compose stack without selecting a post title,
body, source code, person, organization, or identifier:

| Evidence | Observed result |
|---|---|
| Stack availability | PostgreSQL, Valkey, and contextual-orchestrator healthy; backend and frontend running; backend `/healthz` and frontend `/` returned HTTP 200 |
| Source boundary | 43,839 source posts: 43,814 have both source-system and source-record identity; 25 lack that import identity |
| Source state/body | 43,814 rows carry source-state evidence; 43,438 rows have a non-empty body; 87,297 source revisions persist |
| Derived content | 562,394 semantic units, 1,308 live lineage edges, 48 KG navigation edges, and 95 persisted summaries |
| Run registry | Three runs: one lineage, one report, one TEPP; latest states are two Succeeded and one Failed |
| Run evidence | One snapshot with 42,577 members; one persisted reconstruction with 1,281 edges; zero persisted TEPP results |
| Requester/processor | `post_summary_action` exists with composite actor foreign keys; one authorized target refresh stored three action rows |
| Summary refresh | One authorized target request returned HTTP 200 with contract v5, four key events, one role, three actions, and one project |
| Authentication | Real synthetic-user OIDC login, live JWKS fetch, and RS256 verification passed |
| Authorization | Unauthenticated `/api/analysis-runs` and `/api/posts` returned 401; four focused live-Keycloak/PostgreSQL API tests covering authenticated account, list ABAC, direct deny, and missing token passed |
| Focused contracts | Post-summary and transaction-contract tests: 31 passed, 1 skipped; the skip is not runtime proof for the skipped capability |

These observations prove data presence and the listed boundaries only. They do
not prove a browser-clicked buyer journey, current TEPP transport success,
post-summary-action population across the corpus, or equivalence between every
running container image and the PR head. The target refresh is bounded runtime
evidence for one authorized post, not a corpus-wide acceptance claim.

## Active PR audit

The following table is the historical 17:08 snapshot; it is retained to show
why the dependency graph was recorded, not as current merge evidence. Queued
checks and review gates mean none of those rows was protected-main truth.

| PR | Proposed increment | Base → head | Snapshot state |
|---|---|---|---|
| #301 | Global Ask knowledge cutoff | `#264 stack` → `v2.23.0` | Ready / UNSTABLE |
| #298 | bounded async lineage LLM rebuild | `#276` → `v2.22.0` | Ready / UNSTABLE |
| #287 | exact Event Lineage channel evidence | `#276` → feature | Ready / UNSTABLE |
| #286 | exact byte-bounded MCP browser admission | `#270` → fix | Ready / UNSTABLE |
| #285 | project lifecycle timeline | `#264 stack` → `v2.18.4` | Ready / UNSTABLE |
| #282 | TEPP project history in read/Ask | `#264 stack` → `v2.18.0` | Ready / UNSTABLE |
| #276 | public verification of Global Ask claims | `#266` → `v2.20.0` | Ready / UNSTABLE |
| #275 | evidence-bound Event Intelligence | `#270` → `v2.18.3` | Ready / UNSTABLE |
| #270 | authenticated MCP Global Ask | `main` → feature | Ready / BLOCKED / review required |
| #266 | Event Lineage to Keyman focus | `#264` → `v2.19.0` | Ready / BLOCKED / review required |
| #264 | keep Event Lineage DAG focus | `#263` → `v2.17.0` | Ready / BLOCKED / review required |
| #263 | Ask citation to Event Lineage | `#262` → `v2.16.0` | Ready / BLOCKED / review required |
| #262 | Customer post to Event Lineage | `#261` → `v2.15.0` | Ready / BLOCKED / review required |
| #261 | Calendar commitment to Event Lineage | `#260` → `v2.14.0` | Ready / BLOCKED / review required |
| #260 | Weekly VOC to Event Lineage | `#258` → `v2.13.0` | Ready / DIRTY / review required |
| #258 | buyer evidence board and ontology surface | `main` → feature | Ready / BLOCKED |
| #192 | plural affiliation next action | `main` → `v0.77.0` | Ready / DIRTY / review required |
| #190 | duplicate-numbered entity-resolution ADR | `main` → docs | Ready / BLOCKED |

The dominant delivery topology is a long dependent stack rooted at #258 and
then #260-#266. Parallel descendants (#275, #282, #285, #276-#301) are based
on intermediate heads rather than one integration head. Green checks on a
child do not prove that the stack is mergeable or that the behavior exists on
main.

Manual triage of #258's four unresolved scanner threads found literal SQL in
`entity_relationship_ingestion.py` and `demo_scope.py`; request-derived entity
ids are passed as `$1` arguments rather than interpolated. This is evidence for
a likely narrow false-positive suppression, not authority to dismiss the
findings: the required security workflow and independent reviewer must accept
the exact-head disposition.

## Current exact-head audit: 2026-08-20 18:47

The active stack was re-fetched after each normal branch update. The current
heads are: #258 `f8d2fa98d622e4294cf08f24a87a7db697479f4f`, #260
`dfd95d9cd98b0ea8a51136b5f6615077b837ff1d`, #261
`bd1b4d2fbb53978b5c231b4aa00531632604f6ec`, #262
`80445b8acffb356f42a4e8ae4a7b3a1d24b07cb2`, #263
`d670acd51eb24c6fcf235f9681018d8ce45b19b4`, #264
`d5dbdf711121384199d5f586a06f5fd04dd32251`, #266
`26a6d9c61c7a7c8b52c924858a362c728f67a320`, #270
`3a24c6b774bcfdd539e7e01d11195ce1887e6f12`, #275
`35035783fae5f1e6763b38dbb6daf3d86934fdf5`, #276
`635420d29c1637718d7f9ea985b7940ef74a4cac`, #282
`6eeaf89de45f8f236858164bd211b21f5fddb7c4`, #285
`4eaeb2305f91fd0d339845bda4b6b23a93cadc11`, #286
`1175cd9db3fdabb6b31179808092bf058e8cd536`, #287
`554efb9b047b37c9027296116aa393d94fce6b4b`, #298
`49c9976fa6ee3792b9adae5b8132365a67c9bb15`, #301
`59ccdf91bfddfe885be775b5c466819f5350baf5`, #302
`40b0a8ea22ff7fb6de5419feefaa244cca3070f5`, #303
`2702fd69ab6000fc6c7bc6cf9ed5d3dfdb362970`, #306
`e0dbc3860278e13d74b6dadd5be4fd75e9c107b1`, #307
`313d38a4b58b99aaca279607486684ac04582de5`, #308
`3c74f1fa536cff3987f38139303f06cd48a8d9c7`, and #309
`e6fd907ed36d1228729c0df8d6cd22f603051891`.

Twenty-four PRs are open in the repository, including the 22 PRs listed above
from #258 onward. At this audit no PR had a formal `APPROVED` review. Required
checks for the updated heads were still queued or otherwise non-terminal, with
no completed failure used as merge evidence. This is a gate state, not a merge
claim. The parallel buyer-surface branches were also checked for ADR identity
collisions: #308 owns ADR 0112 and #309 owns ADR 0113.

Local regression evidence for the newly audited branches includes #303 backend
focused image/persistence/static-SQL tests `49 passed`, #303 frontend `135
passed`, #306 frontend `130 passed`, #307 frontend `131 passed`, #308 full
backend `723 passed, 16 skipped` plus a focused normalization regression `5
passed`, and #309 frontend `133 passed`. These are branch-local observations
and do not replace protected Checks or independent review.

## Gap register

| Priority | Gap | Evidence | Closure criterion |
|---|---|---|---|
| P0 | No protected-main integrated buyer journey for the active feature stack | Main is 2.12.5; 24 open PRs span dependent and parallel bases | Establish one reviewed integration order, update each exact head, pass required checks, merge without bypass, then run login-to-source browser acceptance on main |
| P0 | Current runtime proof is incomplete | The current aggregate/OIDC/ABAC checks cover data presence and selected boundaries; 2026-08-18/19 notes cover other slices, but no evidence set proves the entire PR head or main journey | Complete the real-stack matrix on an exact revision: browser login/navigation, Ask, reports, Vision, TEPP availability, action population, and cleanup |
| P0 | PR #190's duplicate ADR identity was corrected but is not protected-main truth | Active PR head `ac1b4e17` now uses ADR 0038 and aligns the entity-resolution claims with implementation; independent review and Checks remain pending | Re-audit exact head, obtain independent approval, pass required Checks, and merge normally; never merge a duplicate ADR identity |
| P0 | PR #258 is not review/CI complete at its exact current head | #258 is mergeable but BLOCKED: 14 of 22 checks queued, no approval, and four unresolved scanner threads on two SQL modules | Classify each finding against the literal SQL and bound arguments; fix a real flow or add a narrow documented suppression for a false positive, resolve threads, obtain independent approval, and re-check the exact head |
| P1 | Requirements were implicit across ADRs and architecture phases | No prior PRD/TRD/requirement traceability baseline existed | Keep FR/NFR IDs in this document linked from ADR index; require new product PRs to name affected IDs and runtime evidence |
| P1 | Active PR topology obscures release truth | The current 24-PR snapshot contains blocked, unstable, and unknown merge states; many bases are other open branches | Publish a dependency order, retire obsolete/duplicate branches, and avoid version claims until their base chain reaches main |
| P1 | ADR 0100 is exercised only by a bounded target, not accepted across the corpus | Commit `15e1a378` and the v5 contract are on PR #258; one authorized target refresh stored three action rows, while corpus-wide accepted/dropped/absent counts remain unknown | Regenerate an authorized bounded sample, report aggregate accepted/dropped/absent counts, verify source evidence and actor FKs, then exercise the buyer popup without exposing record content |
| P1 | ADR 0101 is active-PR behavior but not protected-main behavior | Commit `1c260f20` contains the corrected ADR link, boundary, and focused tests; independent review and protected-main merge remain pending | Re-audit the exact head, obtain independent approval, pass required checks, merge normally, and collect fresh runtime evidence |
| P1 | ADR status vocabulary is inconsistent and sometimes stale | Several ADRs say “Accepted on this active PR; not protected-main truth” even after branch evolution | Add a mechanical ADR status/link audit that distinguishes Proposed, Accepted-on-PR, Accepted-on-main, and Superseded |
| P2 | ADR numbering skips 0031 and 0093-0097 while file 0092 titles itself ADR 0031 | File identity and displayed identity differ | Correct the 0092 title or document an intentional alias; reserve or explain skipped numbers in the index |
| P2 | Product measures lack explicit targets | Research supports evidence boundaries but not universal model-quality thresholds | Define targets only from an approved evaluation protocol and authorized labeled aggregate dataset; do not invent accuracy goals |
| P2 | UML covers core trust/lifecycle flow but not every buyer navigation branch | Architecture and PR stack evolve faster than diagrams | Add diagrams only when a stable main integration makes a flow materially distinct; keep this baseline small |

## Verification matrix

| Scope | Evidence available now | Claim allowed now | Missing proof |
|---|---|---|---|
| Protected main | `origin/main` manifests show 2.12.5 | Existing main contracts only | Fresh main runtime matrix |
| Historical local runtime | Authenticated PostgreSQL report rebuilds and orchestrator/Vision observations dated 2026-08-18/19 | Those exact bounded observations | Current head/main equivalence and full browser journey |
| Active PRs | GitHub head/base, review, merge, check, and review-thread states at snapshot | Proposed increments and gate state | Normal merge and post-merge runtime behavior |
| Local PR checkout | PR #258 was re-fetched at `f8d2fa98d622e4294cf08f24a87a7db697479f4f`; its backend suite passed `716`, with `16` integration skips | Only the exact observations in the current-data table; no claim for protected-main behavior | Full suite/CI, browser journey, external channel results, review, merge, and corpus-level action evidence |

## Maintenance rule

ADRs remain normative. This document is the product/technical traceability
projection: update the affected FR/NFR row and Gap closure evidence when an ADR
or PR changes product behavior. Never turn a PR title, green unit test, or old
runtime note into a shipped/live claim.
## Checkpoint update: 2026-08-20

### Project-bound major-event actions

The buyer-facing action projection now carries an optional normalized project
key and persists it only when the same post has a matching
`post_project_mention`. An action that cannot be grounded to a project remains
unbound rather than being guessed from its title, customer, PU, sales pool, or
author hints. This closes the mixed-project event ambiguity at the persistence
boundary while preserving legacy unbound actions.

- Implementation: PR #308, `fix/project-bound-summary-actions`
- Decision record: ADR 0111
- Local evidence: backend `719 passed, 16 skipped`; focused migration regression
  `7 passed`; frontend lint, tests, and build passed before publication.
- Integration status: PR #308 is stacked on the buyer-surface branch and is not
  a protected-main merge claim.

### Provider sampling capability gap

The observed gateway failure for an Azure GPT-5-family deployment was a
provider capability rejection of non-default `temperature`, followed by an
unrelated fallback-group failure. The product contract must not select a model
from a local name or fallback table. `contextual-orchestrator` PR #774 adds a
single retry without the rejected optional field for HTTP 400/422 across Chat
Completions, Responses, and raw/proxy transport, while retaining the same
provider and orchestration session.

- Upstream decision record: contextual-orchestrator ADR 0012
- Upstream local evidence: provider protocol and integration tests `16 passed`;
  `git diff --check` passed.
- Integration status: PR #774 is stacked on the paper-grounded orchestrator
  branch; it is not yet evidence of protected-main integration.

LineageWeave must continue to send model, reasoning-effort, protocol, and
VISION selection through contextual-orchestrator. Until the upstream contract
is integrated into the runtime base used by LineageWeave, this gap remains
open for deployment acceptance.

### Project-bound summary-event checkpoint

The mixed-project summary gap is now addressed in the buyer contract. Summary
key events retain the legacy text list, while `key_event_details` carries the
resolved project display name. Persistence stores only a `project_key` that
passes the same-post `post_project_mention` foreign key; ambiguous or
unsupported proposals remain unbound.

- Decision record: ADR 0112
- Schema change: migration 0102
- Buyer surface: project labels are rendered without exposing internal keys
- Evidence: parser, transaction, real PostgreSQL projection, schema, frontend
  lint, and frontend test checks pass on the checkpoint branch

### Verification update

The integrated `60b52f26` checkpoint passes the full backend suite: `723 passed,
16 skipped`, with no test failures. Frontend lint, `131 passed`, and production
build also pass. Four existing dependency deprecation/security warnings remain
non-failing and are not reclassified as product evidence.

## Stale-summary continuity checkpoint: 2026-08-20

The private PostgreSQL runtime showed three inspected target rows with summary
contract versions `2`, `5`, and `5`, while the current contract is `6`. The
same aggregate inspection found persisted 5W1H rows for the two newer rows,
but a current-contract read rejected their older summary projections and
re-entered the live LLM path. This made a temporary gateway failure look like
missing product evidence even though the source body and prior projection
still existed.

ADR 0114 now keeps the default current-contract boundary, but permits the
summary endpoint to return an explicitly labelled stale projection when a
refresh is unavailable or incomplete. The buyer popup shows the saved-summary
state and exposes a retry action; a successful contextual-orchestrator refresh
still performs the only replacement. No private post identifiers or body text
are recorded here.

## Post-content recovery checkpoint: 2026-08-20

The operator backfill path now finalizes the post-content job ledger in the
same transaction as persisted semantic units. A successful synchronous
backfill therefore cannot leave a terminal failed job beside successful
buyer-visible content.

- A bounded private run processed four authorized posts, persisted 89
  embedding rows, and produced one image description with one region artifact.
- The same run persisted one footnote unit and resolved all inspected text
  structure decisions.
- A table-shaped post produced 45 semantic units, including 14 table-row
  units, and its ingestion ledger ended in `succeeded` with an operator audit
  event.
- These are bounded runtime observations only; they do not establish
  corpus-wide parser accuracy or protected-main behavior.

The explicit terminal retry and ledger-finalization contract is recorded in
ADR 0115. PR #311 remains an active stacked delivery candidate; its required
checks and formal approval must be rechecked at the exact current head before
any protected merge claim.

 ## Source-only indentation checkpoint: 2026-08-20

The semantic-unit parser now keeps source leading whitespace and declared
HTML/CSS/OOXML or list-container indentation as separate evidence. Visual
alignment alone cannot become an `explicit` hierarchy level; it is sent to
contextual-orchestrator when available and otherwise remains `unresolved` at
level zero. This prevents mixed editor exports from manufacturing deep list
nesting in the buyer view.

- Decision record: ADR 0103
- Implementation: PR #319, stacked on the adjacent-table correction in PR #317
- Local evidence: backend `731 passed, 16 skipped`; frontend `134 passed`, lint,
  build, and Storybook build passed.
- Integration status: PR #319 is not protected-main truth; exact parent head,
  formal review, terminal Checks, and post-merge browser evidence remain
  required.

 ## Partial visual-region checkpoint: 2026-08-20

The visual locator contract may return valid salient panels without complete
image coverage. The normalizer now keeps those panel coordinates for
region-level OCR and embeddings, then analyzes the original parent image once
so uncovered text is not silently lost. Empty or invalid locator output keeps
the existing whole-image fallback.

- Decision record: ADR 0104
- Implementation: PR #320, stacked on PR #319
- Local evidence: backend `731 passed, 16 skipped`; focused image/normalization
  tests `39 passed`; frontend lint, `134 passed`, build, and Storybook build
  passed.
- Integration status: PR #320 is not protected-main truth; exact stack heads,
  formal review, terminal Checks, and authorized post-merge image evidence
  remain required.

## Current exact-head audit: 2026-08-20 continuation

The protected GitHub state was re-read after the embedding and visual-region
checkpoints. These are gate observations, not merge claims. A blank review
decision means no independent approval was observed; `UNSTABLE` and `BLOCKED`
are not release evidence.

| PR | Base -> head | Exact head | Review/check state |
|---|---|---|---|
| #258 | `main` -> `feat/analysis-run-name-evidence-lineage` | `49804b0fef503be1697b8be61919b022b615ef2f` | `REVIEW_REQUIRED`, `BLOCKED`; no independent approval observed |
| #323 | `main` -> `fix/tepp-request-contract-validation` | `1a27efec6863cd3439a4c6023e1c625ce4d7abf2` | `REVIEW_REQUIRED`, `BLOCKED`; required Checks queued |
| #322 | `fix/stale-summary-buyer-continuity` -> `feat/orchestrator-owned-embedding-consumer` | `1126cfa026876d2427a6f6cf6001eaa8ac609ad5` | `BLOCKED`; per-batch embedding model provenance reset and regression covered; required Checks and fresh independent approval pending |
| #320 | `codex/normalize-source-indent-semantics` -> `codex/preserve-partial-image-regions` | `41d164c570fe232cc1e38a766439e4093d80cb84` | `CLEAN`; Full test and frontend Checks SUCCESS; independent approval pending |
| #324 | `codex/preserve-partial-image-regions` -> `fix/validate-partial-image-regions` | `fdd62a6f8317c93f9ba5fc27393cfb26c69e584a` | `CLEAN`; Full test and frontend Checks SUCCESS; independent approval pending |
| #325 | `fix/validate-partial-image-regions` -> `docs/current-gap-audit` | `4f87b109e6b423dd3429ec226403c63dfc6eac87` | `UNSTABLE`; semantic HTML/Word/OOXML footnote units preserved, body citations remain body text, fresh runtime aggregate evidence is recorded, and #322 provenance guard is tracked; required Checks and fresh independent approval pending |
| #789 | `main` -> contextual-orchestrator embedding capability branch | `3a80d91b8c879e57d30ab87af664546b8712fb15` | `REVIEW_REQUIRED`, `BLOCKED`; upstream Checks queued |

The current implementation checkpoints are local/branch evidence only:
The LineageWeave consumer-side embedding model discovery change is proposed in
PR #322; its ADR 0118 is intentionally not claimed as present on this stacked
branch. Visual locator validation is stacked in #324. Exact-head OpenCode review requests were
issued for #258, #322, #323, #324, and upstream #789. No protected branch was
approved, force-pushed, or merged from this audit.

This update supersedes neither the historical PR table nor the closure
criteria above; it supplies the current gate snapshot needed before the next
review -> fix -> Checks -> merge decision.

## Locator-bound validation checkpoint: 2026-08-20

The partial-region path now rejects non-finite, zero-sized, negative, and
out-of-bounds locator boxes before crop or persistence. Valid panels remain
independently searchable; if every returned box is invalid, the existing
parent-image fallback preserves an honest image-level outcome.

- Decision record: ADR 0104
- Implementation: PR #324, stacked on PR #320
- Local evidence: normalization module branch coverage `100%`; focused image,
  persistence-edge, and normalization tests `52 passed`.
- Integration status: PR #324 is not protected-main truth; its exact current
  head, formal review, terminal Checks, and browser evidence remain required.

## Exact-head refresh: 2026-08-20 23:41 KST

PR #324 advanced to exact head
`b1d1b106419488a0e9f9b608bab98fc1004972c8` after the malformed-locator
fallback and the duplicate baseline-status note were corrected. The local
documentation invariant confirms that the PR #320 integration-status note
appears exactly once. Earlier Python, frontend, build, and Storybook evidence
continues to apply to the unchanged visual-locator implementation. GitHub's
required PR Checks are running for this exact head and no formal approval is
bound to it, so this is not a merge or release claim.
 ## Image locator and buyer table checkpoint: 2026-08-20

A first bounded private reprocessing run completed five parent-image
descriptions and five region embeddings, but aggregate inspection found five
full-image boxes, zero decomposed boxes, and four described region rows. Those
boxes were emitted by the locator and were not evidence of five meaningful
regions. After the full-image guard was deployed, a second bounded run
completed five parent-image descriptions, zero region rows, zero region
embeddings, and 21 total unit/image embedding rows. The final aggregate was
zero full-image boxes, zero decomposed boxes, and zero described region rows.
The parent image channel is usable; detailed visual decomposition remains an
unproven capability rather than a fabricated success.

The normalization path now preserves that distinction: an invalid, partial, or
single full-image locator response keeps parent-image OCR/caption evidence but
does not invent a full-image region row. Buyer OCR that preserves consistent
pipe-delimited rows is rendered as an HTML table, while ordinary OCR remains
readable text. ADRs 0077 and 0110 record these boundaries. The gateway emitted
BrokenPipe errors after timed-out client calls during the bounded run, so the
locator/region latency budget remains an open operational gap.

## Live protected-gate checkpoint: 2026-08-20 22:30 KST

The live repository scan found 35 open pull requests, including two drafts, and
zero formal `APPROVED` reviews at their observed heads. Therefore no pull
request is represented here as protected-main truth or as merge-ready.

PR #270's exact head retained its application checks as successful, but the
external Strix job failed closed after GitHub Models returned HTTP 410 for a
scheduled retirement brownout. The failed job was re-requested directly against
that same head and is queued for revalidation; this is provider availability
evidence, not a source finding and not permission to bypass Strix.

PR #282's exact-head review request was corrected after an earlier comment
contained a stale SHA. Its duplicate ADR-number repair passed the local full
backend suite (`776 passed, 16 skipped`), while the remote Checks remain queued.

The central `.github` scheduler source and focused tests confirm that stacked
pull requests can dispatch the required OpenCode review through the central
repository when the same-repository dispatch credential is present. Current
central dispatch runs are queued by Actions capacity; queue presence is not
treated as approval, a successful review, or a merge result.

This checkpoint is an operational snapshot only. Recompute exact head, formal
review, required Checks, dependency order, and post-merge SHA immediately before
any protected merge.

## Exact-head validation checkpoint: 2026-08-20 22:45 KST

The current stacked delivery head `efd4aab2` passed the local validation matrix:
the backend suite completed with `731 passed, 16 skipped`, frontend lint passed,
Vitest completed with `133 passed`, and the production Vite and Storybook builds
completed successfully. These results cover the checked-out stack only; the
remote PR Checks for #311 remain queued and no independent formal approval is
present.

The current branch is clean and its local HEAD equals the remote branch HEAD.
The product baseline therefore records these results as reproducible delivery
evidence, not as protected-main release evidence.

## Live browser acceptance checkpoint: 2026-08-20 22:55 KST

Against the running Compose stack, a Playwright browser completed the synthetic
OIDC login round trip, loaded a 50-item authorized board page, opened the first
post-detail popup, waited for its asynchronous evidence projection, and closed
the popup. The rendered popup contained 14 sections and 15 headings; the
observed `/api/me`, `/api/posts`, and detail/lineage calls returned HTTP 200.
No source identifier, title, body, or person name is stored in this baseline.

This proves the login-to-list-to-popup interaction for the current local
runtime only. It does not prove that the same journey is available on
protected-main, that private records are universally authorized, or that the
remote PR Checks have completed.

## Live gate refresh: 2026-08-20 22:54 KST

The current REST audit still finds 35 open pull requests and 12 open issues;
no current-head independent approval is available for the active merge queue.
PR #311 is open at `82b7b395` with both required Tests checks queued. PR #258 is
open at `49804b0f`; its current `Analyze (python)` check is queued and its merge
state is blocked. Earlier SQL/SAST comments are bound to predecessor commits,
so they are not treated as current-head failures without a fresh matching scan.

  The current evidence supports continued review/check processing, not a merge
  claim. Re-read the exact head, current review commit, all required Checks, and
  stack dependency immediately before any protected merge.

## Fresh runtime aggregate evidence: 2026-08-21 KST

The local Compose runtime was healthy for the backend, frontend, Keycloak,
contextual-orchestrator, PostgreSQL, and Valkey at the observed development
endpoints. A bounded PostgreSQL catalog projection recorded the following
aggregate counts without exporting source text or identifiers:

| Relation | Rows observed |
|---|---:|
| `source_post` | 43,839 |
| `post_summary_role` | 179 |
| `post_summary_person_mention` | 17 |
| `post_summary_action` | 88 |

Within `post_summary_action`, 30 rows had a requester assignment, 45 had a
processor assignment, all 88 retained evidence text, and 85 were bound to a
project. These figures demonstrate bounded persistence in the current local
runtime; they do not prove protected-main equivalence, complete-corpus
correctness, authorization coverage, or release readiness. Re-run the same
aggregate projection against the authorized deployment before treating it as
buyer-facing evidence.

## Current continuation checkpoint: 2026-08-21 08:39 KST

This section supersedes the older PR snapshot above for the PRs explicitly
re-audited in the current continuation loop. GitHub state is authoritative;
local tests below are branch-local evidence and are not merge evidence.

| PR | Exact head | Base | Current gate | Current evidence |
|---|---|---|---|---|
| #270 authenticated MCP Global Ask | `1881a3cc402d99d8494bd9b936be9099b43ca3e7` | `feat/event-lineage-node-keeps-gnb-focus-v2170` | BLOCKED; review decision empty | Local MCP/auth/Global Ask regression set: 45 passed; import-order correction pushed |
| #325 product/technical baseline | `d80d691cd8ed780a8fb0072199304f595b1ea75e` | `fix/validate-partial-image-regions` | BLOCKED; REVIEW_REQUIRED | This document, ADR 0102, and chunking changes are proposed, not on protected main |
| #328 member locale bootstrap | `d0e159872147c7d7bd8bbf042c5552041eb44a4a` | `fix/oidc-deep-link-locale` | BLOCKED; REVIEW_REQUIRED | Local Frontend locale/deep-link set: 82 passed; TypeScript and lint passed |
| #329 buyer-safe image evidence | `b5b08071ab869854da696566343e97feb04add20` | `fix/validate-partial-image-regions` | BLOCKED; REVIEW_REQUIRED | Local image/normalization/persistence set: 54 backend tests and 13 PostBody tests passed |
| #330 lineage DAG interaction coverage | `e14dd956ad2493c42a16076a2adc095e0df5733b` | `codex/normalize-source-indent-semantics` | BLOCKED; REVIEW_REQUIRED | Frontend regression-only PR; hosted gate and independent review remain required |
| #331 OIDC post deep-link regression | `72e842bad482b73974d8ab4f09d2385582c300d6` | `fix/member-locale-bootstrap-race` | BLOCKED; REVIEW_REQUIRED | Deep-link stack remains proposed and must be checked at its exact head |
| #333 Keyverse-authenticated MCP API keys | `236b83b5af9632f83457dcc822b792dc239bcc7a` | `feat/analysis-run-name-evidence-lineage` | BLOCKED; review decision empty | Remote agent added malformed-revoke coverage; hosted Checks restarted |
| #334 MCP API-key authentication | `89f19eb1378ac785b80ea344d6f4e6e2bbe4a312` | `agent/authenticated-mcp-global-ask` | BLOCKED; REVIEW_REQUIRED | Depends on #333 migration 0051; local full backend suite: 825 passed, 16 skipped |

### Current closure order

1. Revalidate each exact head after any remote-agent push; never use the older
   hash as merge evidence.
2. Merge #258 and its dependent buyer-surface stack only through the repository's
   required independent review and terminal Checks. Do not treat local evidence,
   a skipped review, or a queued workflow as approval.
3. Deploy #333's normalized `mcp_api_key` resource before enabling the API-key
   authentication path in #334. OIDC remains the fallback identity path when
   the key table is not installed.
4. After the relevant stack reaches protected main, run the real browser journey:
   login screen first, locale preference restoration, GNB navigation, source
   post popup, semantic image evidence, and MCP authorization. Record only
   aggregate non-identifying evidence here.

### Newly explicit product gaps

- The MCP key lifecycle and MCP bearer verifier are separate PRs and are not yet
  jointly deployable on protected main.
- The locale and OIDC deep-link fixes are separate dependent PRs; local tests do
  not prove that a logged-in browser session preserves `?post=` on the deployed
  stack.
- Buyer-safe image captions are covered locally, but region-level visual evidence
  and buyer rendering still require post-merge browser evidence.
- The older aggregate runtime table remains historical. It must not be cited as
  proof that the current PR heads or protected main contain these changes.

### Queue roots carried forward from the prior checkpoint

The current root entries from the preceding queue audit were revalidated before
this update and remain proposed, not shipped:

| PR | Exact head | Current gate |
|---|---|---|
| #258 buyer evidence board and ontology surface | `41036e2cd8095c5e7b9c333fd72c542cb676ef5e` | BLOCKED; REVIEW_REQUIRED |
| #309 persisted buyer image-region overlays | `d8a938cd6e7e72b8bc0a7b11149afcfcc7820270` | BLOCKED; REVIEW_REQUIRED |

This continuation checkpoint supersedes the earlier #332 documentation-only
snapshot by retaining its root-head evidence and adding the later MCP, locale,
image-caption, and DAG gate state above.

## Current exact-head continuation: 2026-08-21 09:09 KST

The review/fix loop re-fetched the independent roots and the status-clock
dependent stack after concurrent branch updates. The following are the only
current hashes used as merge evidence in this loop:

| PR | Exact head | Base | Local evidence | Hosted gate |
|---|---|---|---|---|
| #258 buyer evidence board and ontology surface | `41036e2cd8095c5e7b9c333fd72c542cb676ef5e` | `main@2feba74b75863810869cde680b19032a93fba413` | Python `718 passed, 16 skipped`; cleanup branch coverage `100%`; focused suite `18 passed` | required workflows queued; no formal approval; Devin review failure remains unresolved as a review gate |
| #323 TEPP request and search evidence boundaries | `3b57e1cad490b47496d0c25553d28a0c1e3e2ca3` | `main@2feba74b75863810869cde680b19032a93fba413` | Python `570 passed, 16 skipped, 4 warnings`; boolean contract-version regression added | Tests, Semgrep, and Security Scan queued; Devin is a comment-only review, not formal approval |
| #327 Searxng corroboration token precision | `e6ef7cc53bcfef1e3dd61705b9ab243251860730` | `main@2feba74b75863810869cde680b19032a93fba413` | Python `573 passed, 16 skipped`; focused relation suite `25 passed`; isolated line/branch coverage `100%` | required workflows queued; comment-only reviews; no formal approval |
| #326 Python-ahead status write clock | `f9c53e7c18a696260d60bfcdd7c0af5e07c1dda6` | `#327@e6ef7cc53bcfef1e3dd61705b9ab243251860730` | stacked Python `578 passed, 16 skipped, 4 warnings`; clock boundary tests `5 passed`; additive `0030` fixture path exercised | required workflows queued after the new exact head; no formal approval |

Claude's #323 review found no confirmed correctness, security, data-loss, or
authorization defect. The proposed SHA-format concern was checked against
TEPP's current published request schema and dismissed because `snapshot_id`
is specified as non-blank text, not as a SHA. The confirmed boolean type-test
gap was closed in #323. Claude's #326 review found no high-severity defect;
the valid CodeRabbit upgrade-path finding was closed by running migration
`0030` in the PostgreSQL fixture and testing 59 seconds, exactly one minute,
and two minutes.

These results are branch-local observations and hosted queue/review state;
they are not protected-main or release evidence. The next merge candidate is
#258 only after its exact current head has independent formal approval,
resolved review threads, and terminal required Checks. #327 is an independent
root that must be merged before #326; #323 can proceed independently. A queued
workflow is active work, not a blocker or a pass.

## Restack continuation: 2026-08-21 09:23 KST

PR #258 advanced normally after the ADR 0083 pin correction. Its current head
is now `4bb234476ca26aacdd645f3c495a161a2c441790`. The semantic-unit child
PR #302 was merged normally with that current base and now has exact head
`8e1bd783fa2cb3e565983fc3d7b9092d394ff814`; its local validation is Python
`740 passed, 16 skipped, 4 warnings`, frontend `137 passed`, lint/build/
Storybook passed, and chunking coverage remains 100%.

The #302 restack carries #258's reviewed immutable orchestrator pin and ADR
regression check. Hosted Checks and independent formal approval remain
required for both exact heads; no merge or protected-main claim is made.

## Current queue refresh: 2026-08-21 09:21 KST

The live queue now contains 45 open pull requests. The following branches were
opened or advanced after the preceding checkpoint and therefore must be
included in the next exact-head audit; this document does not treat any of
them as merge-ready:

| PR | Exact head | Base | Gate at refresh |
|---|---|---|---|
| #335 current exact-head gap checkpoint | `858f7e4913824b9899710bc5b1e51bc49b43ce52` | `docs/current-gap-audit@d80d691cd8ed780a8fb0072199304f595b1ea75e` | BLOCKED; REVIEW_REQUIRED; required Checks queued |
| #337 Naruon calendar event projection contract | `974cf8b4a5618a43b17584ab762af6630ee4acd0` | `feat/calendar-open-focus-event-lineage-v2140@221cc94db3780e82114ef553729c7a00da554532` | BLOCKED; REVIEW_REQUIRED; required Checks queued |
| #339 TEPP canonical Project history recovery | `26b83f06899a2ad416be746d9a6fb13042bb7659` | `feat/project-history-timeline-v2184-r3@cfc125cb65f26ed7e834976dbff12b6b9790b59c` | BLOCKED; REVIEW_REQUIRED; required Checks queued |

The queue count and gate fields are a point-in-time GitHub observation. Before
reviewing or merging any row, fetch its branch again, compare the exact head
with the review and all required Checks, and confirm the full dependency stack.

## Security-boundary continuation: 2026-08-21 09:40 KST

PR #333's MCP key lifecycle was re-reviewed with Claude and its confirmed
medium metadata leak was fixed. Exact current head is
`065d14f5022f052d8b096f4388a62cb227d12d9e`, based on #258's current
`4bb234476ca26aacdd645f3c495a161a2c441790`. The key table and application
now persist/display only the constant `lw_mcp_` family prefix, while the
random secret remains one-time creation output; the buyer's date-only expiry
is converted to the local calendar day's end.

Post-fix validation is Python `725 passed, 16 skipped, 4 warnings`, frontend
`132 passed`, MCP panel `3 passed`, lint/build/Storybook passed, and diff check
passed. These are branch-local results. #333 remains gated until exact-head
hosted Checks and independent formal approval are terminal-successful; #334
must not enable API-key authentication before migration `0051` is deployed.
