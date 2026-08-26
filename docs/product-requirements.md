# LineageWeave Product Requirements (PRD)

**Status:** Supporting product contract. ADRs remain normative for architecture
and policy.  
**Product boundary:** LineageWeave reconstructs and presents evidence-bearing
record lineage and semantic neighborhoods; it does not own source records or
perform psychometric/statistical estimation.

## 1. Product outcome

An authorized user can turn scattered, timestamped records into navigable
Event Lineage, inspect a distinct typed ontology/provenance neighborhood, and
follow every material claim back to permitted evidence. Missing providers,
hidden evidence, and unresolved semantics remain explicit unknowns rather than
invented facts, scores, weights, or identities.

## 2. Users and next actions

| User | Need | Product next action |
|---|---|---|
| Evidence reviewer | Understand how one record continues another | Open an Event Lineage edge, inspect channel evidence, then open its source records |
| Operations analyst | Find projects, people, organizations, events, and commitments | Open the typed semantic neighborhood or operations case, then inspect cited evidence |
| Measurement consumer | Read calibrated reports without confusing them with facts | Open the TEPP/fast-mlsirm provenance and model status; retry only when the authority is available |
| Administrator | Operate imports, rebuilds, retention, and integrations safely | Use authorized controls and audit status; never infer completion from a queued job |
| Integrator | Reuse LineageWeave standalone or as a module | Depend on published APIs/contracts and inject external services at their owned boundary |

## 3. Functional requirements

### PRD-FR-1 — Event Lineage

- Reconstruct bounded post-to-post parentage from independent channels.
- Keep Event Lineage separate from ontology/KG edges.
- Persist reconstruction profile and participating channel evidence.
- Drop unavailable channels and fail closed on malformed calibrated weights.
- Never label an inferred lineage edge causal or authoritative without
  separate evidence.

Acceptance: synthetic unrelated records remain separate roots; every visible
edge exposes the same authorized endpoints and evidence through API and UI.

### PRD-FR-2 — Ontology and semantic layer

- Publish one canonical repository-case OWL/RDFS/SKOS vocabulary with a
  dereferenceable lowercase compatibility vocabulary.
- Project typed Post, Person, CorporateEntity, Team, Project, and governed
  relationship evidence from PostgreSQL without creating a second mutable
  source of truth.
- Preserve truth status, valid/system time, provenance, and evidence
  references.
- Validate DB-to-RDF projections with SHACL, including complete reified
  ProjectMention subject/predicate/object chains.
- Keep SKOS broader/narrower distinct from OWL subclass semantics.

Acceptance: Turtle, JSON-LD, N-Triples, SHACL, API payloads, persisted IRIs,
and rendered labels agree on term kind, direction, namespace, and provenance.

### PRD-FR-3 — Bounded ontology exploration

- Apply RBAC/ABAC, source eligibility, and knowledge cutoff before graph
  assembly.
- Remove edges whose endpoint is hidden and reveal no hidden totals.
- Use deterministic bounded traversal and an opaque integrity-protected
  keyset cursor for continuation.
- Provide graph interaction and an exact-value alternative with the same
  authorized content.

Acceptance: tamper, scope drift, snapshot drift, unsupported terms, and
dangling endpoints fail closed; fixed input produces stable page boundaries.

### PRD-FR-4 — Semantic source and retrieval

- Preserve source representation and derive ordered paragraph, list, table,
  formula, conversation-turn, and image-region semantic units.
- Route embeddings, LLM, and VISION through contextual-orchestrator.
- Let an authorized administrator enqueue only a bounded page of eligible,
  incomplete posts into the durable worker ledger; acknowledge before model
  work and recover a missing broker wake-up from PostgreSQL.
- Apply authorization/time/process scope before ranking and again before
  response delivery.
- Keep internal post citations separate from external public citations.

Acceptance: a semantic-only term can retrieve an authorized unit; private
content never becomes an external query or citation.

### PRD-FR-5 — Evidence operations

- Show persisted operational cases, actions, commitments, delivery status,
  and similar-VOC evidence with extractive citations.
