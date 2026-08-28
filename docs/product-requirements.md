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
- Preserve one imported primary Voice and allow a `post_admin` to add any
  governed atomic Voice only with an ABAC-visible evidence Post and explicit
  truth state; create the normalized PROV-O derivation server-side and never
  accept an opaque provenance assertion identifier from the caller.
- Let a `post_admin` connect another perspective from the live Post popup by
  choosing an unassigned atomic Voice and an explicit truth state; use the open
  authorized Post as evidence and hide the write action on cutoff views.
- Validate DB-to-RDF projections with SHACL, including complete reified
  ProjectMention subject/predicate/object chains.
- Keep SKOS broader/narrower distinct from OWL subclass semantics.

Acceptance: Turtle, JSON-LD, N-Triples, SHACL, API payloads, persisted IRIs,
and rendered labels agree on term kind, direction, namespace, and provenance;
an additional Voice cannot demote the imported primary or cite hidden evidence;
the exact-value table opens the carrying Post and its authorized derivation
evidence as distinct actions;
the authoring form has explicit selections, permission/cutoff gating, retryable
feedback, keyboard labels, and desktop/mobile Storybook evidence.

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

### PRD-FR-2B — Evidence-bound occupational constructs

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
UI remain unavailable until their separate ADR acceptance. ADR 0253 adds
catalog-bound semantic-unit extraction through contextual-orchestrator's
multi-agent conduct path; exact offered IRIs and verbatim spans are required,
and a digest-bound run record distinguishes a supported empty result from an
unavailable provider. ADR 0254 adds the authorized Post-detail evidence review
surface and honest complete, processing, and unavailable states. ADR 0255
projects assertion-backed constructs into the existing ABAC-filtered ontology
neighborhood without duplicating graph storage or promoting truth. ADR 0257
adds authorized catalog-label search: reviewers type an official O*NET label
and open the earliest visible supporting Post. Constructs without visible
evidence stay undisclosed. Occupation ratings remain unavailable.

### PRD-FR-2C — FJA I/O-Psychology cognitive, affective & behavioral semantic layer

- Project the DOT/FJA Data/People/Things worker functions into their
  grounded nomological network of cognitive, affective, and behavioral
  I/O-Psychology constructs (ADR 0251): information processing, mental
  workload, executive functioning, and appraisal; emotional labor,
  burnout, engagement, psychological safety, and commitment; task,
  citizenship, counterproductive, safety, proactive, adaptive, and
  withdrawal behavior.
- Declare each construct with its psychological dimension and an APA 7th
  literature anchor; keep `:CognitiveConstruct` / `:AffectiveConstruct` /
  `:BehavioralConstruct` disjoint and validate with SHACL.
- Keep FJA-derived constructs distinct from ADR 0248's evidence-bound
  O*NET-style occupational construct classes: no crosswalk, equivalence,
  or implied fit is asserted.
- Carry no numeric weight: the layer is a semantic taxonomy, never a
  calibrated measurement (ADR 0145 governs estimation).

Acceptance: `tests/test_iopsy_taxonomy.py` enforces construct coverage,
literature-anchored metadata, fail-closed lookups, per-function profile
completeness, and composite-job aggregation; `tests/test_ontology_shapes.py`
validates the disjoint SHACL shapes.



### PRD-FR-2B-2 — Occupational classification and worker-characteristic taxonomy

- Publish the 23 major groups of the 2018 Standard Occupational
  Classification (the O*NET job-family grouping) with official titles
  and codes verbatim, plus the four O*NET 31.0 job-zone categories with
  published names and source values 2 through 5 (ADR 0245).
- Publish the worker-characteristic families that work-related
  cognition, affect, and behavior resolve into: Fleishman's four ability
  domains, Holland's six RIASEC interest types with the published
  hexagonal adjacency relation, the six explicitly legacy O*NET work-value
  clusters, and
  the seven higher-order dimensions of the revised O*NET Work Styles
  structure.
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
`tests/test_io_taxonomy.py`; `tests/test_ontology.py` continues to pass
unchanged.

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
  (ADR 0264). Treat the six roots and 18 second-level branches as navigation
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
- Publish the eight O*NET 31.0 Ability, Essential Skill, Transferable Skill,
  and Work Style link tables to Work Activities and Work Context as 1,417
  directed, assertion-level provenance-bearing relations (ADR 0256). Treat
  relevance as neither a causal effect nor a numeric weight.
