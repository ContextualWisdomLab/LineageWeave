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
- Keep name-derived Project candidates scoped to their evidence Post until a
  governed catalog resolution supplies a stable cross-record identity.
- Preserve truth status, valid/system time, provenance, and evidence
  references.
- Validate DB-to-RDF projections with SHACL, including complete reified
  ProjectMention subject/predicate/object chains.
- Keep SKOS broader/narrower distinct from OWL subclass semantics.

Acceptance: Turtle, JSON-LD, N-Triples, SHACL, API payloads, persisted IRIs,
and rendered labels agree on term kind, direction, namespace, and provenance.

### PRD-FR-2A — Worker-function taxonomy

- Publish the DOT/FJA Data/People/Things worker functions (24 concepts,
  official definitions verbatim) in the canonical ontology namespace
  (ADR 0232), each with its definitional ordinal rank. Do not infer a
  DOT-to-O*NET or Fleishman crosswalk that the authorities do not publish.
- Expose the taxonomy through a deterministic application read model with
  fail-closed lookups; an absent function is an honest unknown.
- Carry no numeric weight from the taxonomy: ranks are scale positions,
  never calibrated weights.

Acceptance: completeness, full verbatim definitions, deterministic ordering,
and lookup round-trip isolation are enforced by
`tests/test_worker_function_taxonomy.py`; `tests/test_ontology.py`
continues to pass unchanged.

### PRD-FR-2B — Occupational classification and worker-characteristic taxonomy

- Publish all four levels of the 2018 Standard Occupational Classification:
  23 major groups, 98 minor groups, 459 broad occupations, and 867 detailed
  occupations with exact source parents, titles, and codes (ADR 0252), plus
  the four O*NET 31.0 job-zone categories with
  published names and source values 2 through 5 (ADR 0245).
- Publish the worker-characteristic families that work-related
  cognition, affect, and behavior resolve into: Fleishman's four ability
  domains, Holland's six RIASEC interest types with the published
  hexagonal adjacency relation, the six explicitly legacy O*NET work-value
  clusters, and
  the seven higher-order dimensions of the revised O*NET Work Styles
  structure.
- Publish all 3,006 O*NET 31.0 Content Model Reference elements with exact
  identifiers, names, descriptions, and source-defined outline parents
  (ADR 0255). Treat the six roots and 18 second-level branches as navigation
  classes, never occupation ratings, person traits, scores, or weights.
- Declare typed derivation properties from classifications to
  characteristics but assert no instance binding; binding requires a
  versioned released source profile imported with provenance in its own
  decision.
- Expose everything through a deterministic application read model with
  fail-closed lookups; carry no numeric importance or level rating from
  any occupational profile.

Acceptance: completeness counts, verbatim titles, closed RIASEC
vocabulary, exact published adjacency pairs, deterministic ordering,
canonical namespace, and lookup round-trip isolation are enforced by
`tests/test_io_taxonomy.py`, `tests/test_soc_2018_hierarchy.py`, and
`tests/test_onet_content_model.py`;
`tests/test_ontology.py` continues to pass unchanged.
### PRD-FR-2C — Evidence-bound occupational constructs

- Keep cognitive abilities, work styles, work activities, affective
  reactions, and performance behaviors as non-equivalent construct classes
  (ADR 0248). FJA worker functions remain separate.
- Reuse official external identifiers and source-published relationships;
  never infer a DPT-to-psychology crosswalk or relabel work style as affect.
- Bind a construct to record content only through a provenance-bearing,
  evidence-cited assertion. Do not promote record evidence to a person trait,
  score, causal effect, or job requirement.

Acceptance: SHACL rejects incomplete assertions; ontology tests prohibit FJA
equivalence and require exact Post/evidence/PROV statement structure. ADR 0249
adds normalized, semantic-unit-bound persistence and an authorized Post-detail
projection. ADR 0250 synchronizes all official O*NET cognitive-ability,
work-style, and work-activity Content Model elements into that versioned
registry without importing ratings. Search, graph navigation, extraction, and
UI remain unavailable until their separate ADR acceptance.

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
- Apply authorization/time/process scope before ranking and again before
  response delivery.
- Keep internal post citations separate from external public citations.
- Interpret natural-language retrieval through contextual-orchestrator while
  accepting only literal question phrases; do not invent local stop-word,
  expansion, scoring, or weighting rules.

Acceptance: a semantic-only term can retrieve an authorized unit; private
content never becomes an external query or citation; and multilingual
conversational framing cannot suppress a persisted fact named by an exact
question phrase.

### PRD-FR-5 — Evidence operations

- Show persisted operational cases, actions, commitments, delivery status,
  and similar-VOC evidence with extractive citations.
- Preserve controls during loading and retry; discard responses from an
  earlier navigation scope.
- Distinguish pending, unavailable, failed, incomplete, and succeeded states.

Acceptance: each state tells the user the next valid action and never displays
stale evidence from a previously opened post.

### PRD-FR-5A — Opt-in public claim verification

- Persist an explicit per-question opt-in before any external search begins.
- Nominate only cited, public semantic/KG facts; source bodies, private facts,
  personal facts, and measurement outputs never become external queries.
- Retrieve bounded public evidence through SearXNG and adjudicate through
  contextual-orchestrator's verification mode.
- Report supported, refuted, and not-enough-information outcomes without
  promoting public pages to internal ontology authority.
- Keep external URLs visually and structurally separate from authorized
  internal post citations.

Acceptance: leaving the control off causes no public request; hidden or
uncited facts cause no public request; unavailable services fail closed; and
each displayed public judgment retains its originating internal evidence IDs.

### PRD-FR-5B — Knowledge-cutoff Global Ask

- Persist the optional cutoff with the asynchronous request and reject a future
  instant against the database clock.
- Apply authorization, eligibility, and cutoff filters before candidate limits,
  then cite the retained source revision available at that instant.
- Never replace a missing historical body or semantic channel with current
  state; expose the limitation and later-live-change status.
- Preserve the live contract when no cutoff is supplied.

Acceptance: a later rewrite never appears in a cutoff answer; an uncovered
revision is explicitly unavailable; and API and rendered citations identify
the retained revision and full/partial grounding state.

### PRD-FR-5C — Authenticated MCP Global Ask

- Expose asynchronous submission and owner-scoped job reading over MCP while
  reusing the REST application service and persisted answer payload.
- Validate the exact MCP resource audience, provisioned account, permission,
  affiliation scope, Host, Origin, and bounded request body before a tool runs.
- Consume one distributed quota unit only for an admitted authenticated tool
  call; preflight and rejected admission consume none.
- Require deployment-supplied, load-evidence-backed quota parameters and fail
  closed when shared Valkey cannot decide.

Acceptance: MCP and REST produce the same scope snapshot, verification opt-in,
knowledge cutoff, status, citations, and limitations; cross-account reads are
404-equivalent; and exhaustion returns the bounded actual retry interval.

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

## 7. Traceability

- Product/data boundary: ADR 0001, ADR 0089.
- Asynchronous delivery and database-pool isolation: ADR 0204, ADR 0213.
- Knowledge Graph, ontology, and provenance: ADR 0004, ADR 0011, ADR 0065,
  ADR 0184, ADR 0207, ADR 0222.
- Semantic units and retrieval: ADR 0047, ADR 0062, ADR 0102, ADR 0217.
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