- For claim investigation, rebid response, and handover, persist closed-vocabulary
  milestones only when an authorized source span supports them. Report
  open/resolved/evidence-missing counts and exact elapsed time only between two
  observed endpoints; never invent an endpoint or delay threshold.
- Preserve controls during loading and retry; discard responses from an
  earlier navigation scope.
- Distinguish pending, unavailable, failed, incomplete, and succeeded states.

Acceptance: each state tells the user the next valid action and never displays
stale evidence from a previously opened post. An open lifecycle has a cited
start, a missing end, and nullable elapsed time; a resolved lifecycle links both
endpoint sources and names the source clock used for each instant.

### PRD-FR-5A — Ask answer evidence navigation

- Link each numbered Ask citation to one authorized event card and preserve the
  same number when cards are ordered by observed time.
- Move focus citation-to-card and card-to-citation, then open the existing
  evidence layer or full source post.
- Name `event_occurred_at` or the `created_at` fallback; never turn chronology
  into a project start, predecessor, branch, or recommended response.

Acceptance: keyboard selection works in both directions, every card opens its
authorized source, missing time stays explicit, and any commercial next action
comes from the cited orchestrator answer rather than frontend inference.

### PRD-FR-6 — Measurement boundary

- Consume TEPP accepted/completed wire contracts and fast-mlsirm outputs; do
  not reimplement their arithmetic.
- Use only provenance-bearing estimated weights anchored by independent
  lineage evidence.
- Keep calibrated measurement, reconstruction relevance, and external truth
  verification as distinct constructs.

Acceptance: missing/mismatched authority produces an unavailable state and no
theta, weight vector, or completed-measurement claim.

### PRD-FR-7 — Ecosystem contracts

- contextual-orchestrator owns model discovery, protocol translation,
  reasoning effort, and LLM/VISION/embedding routing.
- Keyverse owns identity; Naruon owns calendar/email projections; RankWeave
  owns ranking fusion; ThreadWeave owns reference threading; TEPP and
  fast-mlsirm own measurement.
- LineageWeave remains independently runnable and importable.

Acceptance: provider failure is visible at the owning boundary; no local
vendor selector, duplicate identity store, or psychometric substitute appears.

## 4. Quality and governance requirements

- Synthetic/non-identifying repository artifacts only; authorized runtime PII
  is protected by RBAC, ABAC, audit, purpose limitation, and retention rather
  than destructive mask-in-place behavior.
- PostgreSQL objects use normalized multiword names, idempotent replayable
  migrations, short transactions, and hot-partition-aware access paths.
- Provider-bound work that can outlive an interactive request uses a durable
  asynchronous job boundary and does not retain a pooled database transaction
  during provider execution. Authenticated concurrent HTTP behavior is
  measured end to end against synthetic Compose data; latency and concurrency
  become release thresholds only after a named deployment and representative
  workload establish an approved capacity/SLO contract. Release evidence
  includes observed Ask-job state counts, measured bottlenecks, and a capacity
  envelope rather than an unmeasured concurrency claim.
- Public APIs have bounded inputs, stable typed responses, and provenance-
  preserving failure states.
- WCAG 2.2 AA, keyboard/touch parity, responsive layouts, reduced motion,
  design tokens, Storybook edge states, and screenshot review apply to every
  customer-facing surface.
- Public functions/classes carry docstrings; changed behavior has statement,
  branch, edge-case, integration, and rendered acceptance evidence.
- Protected delivery requires exact-head terminal checks, zero unresolved
  review threads, independent approval, and a protected-main merge SHA.

## 5. Non-goals

- Owning or mutating an upstream system's source-of-truth records.
- Implementing calibrated mathematical/psychometric models in LineageWeave.
- Treating co-occurrence, attendance, similarity, or model output as a verified
  organization, customer, project, causal, or authoritative relationship.
- Exposing arbitrary SQL, Cypher, SPARQL UPDATE, provider credentials, prompts,
  hidden counts, or raw private evidence.
- Selecting models or weights with name-based guesses, fixed provider order,
  heuristics, or rule-of-thumb constants.

## 6. Release evidence

A release claim requires one exact protected-main head that proves:

1. repository-wide backend/frontend/security/docstring/coverage gates;
2. migration replay and PostgreSQL integration;
3. deterministic ontology publication and SHACL/PROV-O contracts;
4. authenticated aggregate runtime acceptance without identifying artifacts;
5. Storybook edge-state tests plus desktop/mobile screenshots;
6. external provider unavailable/failure/recovery behavior; and
7. synchronized PRD, ADR, architecture, API, changelog, and product-gap
   baseline.

### 6.1 Product identity and evidence relationships

The product must extract product mentions through contextual-orchestrator from
authorized semantic source units, validate verbatim evidence, and resolve only
against the normalized product catalog. Product group, model, variant, and
trade-item identities preserve their hierarchy and scoped GTIN/MPN keys.
Unique, tied, missing, and unavailable outcomes remain distinct. Product links
to posts, projects, orders, sales pools, specification changes, claims, and
external information reuse normalized evidence-bearing records and never
derive identity from keywords, tags, weak source sentinels, or arbitrary
similarity thresholds. Historical processing is bounded, asynchronous,
digest-idempotent, and authorization-filtered when read.

The source post voice scheme (`voc`, `vocc`, `voco`, `vom`, `vop`) and
post-scoped organization relationship scheme (the same five relationships plus
supplier `rel_vos`) remain distinct. Source and derived assertions coexist;
multi-membership and disagreements are reported without forced selection.
Authorized counts use the same period and organization/PU/team/person/product/
project filters and disclose overlapping category totals.

## 7. Traceability

- Product/data boundary: ADR 0001, ADR 0089.
- Asynchronous delivery and database-pool isolation: ADR 0204.
- Knowledge Graph, ontology, and provenance: ADR 0004, ADR 0011, ADR 0065,
  ADR 0184, ADR 0207, ADR 0228.
- Semantic units and retrieval: ADR 0047, ADR 0062, ADR 0102.
- LLM/model boundary: ADR 0070, ADR 0072, ADR 0076, ADR 0079.
- Measurement: ADR 0003, ADR 0145, ADR 0200, ADR 0205.
- UX and publication: ADR 0118, ADR 0159.
- Current delivery gaps and exact heads:
  [`product-technical-gap-baseline.md`](product-technical-gap-baseline.md).

## 8. Ecosystem product-authority register

Repository names below preserve their canonical case. A missing standalone
PRD is not filled by inference; the listed product/architecture source is the
current boundary until that repository adopts one.

| Repository | Product authority read | LineageWeave relationship |
|---|---|---|
| `ContextualWisdomLab/TEPP` | `docs/product/prd-v0.4-approved.md` | Versioned measurement request/result consumer; never reads TEPP storage or computes its models |
| `ContextualWisdomLab/contextual-orchestrator` | No standalone PRD; `docs/product_planning.md`, `docs/architecture.md` | Provider-neutral LLM/VISION/embedding gateway and model/orchestration owner |
| `ContextualWisdomLab/fast-mlsirm` | `docs/PRD.md` | Pinned domain-neutral measurement dependency; not temporal-event authority |
| `ContextualWisdomLab/keyverse` | `docs/PRD.md` | Production OIDC/JWKS/identity control plane; local demo Keycloak is not Keyverse |
| `ContextualWisdomLab/RankWeave` | No standalone PRD; `README.md`, `ARCHITECTURE.md` | Store-agnostic ranking/fusion dependency; caller owns channels and authorization |
| `ContextualWisdomLab/ThreadWeave` | `docs/PRD.md` | Deterministic reference-thread assembly dependency; LineageWeave owns records and persistence |
| `ContextualWisdomLab/DiskSage` | No standalone PRD; `docs/superpowers/specs/2026-07-10-disksage-design.md` | Prospective storage-policy boundary; no current runtime integration |
| `ContextualWisdomLab/wardnet` | No standalone PRD; `README.md`, `docs/architecture.md` | Prospective gateway/network-policy boundary; no current runtime integration |
| `ContextualWisdomLab/naruon` | Scoped `docs/topic-intelligence/PRD.md` only | Owns observed calendar/email projections; LineageWeave owns commitments and combined display |
| `ContextualWisdomLab/LineageWeave` | This PRD, with ADRs normative | Evidence BI/orchestration, lineage, semantic projection, API, and UI owner |