- Bind a construct to record content only through a provenance-bearing,
  evidence-cited assertion. Do not promote record evidence to a person trait,
  score, causal effect, or job requirement.

Acceptance: SHACL rejects incomplete record assertions; ontology tests
prohibit FJA equivalence, require exact Post/evidence/PROV statement structure,
and reproduce every pinned O*NET linkage with its exact source table. Runtime
persistence and UI remain unavailable until their separate ADR acceptance.

### PRD-FR-2D — Occupation-rating source observations

- Persist released occupation-to-element ratings as source observations, not
  ontology weights: release, source table, occupation, element, scale,
  optional category, value, sample/error/interval, suppression, relevance,
  exact source update month, and domain source remain independently auditable
  (ADR 0257); the product must not invent a day for O*NET's `MM/YYYY` field.
- Keep normalized reference identities in third normal form and partition the
  observation store by exact release then source table. An unknown partition
  fails closed instead of entering a catch-all table.
- Preserve decimals and missingness exactly. No local aggregation,
  normalization, person inference, or psychometric estimation is permitted.
- Reject divergent duplicate identities and owner-level truncation. Task
  Ratings remain unavailable until their integer Task IDs and statements have
  a separate normalized source-target contract.

Acceptance: the replay-safe migration creates the normalized store; the pinned
CSV importer validates both rating and scale-reference digests and row counts,
reference identity, source scale, uncertainty, flags, and dates before
persistence; PostgreSQL integration proves missing partitions fail closed and
repeated null-category UPSERT is idempotent.
API, UI, and derived modeling remain unavailable until separate accepted
delivery records.

### PRD-FR-2E — Occupation-rating evidence read

- Let an authenticated user open one exact release/source/occupation profile
  with both rating and scale artifact provenance (ADR 0258).
- Distinguish an unavailable imported source from an available source with no
  observation for the occupation.
- Preserve exact decimal text, uncertainty, suppression, relevance, source
  month, domain source, and declared bounds; derive no ranking or recommendation.

Acceptance: invalid identifiers and unbounded pages are rejected; an unavailable
source never appears as a negative profile; pagination is deterministic; and a
suppressed observation retains its value and warning flag together.

### PRD-FR-2F — Occupation-rating evidence view

- Let an authenticated user submit an exact O*NET-SOC code, release, and source
  from the existing Dashboard without changing the governed GNB (ADR 0259).
- Display published values beside bounds, sample/error/interval evidence,
  source time, and text warnings; link both source artifacts.
- Give different next actions for unavailable source, empty occupation,
  transport failure, and additional pages.

Acceptance: keyboard users can operate the form and named horizontally
scrollable table; narrow layouts retain complete values; suppression remains
visible beside its value; and Storybook covers populated, narrow, unavailable,
and empty states using synthetic data.

### PRD-FR-2G — Imported rating-source catalog

- Populate the occupation evidence selector only from imported artifacts that
  contain observations, preserving release and artifact provenance (ADR 0260).
- Exclude the scale-definition support artifact from the rating-source selector.
- Disable profile submission and state the next action while the catalog is
  loading, empty, or unavailable.

Acceptance: a user never types an internal release/source code; the selector
order follows persisted import time rather than parsed version heuristics; and
the real PostgreSQL integration test proves an imported synthetic artifact is
listed while its supporting scale artifact is not.

### PRD-FR-2H — Occupations represented in a rating source

- Populate the occupation selector with exact stored code/title pairs that
  have observations in the selected imported source (ADR 0261).
- Clear the current occupation and profile when the source changes, and clear
  the profile when the occupation changes; never mix continuation rows across
  occupations or sources.
- Keep unavailable source, available-empty source, loading, and transport
  failure distinct and actionable.

Acceptance: a user selects a stored title rather than typing an internal code;
the PostgreSQL integration test proves the source membership predicate; and
component tests prove selector changes clear prior evidence and pagination
stays bound to the loaded profile identifiers.

### PRD-FR-2I — Occupation catalog title filter

- Let an authenticated user filter the imported occupation catalog by
  published title or retained code without ranking or typed-code fallback
  (ADR 0262).
- Reset the filter when the source changes.
- Disable profile submission and state the next action when the filter
  matches no catalog occupation.

Acceptance: submitting still sends only a catalog identity; a non-matching
filter never creates a request; and Storybook covers a no-match state.

### PRD-FR-2J — Authorized job-family and job-series snapshots

- Import one authorized, pinned organization-specific source snapshot without
  committing runtime rows or creating an organization (ADR 0263).
- Keep job families, job series, standard occupations, organizational units,
  positions, people, and psychological constructs as distinct identities.
- Preserve source-declared multiple-family membership and validity dates; infer
  no parent or occupation binding from a code, label, similarity, or model.
- Persist a standard-occupation binding only when scheme IRI, version, code,
  and source relation are all explicitly supplied.

Acceptance: synthetic tests reproduce a series with two source-declared family
parents, reject cycles and partial bindings, leave an occupation-looking label
unbound, and prove the normalized snapshot store is immutable.

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
- Admit only persisted, provenance-bearing claims for exact cited public posts;
  source bodies, private facts, personal facts, measurement outputs, and claims
  nominated from question-token overlap never become external queries (ADR 0269).
- Retrieve bounded public evidence through SearXNG and adjudicate through
  contextual-orchestrator's verification mode.
- Report supported, refuted, and not-enough-information outcomes without
  promoting public pages to internal ontology authority.
- Keep external URLs visually and structurally separate from authorized
  internal post citations.

Acceptance: leaving the control off causes no public request; hidden or
uncited facts cause no public request; unavailable services fail closed; and
each displayed public judgment retains its originating internal evidence IDs.
An absent or unauthorized persisted envelope performs no external request and
reports that no public claim is available rather than fabricating admission.

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

### PRD-FR-5D — Ask citation and event navigation

- Link each numbered Ask citation to one authorized event card and preserve the
  same number when cards are ordered by observed time.
- Move focus citation-to-card and card-to-citation, then open the existing
  evidence layer or full source post.
- Name `event_occurred_at` or the `created_at` fallback; never turn chronology
  into a project start, predecessor, branch, or recommended response.

Acceptance: keyboard selection works in both directions, every card opens its
authorized source, missing time stays explicit, and any commercial next action
comes from the cited answer rather than frontend inference.

### PRD-FR-5E — Evidence-backed operations Dashboard

- For claim investigation, show the occurrence order, specification change,
  originating order, and sales-pool value only from authorized source spans.
- For rebid and handover, show the discussion, counterparties, our owner, and
  subsequent decision only from authorized source spans.
- Count external-information posts and events, report their share of all
  eligible posts in the selected period, and link their order, project, sales,
  and business relations to the exact supporting post.
- Persist closed-vocabulary milestones for claim, rebid, and handover. Report
  open, resolved, and evidence-missing counts and elapsed time only between two
  observed endpoints; never invent an endpoint or delay threshold.
- Present project-specific journeys only from accepted evidence-bearing
  predecessor and branch relations. A timestamp sort may be labeled observed
  events, but never promoted to a journey.
- Attach digest-bound interval-consistency evidence only to an already
  admitted predecessor edge. Temporal order alone never creates a predecessor,
  branch, responsibility handoff, or causal transition (ADR 0270).

Acceptance: every populated fact, lifecycle endpoint, membership, and journey
event opens an authorized evidence post; an incomplete provenance chain fails
closed instead of returning a partial fitted result.

### PRD-FR-5F — Product and Voice semantic evidence

- Extract product mentions through contextual-orchestrator from authorized
  semantic units and resolve only against normalized product group, model,
  variant, and trade-item identities with scoped GTIN or MPN identifiers.
- Keep unique, tied, missing, unavailable, processing, and successfully empty
  outcomes distinct; source changes invalidate derived analysis and failures
  remain durable and retryable.
- Link product relations to projects and operational facts through authorized
  evidence posts, and suppress live product inference in a historical view
  until a cutoff-bound product contract exists.
- Keep source-post Voice categories (`voc`, `vocc`, `voco`, `vom`, `vop`,
  `vos`, `voe`, `vob`, `vor`, `voi`, `voso`, `vops`) separate from
  organization relationship categories. Preserve source and derived
  multi-membership and disclose overlaps and disagreement without forced
  selection.

Acceptance: zero products is shown only after a completed current-input
analysis; absent or failed analysis provides the next valid action, and every
displayed product or Voice assertion retains navigable authorized provenance.

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
  ADR 0184, ADR 0207, ADR 0222, ADR 0246, ADR 0256.
- Semantic units and retrieval: ADR 0047, ADR 0062, ADR 0098, ADR 0102,
  ADR 0217.
- Evidence operations, products, and Voice: ADR 0206, ADR 0210, ADR 0225,
  ADR 0228, ADR 0244, ADR 0246.
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
