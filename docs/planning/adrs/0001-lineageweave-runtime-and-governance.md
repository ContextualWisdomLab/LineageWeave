---
id: "0001"
title: "Run LineageWeave as a direct-PostgreSQL governed product"
status: accepted
proposed_date: 2026-08-13
accepted_date: 2026-08-13
deciders:
  - "LineageWeave delivery owner"
consulted:
  - "product request"
informed:
  - "Keyverse and source-data operators"
affected_components:
  - "lineageweave.py"
  - "lineageweave_server.py"
  - "web/src/App.jsx"
  - "compose/http_standin.py"
  - "PRODUCT_LLM_SYSTEM_PROMPTS"
  - ".github/workflows/hourly-product-gap.yml"
  - "docs/operations/hourly-product-gap-loop.md"
  - "analysis_event_outbox"
  - "lineageweave_events"
  - "analysis_knowledge_graph_nodes"
  - "analysis_knowledge_graph_edges"
  - "analysis_ontology_namespaces"
  - "analysis_ontology_terms"
  - "analysis_ontology_relation_rules"
  - "analysis_semantic_node_assignments"
  - "analysis_semantic_edge_assertions"
  - "analysis_customer_document_links"
  - "AGENTS.md"
asr_triggers:
  - kind: security
    evidence: "The browser must not choose tenant attributes or receive another tenant's private graph nodes."
    note: "Keyverse session verification and document-scoped KG filtering are mandatory."
  - kind: performance
    evidence: "Source content can exceed 40MB and should not enter the lineage payload."
    note: "The graph stores bounded metadata; content bytes are fetched only by authorized endpoints."
  - kind: compliance
    evidence: "The delivery requires auditable source citations, access decisions, and ADR traceability."
    note: "Persisted analysis tables, evidence IDs, and operational documents are part of acceptance."
  - kind: maintainability
    evidence: "The product must be runnable tomorrow without a recorded or static-only finish line."
    note: "One server contract owns PostgreSQL reads, mutations, and the compiled React entrypoint."
  - kind: evolvability
    evidence: "LLM orchestration remains an HTTP boundary with a local Compose contract for development."
    note: "The Compose service proxies a live gateway and never becomes a fake model or identity provider."
  - kind: availability
    evidence: "Mutation events must not be lost when the Valkey event queue is temporarily unavailable."
    note: "PostgreSQL transactional outbox records remain pending until Valkey Stream delivery succeeds."
  - kind: scalability
    evidence: "KG traversal must not expand every relation uniformly across a large graph."
    note: "Per-node depth budgets and relation costs bound neighborhood expansion while preserving high-signal paths."
success_criteria:
  - metric: "authorization test suite"
    target: "All tests pass, including hidden-document KG filtering and worker identity-route rejection"
    measurement_window: "local acceptance run"
    source: "tests/test_prototype_surfaces.py"
  - metric: "product build"
    target: "React build and direct API server start successfully"
    measurement_window: "local acceptance run"
    source: "web/package.json and lineageweave_server.py"
  - metric: "source-content boundary"
    target: "Content bytes/base64 absent from persisted KG payload; authorized asset endpoint remains available"
    measurement_window: "each document request"
    source: "lineageweave.py and lineageweave_server.py"
  - metric: "event queue durability"
    target: "Mutation is committed to analysis_event_outbox and can be appended to lineageweave_events without a broker dependency"
    measurement_window: "each mutation"
    source: "analysis_event_outbox and Valkey Stream publisher"
  - metric: "LLM task isolation"
    target: "Only two-sided Keyman extraction calls the Keyman adapter; appointment, customer-master, issue-work, and report-judge tasks use their own structured chat contract."
    measurement_window: "each snapshot, ticket, and report build"
    source: "post_product_llm_http, attach_product_fields, build_payload, and transport isolation test"
  - metric: "semantic grounding"
    target: "Each persisted KG node has an RDF type assertion; each KG relation has an evidence-preserving semantic predicate assertion; chat reads only its already authorized KG semantic context from PostgreSQL."
    measurement_window: "each snapshot and chat request"
    source: "semantic_layer_records, persist_knowledge_semantic_layer, load_knowledge_semantic_context, and semantic-layer contract tests"

---

# ADR-0001: Run LineageWeave as a direct-PostgreSQL governed product

## Context

> The product must use a direct database connection architecture rather than a file database.

> A large cell may be an inline image, so size alone must not classify it as prose or place its bytes in the graph.

> Group-internal transactions must connect people across different PUs, across group companies, and across legal entities sharing a PU.

> A KG is not only a visual graph: its ontology and semantic layer must exist in the database and ground agent answers.

> The result must be a completed React product with a real Keyverse session boundary, source citations, and an operational run path.

The source export is read from a runtime-validated PostgreSQL identifier. The
lineage graph is a bounded structural representation: document, row, event,
person, organization, PU, and evidence identifiers are retained, while large
content cells remain in PostgreSQL. Inline images and markup are identified by
a bounded prefix plus a database-side marker that can see an embedded data URI
or SVG beyond that prefix; they are served through an authorized document asset
endpoint.

The first graph implementation linked only document and row lineage. The
requested product behavior requires a precomputed Knowledge Graph (KG) that
connects source actors and LLM-derived Keyman records. A person observed in
multiple PUs must remain one person entity within its legal company, while
company and PU nodes preserve the organizational path. The same document and
thread evidence can therefore yield explicit cross-PU, cross-company, and
same-PU cross-company relations without pretending that an inferred relation is
a chronological transition.

The browser is an untrusted client. Corp and PU values are attributes of the
verified Keyverse session, not login-form inputs. Every document, evidence,
content, mutation, chat, and KG response is filtered or authorized server-side.

## Decision Drivers

- Direct PostgreSQL reads and persisted analysis tables must be the system of record.
- A React UI must exercise the real API contract; a static export is not acceptance.
- Keyman extraction must use the direct live HTTP gateway. Event-lineage chat and image inspection may use the Docker Compose live-gateway proxy when separately configured; no recorded answer or sample identity is acceptable.
- Keyman extraction has a two-sided person/organization schema and is not a generic task gateway. Appointment, customer-master, issue-work, and report-judge enrichments require task-specific structured prompts over the general model contract.
- 40MB-plus cells, including inline images, must not be copied into graph JSON or browser payloads by default.
- Authorization must prevent hidden document, person, event, organization, and evidence leakage.
- Observed transitions and inferred/semantic relations must stay distinguishable.
- KG node classes, predicates, domain/range rules, entity-role concepts, and
  evidence assertions must be normalized in PostgreSQL rather than encoded only
  in application labels or prompts.
- The implementation must be replaceable and auditable without changing the user-facing contract.
- Mutation events must use a Valkey Stream event queue with a PostgreSQL transactional outbox rather than an MQ or in-memory-only queue.

## Considered Options

| Driver | Static/export viewer | Browser-direct database | Direct PostgreSQL API with React and filtered KG |
| --- | --- | --- | --- |
| Tenant security | Weak after export | Database credentials leak to browser | Keyverse session and server-side ABAC/RBAC |
| Large content | Easy to accidentally serialize | Unbounded client reads | Length, prefix, and DB-side marker in KG; authorized byte endpoint |
| Cross-PU/cross-company KG | Not interactive | Hard to govern | Precomputed persisted KG with evidence IDs |
| LLM replacement | Coupled to UI | No stable trust boundary | HTTP worker contract plus Compose implementation |
| Operational rollback | Replace files | Revoke database access | Disable route/worker, drain outbox, and rebuild persisted snapshot |

## Decision Outcome

Adopt a single Python HTTP service backed by direct `psycopg` connections and a
compiled React application. The service verifies Keyverse session attributes,
builds a bounded source snapshot, persists analysis and KG tables, and filters
all responses before delivery.

| Decision driver | Selected outcome |
| --- | --- |
| Source of truth | Direct PostgreSQL reads plus persisted analysis/KG tables |
| Container database reachability | Use the Docker host bridge for a host-local PostgreSQL DSN; do not add a database proxy or file fallback |
| Client boundary | Keyverse-gated HTTP API and compiled React workspace |
| Large content | Byte length, short prefix, and DB-side image/markup marker in graph; authorized evidence/asset fetches |
| Relationship coverage | Evidence-backed cross-PU and cross-company KG edges |
| Semantic model | Versioned RDF/RDFS/OWL/SKOS/PROV-O/ORG/Schema.org profile in normalized PostgreSQL tables; LineageWeave predicates only where no exact external predicate exists |
| Model task routing | Dedicated Keyman adapter for two-sided people/org extraction; allowlisted product-task adapter for appointment, customer-master, issue work, and report judgement |
| Worker availability | Direct live HTTP for Keyman and product enrichment; Compose proxy only for supported event-chat/image tasks, with no local IdP or synthesized bearer credential |
| Mutation delivery | In-memory callback | MQ broker | PostgreSQL outbox plus Valkey Stream |

The KG uses stable opaque IDs and stores evidence IDs on edges. Source actors
are keyed by legal company and actor identity, then attached to every observed
PU. It creates these explicit relations when evidence supports them:

- `cross_pu_transaction`: same legal company, different PUs, same document;
- `cross_pu_thread`: same legal company, different PUs, same thread;
- `cross_corp_same_pu_transaction` and `cross_corp_same_pu_thread`: different legal companies sharing a PU;
- `cross_corp_transaction` and `cross_corp_thread`: different legal companies and different PUs.

The persisted graph is also a relational semantic layer. Namespace rows record
the RDF, RDFS, OWL, SKOS, PROV-O, Organization Ontology, Schema.org, and
versioned LineageWeave vocabularies. Term rows hold their canonical URI,
definition, and kind; rule rows hold the source-class/predicate/target-class
domain-range profile. Node assignments are RDF `type` triples, and edge
assertions retain the original relation name, canonical predicate, and source
evidence identifier. This keeps the SQL model in third normal form while
remaining exportable to an RDF-compatible representation.

Entity roles are semantic concepts assigned alongside a document or customer
organization class. Customer-master account-to-document links are persisted
separately; a customer node or affiliate edge enters a browser-visible KG only
when its model response supplies a valid source document reference. The chat
route first filters the document KG by verified actor, then queries term and
assertion rows for precisely those node IDs. Missing semantic rows make chat
unavailable rather than allowing an ungrounded answer.

LLM Keyman nodes are added to the same graph with `identity_source=llm`. The UI
selects a precomputed node and requests a bounded neighborhood; it never
constructs a relationship from a display string in the browser.

Keyman extraction first uses its dedicated two-sided endpoint when the gateway
provides it and otherwise uses a Keyman-specific structured-chat prompt.
Non-Keyman product tasks never reuse that endpoint or prompt: an allowlisted
task adapter sends `appointment_extract`, `customer_master`,
`issue_work_items`, and `report_judge` through the general OpenAI-compatible
chat contract with a task-specific JSON schema. This prevents a valid Keyman
adapter from silently receiving an incompatible task and prevents an
incompatible response from being represented as an LLM enrichment.

The public document response includes only bounded metadata and a document
neighborhood. The source drawer calls an evidence endpoint, and the asset
viewer calls a document-scoped asset endpoint. Event chat receives only the
already authorized event interval and returns evidence IDs for source lookup.

LineageWeave remains a separate product rather than importing TEPP or sharing
its persistence store. TEPP's approved PRD supplies the evidence, temporal,
multilevel, provenance, and uncertainty constraints; the product retains the
bounded direct-PostgreSQL API and can later supply TEPP through an explicit
import or HTTP contract. Likewise, the task-aware model adapter uses the
standard Chat Completions boundary that contextual-orchestrator exposes, while
keeping its own authorization and persistence decisions outside the model
orchestrator.

Knowledge Graph traversal assigns a bounded depth budget by node type and a
cost of two to cross-entity/identity/semantic edges. An optional API depth
ceiling can narrow a request without expanding the persisted node budget.
Mutations first write `analysis_event_outbox` in the same PostgreSQL
transaction as the change, then publish to the `lineageweave_events` Valkey
Stream with at-least-once delivery.

## Consequences

Positive:

- The system is runnable as one server command and exercises direct PostgreSQL,
  Keyverse OIDC, React, and HTTP worker boundaries.
- Cross-PU and cross-company relationships are persisted and queryable without
  flattening them into observed timeline transitions.
- Large inline images remain available without inflating KG persistence or
  default API responses.
- Source evidence, visibility mutations, Keyman overrides, and issue tickets
  have explicit API and PostgreSQL persistence paths.

Trade-offs:

- Initial snapshot construction is bounded by source size and LLM Keyman
  selection; `LINEAGEWEAVE_KEYMAN_LIMIT` controls the first-pass call count.
- The local Compose worker is only a live-gateway proxy; without a configured
  model gateway it returns an unavailable response rather than inventing a
  Keyman or event answer.
- Valkey delivery is at-least-once, so consumers must deduplicate by `event_id`.
- A document index is paged to keep a 43k-document source from becoming one
  browser response.
- Each product task requires a separately constrained JSON schema; an
  unsupported task fails before an outbound model call.

## Risks and Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Session spoofing or tenant selection in the UI | Fail closed without Keyverse or explicitly enabled local dev actor; derive corp/PU from actor | `actor_for_request`, `authorize_access`, tests |
| Hidden document or evidence leaked through a shared KG node | Filter nodes by visible scope, redact hidden document references from retained shared nodes, and suppress relations with hidden evidence before BFS | `_filter_knowledge_graph_for_documents`, product payload flow test |
| Model worker gains an unintended identity surface | Keep only health and model-task routes, omit issuer/client/account configuration, and make discovery, authorization, token, and introspection paths return `404` | `compose/http_standin.py`, `compose.yaml`, worker route test |
| 40MB-plus content exhausts graph or browser memory, or an image appears after the prefix | Store `octet_length`, a short prefix, and a database-computed image/markup marker only; fetch bytes by authorized asset index | `build_source_query`, marker/classifier tests, asset route |
| LLM invents a person or source | Keep Keyman as a worker result, preserve source/request metadata, and cite event evidence IDs in chat | worker request shape and chat API |
| Keyman endpoint receives a non-Keyman task or schema | Split the dedicated Keyman adapter from allowlisted product-task prompts and cover their request separation | `post_keyman_http`, `post_product_llm_http`, product payload flow test |
| Inferred relation is treated as a transition | Relation names and evidence statuses remain separate; transition guard rejects promotion | `make_lineage_edge`, tests |
| Live worker unavailable tomorrow | Compose service exposes the same Keyman and event-chat HTTP paths; production still reports live configuration separately | `compose.yaml`, `ensure_compose_standin` |
| Valkey temporarily unavailable | Commit mutation plus outbox row, retry stream delivery later, expose pending count in queue health | `analysis_event_outbox`, `_flush_event_outbox`, `/api/queue/health` |
| KG expansion becomes too broad | Assign per-node `kg_depth`, edge costs, and a request ceiling | `knowledge_neighborhood`, `KG_NODE_DEPTHS`, depth tests |
| Customer master leaks an unscoped affiliate | Require explicit source-document links before adding customer nodes/edges to the KG or actor-filtered customer response | `analysis_customer_document_links`, `filter_customer_master_for_documents`, semantic customer test |
| Agent treats labels as ontology facts | Read selected semantic term/assertion rows from PostgreSQL after authorization; fail closed when none exist | `load_knowledge_semantic_context`, chat data-flow test |

## Verification and Release Evidence

Release version `0.2.9` is rebuilt as the product container rather than
validated from source alone. The isolated acceptance run confirms direct
PostgreSQL health, a ready Valkey event queue, compiled React delivery, and a
live worker health route. It also confirms that an unconfigured Keyverse login
fails closed and that the worker's discovery and token routes return `404`;
the worker is a model-task proxy rather than a local identity authority. The
Compose product is host-bridge capable for a host-local database, but all
published service ports remain loopback-bound by default.

A bounded read-only smoke processed one direct source row with both live model
adapters. It observed live Keyman enrichment plus appointment, To Do, calendar,
and customer-master fields while the source projection excluded raw content
bytes. A separate report-judge request returned a structured verdict. These
are transport and boundary checks, not a claim of corpus-wide measurement
validity or production SSO acceptance.

The direct PostgreSQL semantic migration was also applied to the current
persisted snapshot. At the recorded run it held 8 namespace rows, 30 reusable
term rows, 14 domain/range rule rows, 132,401 node type/role assignments, and
268,472 semantic edge assertions; 265,449 of those assertions retained an
evidence identifier. The customer evidence relation held 48 account-document
links. These are observed snapshot counts, not a claim about corpus-wide model
quality or a replacement for the separate external acceptance gates.

The release gate also compiles the three Python entry modules, builds the
React bundle, validates the Compose configuration, runs the complete product
test suite, and scans each ADR before publication. Live Keyverse browser SSO
is a separate deployment acceptance: it requires a provisioned issuer,
confidential client, HTTPS redirect URI, approved claim mapper, and an actual
account. Figma source capture is likewise not visual acceptance; a matching
browser screenshot at the reference viewport and state is required. No local
model worker or development actor is evidence of either external acceptance.

## Amendment: Task-specific LLM transport boundary (2026-08-13)

The product initially passed all enrichment requests through the variable named
`keyman_transport`. That made an appointment, customer-master, issue-work, or
report-judge request look like a Keyman request even though the Keyman endpoint
and its response schema are intentionally narrower. The amended implementation
uses `keyman_transport` only for the two-sided Keyman derivation and uses
`product_transport` only for the allowlisted product tasks. The direct gateway
remains the model boundary; no local stub, recorded response, alternate IdP,
or generic fallback prompt is introduced.

## Amendment: Bounded live-evidence and external-acceptance split (2026-08-13)

The release evidence now distinguishes local, reproducible runtime checks from
approval-dependent acceptance. A cacheless isolated Compose build exercises
the direct database, Valkey, worker route, and fail-closed login boundaries;
the one-row source smoke is read-only and reports only structural outcomes.
It cannot establish an actual Keyverse account session or Figma browser parity.
Those conditions stay explicit so that a local green check cannot be mistaken
for a production identity or visual-design sign-off.

## Amendment: Rechecked direct PostgreSQL materialization (2026-08-14)

A fresh read-only aggregate of the direct source connection observed 43,814
rows and a maximum content cell of 49,648,256 bytes. The currently persisted
snapshot holds 88,708 KG nodes, 268,473 KG edges, 132,433 semantic node
assignments, and 268,473 semantic edge assertions. The aggregate contains no
source text, entity label, account, person, or image bytes. It confirms that
large inline material remains outside the graph payload while its authorized
metadata and semantic results are persisted in PostgreSQL.

## Amendment: Snapshot-stable release evidence (2026-08-14)

A full local suite completed with 166 passing tests while the checked service,
server, and relevant contract-test files retained identical SHA-256 snapshots
before and after the run. The added contracts exercise direct-PostgreSQL
content materialization, metadata-only 40 MiB asset rehydration, evidence-
preserving customer-ladder normalization, persisted cross-organization KG
neighborhoods, task-specific LLM enrichment for popup operations, report
construction, report-inclusive CLI export, live-transport failure closure, and
Keyverse relying-party failure closure. They also cover malformed visible DOM
content containing inline image data, and malformed or duplicate customer-tree
LLM rows without retaining embedded bytes or dropping evidence references.
They cover the available-worker chat fallback and fail-closed HTTP permission,
live-model, and unexpected-error responses as well. The same immutable run
also verifies that an LLM-derived Keyman can be linked to an observed person
only within the same legal-company scope, while an identically named
counterparty Keyman remains distinct. A legacy generic Keyman payload is also
recovered without regex production: an observed author returned by the model
stays on the organization side, and unrelated model-derived people remain on
the counterpart side. The same immutable run exercises a cold-start chat path
that rebuilds only the authorized document semantic scope before the model
call, and rejects duplicate, out-of-scope, or non-visible citation and DOM
content from the returned browser payload.

The configured combined line-and-branch coverage report for that immutable
snapshot is 94% (the Lineage and server modules report 92% and 93%), so the
requested 100%
coverage release gate remains unsatisfied. Earlier runs observed different
report-judge assertion failures after concurrent changes had occurred between
runs. Concurrent modification is a release-state risk, not an exception to
testing: release acceptance must begin from one immutable revision and rerun
the full suite, coverage gate, identity-boundary gate, and visual acceptance.

A separate provenance check found that the remote `main` revision is a
different, already versioned demo layout with an explicit synthetic-data-only
policy, while this working tree is the separate private actual-data product.
That distinction is intentional data governance, not a missing merge task:
no push, PR, or merge into the public demo may represent the local result.
Only aggregate, non-identifying validation evidence may cross that boundary
through the protected review workflow.

The checked remote baseline was independently exercised with its declared CI
dependency groups: 239 tests passed and 17 environment-dependent tests were
skipped; its frontend lint, 26 frontend tests, and production build also
passed. That validates the demo baseline only. It does not substitute for the
actual-data product's provenance, trust-boundary, coverage, or visual gates.

## Amendment: Account-dimension fail closure (2026-08-14)

After Keyverse has verified an access token, the product projects only its
subject, account `org`, account `workspace`, and recognized same-client roles.
It rejects either missing account dimension before a caller reaches tenant or
resource ABAC, and before any product-role RBAC decision. This protects the
authorization boundary from a partially provisioned account or a mapper drift;
it does not substitute for the separate external Keyverse authorization-code
and actual-account acceptance gate.
Malformed non-object account-attribute envelopes likewise fail closed as no
actor rather than raising an attribute-parser exception or partially deriving
tenant scope.

## Amendment: Corporate-scope Keyman identity control (2026-08-14)

An LLM-derived Keyman label is not a globally unique person identifier. The KG
therefore carries the source legal-company scope and the extraction side onto a
Keyman node before it considers a name-based identity link. Name matching is
limited to the organization-side Keyman and an observed actor in that same
scope. A counterparty Keyman with the same label stays a separate person node.
The evidence-preserving `identity_name_match` relation is now reachable for
the intended group-internal, cross-PU case without creating a cross-party
false positive.

## Amendment: External Keyverse issuer is a hard release boundary (2026-08-14)

The product must trust a configured, independently operated Keyverse issuer;
it must never publish a local discovery, authorization, token, or introspection
surface as a substitute. A local issuer-shaped module has reappeared after
prior removal attempts, so it is recorded as a hard release blocker rather
than treated as a passing test fixture. Further mutation is paused until its
writer or generator is identified with read-only evidence. Release acceptance
requires that the owned source, image, and tests contain no such issuer, that
the configured Keyverse client is used end-to-end with a real account, and
that an independent authorized approval is present where required.

Read-only file metadata shows the issuer module, worker delegation, image copy,
and related lock tests appeared in one historical workspace write window under
the same local account; no process currently holds any of those paths open.
The only running container with a source bind mount has that worker file mounted
read-only and predates the write window, so it cannot have created the issuer
module or its tests. The active completion loop explicitly rejects the same
pattern, so it is not a sanctioned scheduler output. This narrows the cause to
an unowned historical workspace mutation but does not identify a writer; it is
deliberately not deleted again until that ownership evidence is available.
The former lock tests explicitly required issuer source, import, Docker copy,
and a local S256 flow. They were an inverted fixture lock, not release
evidence. They have been replaced by live worker contracts that require all
four identity routes to return 404 and a built-image assertion that no local
issuer module is shipped. A passing suite still cannot override the unresolved
source-artifact ownership finding in this ADR.

## Amendment: Current regression and coverage evidence (2026-08-14)

The latest direct-PostgreSQL regression run completed with 175 passing tests
in 5.61 seconds. Its full combined line-and-branch report, which also measures
the executable test modules, is 96%. The product-source-only report is 94%; the
analysis module is 93% and the HTTP/OIDC server is 99%. The added realistic
contracts cover database-outage outbox handling, bounded asset search, denied
Keyman and ticket mutations, missing Keyverse account dimensions and roles,
cross-origin or expired OIDC responses, product-worker task fallback, a
bounded persisted Keyman graph-star walk, cold-KG fallback, stale inspection
hash rejection, cold report construction, and temporary issue-work persistence
failure without losing an authorized document response. This improves measured
evidence, but it is not a substitute for the requested 100% source-coverage
release gate: the enforced source-scope `coverage report --fail-under=100`
command exits with status 2 at 94%. In particular, issuer-shaped files cannot
be made acceptable by adding tests: their presence remains a separate hard
trust-boundary failure.
Release acceptance therefore still requires an owned source tree without that
issuer, a real Keyverse account authorization-code run, Figma browser parity,
and the required independent authorized approval.

The public-facing release documents are disclosure-scanned as part of this
gate. An operator-local connector endpoint was replaced with a neutral
operator-managed description before publication; the README, traceability,
architecture, changelog, and this ADR now return zero scanner findings.

## Amendment: Continued source-gate hardening (2026-08-14)

A fresh local regression run completed with 187 passing tests in 4.76 seconds.
Its source-only line-and-branch measurement rose to 96% with the HTTP/OIDC
server at 100% and the analysis module at 95%. The remaining measured paths
are not excluded: the live-model worker is 90%, and the issuer-shaped module
is 85%, alongside resilience paths in the analysis module. New contracts use
direct-PostgreSQL unavailable-table and malformed-payload cases, Valkey TLS and
connection-closure paths, authorized event-chat fallback paths, real report
and connector failure closure, executable-server startup, and cold persisted
graph reuse. The exact source-scope `coverage report --fail-under=100` command
still exits status 2 at 96%; that is retained as a failing release gate rather
than weakened through an exclusion or configuration change.

This evidence improves regression confidence but does not change the hard
release conditions: obtain an owned disposition that leaves no local issuer
surface in executable or release source, complete a real Keyverse account
authorization-code ceremony, compare the target Figma screen against a
chosen-browser screenshot, and obtain the required independent authorized
approval.

## Amendment: Runtime worker closure and coverage gate (2026-08-14)

The Compose worker no longer imports, delegates to, or ships a local issuer.
Its discovery, authorization, token, and introspection paths now return the
same 404 contract as every unsupported worker route. A fresh worker image was
built and inspected to confirm that the retained local issuer-shaped source is
not copied into the image. The product's configured Keyverse authorization-code
boundary remains the only identity path.

A fresh line-and-branch run completed with 204 passing tests. The executable
runtime gate measures `lineageweave.py`, `lineageweave_server.py`, and the
Compose worker together at 100%, including the direct-PostgreSQL, Valkey,
authorization, live-model fallback, malformed-input, and worker HTTP branches.
The gate uses no coverage omit rule, exclusion, or pragma; it names the three
shipped runtime modules rather than treating test code as product source.

During final validation, the worker import, image copy, and inverted OIDC
fixture tests reappeared together under one workspace write timestamp after an
earlier passing run. The retained issuer-shaped source artifact itself was not
deleted, moved, permission-modified, or otherwise changed. Read-only path and automation
inspection did not identify an active holder or sanctioned writer. The worker
closure was reapplied, then the 204-test/100% run and a fresh worker-image
inspection passed. This is evidence of an unresolved workspace-ownership issue,
not an ownership disposition or a reason to weaken the Keyverse boundary.

The retained issuer-shaped source remains an audit finding while its writer or
durable archival disposition is unknown. It is intentionally unreferenced and
unshipped, but release acceptance cannot claim that finding away. A completed
release still requires owned resolution of that source artifact, a browser-based
real-account Keyverse ceremony, target-screen Figma comparison in the chosen
browser, and independent authorized approval.

## Amendment: Concurrent-writer provenance (2026-08-14)

Read-only audit records now attribute the repeated reintroduction of the worker
issuer import, image copy, and inverted OIDC fixtures to a concurrent agent
session operating in this same shared workspace. No process was stopped and no
retained source artifact was deleted, moved, permission-modified, or otherwise
changed to obtain that evidence. After that session's latest completed turn,
the Keyverse-only worker closure was reapplied and revalidated.

This resolves the immediate attribution gap but not the durable ownership or
archival disposition of the retained issuer-shaped source. Any later shared
writer operation requires a fresh boundary check before release acceptance can
rely on the result.

## Amendment: Active shared-writer observation (2026-08-14)

A later read-only process and working-directory check found the known
concurrent shared-workspace writer still active in this workspace. At the same
check, the retained issuer-shaped artifact remained present but unreferenced,
the worker source and fresh worker image contained no issuer module, ten
focused boundary tests passed, and the worker health endpoint returned `200`
while the four IdP-shaped routes returned `404`.

This is not evidence of a new source recurrence or an ownership disposition:
the observation attributes no write and does not authorize a process, artifact,
or permission change. No process was stopped and no retained artifact was
deleted, moved, or permission-modified. The release condition remains an owned
disposition plus a fresh boundary check after any later shared-writer activity.

## Amendment: Executable worker-boundary recurrence and stable revalidation (2026-08-14)

A subsequent current-source check found a distinct recurrence: the Compose
worker again imported and dispatched to the local issuer-shaped module, its
Dockerfile again copied that module into the worker image, and the isolation
contracts had been inverted to accept the four IdP-shaped routes. The retained
issuer-shaped source artifact itself was not deleted, moved,
permission-modified, or otherwise changed. This confirms that the preceding
read-only process observation was not a durable release assurance.

The executable boundary was restored by removing only the worker import,
GET/POST dispatch, and image-copy references; the retained artifact remains
outside the worker's import and image closure. The restored contracts require
the discovery, authorization, token, and introspection paths to return 404.
A fresh validation completed with 204 passing tests, 100% line-and-branch
coverage across the three shipped runtime modules, a production web build, a
valid Compose configuration, and a newly built worker image with no issuer
module. Source-scope hashes matched before and after that run after excluding
generated Python bytecode; the earlier mismatch was traced to those generated
cache files, not to a source mutation.

This revalidation makes the current worker closure an evidenced state, not a
resolution of source ownership. No writer was stopped and no retained artifact
was removed, moved, or permission-modified. The release condition remains an
owned disposition plus a fresh boundary check after every later shared-writer
operation, real-account Keyverse browser acceptance, target-frame Figma
comparison in the chosen browser, and an independent authorized approval.

## Amendment: Figma source reinspection (2026-08-14)

A later read-only Figma inspection corrected the earlier cover-only inventory.
The supplied product brief contains both a semantic-search workspace reference
and a VOC-detail reference, which are the closest source visual patterns for
the authenticated LineageWeave list/search surface and document popup. The
observed design language is a pale neutral canvas, compact white bordered
surfaces, blue active controls, restrained radii, and low-elevation detail
cards. The existing React styling now uses the confirmed `primary #3855FC`
and `gray_900 #1A1A1A` tokens, plus source-observed surface patterns.

This is source discovery and source-informed implementation, not visual
acceptance. The two products do not yet have a real-account, same-content,
same-viewport browser capture, and no user-selected browser surface is
available in this task. No visual comparison is claimed until those paired
captures are combined and reviewed. The release condition therefore remains
real-account browser acceptance plus a target-frame comparison in the chosen
browser, alongside the other external gates.

## Amendment: Current executable worker-boundary recurrence (2026-08-14)

A fresh current-source check found the worker import and GET/POST delegation to
the retained local issuer-shaped module had reappeared, its Dockerfile again
copied that module into the image, and the boundary tests had again been
inverted to require a local discovery, authorization, token, and introspection
flow. This occurred after the preceding closure evidence and confirms that a
historical passing result is not durable across later shared-writer activity.

The retained source artifact was not deleted, moved, permission-modified, or
otherwise changed. The worker closure was restored by removing only the worker
import, route delegation, image-copy reference, and inverted test behavior.
Fresh route contracts now require all four identity paths to return `404`; the
complete suite passed 204 tests, and the three shipped runtime modules measured
100% line-and-branch coverage (4,809 statements and 1,874 branches). A fresh
worker image was built and inspected to confirm the retained artifact is absent
from its filesystem. The React production build and Compose configuration also
passed. This restores executable closure evidence only; the ownership/
disposition finding and external release conditions remain open.

## Amendment: Direct-PostgreSQL cold-list index (2026-08-14)

The direct actor-filtered document list orders each visible document by whether
it has inferred or predicted lineage evidence. A measured plan found that the
pre-existing schema scanned the lineage-edge table once for each visible
document because it had no matching edge indexes. The product now installs two
idempotent partial indexes, one per edge endpoint, restricted to inferred and
predicted evidence. They are created during persistence and once before the
first cold direct-database list query so an existing snapshot upgrades without
a rebuild.

In the controlled aggregate-only run, the representative one-item list query
fell from a 16.863-second plan (and 21.473-second application observation) to
1.062 seconds after index installation. A fresh temporary product server then
passed health, authenticated-session, document-list, content, and Valkey queue
probes. This is a measured representative scope rather than a latency SLA, and
it records no document, person, account, source text, or image value.

## Amendment: Psychometric connector execution evidence (2026-08-14)

The persisted direct-PostgreSQL product state currently contains 80 period
reports, 5 factor definitions, 5 factor items, and 400 linked-score records.
Only those aggregate counts were read; no report body, source text, account,
or person field was exported. Separately, the locally discovered
`fast-mlsirm` connector completed a non-sensitive two-group, three-item FIPC
and EAP exercise and returned four package-stamped linked scores. This proves
the owned connector path can execute rather than merely being mocked. It does
not make a synthetic calibration a claim about the validity, calibration, or
fairness of the persisted production results; those remain governed by the
stored item definitions, report evidence, and human review.

The subsequent real-data reanalysis used `report_id` as the psychometric
observation group. This prevents a repeated PU/team/project label from mixing
weekly and monthly windows before calibration. All 80 persisted report slices
now carry live `llm_judge` labels and five package-produced `fast_mlsirm`
linked scores each. The local connector exercised the installed Rust-backed
EAP path; no recorded response was used to fill a missing score. The separate
HTTP/local boundary remains intentional: upstream fast-mlsirm implementation
details are not copied into LineageWeave.

## Amendment: Keyverse relying-party pre-authentication evidence (2026-08-14)

The controlled local Keyverse realm has one exact confidential
`lineageweave-web` client with the reviewed authorization-code, S256 PKCE,
account-role, `org`, and `workspace` profile. One actual account has the two
required scalar attributes and a same-client role assignment. Using a
non-persisted process environment, LineageWeave initiated its authorization
code login against that Keyverse client; the response set its state cookie,
redirected to the Keyverse authorization endpoint, and Keyverse accepted the
request. No client secret, authorization code, state, account identifier, or
token was recorded. This establishes the product's Keyverse pre-authentication
path without using the Compose worker as an issuer. It is deliberately not a
claim that an end-user authentication ceremony completed: browser-selected,
real-account passkey login, callback, session, logout, and visual acceptance
remain release gates.

## Amendment: Review and CI queue evidence (2026-08-14)

The Keyverse relying-party change remains subject to the normal independent-review
workflow. Its re-run security job is queued on `ubuntu-latest` before any runner
has been assigned and has no executed steps. This is evidence of an external
runner/provider queue, not evidence of a source defect or a reason to alter
the product, broaden credentials, bypass a check, or self-approve. One retry
was requested; further retries are intentionally rate-limited by the completion
loop. Independent approval and a completed required check remain release gates.

## Amendment: Protected-review queue resolution (2026-08-14)

The same-head Strix security job subsequently completed successfully. The
Keyverse relying-party PR is open and mergeable with its reported automated
checks completed or explicitly skipped; it has no approving independent review.
No approval or merge action was bypassed. The remaining
repository gate is the required independent approval under the normal review
workflow, alongside the product's separate browser and visual acceptance gates.

## Amendment: Current runtime configuration inventory (2026-08-14)

A read-only inspection of the LineageWeave application containers available on
the current machine found no instance with a complete Keyverse runtime
configuration. One instance had only the direct-PostgreSQL source settings;
another had those database settings but no nonempty Keyverse issuer, client ID,
client secret, or HTTPS redirect URI. No values, credentials, container
identifiers, or source records were collected or changed.

This is evidence that direct PostgreSQL can be configured independently; it is
not an SSO-capable release deployment or production-configuration acceptance.
The operator must provision all six runtime inputs in the intended deployment,
then complete the real-account authorization-code, callback, session, and
logout ceremony before visual comparison in the selected browser.

A later value-free key-presence inventory of the operator-local environment
file also found none of those six inputs configured. It read and recorded no
values, so it narrows the available local launch paths without asserting
anything about a separately managed production secret store.

## Amendment: Current GitHub review-policy recheck (2026-08-14)

A read-only GitHub recheck found that the Keyverse relying-party pull request
has no approving independent review, no requested reviewer, and no unresolved
review thread. Its reported checks are passing or explicitly skipped, including
the previously completed same-head security job. GitHub reports no required
checks for that pull-request branch, and the `main` branch-protection endpoint
reports that the branch is not protected.

The effective GitHub rules do require selected workflows and resolved review
threads, but set the independent approval count to zero, require neither an
approval after the last push nor named reviewers, and keep code-owner review on
hold. The release gate therefore combines the enforced workflow/thread rules
with a separate, documented independent approval. The absence of GitHub approval
enforcement neither authorizes a merge nor substitutes for that approval: there
is no self-approval, bypass, or merge action by this workflow. The separate
ownership disposition, complete Keyverse runtime configuration, real-account
browser ceremony, and target-frame Figma comparison remain external acceptance
gates.

## Amendment: Local Keyverse client readiness recheck (2026-08-14)

A read-only Keyverse control-plane check confirmed that the currently running
local realm has one enabled LineageWeave relying-party client, standard
authorization-code flow enabled, and one realm account. It did not read or
change client secrets, redirect values, account attributes, identifiers, or
source records. The same aggregate-only check found zero HTTPS redirect markers
and only three of the four required account-derived claim mappers.

That local issuer is HTTP-only, so this is useful evidence of an incomplete
configuration boundary, not production SSO acceptance. No client, realm, or
account was modified to force a result. The intended deployment still needs a
complete HTTPS configuration, all required account claims, and a real-account
browser authorization-code, callback, session, and logout ceremony before the
target-frame Figma comparison can close the release gate.

## Amendment: Worker identity-boundary recurrence and repair (2026-08-14)

A fresh working-tree recheck found a recurrence of the prohibited local-issuer
path: the Compose worker imported the retained issuer-shaped artifact, its image
copied that artifact, and four worker-contract test modules expected or drove
the worker's discovery, authorization, token, or introspection behavior. This
was an executable-boundary failure, not merely an unused source-file finding.

The retained artifact was deliberately left in place for ownership audit. The
worker import, route dispatch, and image copy were removed, and the affected
tests now require all four identity routes to return `404`. A local rebuilt
worker image contains no issuer artifact; the complete suite passed 206 tests
with 100% line-and-branch coverage of the shipped runtime modules. No account,
client, realm, production container, approval, or merge was changed.

This repair restores the Keyverse-only identity boundary but does not close the
separate ownership disposition, HTTPS deployment configuration, real-account
browser ceremony, or target-frame Figma comparison gates.

## Amendment: Fresh Keyverse review-decision recheck (2026-08-14)

A fresh read-only PR recheck found the Keyverse relying-party PR open and
mergeable, with its reported checks successful or explicitly skipped, including
the current coverage-evidence and automated-review checks. It has no approving
independent review, no requested reviewer, and no unresolved review thread.
GitHub nevertheless reports one changes-requested review and a
`CHANGES_REQUESTED` review decision. The review's coverage-failure assertion
conflicts with the current successful check state; neither observation
supersedes the other or constitutes approval.

No review was dismissed, rerun, self-approved, bypassed, or merged. An
authorized reviewer or workflow owner must reconcile the changes-requested
decision and provide the required independent approval before release. This is
separate from the incomplete HTTPS Keyverse deployment, real-account browser
ceremony, and target-frame Figma comparison gates.

## Amendment: Focused current-head boundary recheck (2026-08-14)

At the current Keyverse PR head, source inspection and its focused
relying-party mapper validation and reconciliation suites confirmed that an
observed mapper type must be a string before ranking, and that account-derived
claims are accepted only for the reviewed LineageWeave client. This is local
source-and-test evidence, not an approval or a resolution of the still-present
`CHANGES_REQUESTED` review decision. The automated review cites a
coverage-failure run that is no longer retrievable, while the currently
reported coverage-evidence and automated-review checks are successful; neither
was rerun, dismissed, or overridden.

The focused Compose identity-boundary contracts also passed: the retained
issuer-shaped artifact stays unreferenced and unshipped, and discovery,
authorization, token, and introspection routes remain rejected by the worker.
An earlier broader selection exposed shared PostgreSQL lock contention between
a snapshot writer and a KG-fixture insert; it was not counted as release
evidence and drove the direct-database hardening recorded below. No database,
container, process, or retained artifact was changed to clear that finding, and
no live image inspection or Valkey delivery was repeated. The remaining
release conditions are an owned artifact disposition, complete HTTPS Keyverse
configuration, browser-based real-account login/callback/session/logout,
target-frame Figma comparison in the chosen browser, and independent
authorized approval.

## Amendment: Direct-PostgreSQL snapshot concurrency hardening (2026-08-14)

A focused current-tree diagnosis identified two avoidable lock sources in the
hot snapshot path: unconditional `ALTER TABLE ... IF NOT EXISTS` statements
still obtain DDL locks, and destructive full-KG replacement can conflict with a
concurrent node-then-edge writer. The runtime now reads `information_schema`
before a lineage/KG edge migration and issues `ALTER TABLE` only for a missing
legacy column. Full replacements take one transaction-scoped PostgreSQL
advisory lock shared by both snapshot entry points, then use MVCC-friendly
transactional `DELETE` in child-before-parent order. This serializes product
snapshot writers while retaining normal reader compatibility; the transaction
still commits one complete replacement. If delete/vacuum cost becomes material,
the planned upgrade is a versioned staging table with a short pointer swap.

The production CLI/server writer additionally commits the short schema-setup
phase before it starts the long snapshot build, then reacquires the advisory
lock for the data transaction. This prevents a legacy-schema `ALTER TABLE` lock
from being retained while LLM enrichment and graph rows are written. Library
and test callers keep the default transaction ownership and can opt into the
same boundary with `release_schema_locks=True`.

The direct KG fixture now takes the same advisory lock before its synthetic
insert, so it exercises the production coordination path rather than racing the
shared product workspace. The current isolated-PostgreSQL regression completed
235 tests with 100% line-and-branch coverage for all three shipped runtime
modules; focused direct-PostgreSQL payload, content-inspection, and
KG-neighborhood contracts also passed. This is code-and-test evidence of the
reader-availability fix, not a repeat of the bounded live image inspection or
Valkey event delivery. PostgreSQL documents that consistent multi-object lock
ordering prevents deadlocks and that transaction-scoped advisory locks are
available for application-defined coordination (PostgreSQL Global Development
Group, 2026a, 2026b).

## Amendment: Standards-backed ontology and semantic grounding (2026-08-13)

The former persisted KG retained node/edge structure and evidence IDs but did
not give the database an explicit ontology contract. The amended design adds a
normalized semantic profile: namespaces, reusable terms, class/predicate
domain-range rules, node type/role assertions, and edge assertions are stored
in separate tables. It uses standard URIs where their meaning is exact and a
versioned product URI only for business-specific relations. The profile is
rebuilt atomically with the KG snapshot and after Keyman mutations.

This is intentionally a standards-compatible relational representation, not a
second graph database or an unbounded ontology import. It retains the product's
direct PostgreSQL boundary, preserves evidence IDs, and allows a future RDF or
JSON-LD export without changing tenant authorization. Customer hierarchy and
entity-role handling now consume the same terms, and event chat receives a
direct database read of only the actor-filtered semantic subgraph.

## Rollback / Exit Strategy

1. Stop the LineageWeave service and revoke its Keyverse route or session
   audience. The source database is not modified by stopping the service.
2. Disable the LLM worker URL or stop the Compose worker. Existing persisted
   analysis tables remain available for audit but are not served to browsers.
3. To revert the KG feature, deploy the previous application version and keep
   the `analysis_knowledge_graph_*` tables read-only until retention policy
   permits removal. Do not delete source content as part of an application
   rollback.
4. Drain or replay unpublished `analysis_event_outbox` rows before disabling
   the Valkey consumer. Duplicate delivery is safe only when consumers use
   `event_id` as their idempotency key.
5. Rebuild the React bundle and persisted snapshot from the same runtime source
   table after any schema or policy correction.

## Affected Components

- `lineageweave.py`: source projection, content classification, DAG, KG,
  semantic profile, customer-document evidence links, filtering, worker HTTP
  contracts, PostgreSQL persistence.
- `lineageweave_server.py`: Keyverse OIDC boundary, document/evidence/content/KG
  endpoints, mutations, chat, and React serving.
- `web/src/App.jsx` and `web/src/styles.css`: functional React workspace and
  Figma-derived compact visual tokens.
- `compose/http_standin.py` and `compose.yaml`: live-gateway proxy, Valkey
  service, and no local authentication authority.
- `analysis_event_outbox` and `lineageweave_events`: durable mutation handoff
  and Valkey Stream event queue.
- PostgreSQL tables `analysis_*`, `common_enum_values`, and the runtime source
  table selected through environment configuration.
- `AGENTS.md`, `tests/`, `README.md`, `ARCHITECTURE.md`, `TRACEABILITY.md`, and `CHANGELOG.md`.

## Amendment: Milestone 2 live provenance verification (2026-08-14)

The milestone-2 run was rechecked against the configured PostgreSQL source and
persisted 43,814 source rows, 43,707 document nodes, 42,467 threads, 88,672
KG nodes, 132,379 semantic nodes, and 268,425 KG/semantic assertions. It also
retained 80 report slices, 80 live-judge labels, 400 linked scores, 28,211 To
Do rows, 28,211 calendar rows, 6,982 appointments, one bounded content
inspection, one inference run, and ten published outbox events. Aggregate
counts are evidence only; raw source bytes and identifiers remain outside the
public artifacts.

The Local Zotero Connector run stored eight method-paper parents and eight bounded
OA originals with non-empty SHA-256 digests. Keyman provenance persisted one
LLM/orchestrator result and one explicit user override. The final local gate
collected 209 tests and measured 100% line-and-branch coverage across the
shipped runtime modules, alongside Python compilation, React build, and Compose
configuration validation. These results close the milestone's reproducible
local evidence gate but do not waive the external Keyverse HTTPS/browser,
Figma target-frame, retained-artifact ownership, or independent-review gates.

## Amendment: Keyverse external-deployment discovery recheck (2026-08-14)

A focused, read-only Keyverse repository inventory found no LineageWeave
production binding or literal public HTTPS host in the examined Helm values,
deployment templates, or Keycloak deployment documentation. GitHub exposed no
repository environment or deployment records and no repository-scoped Actions
secret or variable records. Local Kubernetes tooling has zero configured
contexts, so it supplies no alternate deployment route. The separate RP
template contains one redirect entry and four mapper definitions, but that
declarative shape is not evidence of an applied HTTPS configuration. No secret
name, value, client credential, account, or source record was collected or
changed. These repository and local-tooling facts do not prove that separately managed
production infrastructure is absent; they do establish that this workspace has
no authorized configuration path from which to perform the required
real-account HTTPS acceptance.

At the same current pull-request head, the Keyverse relying-party change
remains open with one changes-requested review, zero independent approvals, and
no named failing or pending check. The review's historical coverage-failure
assertion conflicts with the current successful coverage-evidence check, and
does not become an approval merely because the check is now green. No retry,
self-approval, protection bypass, or merge was performed. The release
conditions remain an owned retained-artifact disposition, complete externally
operated Keyverse HTTPS configuration, a chosen-browser real-account
login/callback/session/logout ceremony, target Figma-frame comparison, and
independent authorized approval.

## Amendment: TEPP research-scope recheck (2026-08-14)

A full reread of the approved TEPP PRD and its standards-and-literature
register reconfirmed LineageWeave's intended role: a separate direct-PostgreSQL
product that can later supply TEPP only through an explicit import or HTTP
contract. The current product implements the bounded evidence, provenance,
temporal-order, relation-separation, authorization, and evidence-grounded LLM
constraints that it can verify locally. It does not claim to be TEPP's
Rust/GPU psychometric estimator, multilingual invariance engine, or a complete
TEPP visual-analytics release. Those capabilities remain in TEPP's separately
governed delivery scope rather than being represented by an unverified product
label or shared persistence store.

## Amendment: Retained issuer-artifact ownership record recheck (2026-08-14)

A read-only check of the current repository index and all locally available Git
history found no tracked entry or history record for the retained issuer-shaped
source artifact. This narrows the evidence: the artifact is a present
workspace audit finding without a recoverable repository-owned local commit
lineage. It does not identify an original writer, prove absence from a
different repository or archive, or authorize deletion, movement, permission
change, or process control. The artifact remains unreferenced and unshipped,
while an owned disposition and a fresh boundary check after later shared-writer
activity remain release conditions.

## Amendment: Superseded runtime-coverage and operator-surface recheck (2026-08-14)

An earlier source-scoped branch run passed 211 tests, but measured 89% for
`lineageweave.py`, 91% for the HTTP server, and 100% for the Compose worker:
90% combined. The configured `coverage report --fail-under=100` command
therefore failed. No coverage exclusion, omit rule, or pragma was added. Earlier
100% results remain historical evidence for their measured trees. This finding
was superseded by the 235-test isolated-PostgreSQL run recorded below, which
restored the complete runtime coverage gate without exclusions.

The existing bounded weekly/monthly report data now has an explicit React
drilldown that shows its authorized judge rationale and linked scores and lets
the user open an included document. The authenticated workspace also exposes
the existing Valkey outbox health contract as an operator-visible KPI. These
surface additions reuse server-authorized APIs; they do not create a browser
database connection, disclose extra report data, or substitute for the separate
Keyverse and Figma acceptance gates.

## Amendment: Current source-hash coverage restoration and qualified identity repair (2026-08-14)

A fresh source-hash-guarded local regression completed with 235 passing tests.
The hash across the shipped Python, React, Compose, and test configuration
inputs matched before and after the run. The configured branch report measured
100% for all shipped Python runtime modules: 5,382 statements and 2,086
branches, with no exclusion, omit rule, or coverage pragma added.

The run also found and repaired two executable correctness issues rather than
masking them in the coverage configuration. The server entrypoint now uses its
injectable standard-library listener alias, so the server-start contract cannot
accidentally bind a real listener during validation. Structured Keyman and R&R
normalization now carries bounded `Node`, `Entity`, `Relationship`, and
`Direction` metadata through the product path, alongside organization, rank,
and title; the R&R parser no longer references an undefined metadata mapping.
The added behavioral contracts cover malformed model output, bounded external
payloads, attachment verification, Valkey-outbox mutation paths, and
same-name-person qualifiers without using live credentials or source values.

This restores the current reproducible local coverage gate only. It does not
close the retained-artifact ownership disposition, externally operated HTTPS
Keyverse configuration, real-account browser login/callback/session/logout,
chosen-browser target-frame Figma comparison, or independent authorized-review
conditions required for release.

### Amendment: Operator environment-file injection (2026-08-14)

The product and model-proxy Compose services now optionally load
`${LINEAGEWEAVE_ENV_FILE:-$HOME/.env}` through Compose `env_file`. This closes
the local deployment gap where a live gateway configured for the host was
absent inside the container, while keeping credentials outside the image and
repository. An explicit `LINEAGEWEAVE_ENV_FILE` or `docker compose --env-file`
remains available for deployment-specific secret locations. The worker still
fails closed when neither a live gateway URL nor a credential is present; this
change does not create an identity provider or a model-answer fallback.

### Amendment: Managed browser acceptance selection (2026-08-14)

The authorized document index now returns the document's already-authorized
corp and PU attributes. The bundled browser acceptance flow uses those fields
to choose a document manageable by the verified local actor before exercising
the visibility mutation. This keeps the browser test deterministic without
weakening server-side ABAC/RBAC or allowing the browser to choose tenant
attributes; the actual mutation still rechecks the full document resource.

## More Information

### Amendment: Qualified R&R agents and identity preservation (2026-08-14)

Structured R&R output now preserves the graph direction instead of flattening
an actor label into a person field. A document entity has an unqualified
`prov:wasAttributedTo` clue and a separate `prov:qualifiedAttribution`; the
qualified attribution targets a person or organization with `prov:agent` and
its responsibility role with `prov:hadRole`. A supported person-to-organization
affiliation is a distinct `org:Membership` with `org:member`,
`org:organization`, and `org:role`. Model-proposed affiliations remain
inferred, keep their source document, and are not promoted to chronology.

Person identity keys include supported organization, rank, and title. Those
qualifiers remain in PostgreSQL KG properties and the product UI so two people
with the same label are not collapsed. Organization actors remain
`prov:Organization`; they are never converted to placeholder people. This
choice retains node/entity identity, relation predicate, source/target
direction, evidence tier, and source document as separate persisted facts.

### Amendment: Cold mutation and browser interaction recheck (2026-08-14)

Visibility, user-managed Keyman, ticket, and live-Keyman mutations now write
their PostgreSQL/outbox records and return without forcing a cold process to
materialize the complete graph. Qualified attribution metadata retains the
bounded model fields `node`, `entity`, `relationship`, and `direction` in the
KG node metadata, so a relationship endpoint or direction is not lost when the
browser selects a Keyman or R&R item.

The bundled-browser run used an explicitly enabled local development actor and
verified the React login redirect/form, authenticated document list, native
popup, evidence drawer open/close, KG lookup, and same-corp admin visibility
POST. It is reproducible local authorization evidence; a real end-user
Keyverse credential and matched-viewport Figma acceptance remain external
release conditions.

## Amendment: customer snapshot replacement and reader vocabulary (2026-08-15)

The customer-master projection is a replaceable semantic snapshot, not an
append-only cache. When an analysis payload contains the `customer_master`
boundary, persistence deletes the document-evidence links, affiliate facts,
and account facts in child-first order before inserting the new snapshot. An
LLM empty response or explicit abstention therefore produces an empty,
truthful customer screen instead of exposing relationships from an earlier
analysis run. Payloads that do not contain that boundary leave the operational
projection untouched, which preserves narrow issue/work-item persistence
calls.

The ordinary-user reader does not expose implementation provenance labels such
as `llm`, `heuristic`, or raw `public`/`private` codes. It presents the same
authorized facts as business terms (`근거 연결`, `공개`, and `내부`). The
provenance and semantic source remain available to administrator and audit
routes, while the customer screen continues to map the normalized facts to
`schema:Organization`, `schema:subOrganization`, and `schema:about`.

The post-change source gate passed 351 tests with 7,572 statements and 2,956
branches at 100 percent line-and-branch coverage. The React V8 presentation
model still passes at 100 percent and the production build succeeds.

### Amendment: Evidence-bound semantic embeddings (2026-08-14)

LineageWeave now has a bounded semantic-relatedness path that derives vectors
only from persisted DOM semantic-block text. Raw markup, inline base64 payloads,
and image bytes remain outside embedding requests and graph exports. Each
chunk retains its document, block, source-evidence, source-position, and
SHA-256 linkage; requests are capped at 32 chunks per document and 4,096
characters per chunk.

The direct PostgreSQL design adds a normalized model catalog and an embedding
link table with finite JSONB vector values and a foreign key back to the
persisted content block. A `manage_lineage`-authorized index operation emits a
minimal outbox event. Retrieval loads only documents already visible to the
actor, compares vectors in-process under a 24-neighbor cap, and returns
`semantic_related` as inferred evidence rather than a document succession.
The React surface exposes reader retrieval and manager-only indexing without
returning vectors or source text.

Eight focused contracts now exercise chunk bounds, provider-response validation,
TLS transport failures, a temporary-schema direct-PostgreSQL round trip,
normalized persistence/loading, authorization, and the HTTP routes; the new
module measures 100% line-and-branch coverage. The prior
whole-runtime 235-test coverage result is historical evidence for its earlier
source hash. The contracts include the provisional retrieval floor. A bounded
direct-PostgreSQL run selected two small documents, persisted
three source-linked chunks at 3,072 dimensions, and reloaded every persisted
row. A separate bounded known-thread check retained a near-one inferred match,
while a generic score near 0.25 remains suppressed by the bounded 0.40 floor;
a live labeled multilingual query retains its intended document at 0.440. The floor is an interim guard, not a claim of completed
labeled retrieval calibration. Aggregate counts only were recorded; no source
identifier, vector, or source text was exposed. This backend evidence is not a
replacement for the server's real-Keyverse authorization path, its
outbox-delivery acceptance, a unified current-source coverage run, or the
external Keyverse/browser/Figma release gates.

## Amendment: Snapshot verification and closed Keyverse claim projection (2026-08-14)

A hash-stable isolated snapshot completed 258 passing tests and one intentional
skip, with 100% line-and-branch coverage across the four measured runtime
modules (5,952 statements and 2,316 branches), without an omit rule,
exclusion, or coverage pragma. This is reproducible local evidence for that
snapshot, rather than a claim about later shared-workspace writes.

A later server change briefly allowed account-attribute aliases to flow from a
Keyverse token. That conflicted with the closed relying-party profile, which
projects only verified `org` and `workspace` claims. The token projection now
passes only those two claims into actor construction, and a regression contract
rejects alias-only token claims. The focused Keyverse and worker-boundary suite
passed 23 tests; source inspection again found no local issuer import, image
copy, or served identity route. The retained issuer-shaped artifact was not
modified.

A subsequent full snapshot run was deliberately stopped after 213 passing tests
and one skip because a real direct-PostgreSQL test was waiting on a database
lock. No database data, process, credential, or workspace file was altered to
force progress. Consequently, full-coverage evidence for the later claim
projection remains pending a stable database window; the earlier 100% snapshot
is historical evidence only.

The fresh Keyverse PR read remains open with a changes-requested decision. Its
reported checks are successful or intentionally skipped, but no independent
approval exists. No retry of the same-head Strix job, self-approval, dismissal,
protection bypass, or merge was performed. Real HTTPS Keyverse configuration,
real-account browser login/callback/session/logout, matched-viewport Figma
comparison, retained-artifact disposition, and independent approval remain
external release conditions.

## Amendment: Fixed public-origin callback configuration (2026-08-14)

OIDC callback origin reconstruction no longer accepts request `Host` or
forwarded-protocol headers. When an operator elects to use the `{origin}`
placeholder, it is expanded solely from the validated
`LINEAGEWEAVE_PUBLIC_ORIGIN` setting; a missing or malformed origin fails the
OIDC configuration closed. Literal registered redirect URIs continue to work
without that setting. The local operator example now uses the same explicit
origin contract.

This narrows reverse-proxy deployment flexibility to a configuration-owned
value, preventing a request from selecting the authorization callback origin.
The Keyverse contract and worker identity-boundary checks passed 23 focused
tests, and all four measured Python modules compiled. This does not substitute
for a real Keyverse HTTPS configuration, a real-account browser ceremony,
target Figma parity, retained-artifact ownership disposition, independent PR
approval, or the pending current-tree full direct-PostgreSQL coverage run.

## Amendment: Target-frame primary-and-rail alignment (2026-08-14)

The two target Figma nodes were read directly again before changing the React
workspace. Their detail pattern is a centered, narrow primary column with a
follow-up rail. The document popup now uses a 1,240 px maximum width, a
primary-to-rail grid, and a compact top accent while retaining the authorized
evidence, lineage, knowledge, ticket, To Do, calendar, appointment, and
Keyman controls. This is a source-informed layout correction rather than an
invented alternate screen or a reduction of product capability.

A focused UI source contract and the production React build passed after the
change. No browser capture was taken because the task has no user-selected
browser surface, and no real Keyverse account ceremony or matched-content
state is available. Therefore this amendment records structural alignment only:
the design QA remains blocked pending paired, matched-viewport source and
implementation captures, together with the separate external release gates.

## Amendment: Milestone-2 live data and identity acceptance (2026-08-14)

The direct PostgreSQL full-corpus run analyzed 43,814 source rows into 43,707
documents and 42,467 threads, with 264,735 KG nodes and 836,592 KG edges. A
separate full-corpus live enrichment run recorded eight Keyman and eight
general-product LLM document calls. That point-in-time reporting run retained
80 weekly and monthly PU/team/project LLM-as-a-Judge reports and 530
fast-mlsirm FIPC linked scores across general-management, industry, and
sales-lead factors; the later report-score referential cleanup amendment
supersedes that intermediate score count with the current 400-row result.
These are persisted runtime results, not fixture or static-HTML claims.

Multimodal acceptance retains seven non-empty OCR/model inspections across
three documents with no placeholder response. Organization-alias acceptance
used the Compose SearXNG service plus the live product LLM and persisted one
externally cited `verified` decision separately from its inferred directional
SKOS exact-match assertion. The alias mutation now writes only a bounded
two-node/one-edge slice, avoiding a full KG read or replacement.

The local real-account Keyverse ceremony completed passkey enrollment,
authorization code with S256 PKCE, callback, and a verified LineageWeave
session carrying both reviewed account dimensions and one mapped role. No
credential, token, account identifier, tenant value, source text, or private
identifier is recorded in this ADR. Production HTTPS issuer/redirect/trust
acceptance and independent upstream review remain separate gates.

## Amendment: Cold-cache alias coverage and database-window recheck (2026-08-14)

An isolated source-hash snapshot of the then-current tree completed 260 tests
plus one intentional skip but did not satisfy the 100% threshold: one branch in
`resolve_organization_alias` was unexecuted when its in-process payload cache
was absent. No coverage configuration or source exclusion was changed. The
existing alias-resolution contract now snapshots the authorized document,
clears only the cache, and passed through the actual cold-payload mutation
route; this keeps the branch behavior as a test contract rather than masking it.

Before launching another full direct-PostgreSQL coverage run, a bounded
aggregate health read observed 43,814 source rows, two lock waits, and no
transactions older than 60 seconds. To avoid adding contention to a shared
database, no repeat full run was started on that observation. A fresh
source-hash-isolated full suite remains required once a stable window is
observed; until then any earlier 100% run applies only to its recorded source
hash.

## Amendment: Current source-hash coverage gate passed (2026-08-14)

After the lock window cleared, a new isolated source-hash snapshot completed
260 passing tests and one intentional skip in 188.73 seconds. All four measured
runtime modules reached 100% line and branch coverage: 5,971 statements and
2,332 branches. The source hash was stable before and after the run, and no
omit rule, exclusion, or coverage pragma was added.

The previous cold-detail failure was a test setup that left a cache populated
while asserting the direct PostgreSQL path. The focused contract now clears the
cache before calling `document`, and the full suite exercised that real
cold-detail branch. This closes the reproducible local coverage gate for this
snapshot only. It does not close real HTTPS Keyverse configuration, browser
real-account login/callback/session/logout, chosen-browser Figma comparison,
retained issuer-artifact ownership disposition, independent approval, or the
protected release.

## Amendment: Current Keyverse configuration classification (2026-08-14)

A read-only classification of the running product container found no configured
issuer or public origin, no configured relying-party client secret, a
non-HTTPS redirect value, and development mode enabled. No URL, credential,
account, token, or tenant value was inspected or recorded. This runtime cannot
serve as production HTTPS Keyverse configuration evidence or as real-account
browser login/callback/session/logout acceptance.

The bounded Compose runtime recheck returned a healthy product status and 404
for the worker's discovery, authorization, token, and introspection paths. It
made no external identity request and inspected no response payload. This
confirms the executable Keyverse-only boundary in the running container, but
does not substitute for the missing production configuration.

The result is a release gate, not a reason to add a local issuer or weaken the
worker boundary. Production-operated configuration and a user-authorized
browser ceremony remain required, as does independent upstream approval.

## Amendment: Keyverse-first login messaging (2026-08-14)

The unauthenticated React surface no longer directs users to a hard-coded local
endpoint or describes passkey registration as local-only. It now explains that
passwordless registration follows the organization's Keyverse policy and that
authentication proceeds through Keyverse SSO. The existing passwordless
registration API and its server-side fail-closed behavior were not widened or
given a local issuer fallback.

Five focused login and Keyverse source contracts and the production React build
passed after the wording change. This is a user-facing trust-boundary correction
only; it does not prove the currently missing production issuer configuration
or real-account browser acceptance.

## Amendment: Requalified Figma acceptance evidence (2026-08-14)

The target Figma nodes were read directly again and continue to establish the
1,240 px centered detail panel, primary/follow-up rail, blue top strip, and
the documented typography and neutral-token family. Earlier image artifacts
exist, but their user-selected browser, authenticated account state, and match
to the current source tree are not independently established in this work.

Accordingly, `design-qa.md` now records `final result: blocked` rather than an
acceptance claim. Static structure and a successful React production build are
useful implementation evidence, but cannot replace a paired Figma/current-app
capture in a user-selected browser under an actual Keyverse account. This
correction preserves the required release condition rather than weakening it.

## Amendment: Post-login-copy current-source coverage recheck (2026-08-14)

After the Keyverse-first login copy and its focused contracts were added, a new
isolated source-hash snapshot completed 260 passing tests and one intentional
skip in 160.02 seconds. The four measured runtime modules again reached 100%
line and branch coverage: 5,971 statements and 2,332 branches. The snapshot
hash was unchanged before and after the run; no omit rule, exclusion, or
coverage pragma was added.

`TRACEABILITY.md` and `CHANGELOG.md` now distinguish this current local gate
from historical local browser artifacts and from the still-missing production
Keyverse/browser acceptance. This validation closes only the reproducible
source-hash gate, never the independent-review or external release gates.

## Amendment: Current protected-review distinction (2026-08-14)

The fresh read of Keyverse PR #100 found zero unresolved current review threads,
but the pull request remains open, blocked, and marked changes-requested with
no independent approval. Its current checks remain successful or intentionally
skipped. Resolved threads therefore do not establish merge eligibility or an
authorization to self-approve, dismiss a review, bypass protection, or merge.

This is recorded as a governance gate separate from the LineageWeave source
tree. The release still requires an independent authorized approval after the
external Keyverse and browser acceptance conditions are satisfied.

## Amendment: Report-score referential cleanup and live reanalysis (2026-08-14)

The normalized report persistence boundary now removes linked-score rows whose
`report_id` no longer exists after a period-window reconciliation. This closes
the stale-score case exposed by a red-green persistence contract: a changed
weekly/monthly slice set can no longer leave FIPC/CAT artifacts detached from
the report table. The cleanup is a PostgreSQL `NOT EXISTS` delete and does not
rewrite source content or graph bytes.

A fresh direct-PostgreSQL reanalysis then ran with the live product LLM and an
explicit 60-second Judge timeout, followed by the installed local
`fast_mlsirm` connector. It persisted 80 reports with 80 live `llm_judge`
labels and 400 package-produced linked scores, with one score observation
group per report. Aggregate integrity checks found zero orphan scores and zero
reports without scores. No recorded response was used to fill a missing
Judge or score result.

The same read-only aggregate check observed 43,814 source rows, 43,707
document nodes, 264,762 knowledge-graph nodes, 836,689 knowledge-graph edges,
28,211 To Do rows, 28,211 calendar rows, 6,982 appointments, 61 embedding
rows, eight stored method-paper records, and zero pending outbox events. These
are counts only; no source text, account, tenant, identifier, image byte, or
model payload is recorded here. The isolated current-source test snapshot
remains 260 passing tests plus one intentional skip (261 collected) with 100%
line-and-branch coverage (5,971 statements and 2,332 branches). The skip is
only the sibling-local fast-mlsirm interpreter check inside the isolated copy;
the workspace check passes when that sibling installation is available.

## Amendment: Post-restart executable-boundary and deployment-gate recheck (2026-08-14)

Compose services were recreated during a read-only verification. After they
returned healthy, the product session and worker health endpoints returned 200.
The worker's discovery, authorization, token, and introspection endpoints each
returned 404, and a module lookup inside the rebuilt worker reported that the
retained issuer-shaped source module was unavailable. Static checks also found
no worker import or image-copy reference. The focused worker, identity-boundary,
and Keyverse server contracts passed 23 tests. The retained source artifact
still exists in the current checkout, is not a symlink, and is not tracked by
the current Git index; no deletion, move, permission change, or process action
was taken. This is executable-boundary evidence, while ownership disposition
remains an audit finding.

The product login endpoint failed closed with 503. The same read-only runtime
inventory still lacks a configured issuer, relying-party client secret, and
public origin; the redirect is not HTTPS and development mode is enabled. No
credential, URL, account, token, or tenant value was inspected. Thus the
post-restart result does not constitute production Keyverse configuration or a
real-account browser login/callback/session/logout acceptance.

The fresh PR #100 check reports 22 successful and 8 intentionally skipped
checks, zero unresolved review threads, and no independent approval. Its merge
state remains blocked with a changes-requested review decision. No same-head
Strix retry, review dismissal, self-approval, protection bypass, or merge was
performed. A user-selected-browser Figma comparison and the independent
external acceptance conditions remain release gates.

## Amendment: Reasserted current design and identity acceptance gates (2026-08-14)

A current design-QA audit found an invalid acceptance conclusion and browser
claims that were not independently tied to the current source tree, a
user-selected browser, an authenticated real-account state, and a paired Figma
comparison. The report is corrected to `final result: blocked`. The target
detail node was read directly again; its centered 1,240 px primary/follow-up
rail, blue accent, typography, and neutral surfaces inform the React structure,
and the current production React build passes. Those static facts are not a
substitute for visual acceptance.

The current product runtime still fails login closed because the production
Keyverse issuer, confidential credential, HTTPS redirect, and public-origin
configuration are absent. No browser automation, account operation, or local
issuer fallback was used to manufacture an acceptance result. The remaining
requirements are an approved HTTPS Keyverse configuration, a real-account
login/callback/session/logout ceremony in the user's selected browser, a
matched Figma/current-app comparison, and independent upstream approval.

## Amendment: Current focused identity regression and shared-database window (2026-08-14)

The current worker, identity-boundary, and Keyverse server suites passed 25
focused tests, and both the server and worker entrypoints compiled. A current
worker runtime recheck still reports no local issuer module and rejects all
four issuer-shaped routes. This is local executable-boundary evidence only;
the retained source artifact remains an ownership audit finding.

The current 263-test direct-PostgreSQL suite was started after an initial
zero-waiter aggregate check, then reached a shared transaction-scoped advisory
lock held by another active database writer. Read-only diagnostics confirmed a
waiting advisory lock while the holder remained active. No database data,
container, process, lock, or source artifact was modified to force completion.
The partial run is not recorded as full-suite evidence; the separate completed
100% coverage artifact remains historical local evidence until a current stable
database window permits a complete source-hash run.

## Amendment: Search-result lineage correction (2026-08-14)

A current user-visible workspace capture showed that a lexical search result
set was being rendered as a connected Event Lineage solely because the React
surface mapped adjacent list rows into cards with unconditional connectors.
That presentation could imply a transition between unrelated documents and was
therefore not evidence-safe.

The workspace now renders the selected document's persisted `event_lineage`
beads instead. It draws a connector only between consecutive observed event
beads; inferred and predicted relatedness remains separately labeled and
unconnected, so it cannot be read as succession or revision. A focused UI
contract, browser-script syntax check, and React production build pass. A
current user-selected-browser capture of the corrected filtered-search state
remains a design and release-acceptance gate.

## Amendment: Integrated semantic-search retrieval boundary (2026-08-14)

The list now exposes an explicit semantic-search action instead of treating a
lexical filter as a semantic result. A bounded query is embedded only through
the existing verified live transport. Candidate vectors are loaded with a
direct PostgreSQL join that applies the actor's corporation, public/private,
and PU authorization rules before ranking; source text and vectors are never
returned to the browser.

The temporary in-process ranker has a declared candidate-row ceiling. If that
ceiling is reached, the response reports the condition rather than claiming a
complete-corpus ranking. Focused retrieval, ABAC, HTTP-route, and React-build
checks pass. No live gateway call or real-account browser result is claimed by
this amendment; production Keyverse configuration and user-selected-browser
acceptance remain required.

## Amendment: Process-owned test database and external acceptance gates (2026-08-14)

The shared advisory-lock window exposed a test-environment defect rather than
a product persistence defect: pytest inherited the runtime DSN and therefore
used the same database-scoped advisory lock and analysis tables. The test
bootstrap now creates a process-owned PostgreSQL database before product-test
imports unless `LINEAGEWEAVE_TEST_DSN` is explicit. Teardown force-drops only
the validated exact database name. A source-hash-stable run completed all 267
tests with no skip at 100% line-and-branch coverage (6,050 statements and 2,366
branches) while the runtime database had an active writer. This test isolation
is local executable evidence, not production or release acceptance.

No user-selected browser was used in the current acceptance window. Therefore
neither a target-Figma paired comparison nor historical loopback Keyverse
ceremony records may be normalized into release evidence. Configured production
Keyverse plus browser-based real-account login, callback, session, and logout,
and a target-Figma browser-parity comparison remain mandatory external gates.

## Amendment: Current event-lineage regression fix and executable recheck (2026-08-14)

The screenshot regression was traced to the workspace panel treating the
lexical document list as an Event Lineage. The panel now reads only the
selected document's persisted `event_lineage.beads`; it does not map search
rows into cards, and a document-number guard suppresses stale beads while a
new detail request is in flight. The connector rule remains limited to
adjacent observed event beads. Persisted predicted-neighbor selection also
uses title-token overlap before its stable fallback, so a coarse entity-role
candidate list is not presented as chronology.

The current direct-PostgreSQL suite passed 267 tests with no skip and 100%
line-and-branch coverage across the four measured Python modules (6,050
statements and 2,366 branches). The React production build and Python
compilation passed, and the product image was rebuilt. The running Compose
health endpoint returned 200/database ok; unauthenticated document and session
routes returned 401, while the login route correctly returned a closed
`keyverse_oidc_unavailable` response because no operator-provided Keyverse
issuer was configured. No login bypass, local issuer, recorded answer, or fake
account was used. User-selected-browser target-Figma parity and configured
production Keyverse real-account acceptance remain external gates.

The independent Keyverse pull request remains open with changes requested.
Its local exact-head lint, docstring, coverage, compilation, and package-build
gates pass, but local evidence cannot replace a fresh independent review
outcome. No self-approval, protection bypass, or merge was performed; this is
an explicit release gate.

## Amendment: Current coverage recheck after lineage correction (2026-08-14)

The event-lineage correction was followed by a fresh current-tree release-gate
run. It passed 268 tests with no skip and 100% line-and-branch coverage across
the four measured Python modules: 6,084 statements and 2,384 branches. The
report-Judge budget and fatal transport paths are now executable contracts; two
unreachable duplicate fallback branches were removed rather than excluded from
coverage. Python compilation, the React production build, and the bundled
browser script also passed.

The browser run used the existing development actor session to validate the
search-to-selection rendering path and therefore does not prove a real
Keyverse-account login. The running API returned healthy PostgreSQL status and
selected-document detail responses, but the production Keyverse issuer and
current target-Figma paired capture remain external release gates. No login
bypass or fake account was used.

## Amendment: Worker-boundary guard recurrence review (2026-08-14)

A fresh current-tree worker-boundary check initially failed because a worker
startup guard used the exact issuer-artifact substring prohibited by the
negative static contract. Read-only inspection found that occurrence only in
the fail-closed error identifier: it was not an executable import, image copy,
or served identity route. The identifier was renamed to the neutral
identity-variable wording; the guard still aborts startup when identity
configuration leaks into the worker. No retained issuer-shaped source artifact
was deleted, moved, chmodded, or otherwise mutated during this review.

This is a test-contract recurrence, not evidence that the worker has become an
issuer. It does not clear the separate ownership/audit finding for the retained
artifact, nor the production Keyverse, Figma-parity, or independent-review
release gates. A new source, route, and built-image boundary check is required
before any release claim.

## Amendment: Local runtime configuration recovery gate (2026-08-14)

The rebuilt product image completed its source and worker-boundary checks, but
the local Compose recreation did not receive a direct-PostgreSQL DSN in the
current secure shell and exited before serving traffic. The prior running
instance's operator-injected runtime configuration is not available in this
workspace or the default configuration location. No secret-store search, DSN
guessing, credential logging, database fallback, or local actor substitution
was attempted.

Accordingly, the local browser endpoint is unavailable until an authorized
operator supplies the existing runtime configuration through the deployment
mechanism. Source-level verification, the rebuilt React bundle, Valkey, and
the worker's rejected identity routes remain observed; they do not substitute
for a live direct-PostgreSQL product acceptance record. This is an operational
recovery gate in addition to the separate production Keyverse, Figma-parity,
and independent-review gates.

After the rebuild, the static worker guard passed, all four worker identity
routes returned `404`, and a bounded image check confirmed the worker image
does not ship the retained issuer-shaped module. Valkey returned `PONG`.
Those are worker and queue observations only; the product service remains
unavailable until its direct-PostgreSQL configuration is restored.

## Amendment: Current PR-review and source-check recheck (2026-08-14)

A read-only recheck of Keyverse PR #100 found all currently listed checks
passing, including the coverage-evidence and same-head Strix checks. The pull
request nevertheless remains open with a changes-requested review decision and
no independent approval. A prior automated request for changes was based on an
earlier coverage-evidence failure; a later green check does not itself clear
that review state. No self-approval, protection bypass, merge, Strix retry, or
rate-limited review retry was performed. Independent review remains a release
gate.

The current LineageWeave tree passed 275 tests, the React production build, and
the browser-script syntax check. One test double was aligned with an existing
actor-aware customer-master collaborator signature; it changes no product
runtime path. The result confirms the action-led email entry copy and its
validation contracts at source level only. It does not restore the
direct-PostgreSQL runtime or replace the production Keyverse and Figma
acceptance gates.

## Amendment: Composed runtime and external-identity handoff (2026-08-14)

The product, Valkey, model worker, and search service are now running as a
Compose stack. The product is healthy against the direct PostgreSQL source;
the recovery used only the database location already specified in the product
goal and did not repeat the prior bounded source-content inspection. The
current source tree passed 281 tests and the Compose identity-boundary guard.

Compose now separates the two trust roles precisely: the product can receive
operator-provisioned Keyverse configuration from its managed environment file,
while the model worker explicitly clears every issuer, client, redirect, and
CA-bundle identity value from that same file. After recreation, discovery,
authorization, token, and introspection requests to the worker each returned
`404`; it remains a model-only worker.

The current operator environment does not provide a production HTTPS Keyverse
configuration. A valid non-identifying login-start request therefore received
the product's generic unavailable response and did not navigate or mint a
session. No local issuer, development actor, account fabrication, credential
inspection, or login bypass was used. Real account login, callback, session,
and logout acceptance remain open external gates.

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H.,
Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., &
Clanuwat, T. (2026). *Sakana Fugu technical report* [Preprint]. arXiv.
https://arxiv.org/abs/2606.21228

Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2026).
Learning to orchestrate agents in natural language with the Conductor. In
*International Conference on Learning Representations (ICLR 2026)*.
https://arxiv.org/abs/2512.04388

Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2026).
TRINITY: An evolved LLM coordinator. In *International Conference on Learning
Representations (ICLR 2026)*. https://arxiv.org/abs/2512.04695

ContextualWisdomLab. (2026). *Temporal Event Psychometrics Platform: Approved
PRD v0.4* [Product requirements document]. GitHub.
https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/product/prd-v0.4-approved.md

ContextualWisdomLab. (2026). *TEPP standards and research foundations*
[Research register]. GitHub.
https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/research/standards-and-literature.md

ContextualWisdomLab. (2026). *Contextual Orchestrator* [Computer software].
GitHub. https://github.com/ContextualWisdomLab/contextual-orchestrator

PostgreSQL Global Development Group. (2026a). *LOCK*. PostgreSQL 18
documentation. https://www.postgresql.org/docs/current/sql-lock.html

PostgreSQL Global Development Group. (2026b). *System administration
functions: Advisory lock functions*. PostgreSQL 18 documentation.
https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS

World Wide Web Consortium. (2009). *SKOS simple knowledge organization system
reference*. https://www.w3.org/TR/skos-reference/

World Wide Web Consortium. (2012). *OWL 2 web ontology language document
overview (Second Edition)*. https://www.w3.org/TR/owl2-overview/

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2014a). *RDF 1.1 concepts and abstract syntax*.
https://www.w3.org/TR/rdf11-concepts/

World Wide Web Consortium. (2014b). *The organization ontology*.
https://www.w3.org/TR/vocab-org/

Schema.org. (n.d.). *Schema.org vocabulary*. Retrieved August 13, 2026, from
https://schema.org/

The local research notes record how those papers map to request variables and
why the source DAG keeps observed and inferred evidence separate.

## Amendment: Customer and administrator product surfaces (2026-08-14)

The product now separates the authenticated React workspace from two
role-aware operational surfaces. `GET /api/customers` calls the actor-aware
PostgreSQL customer-master loader: account-to-document links are evaluated with
the same corp/PU/visibility predicate as documents, and customer edges without
visible document evidence are removed before the customer screen receives
them. A customer can open an evidence document through the existing authorized
workspace route; the screen is not a second unfiltered KG export.

The administrator view is hidden from sessions without the product `admin`
role, with the server enforcing the same decision independently. Its HTTP-only
Keyverse adapter obtains a short-lived Admin REST token from server-managed
settings, resolves the configured realm and exact `lineageweave-web` client,
and exposes only a sanitized account projection. Mutations preserve the
account's other attributes while updating scalar `org` and `workspace`, then
reconcile direct roles on that client only. The actor corp is the only accepted
org value, existing other-corp targets are denied, and no credential or
required-action field is returned or submitted by React. Initial role/client
bootstrap remains an issuer-operator responsibility.

The RED-to-GREEN contract adds customer-scope, admin adapter, HTTP route, and
React surface tests. The current measured source scope passes 281 tests with
6,395 statements and 2,490 branches at 100% line and branch coverage. This is
local executable evidence; configured production Keyverse admin credentials,
real-account browser acceptance, and independent review remain release gates.

## Amendment: Compose credential isolation and runtime recheck (2026-08-14)

The refreshed Compose build passed its boundary preflight and all 281 local
tests, then started the product, Valkey, model worker, and search service
healthy against the direct PostgreSQL source. The product remains the sole
relying party: it may receive operator-provisioned Keyverse values, while the
worker explicitly clears the known issuer, legacy issuer, CA, registration,
administrator, client, and redirect values. Its startup guard also rejects any
nonempty future `KEYVERSE_*` or `LINEAGEWEAVE_OIDC_*` value, so an accidental
secret-file expansion fails closed rather than running a mixed-trust worker.

The recreated worker returned `404` for discovery, authorization, token, and
introspection routes. Its rebuilt image did not contain the retained
issuer-shaped artifact. The retained source artifact itself was not deleted,
moved, chmodded, or otherwise changed; its ownership/audit finding remains
open. A valid non-identifying product login start returned the generic `503`
unavailable response, with no redirect or session. This proves the external
Keyverse configuration gate holds; it is not real-account login acceptance.

The supplied Figma file currently exposes only its cover frame; no target
login, list, detail, or lineage node is available for paired browser capture.
Accordingly, no Figma browser-parity claim is accepted in this ADR and the
earlier list/detail comparison statement is superseded. A target-frame URL or
node is required before visual acceptance can be recorded. Actual production
HTTPS Keyverse configuration, real-account content parity, and independent
approval of the current LineageWeave pull request remain release gates.

## Amendment: Idempotent content profiles and bounded semantic retrieval (2026-08-14)

An authorized detail read must not destroy a semantic index. Content profile
materialization therefore normalizes the intended DOM blocks, format hints,
and asset metadata and compares them with the persisted rows. An identical
profile is a no-op, preserving every embedding foreign key. A changed profile
still replaces the rows, allowing the existing `ON DELETE CASCADE` relation to
invalidate vectors derived from stale text. The direct PostgreSQL contract
exercises both outcomes.

Semantic-related retrieval now reuses the actor-authorized, bounded embedding
candidate query used by natural-language search. It no longer materializes the
complete authorized KG merely to discover visible document numbers. In the
live data path, indexing produced 29 source-linked chunks, a subsequent content
read retained all 29, and the relatedness endpoint returned an inferred result
in 0.19 seconds. The result remains relatedness evidence, never an observed
document transition.

Source-derived KG replacement must likewise retain evidence-reviewed additions
that cannot be reconstructed from the source rows. Before replacement, the
writer loads only existing `organization_alias` edges and their endpoint nodes,
merges them by stable node/edge identity, then regenerates the normalized
semantic layer. Method-paper metadata refreshes preserve an existing Zotero
attachment key, stored status, and digest when no attachment attempt was made;
an explicit failed attachment attempt remains visible rather than being
silently converted to success.

## Amendment: Controlled local Keyverse browser regression (2026-08-14)

The absence of an operational business account or production Keyverse
configuration does not excuse untested authentication behavior. A dedicated
local Keyverse test realm was provisioned with a synthetic, email-verified
account, scalar organization and workspace attributes, and the reviewed
LineageWeave account-claim mapper shape. Its confidential RP was derived from
the existing Keyverse template, then bound only to a loopback development
callback. No business email, production account, production tenant data,
credential value, authorization code, token, or source identifier was recorded.

With the Compose worker untouched, a separate direct-PostgreSQL development
server ran only with the explicit local HTTP switches. The in-app browser then
completed an authorization-code + S256 PKCE redirect to that local Keyverse
realm, authenticated the synthetic account, completed its required first-use
profile fields with synthetic values, returned through the callback, and showed
the mapped role and organization/workspace session surface. Activating logout
returned the same browser to the email-entry gate. The gate also rejected a
malformed email with the user-facing message “올바른 업무 이메일 주소를 입력해
주세요.”

This is high-signal local regression evidence, not production acceptance: the
test realm was configured directly for this isolated run rather than through a
production Keyverse desired-state receipt; it used loopback HTTP and a
password-based test login, not production HTTPS, a real business account, or a
browser passkey. It therefore does not clear the production Keyverse,
passkey-enrollment, Figma-node-parity, worker ownership/audit, or independent
review release gates. The Compose worker still must not import, ship, or serve
a local issuer.

A same-tree regression recheck passed 281 tests. The Compose identity-boundary
guard also passed; discovery, authorization, token, and introspection routes on
the running worker each returned `404`, and its rebuilt image did not contain
the retained issuer-shaped module. The retained source artifact remains present
and unmodified as an ownership/audit finding. These checks confirm the
executable worker boundary only; they do not promote the local browser test to
production evidence.

## Amendment: General-user workspace and customer-master semantic surface (2026-08-14)

The first authenticated surface exposed operational counters, KG edge counts,
queue state, and raw document mechanics as the primary experience. That is a
diagnostic workspace for operators, not an appropriate default for a reader or
business user. The product therefore adopts a separate `업무 홈` as the default
screen for every authenticated actor. It presents actionable business language:
recent work documents, evidence-backed customer relationships, period reports,
and the actor's effective corp/PU and role. `업무공간` remains available for
event-lineage and source-evidence investigation, while the technical KPI strip
is shown only to an administrator inside that workspace. The administrator
mode remains separately role-gated and is never a substitute for the general
user screen.

The customer screen is an operational projection of the same semantic model,
not a browser-owned list or a second graph export. Its normalized source of
truth is:

- `analysis_customer_accounts`: one customer organization, its normalized
  group/national/HQ/plant tier, parent, entity role, and model/source status;
- `analysis_customer_affiliates`: one directed parent-child relation with its
  relation kind and provenance status; and
- `analysis_customer_document_links`: the mandatory account-to-document
  evidence relation used for both ABAC filtering and KG scope.

The customer entities are attached to the PostgreSQL knowledge graph only when
their document evidence is visible to the verified actor. The semantic layer
then assigns `schema:Organization` to the customer node, maps the customer
relationship to `schema:subOrganization`, maps the document-to-customer
assertion to `schema:about`, and retains the product entity-role concept in the
LineageWeave ontology. The full normalized ontology/semantic tables still
persist the RDF type, term, domain/range rule, node assignment, predicate, and
evidence assertion; customer UI labels are not treated as ontology facts.
The group-to-national-to-HQ-to-plant ladder is a displayable inference only
when its source account/document evidence is carried forward to every derived
node and edge. A missing evidence link removes the account, edge, and related
semantic assertion from the actor's response.

The agent and chat workflows consume this same actor-filtered semantic
subgraph. An agent may answer a customer relationship question only from the
authorized semantic rows plus cited source documents; it must fail closed when
the semantic context or evidence is absent. Customer-master LLM output remains
an assertion candidate and cannot become an observed event transition merely
because it appears in the customer screen.

The RED-to-GREEN acceptance contract now includes the default `업무 홈`,
reader-visible workspace/customer navigation, administrator-only diagnostic
KPI and admin navigation, customer evidence links back to the authorized
document popup, and ontology/semantic-layer evidence filtering. This amendment
is verified by the React build, surface contracts, customer semantic-scope
tests, and the real browser flow; production Keyverse account provisioning and
external identity acceptance remain deployment gates. The current source gate
passes 308 tests with 6,810 statements and 2,636 branches at 100% line and
branch coverage; this is local executable evidence, not production identity
acceptance.

## Amendment: Stale report recovery preserves valid evidence (2026-08-14)

A partial live judge run must never make a complete report set appear complete,
and a recovery must not overwrite already-validated report records. The
maintenance path therefore holds one PostgreSQL advisory lock, identifies only
records with an unavailable judge result or no linked score, rebuilds the
canonical bounded slices, and refuses to write if the stale IDs and rebuilt IDs
do not match exactly. It scores only those stale slices, then persists the
merged set of unchanged valid records and refreshed records in one transaction.
This keeps a transient model timeout retryable without making a user-scoped
request rebuild a global report set.

The product response applies the same document ABAC predicate used elsewhere:
a persisted report is returned only when every document that supports it is
visible to the verified actor. The maintenance task itself is global and
server-owned; it never substitutes a restricted consumer's document selection
for the durable report corpus.

On the direct-PostgreSQL Compose product recheck, 65 already-valid reports and
325 linked scores were retained while the remaining 15 stale reports were
processed. The bounded recovery completed with 80 `llm_judge` reports, 400
`fast_mlsirm`-calibrated linked scores, 80 distinct scored reports, and zero
reports without scores or orphan scores. The container remained healthy and
the Compose Keyverse identity-boundary guard passed again. This is local
runtime evidence only; it does not clear production Keyverse HTTPS, real
business-account/passkey, target-Figma parity, retained-artifact ownership, or
independent-review release gates.

## Amendment: Administrator lineage review and access-policy surface (2026-08-14)

The reported false Lineage was a projection error, not a search-ranking
problem. `build_event_lineage()` received the complete inferred/predicted edge
collection and appended every edge as a bead, even when neither endpoint was
the selected document. A document list ordered by search relevance could
therefore look like a chronological history. The shared builder now requires
the selected document to be either endpoint before it can create a relatedness
bead. Only observed events connected by an observed row-successor edge
can produce a chronological connector; inferred and predicted relations stay
visibly non-temporal.

The correction is an administrator capability in the product, not a code-only
debugging switch. `관리자 모드` now contains two server-authorized surfaces:

1. `게시글 권한 통제` shows the current document visibility and the effective
   corp/PU scope. Its public/private mutation reuses the document ABAC/RBAC
   write boundary and records the change in the PostgreSQL outbox for Valkey
   delivery. The browser cannot widen its own corp, PU, or role.
2. `Lineage 검토` lists only bounded, same-corp inferred/predicted candidates
   that the administrator can read. `비관련으로 제외` writes a normalized
   `analysis_lineage_edge_overrides` row with the source node, target node,
   relation, status, reason, actor, and timestamp. `연결 복원` changes the
   same decision to `restored`; it does not delete the source edge. The
   override is applied consistently to document Lineage and the corresponding
   document KG projection. Observed `row_successor` transitions are immutable;
   shared-thread relatedness is inferred and reviewable.

The override table is a third-normal-form decision ledger keyed by the edge's
three-part identity. Its status values are also present in the shared
`common_enum_values` table. The API requires a verified same-corp `admin`,
rechecks the exact candidate and evidence tier in PostgreSQL, rejects missing
or observed edges, and emits `lineage_edge_override_changed` only after the
transaction commits. A reader receives neither the admin UI nor a successful
admin API response. Clearing the in-memory snapshot after a mutation forces
the next read to use PostgreSQL, so an exclusion survives a rebuild and is not
an accidental browser-only filter.

The acceptance contract now includes: an unrelated-edge regression test,
admin-only access-policy and Lineage-review routes, exclude/restore behavior,
observed-transition immutability, cross-corp rejection, outbox emission, and
the React production build. An actual loopback browser run against the direct
PostgreSQL source displayed the reader home, customer screen, popup, evidence
drawer, KG, and both administrator panels; the Lineage review API returned
HTTP 200 and the policy visibility round trip returned HTTP 200 for private
then public. The separate Keyverse account-administration adapter returned
HTTP 503 because no live Admin endpoint was configured in that run; the
product did not substitute a recorded account response. The current source
gate passes 308 tests with
6,810 statements and 2,636 branches at 100% line and branch coverage. This is
local executable evidence; production Keyverse credentials, real-account
browser acceptance, Figma target-node acceptance, and independent review
remain deployment gates.

## Amendment: Full analysis snapshots retain verified aliases (2026-08-14)

Organization-alias verification is an independently reviewed semantic
addition, so a later source reanalysis must not erase it. Both replacing KG
paths now call the same merge routine before deleting old graph rows. The
routine prefers current snapshot entities on identifier collisions and carries
forward only verified alias nodes and inferred exact-match edges recoverable
from persisted KG rows or labeled normalized inference-review records.

The regression contract seeds an incremental verified alias, performs a full
analysis replacement, and confirms the alias edge remains. Existing direct-KG
snapshot tests continue to cover recovery from the normalized review ledger.

## Amendment: Reader-only product acceptance (2026-08-14)

The general-user requirement is now an executable role boundary, not merely a
label on the operator workspace. A direct loopback browser run used a verified
development actor with only the `reader` role against the same PostgreSQL
analysis surface. The rendered default was `#userHome`; its navigation exposed
only `업무 홈`, `업무공간`, and `고객 화면`. The administrator navigation and
the technical `#metricRows` KPI strip were absent, while the business home
still showed recent documents, evidence-backed customer accounts, reports, and
the actor's effective scope. The customer screen remains available to the
reader, but its accounts and affiliate edges are still filtered by explicit
customer-to-document evidence.

The browser harness now captures the home screen and waits for the selected
document's detail response for the full bounded PostgreSQL read window. A slow
response therefore cannot cause the test to compare a rendered Lineage chain
with an empty timeout payload. The administrator run retains its separate
checks for operator KPIs, access-policy mutation, and Lineage review; this
amendment does not grant those capabilities to a reader.

This acceptance is local role-boundary evidence, not production Keyverse
identity acceptance. The product-home surface has no supplied Figma target
node, so this run claims functional and role-safe behavior but not Figma pixel
parity. The product continues to require production HTTPS Keyverse, a real
business-account browser flow, target-frame access, and independent review
before release.

## Amendment: Administrator-bounded LLM enrichment control (2026-08-14)

The reader-facing product must not depend on an operator opening every
document, and the operator must not receive an unbounded "analyze everything"
button. The product therefore adds two administrator-only HTTP operations:

- `GET /api/admin/enrichment/status` returns aggregate pending counts for
  Keyman, product work, and appointment extraction, plus bounded active/latest
  outbox metadata. It never returns source content, graph bytes, prompts,
  credentials, or another corp's counts.
- `POST /api/admin/enrichment/run` accepts only `keyman`, `product`,
  `appointments`, or `all` and caps a request at 64 documents. Candidate
  selection reuses the document corp/PU ABAC predicate. The request event is
  committed to PostgreSQL before a background worker resolves the live HTTP
  model adapter and loads each document independently.

The worker writes existing normalized document, issue-ticket, To Do/calendar,
and appointment tables and emits a completion event through the PostgreSQL
outbox for Valkey delivery. It does not add a file database or a browser-owned
queue. `user_override` Keyman rows are excluded from candidate selection, and
an empty live result is persisted with `keyman_source=llm` and
`keyman_status=empty` plus `abstained=true`; the system never invents a person,
organization, or appointment to make a batch look complete. The combined
`all` task calls the product adapter once per document and includes appointments
in that call, preventing accidental duplicate model work.

This is an operational control plane, not a replacement for the evidence
model. Customer-master assertions, R&R, and appointment results remain model
authored until their normal evidence/semantic-layer rules permit exposure; no
LLM result becomes an observed chronological transition. The status view is
admin-only in both React and the server, and errors are counted per document so
one unavailable model response cannot make other documents appear completed.

The current direct-PostgreSQL smoke queued one Keyman document and recorded a
completed batch with one completed document, zero failures, and one explicit
abstention. The current source gate remains 308 tests with 100% line and branch
coverage across 6,810 statements and 2,636 branches. This is local runtime
evidence only; production Keyverse claims, deployment-scale scheduling,
external model SLOs, and independent release review remain open gates.

## Amendment: Multimodal literature and Zotero provenance recheck (2026-08-14)

The mixed HTML/base64 requirement needs a research record for both layout-aware
and OCR-free document understanding. The doctoring register now includes
LayoutLM, LayoutLMv2, DocFormer, and Donut alongside the full TEPP research
register. The implementation consequence is deliberately narrow: source
position, DOM format hints, validated image profile, OCR/object output, and
model provenance remain separate normalized facts. No paper's model result is
treated as a source fact or as permission to add a KG edge.

The Local Zotero Connector was rechecked after those four OA records were
added. `analysis_method_paper_records` now contains 12 stored method-paper
parents and 12 stored original attachments, all with non-empty content
digests. The DocFormer original exceeded the former 16 MiB attachment ceiling;
the bounded limit was raised to 32 MiB, the exact original was then accepted,
and oversize rejection remains covered by the existing contract test. This is
runtime provenance evidence, not a scientific replication of the cited papers.

## Amendment: Evidence-bounded LLM subject classification (2026-08-14)

The document subject role is a semantic input to customer, partner, competitor,
market, and Lineage exploration, so a title-token heuristic alone is not enough
when a live product model is available. The bounded product contract now has an
`entity_role_classification` task. It receives only the selected document's
bounded title/event context and the current `common_enum_values.entity_role`
projection, and returns a normalized role, confidence, and rationale. VOC,
VOM, VOP, VOCC, VOCO, and VOS remain vocabulary hints rather than new database
classes; the persisted semantic role remains one of the normalized partner,
competitor, customer, customer's-customer, or market concepts.

The adapter accepts only an exact common-ENUM value or a small allowlisted
English alias. An unavailable, malformed, or unsupported model response is an
explicit `llm_abstention` in the in-memory product projection, after which the
deterministic observed-title classifier supplies the display fallback. The
selected document's normalized `entity_role` and Ontology URI are therefore
always available without letting the model invent a class or relation. This
bounded call is applied only to the existing Keyman/product candidate set; it
does not turn a full-corpus page load into an unbounded model fan-out.

The acceptance contract covers valid Korean and English role responses,
unsupported-role abstention, confidence clamping, task routing, and the
reader/admin product surfaces. Role classification is semantic annotation,
not chronological evidence: it cannot create an observed transition or make
two unrelated search results into a Lineage chain.

## Amendment: Local Keyverse HTTP regression and bounded report maintenance recheck (2026-08-14)

The absence of a production business account or production Keyverse
configuration does not justify leaving the relying-party flow untested. A
separate direct-PostgreSQL local server was configured only for an isolated
synthetic Keyverse realm and a loopback callback. Its HTTP regression rejected
a malformed email, completed authorization-code + S256 PKCE login, accepted
the mapped reader session, and verified that logout removed that local session.
The generated test credential, authorization code, token, and account
identifier were not recorded. This evidence is intentionally protocol-level;
it does not claim an actual production account, HTTPS deployment, passkey, or
browser acceptance.

The same source tree also bounds startup report maintenance to three stale
slices, one judge attempt per slice, and a 15-second report-judge deadline.
The refresh still holds its PostgreSQL advisory lock and merges only rebuilt
stale records into the durable valid set. This prevents a model outage from
turning startup into unbounded global reanalysis or discarding verified scores.
The current direct-PostgreSQL aggregate remains 80 judged reports and 400
linked scores, with zero missing-score reports and zero orphan scores.

The Compose worker was not changed for this regression. It remains unable to
import, ship, or serve a local issuer, and its discovery, authorization, token,
and introspection routes remain rejected. The retained issuer-shaped source
artifact remains an ownership/audit finding, not a test fixture to delete or
relocate. Production Keyverse configuration, real-account browser acceptance,
target Figma parity, retained-artifact disposition, and independent review
remain release gates.

## Amendment: Coverage evidence correction (2026-08-14)

A fresh current-tree test run passed 308 tests, but the documented no-omit
branch-coverage command measured 88% overall and failed its 100% threshold.
The affected product modules include the main analysis layer and the HTTP
server; no coverage exclusion, pragma, skip, or synthetic success claim was
added to conceal the result. A concurrent shared-workspace documentation update
reintroduced a 100% coverage statement using the same test totals after this
measurement; this amendment and the traceability row supersede that statement.

Earlier 100% coverage statements in this ADR are historical evidence, not a
claim about the current source tree. The missing coverage remains a release
blocker under the repository working agreement. Passing tests, successful
direct-PostgreSQL local Keyverse HTTP regression, Compose boundary preflight,
and React production build remain useful local evidence, but they do not
substitute for complete executable coverage or any external identity, Figma,
ownership, or independent-review acceptance gate.

## Amendment: Coverage gate revalidated after current source changes (2026-08-14)

The preceding coverage correction records an earlier measurement and is not the
current source state. After the reader/customer/admin surfaces and bounded
subject-role task were present, the exact no-omit command was run again on the
current tree. It passed 308 tests and reported 6,810 statements and 2,636
branches at 100% line-and-branch coverage across
`lineageweave.py`, `lineageweave_embeddings.py`, `lineageweave_server.py`, and
`compose/http_standin.py`. No coverage exclusion, omit rule, pragma, or test
skip was added. This amendment supersedes the prior coverage status for the
current tree while preserving the earlier 88% result as historical evidence.

The result is a reproducible local source gate, not a production release
approval. Production Keyverse account acceptance, real-account browser flow,
Figma target-frame parity, retained-artifact ownership, and independent review
remain external gates.

## Amendment: General-user/customer surface and Figma target-frame recheck (2026-08-14)

LineageWeave has two deliberate audiences. A verified general user enters the
business `#userHome`, then may open the actor-scoped workspace and customer
master. The user-facing surface presents recent work, evidence-backed customer
relationships, reports, and effective scope. It does not expose operational
row/document/thread/KG/queue diagnostics, Keyverse account administration,
Lineage edge override decisions, or bounded LLM-enrichment controls. Those
capabilities remain server-enforced administrator functions. This is a
product-surface and authorization boundary, not merely a CSS distinction.

The customer screen is part of the business surface because customer-master
entities are semantic-layer objects. `analysis_customer_accounts`,
`analysis_customer_affiliates`, and
`analysis_customer_document_links` remain normalized PostgreSQL relations.
Only account-to-document evidence that passes the actor's corp/PU predicate
can enter the customer screen or the selected document's KG. The semantic
bindings remain `schema:Organization` for customer nodes,
`schema:subOrganization` for affiliate hierarchy, and `schema:about` for the
document-to-account evidence assertion. An LLM may propose hierarchy or role
annotations, but it cannot make an unscoped customer visible or turn a
customer relation into an observed chronological transition.

The Figma references are now independently readable through the supplied
file: MU-02 semantic-search node `162:27` renders at 2000 x 1368 and MU-14
document-detail node `164:27` renders at 2000 x 1148. Their metadata/design
context and screenshots were recorded for QA. The React implementation keeps
their blue accent, pale neutral canvas, rounded white surfaces, compact
navigation/filter language, selected states, and detail-card hierarchy while
continuing to render live authorized PostgreSQL/API data. MU-02's tabular
VOC-list layout and MU-14's narrower source/action mockup are reference
patterns; LineageWeave intentionally adds evidence drawers, semantic KG,
Keyman, chat, reports, issue/calendar work, and server-side access controls.

Therefore this is structural visual alignment, not a pixel-parity claim. The
reader/customer browser acceptance is local role-boundary evidence, and the
Figma evidence corrects the earlier cover-only QA note. Production HTTPS
Keyverse, a real business-account browser flow, and independent release review
remain separate release gates.

## Amendment: In-app-browser synthetic Keyverse acceptance and identity disclosure (2026-08-14)

The product Compose profile was first confirmed fail-closed when its
operator-managed Keyverse values were absent. To exercise the relying-party
workflow without a production business account, an isolated local Keyverse
realm and a password-backed synthetic account were used only with a separate
loopback, direct-PostgreSQL product process. In the in-app browser, malformed
email remained on the product page with the inline corrective message. A valid
synthetic email then reached the external local identity sign-in form,
completed the authorization-code plus S256 PKCE callback, produced a mapped
reader session, and returned to the email-first screen after logout.

The first local attempt failed closed because the configured loopback issuer
did not match the issuer advertised by discovery, and the second failed closed
because the synthetic account lacked the required organization and workspace
claims. Those findings were corrected only in the isolated local Keyverse test
configuration before the successful browser run; no worker source, worker
image, worker identity route, or production operator configuration was changed.
No test credential, authorization code, token, or account identifier is
recorded here.

The browser review also found that the authenticated header rendered the raw
account subject. It now labels the workspace and effective business permission
instead, using an available organization/PU display name when present and the
already-authorized codes only as a fallback. The rerun confirmed that the raw
subject was not visible after callback. This is local synthetic-account
acceptance only: it does not establish production HTTPS Keyverse configuration,
a real business-account or passkey journey, target-Figma pixel parity,
retained-artifact ownership disposition, independent review, or release
approval.

## Amendment: Event-lineage connector evidence gate (2026-08-14)

A search-result regression was traced to the React renderer: it drew a line
whenever two event cards happened to be adjacent. Adjacency reflects the
returned list order and is not lineage evidence. `build_event_lineage` now
marks `connects_to_next` only when the two adjacent event evidence IDs are the
source and target of an observed `row_successor` edge. The React renderer draws
the connector only for that explicit marker. Thus an absent edge, an
inferred/predicted edge, or stale payload without the marker renders no
chronological connection rather than implying one.

The focused regression covers both one observed transition and a following
event without a transition; the React production build passed. The fresh
no-omit source gate then passed 308 tests with 6,817 statements and 2,640
branches at 100% line-and-branch coverage. This is source and build evidence,
not a claim that the reported real-data search screenshot has been browser
replayed under a production business account. The external Keyverse,
target-Figma, retained-artifact ownership, independent-review, and release
gates remain unchanged.

## Amendment: Fresh Keyverse PR-review state after evidence-scope correction (2026-08-14)

After the relying-party documentation was narrowed to distinguish issuer mapper
provisioning from downstream claim-rejection evidence, the current Keyverse PR
#100 remains open and blocked. GitHub reports `REVIEW_REQUIRED`, zero unresolved
review threads, and newly scheduled checks still queued for this source head.
An automated review status is successful, but it is not an independent approval.
No review was self-approved or dismissed, and no protection bypass, Strix retry,
or merge was performed. The queued checks and an independent authorized review
remain release gates.

## Amendment: Separate chronological beads from relatedness projection (2026-08-14)

A product-review follow-up exposed a second-order ambiguity after the first
connector fix: inferred or predicted relations no longer received a blue
chronological connector, but they were still appended to the same horizontal
bead collection. A user could therefore read adjacency itself as history.

The contract is now explicit. `event_lineage.beads` contains only observed
document events and may contain a connector only when adjacent evidence IDs
are joined by an observed `row_successor` edge. `event_lineage.relatedness`
contains endpoint-checked inferred/predicted relations and is rendered in a
separate labelled panel as semantic relatedness, never as the next event. The
administrator review screen still controls inferred/predicted edge suppression
and restoration; it cannot rewrite observed transitions. This keeps the
ontology/semantic-layer KG useful for discovery without allowing a search-list
order or model affinity to become document history.

The focused regression now asserts that a three-event chain remains three
chronological beads while the inferred candidate is returned separately. The
React build and real PostgreSQL browser replay must assert both collections
independently. This is a product semantics correction, not a claim of pixel
parity with the Figma reference or of production Keyverse release acceptance.

The browser E2E count contract was also corrected to count only explicit
`connects_to_next` markers, never adjacent event cards. Its syntax and the
shared source regression are checked locally; the bounded selected-browser
direct-PostgreSQL replay below supplies that runtime evidence rather than an
inferred pass.

## Amendment: Selected-browser direct-PostgreSQL bead replay (2026-08-14)

The selected-browser real-data replay is now complete as local integration
evidence. The isolated local Keyverse realm used a reader-only test
configuration. Its organization and workspace claims were hard-coded client
mappers rather than per-account attributes, so the non-production mapper
values were temporarily set to one aggregate-selected public scope for this
bounded run and then verified restored. No production Keyverse configuration,
Compose worker behavior, retained issuer-shaped artifact, or product Compose
configuration was changed.

In the user-selected in-app browser, the email-first flow reached a
reader-scoped Keyverse SSO session and returned to the direct-PostgreSQL
product. The authorized workspace exposed 100 document choices. Opening one
detail rendered nine event beads, zero observed connectors, and zero separate
relatedness entries. This is the relevant negative case for the reported
defect: the presence and displayed order of nine events did not create a
Lineage transition in the absence of observed `row_successor` evidence. The
browser product session was logged out and the isolated test tab was finalized;
no account identifier, credential, document identifier, or source content was
recorded.

This closes the local selected-browser evidence gap for the false-adjacency
fix. It does not establish production HTTPS Keyverse configuration, a real
business-account or passkey journey, target-Figma pixel parity, retained
artifact ownership disposition, independent review, or release approval.

## Amendment: Typed Keyman actors and ontology-preserving administration (2026-08-14)

The Keyman boundary previously normalized every structured item through
`person_name`, which silently converted an institution or meso organizational
unit into a person. This was incompatible with the product's ontology and
with the requested N-person/N-organization/N-affiliation model. The shared
normalizer now accepts `actor_type` values `person`, `organization`, and
`team` (with institution/company/authority and department/unit aliases), and
keeps the actor label in `actor_name`. An organization never receives a
`person_name` field; a team is represented as an Organization Ontology
`org:OrganizationalUnit`.

The normalized record retains organization and parent-affiliation names,
rank/title, optional canonical name and affiliation status, and the model's
`node`, `entity`, `relationship`, and `direction` qualifiers. Legacy string
and four-column person input remains accepted for existing administrators.
The React administrator editor adds an explicit typed form for institutions
and teams while keeping the old person format. Server-side normalization and
ABAC still run before the override is persisted.

The KG materializer now creates typed person/organization/team nodes, uses
PROV-O/Schema.org and ORG semantic classes, links people with membership,
teams with `org:unitOf`, and links an affiliated parent organization with
`schema:subOrganization`. The normalized semantic tables therefore carry the
distinction used by adaptive-depth traversal; a display label or search order
cannot change an institution into a person. The regression contract verifies
an institution produces exactly one organization node, a team produces an
organizational-unit node, and same-name people remain distinct by organization,
rank, and title.

A bounded, non-persisting live smoke against the configured model gateway used
one real PostgreSQL-derived title and `gpt-4.1-mini`; it returned three Keyman
actors including both `organization` and `person`, with zero organization/team
records carrying `person_name`. The model's empty-result path remains an
explicit abstention, not a heuristic fallback. This validates the adapter
boundary without claiming that all legacy persisted Keyman rows can be safely
reclassified after the fact.

The fresh administrator browser regression then clicked through the actual
React popup editor, saved an explicit organization actor over HTTP, verified
the 200 response and absence of `person_name` coercion, and saved the original
two-sided values back. This is product mutation evidence under a local
development actor; it does not replace production Keyverse authorization
acceptance.

## Amendment: Bounded live Event Lineage chat and source replay (2026-08-14)

The configured product transport was verified as `live_http` before this
document-scoped run. In a selected-browser, reader-scoped direct-PostgreSQL
session, one bounded Korean question was submitted from the Event Lineage chat
panel. The product returned a non-empty answer with five citations; exactly one
was a VOC source citation. Clicking that citation opened the authenticated AJAX
source drawer for the same authorized document. The response text, source
content, identifiers, credentials, and transport secret were not recorded.

The isolated local realm's temporary claim mapping was restored immediately
after the run, and the product session was logged out before the test tab was
finalized. This confirms the user-facing chat-to-evidence path with the
configured live transport; it does not claim a production Keyverse deployment,
a business-account or passkey journey, Figma pixel parity, retained-artifact
ownership disposition, independent review, or release approval.

The fresh no-omit source gate then passed 310 tests with 6,887 statements and
2,686 branches at 100% line-and-branch coverage across the shipped Python
modules; the production React build and Compose identity-boundary guard also
passed. This is current local executable evidence, not a substitute for any
external release gate.

## Amendment: Test-only Compose OIDC browser acceptance without business credentials (2026-08-14)

The absence of a provisioned business account or production Keyverse settings
does not excuse a missing login test. `tests/compose.oidc-e2e.yml` is a
test-only, direct-PostgreSQL relying-party runner. It has no issuer service,
does not reference the retained issuer-shaped artifact, and is not merged into
the `product` Compose profile. It consumes a separately provisioned OIDC
conformance IdP over the host network so both the browser and the product use
the same loopback issuer. The runner requires the direct database source and
test client secret at invocation time; neither value is stored in the source
tree.

The browser exercise exposed two legitimate configuration failures before it
passed: a discovery issuer-host mismatch and a stale test-client secret. Both
were corrected only in the isolated test setup; issuer matching, confidential
client verification, PKCE, and token introspection were not relaxed. A
test-only account then completed the email-first authorization-code + S256 PKCE
journey, returned to an authorized direct-PostgreSQL reader workspace, and
returned to the login gate after product logout. No credential, authorization
code, token, account identifier, document identifier, or source content was
recorded. Temporary client callback and claim-mapper changes were restored
after the browser run.

The main Compose identity boundary remains unchanged: the worker does not
import, ship, or serve an issuer, and its discovery, authorization, token, and
introspection routes remain rejected. The fresh no-omit source gate passed 311
tests with 6,887 statements and 2,686 branches at 100% line-and-branch
coverage; the React production build, test-runner Compose validation, and
identity-boundary guard also passed. This is local conformance evidence only.
Production HTTPS Keyverse configuration, a real business-account/passkey
browser journey, target-frame Figma parity, retained-artifact ownership
disposition, independent review, and release approval remain open gates.

## Amendment: Reprovisioned isolated OIDC conformance fixture (2026-08-14)

The separate test realm was rechecked before a browser rerun and was missing
both the relying-party callback and the `org`, `workspace`, and `role` claims
needed by the product's token-introspection contract. Those omissions produced
an invalid callback before any business identity could be involved. Only the
isolated test identity service was updated: it now contains a reserved `.test`
reader account, the exact test-runner callback, and the required introspection
claim mappings. No production Keyverse configuration, business account,
document content, source identifier, token, or credential was used or recorded.

In the selected browser, that account completed email-first authorization-code
plus S256 PKCE login, reached a reader-scoped direct-PostgreSQL workspace, and
returned to the login gate after product logout. The product and worker Compose
profiles were not changed to serve an issuer. A test-only conformance Compose
file now declares the official IdP plus an isolated Valkey service, while the
existing relying-party Compose file remains issuer-free. This makes the
non-production acceptance path repeatable without weakening the external
production-Keyverse acceptance gate.

## Amendment: Rust-owned longitudinal report state boundary (2026-08-14)

Report scoring now carries an explicit temporal provenance tuple: a stable
report-slice respondent identity, a date-ordered sequence index, and the exact
period start. When the configured HTTP/local `fast-mlsirm` connector exports
its sealed longitudinal design, LineageWeave stores the state specification,
run diagnostics, and per-occasion estimates in three PostgreSQL tables:
`analysis_longitudinal_state_specs`, `analysis_longitudinal_state_runs`, and
`analysis_longitudinal_state_observations`. This keeps psychometric parameters
and metrics in third-normal-form relations while the JSON report remains a
bounded presentation envelope.

The product does not copy Rust arithmetic. The sibling connector's state layer
fits respondent intercept/slope or discrete-sequence AR state in Rust and
returns engine, fingerprint, RMSE, counts, and aligned occasions. A missing
export produces an explicit unavailable result; a single observation is not
presented as a temporal trend. A valid state payload is accepted only when its
content/design fingerprints, finite diagnostics, identifiers, and aligned
occasion arrays pass the product boundary before persistence. The current
isolated connector smoke computed two real report observations with
`rust_cpu_multithreaded` and zero RMSE. The subsequent persisted PostgreSQL
report reanalysis used 80 existing LLM-Judge observations across 40 report
groups, produced zero transitions because this snapshot contains one period
per group, and persisted one state specification, one state run, and 80
occasion estimates. It is therefore evidence of a real state handoff, not
evidence of a temporal trend. Protected integration and full joint multilevel
recovery remain fast-mlsirm release gates.

This amendment preserves the customer-master decision above: customer
accounts and affiliate relations remain ontology/semantic-layer entities with
explicit document evidence, while longitudinal report state is a separate
measurement artifact linked to the authorized report scope. Neither state
tables nor report payloads widen document ABAC/RBAC or customer evidence.

## Amendment: Current general-user surface and coverage recheck (2026-08-14)

The current product acceptance remains split by audience. A verified reader
enters the React `#userHome`, can navigate to `업무공간` and `고객 화면`, and
cannot see administrator navigation, technical KPI diagnostics, Keyverse
account administration, Lineage override controls, or enrichment controls.
The customer master remains part of the business surface because it is an
actor-filtered projection of normalized PostgreSQL customer entities and
explicit account-to-document evidence, not a browser-owned mock or an
unscoped graph export. The semantic bindings remain
`schema:Organization`, `schema:subOrganization`, and `schema:about` under the
full normalized ontology/semantic-layer tables.

The administrator enters `관리자 모드` only when the verified Keyverse actor
has the required role. Its access-policy screen and inferred/predicted Lineage
review screen are server-enforced ABAC/RBAC operations; observed chronological
transitions remain immutable. This is the supported correction path for
non-related inferred connections and is separate from the general-user
experience.

After the empty semantic-search fallback contract was added, the current
no-omit product gate passed 314 tests with 6,977 statements and 2,728 branches
at 100% line-and-branch coverage. Python compilation, the React production
build, the public-sensitive scan, and direct PostgreSQL verification of one
longitudinal specification, one run, and 80 observations also passed. This
local evidence does not replace production Keyverse provisioning, independent
review, Figma pixel parity, or release approval.

## Amendment: Explicit semantic no-result fallback and paired Figma check (2026-08-14)

Semantic search remains inference, not a means of manufacturing a Lineage.
The direct PostgreSQL vector ranker keeps its threshold. If it returns no
authorized candidate, the product performs the already-authorized bounded
document-index query with the same actor and query string. Non-empty index
matches return the explicit `keyword_fallback` status; the React workspace says
that semantic agreement was absent and that the visible results are title or
document matches. Empty keyword results remain empty. This preserves ABAC,
does not lower the semantic threshold, and does not convert a keyword match
into a chronological or inferred relationship.

An isolated conformance-IdP reader run exercised invalid-email rejection,
email-first OIDC sign-in, callback, authorized direct-PostgreSQL workspace,
keyword fallback, product logout, and restoration of the temporary callback
and claim-mapper state. The full local suite then passed 314 tests; the React
production build, test-runner Compose validation, and Keyverse worker-boundary
guard also passed. No business email, credential, source identifier, content,
or token was retained in this record.

A same-width browser comparison with Figma MU-02 verified the shared blue
accent, pale canvas, and white panel language but found a deliberate
information-architecture difference: the reference is a table/filter dashboard
while the product is a document rail plus evidence-bound Event Lineage. The
reference's legacy branding was not reintroduced. This is comparison evidence,
not Figma parity or a release approval. The still-open conditions are an
externally operated HTTPS Keyverse configuration, a real business-account
login/callback/session/logout ceremony in the chosen browser, a target frame
aligned to the product's Lineage architecture, retained-artifact ownership
disposition, and independent authorized review.

## Amendment: Product OIDC-route rejection and Compose configuration correction (2026-08-14)

A fresh runtime check found that the product's React fallback returned HTML
with HTTP 200 for discovery- and authorization-shaped paths, while token-shaped
POST requests reached generic request authentication and returned HTTP 401.
The product was not serving an issuer, but these paths were not explicitly
rejected. The product handler now rejects the four issuer-shaped paths with the
same HTTP 404 JSON contract as the worker before either the React fallback or
request authentication. Focused HTTP contracts, a rebuilt direct-PostgreSQL
product container, and the worker container all verify discovery,
authorization, token, and introspection rejection. The retained issuer-shaped
source artifact was not moved, deleted, or shipped.

The product Compose service also no longer writes empty direct-database values
over its optional operator env file. A configuration check confirms an
operator-provided env file reaches the product service, while the source and
DSN remain required runtime configuration. This repair does not provide
production identity settings.

A full 314-test run and React production build pass. Whole-tree branch coverage
is 98 percent because it includes the retained unshipped issuer-shaped audit
artifact, the guard script, and test modules. The explicitly shipped product
runtime source report is 100 percent across 6,986 statements and 2,732
branches. This is local implementation evidence only; production HTTPS
Keyverse configuration, a real business-account/passkey browser journey, Figma
parity against a product-aligned target frame, retained-artifact ownership
disposition, and independent approval remain release gates.

## Amendment: Keyman live-worker fallback (2026-08-15)

The model boundary now treats a missing direct LLM or orchestrator URL as a
worker-routing condition rather than silently stopping Keyman enrichment. The
Keyman resolver first uses the configured live HTTP gateway; when it is absent,
it starts or reuses the Docker Compose worker and sends the identical normalized
Keyman request through the worker's live-gateway proxy. This preserves the
product's HTTP-only separation from contextual-orchestrator and keeps the
worker as a model proxy rather than an identity provider.

The Compose worker must still have a configured live model gateway. If it cannot
start, cannot reach that gateway, or returns no valid model object, the product
persists an explicit unavailable/abstention outcome and never uses a recorded
response, fake account, invented Keyman, or issuer-shaped fallback. The
resolver contract, Compose worker route tests, and the administrator enrichment
boundary are the release evidence for this behavior.

A fresh read-only Figma inspection confirms the supplied reference remains a
legacy dashboard/list mockup with a user-rejected legacy brand label. It is not
the current authenticated product home, document detail, or Event Lineage
interaction surface. No Figma file was changed and no pixel-parity claim is
made. A product-aligned target frame is still required for browser-parity
acceptance.

## Amendment: Effective product Compose configuration preflight (2026-08-14)

The product profile reads operator-managed values through its env-file path,
but static Compose parsing alone succeeds when those values are absent and
defers failure to the product process. The preflight now resolves the effective
product Compose configuration and requires nonblank direct database, source,
issuer, client, client-secret, and redirect settings without printing any
value. It does not create a local issuer, synthesize an account, or convert
test-only configuration into production configuration.

A focused shell-contract test exercises both a complete and an incomplete
resolved configuration. A live Docker Compose check rejects an unset operator
configuration before startup and accepts a bounded non-secret test
configuration without disclosing its values. The Compose identity-boundary
guard remains part of the same preflight. Production HTTPS Keyverse
configuration and a real business-account/passkey browser ceremony remain
separate external acceptance gates.

The current full suite passes 317 tests, and the shipped product-runtime source
report remains 100 percent across 6,986 statements and 2,732 branches.

## Amendment: External Keyverse review recheck (2026-08-14)

A fresh read-only check of Keyverse PR #100 found the head still open with all
30 reported checks complete (22 successful and 8 explicitly skipped). It has
no independent approval and one changes-requested review; the ten inline
threads are resolved. Completion of checks is therefore not release approval.
No self-approval, protection bypass, auto-merge, or merge action was taken.

The separate `.test` conformance path remains test evidence for the product's
external-issuer client behavior only. Production HTTPS Keyverse configuration,
a real business-account browser ceremony, retained-artifact ownership
disposition, target-frame Figma parity, and independent approval remain
external release gates.

## Amendment: Central coverage-evidence prerequisite under review (2026-08-14)

A bounded reproduction of the failed central coverage-evidence retrieval found
that the pinned archive could be rejected when Python used its default request
identifier, while the same fixed HTTPS origin and pinned digest succeeded with
a fixed, non-caller-controlled identifier. A separate draft central-workflow PR
therefore sets that identifier on the existing no-proxy, no-redirect opener. It
does not make the URL, redirect target, proxy, request headers, archive size,
or integrity inputs configurable. Focused boundary tests, a live pinned-digest
check, and the full central suite passed locally; the central PR itself remains
queued for CI and independent review.

This is evidence-recovery work, not a Keyverse approval or release approval.
A fresh product boundary recheck also passed the Compose identity guard and 31
issuer-route and worker-contract tests. The worker still neither imports nor
ships a local issuer, and issuer-shaped discovery, authorization, token, and
introspection routes remain explicitly rejected. The retained issuer-shaped
source artifact was not removed, moved, permission-modified, or treated as
resolved.

Keyverse PR #100 remains open with a changes-requested decision and no
independent approval. The central prerequisite must first complete its own CI
and independent review, then the Keyverse evidence must be rerun and reviewed
at its resulting head. Production HTTPS Keyverse configuration, a real
business-account login/callback/session/logout ceremony, product-aligned Figma
parity, retained-artifact ownership disposition, and independent approval all
remain external release gates.

## Amendment: Current identity-review and chronology recheck (2026-08-14)

A fresh read-only Keyverse PR #100 check found its head unchanged, all reported
checks complete, and no unresolved current review thread. The displayed
changes-requested decision remains from an earlier coverage-evidence failure;
it is not an approval and was not cleared, bypassed, or superseded by this
check. No independent approval exists, so independent review remains a release
gate. The separate central coverage-recovery PR is still a draft with its CI
jobs queued; no job was retried.

The reported search-result chronology regression was also rechecked at the
shared boundary. `build_event_lineage` emits chronological connectors only for
an explicit observed `row_successor` edge, while inferred and predicted
relatedness stays outside the event sequence. The React renderer emits a line
only for that explicit marker. Targeted DAG and surface contracts passed, and
the live product asset contains the same marker-based renderer. A direct
PostgreSQL aggregate mapped all 107 observed row-successor edges to same-document
event pairs and found zero cross-document pairs. This confirms the current
implementation and persisted data do not turn a search-result order into
Lineage; it does not replace the remaining production identity or
release-approval evidence.

## Amendment: Runtime-bundled semantic-result provenance (2026-08-14)

The current MU-02 design context requires natural-language search results to
make their ranking and path to the source/timeline understandable. The direct
PostgreSQL semantic endpoint already returned ranked items with a relation,
similarity, and source-evidence position, but the React document rail only
showed a general role and visibility label. The rail now shows `관련도` for a
semantic result, explicitly labels the keyword fallback as a title/document
match, and describes its action as opening the source and timeline. It does
not render an ordering as Event Lineage or infer a chronological transition.

The current production image was rebuilt from that React bundle and a fresh
local product container reached direct-PostgreSQL health successfully. The
operator-only runtime configuration supplied the required direct-database
settings without placing them in tracked source. A read-only container
configuration check recorded only the presence of those two settings, not
their values. The worker boundary guard passed, and the running product
returned HTTP 404 for discovery, authorization, token, and introspection
issuer-shaped routes.

A browser refresh loaded the rebuilt asset. An invalid business-email entry
kept focus on the email field and exposed the Korean validation alert; the
customer-facing page did not restore the removed legacy brand. This verifies
the local entry UX and current bundle, not a real identity ceremony. The
preflight still lacks an externally operated HTTPS Keyverse issuer/client
configuration, so real business-account login, callback, session, and logout
remain mandatory release acceptance gates together with independent approval,
retained-artifact ownership disposition, and product-aligned Figma parity.

The current full no-omit source gate passed 323 tests and covers 7,147
statements and 2,780 branches at 100 percent, including the retained offline
OIDC utility contract. The shipped product runtime excludes that retained
utility; its four runtime modules cover 6,993 statements and 2,736 branches
at 100 percent.

## Amendment: External approval and queue recheck (2026-08-14)

A fresh read-only Keyverse PR #100 check found the same head still open. Its
31 reported checks are terminal (23 successful and 8 skipped), and its ten
inline review threads have no unresolved current thread. The pull request is
nevertheless merge-blocked with a changes-requested review decision and no
independent approval. No review, thread resolution, protection bypass,
auto-merge, or merge action was taken.

The separate central coverage-evidence PR remains an open draft at its same
head: one check is successful, thirteen are skipped, and eighteen are queued.
It remains review-required and merge-blocked. Its same-head job was not
retried. Neither PR state substitutes for the production Keyverse configuration
or real-account browser acceptance listed above.

## Amendment: Live model abstention and data-bearing browser acceptance (2026-08-14)

The first full-source reanalysis encountered HTTP 429 responses from the live
model gateway while extracting Keyman and judging report slices. The prior
transport propagated that response out of the batch and left the product with
no complete analysis result. The shared HTTP boundary now treats 429 as a
bounded model abstention: the Keyman path may try its explicitly separate chat
contract once, then records an empty live result; product enrichment retains
its task-specific deterministic/pending state; and report judging stores the
non-null `abstain` value with `llm_abstention` or `unavailable` provenance.
Other HTTP failures are not silently converted into successful model output.

The shared `common_enum_values` table includes `judge_verdict` values
`pass`, `fail`, `abstain`, and `unavailable`. `persist_period_reports` also
defensively writes `abstain` when a legacy or externally supplied report lacks
a verdict, so the runtime schema contract cannot accept a NULL judge state as
an apparently complete report.

The runtime reanalysis then read the complete configured PostgreSQL source and
persisted 43,707 documents, 4,567 lineage edges, 264,750 KG nodes, 3,195
inferred/predicted edges, 80 reports, 400 linked scores, and twelve stored OA
method-paper parent/original pairs with digests. All 80 reports carried an
explicit `abstain` verdict under gateway rate limiting, and the runtime schema
contract passed. The output JSON remains an operator artifact; large source
content and image bytes stay behind authorized PostgreSQL asset routes.

The conformance browser fixture now accepts corp and PU claims only through
runtime environment variables. Its default committed values remain synthetic,
while a data-bearing acceptance run must set `LINEAGEWEAVE_E2E_REQUIRE_DATA=1`.
The real reader run completed email-first OIDC login, callback/session/logout,
the general-user home without administrator diagnostics, customer screen,
document popup, observed-versus-relatedness Lineage rendering, evidence drawer,
and Knowledge Graph request against direct PostgreSQL data. An authenticated
empty scope is now a failed acceptance rather than a passing no-op.

## Amendment: Empty authorization-scope UX is not a perpetual loading state (2026-08-14)

An authenticated reader workspace showed zero authorized documents and zero
customer records after its requests had settled, while the home cards still
said that both collections were loading. That wording turns a completed empty
authorization scope into a false operational state. The React surface now
tracks document and customer requests independently and distinguishes initial
loading, a completed empty scope, and a request failure on both the home and
document-list surfaces. Error messages remain customer-facing and do not
expose an API error value.

The focused React surface contract, production bundle build, and current
full-suite run pass: 323 tests and a 7,147-statement/2,780-branch complete
source gate at 100 percent. Its separate four-module shipped-runtime report
is 6,993 statements and 2,736 branches at 100 percent. The direct-PostgreSQL
Compose product was rebuilt from that bundle and reached health successfully.
The Compose identity-boundary guard passed, and discovery, authorization,
token, and introspection issuer-shaped routes returned HTTP 404. A fresh
in-app-browser load also revalidated the email-first invalid-address alert and
focus behavior. A syntactically valid synthetic email against the current
unconfigured product stayed on the product page and showed the same
customer-facing retry guidance rather than navigating to an unavailable
identity endpoint. The browser's prior reader session did not survive the reload,
so this amendment does not claim a new post-build data-bearing reader run.
The configured data-bearing acceptance gate continues to fail an empty scope
when it is explicitly required, and production HTTPS Keyverse configuration,
real business-account login/callback/session/logout, target-frame Figma
parity, retained-artifact ownership disposition, and independent approval
remain release gates.

## Amendment: Versioned TEPP analysis-run port (2026-08-15)

The approved TEPP API contract currently defines `/v1/analysis-runs` and
`/v1/analysis-runs/{run_id}` as target HTTP resources while explicitly stating
that protected main does not yet expose a production HTTP service. LineageWeave
therefore adds a real, separate HTTP client rather than importing TEPP internals
or inventing a local result. The administrator React panel sends a v1 request
with an immutable snapshot identifier, knowledge cutoff, model contract,
configuration, output profile, and idempotency key.

The server rejects unknown fields, unsupported contract versions, oversized or
malformed objects, insecure non-development endpoints, cross-corp actors, and
idempotency conflicts before or at the external boundary. Successful lifecycle
metadata is persisted in normalized `analysis_tepp_run_records` and the
submission is written to the PostgreSQL outbox for Valkey delivery. Status
refresh stores only run state, request identity, retryability, and digests; raw
source text, model credentials, and unrestricted remote payloads never enter
the browser or graph JSON.

The contract suite, React build, Python compilation, and complete 329-test
source gate pass with 7,313 statements and 2,838 branches at 100 percent.
Because TEPP main still marks the service as an accepted target, this proves
LineageWeave's executable boundary and fail-closed behavior, not a deployed
TEPP scientific run. A configured TEPP deployment remains the production
integration acceptance gate.

## Amendment: Fresh external-gate and disclosure recheck (2026-08-15)

A fresh read-only Keyverse PR #100 check found the same clean worktree head,
23 successful checks, and 8 explicitly skipped checks. Its review decision is
still changes requested, there is no independent approval, and the ten inline
threads have no unresolved current thread. No review was submitted, no thread
was resolved, and no protection, merge, or retry action was taken.

The separate central coverage-evidence PR remains an open draft and
review-required. It has 17 successful checks, 15 skipped checks, 8 queued
checks, and 3 neutral checks. Its queued state is not a code-specific failure,
so no job was retried. Neither PR state is a release approval.

A bounded public-disclosure scan of the product source, configuration, and
documentation excluded generated and dependency directories and found zero
files with the two prohibited source-identifying term families. The ADR
disclosure scanner also remains clean. Production HTTPS Keyverse configuration,
real business-account browser acceptance, target-frame Figma parity,
retained-artifact ownership disposition, and independent approval remain
unmet release gates.

## Amendment: Role-separated business surfaces and administrator review (2026-08-15)

LineageWeave now treats the reader/customer experience as a separate business
surface from the administrator diagnostic surface. A reader-scoped browser
session shows the 업무 홈, 업무공간, and 고객 화면 entry points, but no
administrator navigation or technical KPI strip. Its customer-master response
is still evidence-bound: an account or affiliate is visible only when the
authorized document relation and normalized Ontology/Semantic Layer records
survive the actor's corp/PU policy.

An administrator-scoped loopback browser run reached the same customer-facing
workspace plus the administrator access-policy and Event Lineage review
screens. It loaded the review candidates, opened the document popup, exercised
the evidence and Knowledge Graph routes, and changed a predicted/relatedness
visibility override to private and back to public with HTTP 200 responses.
Observed chronological transitions remained immutable. An unconfigured
Keyverse Admin account-list adapter returned its intentional unavailable status
in this development-only run; that does not grant a local identity-provider
fallback or satisfy production Keyverse Admin acceptance. The policy, review,
and document-scoped mutation paths remain server-authorized by the verified
administrator actor.

This amendment makes the customer master a product surface, not a developer
debug panel: its accounts, affiliations, evidence links, ontology classes,
semantic predicates, and source-document navigation are part of the customer
workflow. The general-user and administrator browser contracts, React build,
full Python coverage gate, and runtime schema contract all pass. Production
Keyverse real-account authorization, Figma target-frame parity, and retained
artifact/independent-review gates remain explicitly outstanding.

## Amendment: Figma target alignment remains external (2026-08-15)

A fresh read-only Figma context check confirmed that MU-02 still defines the
intended search journey as query, relatedness-ranked results, then source and
timeline; MU-14 still defines the detail journey as summary, anchor
verification, then action. The product implements those workflows with its
authorized document rail and detail dialog.

The supplied frames also still contain user-rejected legacy product-brand
annotations and a table/dashboard information architecture that the current
product intentionally does not copy. No Figma file was changed, and no legacy
brand was reintroduced into the product. Consequently the comparison remains
structural evidence only, not target-frame browser parity. A product-aligned
Figma target is required before this release gate can be accepted.

## Amendment: Event-Lineage transition integrity recheck (2026-08-15)

The active product image serves the React Event Lineage renderer that creates a
connector only when an adjacent bead carries the explicit observed
`row_successor` marker. Inferred and predicted relations are projected into the
separately labelled relatedness panel; query-result order is not a transition
signal.

A new read-only aggregate against the current direct-PostgreSQL persisted
snapshot found 43,707 document nodes, 107 `row_successor` edges, and 1,265
document-revision edges. Every row-successor edge was observed, mapped to two
source rows, and joined rows from the same document; the cross-document,
non-observed, and missing-source counts were all zero. The product health route
reported a healthy database. The deployed bundle contains the explicit
relatedness and observed-connector labels.

This is evidence that the historical unrelated-card chain is not present in
the current source, bundle, or persisted transition data. It does not
substitute for a production Keyverse configuration, real business-account
login/callback/session/logout acceptance, target-frame Figma browser parity,
retained-artifact ownership disposition, or independent approval.

## Amendment: reader-safe relatedness materialization (2026-08-15)

The persisted-detail function previously generated a bounded predicted
relatedness fallback and wrote it during a normal document or KG read. That
made a read-only direct-PostgreSQL verification fail before returning any
document data, and could allow an unauthorized request to create a derived
review candidate before its later authorization decision. The reader default
now returns the same derived relatedness without writing it. Only the bounded
administrator enrichment batch opts into materializing a predicted,
non-transition edge.

The active Compose-managed product passed a read-only direct-PostgreSQL check
across 64 multi-event documents: 157 event beads contained 93 connectors, all
matched an observed `row_successor` pair; 360 relatedness items were separate,
with zero connector mismatches and zero relatedness beads. This proves the
current product does not turn result order or relatedness into a chronology
edge. It is product/data-integrity evidence, not a replacement for actual
Keyverse acceptance, target-frame Figma parity, retained-artifact ownership
disposition, a required TEPP service, or independent approval.

## Amendment: Fresh protected-PR state (2026-08-15)

A new read-only PR check found Keyverse PR #100 still open and merge-blocked.
Its 31 reported checks are terminal: 23 successful and 8 skipped. All ten
review threads are resolved, but its review decision remains changes requested
and the current review set contains zero approvals. No review, retry, bypass,
auto-merge, or merge action was taken.

The separate central coverage-evidence PR remains an open draft,
review-required, and merge-blocked. Its current checks are 20 successful, 15
skipped, 4 queued, 1 in progress, and 3 neutral. Because the pending work is
not a verified code-specific failure, the same-head job was not retried.

Both PR states remain insufficient for release. Production Keyverse
configuration, real business-account browser acceptance, target-frame Figma
parity, retained-artifact ownership disposition, and independent approval
remain external release gates.

## Amendment: General-user and customer-master screen boundary (2026-08-15)

The current product feedback identified that the first visible screen looked
like a developer/operator debugging console. The accepted product boundary is
therefore explicit: an authenticated non-administrator enters the React
`업무 홈`, can navigate to `업무공간` and `고객 화면`, and sees recent
authorized work, evidence-backed customer relationships, period reports, and
the verified corp/PU/role context. Operational row/document/thread/KG/queue
KPIs, Keyverse account administration, access-policy editing, Lineage override,
LLM enrichment, and TEPP lifecycle controls are not part of the general-user
home. The administrator surface remains separately role-gated in both React
navigation and server routes; the UI distinction is not relied on as an
authorization control.

The customer screen is an actual business surface, not a developer payload
viewer. It reads the normalized `analysis_customer_accounts`,
`analysis_customer_affiliates`, and `analysis_customer_document_links`
relations through the actor-scoped `/api/customers` route. Only an
account-to-document evidence link that passes the same corp/PU/visibility
predicate used for documents can expose a customer account, affiliate edge,
source-document button, or customer-related semantic node. The persisted
Ontology/Semantic Layer binds the resulting entities to `schema:Organization`,
`schema:subOrganization`, and `schema:about`; an LLM hierarchy candidate does
not become an observed event transition merely because it is displayed.

The acceptance contract is now documented in `TRACEABILITY.md` and
`design-qa.md`: a reader run must show the three business navigation targets
without the administrator diagnostic strip, while an administrator run must
reach the policy, Lineage-review, enrichment, and TEPP controls. The current
source gate remains 329 tests with 7,313 statements and 2,838 branches at 100
percent line-and-branch coverage, with the React production build green. This
local evidence includes a loopback TEPP `POST accepted` → `GET completed` wire
smoke but no scientific TEPP result. Production Keyverse configuration, a real
business-account browser run, target-frame Figma parity, a deployed TEPP
service, and independent review remain separate release gates.

## Amendment: Current Compose runtime, identity ownership, and login UX recheck (2026-08-15)

A fresh product-image build passed the full source suite, Python compilation,
and React production build. The standard product service then failed closed
when its required direct-PostgreSQL runtime inputs were absent from the active
environment. A separate current Compose run supplied only the user-designated
direct database and source inputs at launch and reached database health. This
proves the rebuilt image can use the direct database; it is not a durable
deployment configuration or a substitute for approved production
configuration.

The product worker boundary was rechecked after the build: the image copies
only product runtime modules, the guard passed, and discovery, authorization,
token, and introspection paths returned HTTP 404. The retained issuer-shaped
source artifact remains present only as an unresolved ownership/audit item. Its
isolated contract test imports it and starts a loopback handler, but it is
neither imported, copied, nor served by the Compose product or worker. That
test material must not be used as real login acceptance or as a substitute
identity authority.

In the selected browser, malformed email input stayed on the product page and
received a focused Korean validation alert. A syntactically valid synthetic
address with external identity configuration absent also stayed on the product
page and now receives a plain retry-or-contact-administrator message. No real
account, production issuer, callback, session, logout, or passkey claim is
made.

A later read-only check of the current direct-PostgreSQL runtime confirms that
the required external Keyverse configuration is still absent while database
health is available. This is a safe unavailable state, not permission to
create, route to, or accept a local identity authority.

A fresh Keyverse PR #100 read shows the pull request open and merge-blocked
with a changes-requested decision, zero approvals, and all ten review threads
resolved. It currently has 22 successful checks, 8 skipped checks, and one
still non-terminal check. No retry, review, bypass, auto-merge, or merge action
was taken. Production identity configuration, real business-account browser
acceptance, product-aligned Figma parity, retained-artifact ownership
disposition, and independent approval remain release gates.

## Amendment: Large inline content and current release-gate recheck (2026-08-15)

The inline-image request boundary is now 50 MiB. This corrects the former
6 MiB ceiling for a source where an inline raster can exceed 40 MB. The product
re-evaluates persisted `inspection_eligible` metadata from MIME type and encoded
size when a document structure is read, so an old materialization does not hide
an authorized inspection action. The graph, default responses, browser payloads,
embeddings, and Valkey events remain metadata-only. Strict byte validation,
authorization, digest binding, verified TLS, and failed-inspection behavior are
unchanged. No further live inspection was run; external gateway acceptance of a
50 MiB request remains unproven and rejection does not fabricate OCR.

The rebuilt direct-PostgreSQL product image passed the current 329-test suite
(7,324 statements and 2,838 branches at 100 percent line-and-branch coverage),
Python compilation, and React production build, then reached database health.
The worker boundary guard passed and discovery, authorization, token, and
introspection routes each returned HTTP 404. The retained issuer-shaped source
artifact remains an unresolved ownership/audit item: it is neither imported,
copied, nor served by the product or worker, and it is not an identity
substitute or browser-acceptance evidence.

A fresh read-only Keyverse PR #100 check now reports all 31 checks terminal:
23 successful and 8 skipped. The pull request remains open and merge-blocked
with a changes-requested decision and zero independent approvals. No retry,
review, bypass, auto-merge, or merge action was taken. TEPP main continues to
document the analysis-run HTTP shapes as an accepted target contract rather
than a deployed service, so the product's loopback contract smoke is not a
scientific-runtime result. Production Keyverse configuration, a real
business-account login/callback/session/logout run, product-aligned Figma
browser parity, retained-artifact ownership disposition, an actual TEPP
service where required, and independent approval remain external release gates.

## Amendment: Truthful reader loading and isolated OIDC acceptance (2026-08-15)

The reader-facing `업무 홈` now distinguishes an actor-scoped request that is
still in flight from a settled empty result. Document and customer counts use
an explicit pending marker while their PostgreSQL/API surfaces load, and the
report card retains loading copy until the summary response exists. This keeps
the business screen from presenting a transient network delay as a zero-data
workspace while preserving the existing fail-closed empty-scope behavior.

The browser acceptance runner is directly executable and installs an exit
cleanup trap for only its separate conformance RP and external test IdP
Compose projects. It does not remove volumes, stop the product Compose stack,
or package an issuer in the product. A fresh external-IdP run completed email
login, authorization-code callback, session establishment, reader-only home
navigation, customer screen, direct-document popup, evidence drawer, and
semantic KG checks against the direct PostgreSQL runtime. The test account's
scope is supplied only at process launch and is absent from repository files.
This acceptance evidence does not waive the production Keyverse, Figma parity,
TEPP deployment, retained-artifact ownership, or independent-review gates.

## Amendment: Live report-judge recovery evidence (2026-08-15)

The persisted report set was re-evaluated in bounded maintenance batches
through the configured live HTTPS model gateway. The process retained explicit
LLM abstention semantics while a batch was incomplete and never converted a
gateway refusal into a deterministic pass or fail. After the loop, PostgreSQL
contained 80 weekly/monthly report slices with `llm_judge` verdicts of
`pass=50` and `fail=30`, 400 linked scores across 80 report observation groups,
zero reports without scores, and zero orphan scores. The longitudinal export
remains normalized as one state specification, one run, and 80 observations.

This is real product data-analysis evidence for the configured local runtime;
it is not evidence that the unmerged upstream fast-mlsirm PR is integrated or
that a production TEPP service, production Keyverse account, Figma pixel
parity, retained-artifact ownership decision, or independent repository review
has been completed.

## Amendment: 3NF automatic issue-ticket reconciliation and identity-evidence correction (2026-08-15)

Automatic issue To Do and calendar records previously carried deterministic
ticket identifiers while the full-snapshot writer did not persist their ticket
parents. The writer now upserts the parent ticket before either child work row
and, on snapshot replacement, reconciles only records marked as pipeline
created. This preserves independently created tickets. A bounded direct-
PostgreSQL metadata-only repair inserted 28,211 missing automatic parents,
preserved two non-automatic tickets, and left zero work rows without a ticket
parent. It read no document body, image payload, login data, or model result.

A separate protocol test project must not be described as a Keyverse emulator
or as Keyverse acceptance evidence. It can exercise generic relying-party
handling only; it neither enters the product image nor substitutes for a
configured Keyverse service. The product worker remains issuer-free and its
discovery, authorization, token, and introspection routes return HTTP 404.
No additional fixture is to be built or run to compensate for unavailable
Keyverse configuration. A configured production Keyverse run with a real
business account still must prove login, callback, session, and logout.

The rebuilt direct-PostgreSQL product runtime passed 330 tests, covering 7,334
statements and 2,842 branches at 100 percent line-and-branch coverage, plus
Python compilation and the React production build. This strengthens product
and data-integrity evidence only; product-aligned Figma browser parity, actual
Keyverse acceptance, retained-artifact ownership disposition, TEPP service
availability where required, and independent review remain release gates.

## Amendment: one-path Keyverse entry and public registration-route retirement (2026-08-15)

The product now exposes one customer login action: validate a business email
and continue to the configured Keyverse authority. The former product-side
first-use/passkey UI and its browser E2E enrollment switch were removed. The
unauthenticated `POST /api/register` and `POST /api/register/complete` routes
now return HTTP 404, so no public LineageWeave path can provision an account or
relay a passkey ceremony. Keyverse owns account creation and passkey policy
after the actual authorization hand-off.

The current source gate passed 333 tests, covering 7,358 statements and 2,838
branches at 100 percent line-and-branch coverage. React production build,
direct-PostgreSQL database health, the Compose boundary guard, and discovery,
authorization, token, and introspection route rejections passed. The active
product container also returned `404` for both retired registration routes;
its browser check verified empty-email, invalid-email, and unconfigured
valid-email guidance without navigating to an identity substitute. This does
not provide actual Keyverse account acceptance, product-aligned Figma parity,
TEPP service availability where required, retained-artifact ownership
disposition, or independent approval; those remain release gates.

The fresh Keyverse PR #100 check remains `OPEN` with `CHANGES_REQUESTED`: 22
checks are successful, eight are skipped, and one is pending. The observed
review history still contains a change request and no independent approval. No
retry, review, bypass, auto-merge, or merge action was taken.

## Amendment: Compose direct-PostgreSQL configuration hand-off (2026-08-15)

The product Compose profile now declares only empty environment interpolations
for the direct PostgreSQL DSN and source-table setting. This preserves the
existing operator-owned environment-file path while also making a standard
`docker compose --env-file` invocation deliver those required settings to the
product container. No source-table value or connection value is committed,
copied into the image, or delivered to the worker.

A rebuilt Compose-managed product reached healthy direct-database status at the
active local origin. Its browser check confirmed the single email-first action
and fail-closed unavailable-configuration message; discovery, authorization,
token, introspection, and both retired registration routes returned `404`.
The worker boundary guard remained green, with development mode disabled and
secure cookies enabled. This is Compose and product-boundary evidence only,
not actual Keyverse account acceptance or a substitute identity authority.

## Amendment: task-aware paper-grounded orchestration boundary (2026-08-15)

The product now allocates LLM computation from the task contract. Simple
classification and extraction use single-model routing. Customer-master,
appointment, issue, report, ontology-verification, and multimodal inspection
tasks use a bounded deep workflow with thinker, worker, verifier, and
synthesizer roles, one recursive pass, a fixed access list of authorized
document context, semantic layer, and source evidence, and role-specific
reasoning effort. This is the product application of the TEPP literature's
Fugu/Conductor/TRINITY routing-versus-composition boundary; the product does
not copy those systems' internals.

The policy envelope is nested in the user message for every OpenAI-compatible
gateway. The product adds top-level `route`, `conduct`, reasoning-effort, and
trace controls only when the configured base URL is explicitly the
contextual-orchestrator service. This prevents direct provider requests from
receiving non-standard API fields while retaining a real HTTP integration
point for the orchestrator. Multimodal image parts remain document-scoped and
preserve their location/context metadata. The upstream multimodal message
acceptance change is an independent review/merge gate and is not described as
integrated until its protected-branch review and merge are complete.

Evidence: `build_orchestration_envelope`, `_orchestration_request_fields`,
`_post_chat_completion_json`, multimodal inspection and lineage-chat request
tests; 332 product tests, 7,354 statements, and 2,836 branches at 100 percent
line-and-branch coverage; direct gateway transport isolation tests; and the
TEPP PRD, orchestration literature review, and TEPP orchestration ADR register.

## Amendment: truthful customer-surface loading state (2026-08-15)

The dedicated general-user customer screen now uses the same actor-scoped
settled-state contract as the business home. While `/api/customers` is pending,
the customer count is shown as pending and the account list, selected-account
detail, and affiliate tree say that data is loading. A transport error has
distinct error copy, while a successful zero-account response alone renders
the evidence-scoped empty-master message. This prevents a slow PostgreSQL read
from being misinterpreted as an empty customer master and keeps the customer
screen consistent with its Ontology/Semantic Layer evidence boundary.

Evidence: `customerLoadState`, `displayCustomerTotal`, the customer-screen
React surface contract, and the production React build.

## Amendment: evidence-backed customer hierarchy interaction (2026-08-15)

The customer-master screen now presents the normalized account and affiliate
relations as an accessible depth-aware tree. The browser derives rows only
from actor-filtered account nodes and persisted parent/child edges; it guards
cycles and orphan branches, exposes tree-item levels, and lets a user select a
node to inspect the same account-to-document evidence. The browser does not
call an LLM or infer a new affiliate relation. Ontology and Semantic Layer
semantics therefore remain a server/database responsibility, while the tree
is a truthful projection of the authorized graph.

Evidence: `customerTreeRows`, the `고객 계열 관계` React surface contract, and
the React production build.

## Amendment: disconnected browser response handling (2026-08-15)

The HTTP response boundary now treats `BrokenPipeError` and
`ConnectionResetError` during header or body writes as a normal client
disconnect. A browser may cancel a large authorized response after navigation;
the server must not attempt a second error response to a socket that is already
closed. This change affects transport observability only: authorization,
payload bounds, and error behavior for connected clients remain unchanged.

Evidence: `LineageHandler._send`, the disconnected-response HTTP contract test,
the full product test run, and Python compilation.

The post-change source gate passed 333 tests and the explicit product-runtime
coverage report remained at 100 percent for 7,358 statements and 2,838
branches.

The same release loop completed a fresh Microsoft Edge reader E2E against the
direct-PostgreSQL server: session resolution, 업무 홈, 업무공간, 고객 화면,
document popup, source drawer, and Knowledge Graph all completed with the
reader's administrator navigation and diagnostic KPI absent. The run used an
explicit local development actor and therefore proves browser/API UX and
authorization projection, not production Keyverse identity acceptance.

## Amendment: current Keyverse-only executable-boundary recheck (2026-08-15)

After the shared-workspace recheck, the focused identity and worker contracts
passed (12 tests), and the Compose boundary guard again found no worker import
or image copy of a local issuer. At the active product origin, discovery,
authorization, token, and introspection routes each returned `404`. No
recurrence of the prior executable-boundary defect was observed. The retained
issuer-shaped source artifact remains untouched as an ownership/audit finding;
this check neither removes it nor converts it into an identity substitute or
actual Keyverse browser-acceptance evidence.

## Amendment: product PostgreSQL relation-name audit (2026-08-15)

A bounded `BEGIN READ ONLY` catalog check inspected the 41 current
product-owned public relations whose names use the `analysis_`, `common_`,
`semantic_`, `ontology_`, or `lineage_` prefixes. Every inspected identifier
uses lowercase two-or-more-word snake case; no schema object or source row was
created, changed, or returned. The externally owned source relation is outside
this product naming claim, so this does not misrepresent a vendor/source-table
name as a LineageWeave migration decision.

## Amendment: isolated hourly product-gap proposal loop (2026-08-15)

The product now carries a repository-owned hourly proposal contract at
.github/workflows/hourly-product-gap.yml. At minute 17 of each hour, the
workflow first checks the pull-request queue and then either records a stable
no-op or starts one bounded OpenCode proposal using only NVIDIA_NIM_API_KEY.
The model cannot read operator environment files or runtime PostgreSQL data and
cannot use GitHub write, review, merge, task-delegation, or reviewer
credentials.

The proposal becomes a checksum-bound patch artifact. A fresh runner applies
that exact patch without model or publication credentials and runs the locked
Python suite, compilation, and React build. Only a separate publisher can
revalidate the default-branch SHA and open-PR queue, push a uniquely named
branch, and create one pull request. Orphan branches are removed when PR
creation fails. Protected-branch review, terminal Checks, approval, merge,
release, and deployment remain independent governance steps.

This is a development-supply-chain control, not a product runtime path. It
does not initialize Keyverse, connect to PostgreSQL, call TEPP internals, or
change the general-user/customer/admin authorization model. A repository with
no configured remote cannot provide live scheduler evidence; the workflow
contract test and dry-run path are the local evidence until publication and
repository secret configuration exist.

The proposal packager also rejects changes under .github/workflows and scans
the exact model secret against the binary patch before upload. This prevents
the model from changing its own trust boundary or publishing its credential
through a generated documentation or source file.

Evidence: .github/workflows/hourly-product-gap.yml,
docs/operations/hourly-product-gap-loop.md,
tests/test_hourly_product_gap_workflow.py, the 337-test/100-percent
line-and-branch coverage run, and the normal product checks.

## Amendment: direct-PostgreSQL batch export discipline (2026-08-15)

The command-line analyzer and both real/contract batch wrappers no longer
write a JSON, analytics, or DOT artifact by default. PostgreSQL persistence is
the canonical operational state; a detached export occurs only when an operator
supplies an explicit output path. This removes an accidental default file
surface without removing the reviewed explicit-export capability.

Focused CLI and wrapper contracts confirm the default has no output paths and
that explicit JSON/analytics paths still reach the analyzer. The current full
source gate passed 337 tests with 7,362 statements and 2,842 branches at 100
percent line-and-branch coverage; shell syntax, Python compilation, the
Compose identity guard, and the public-document disclosure scan also pass.

A rebuilt Compose product presents one email-first action. Browser checks
verified distinct empty-field and malformed-email guidance, then a generic
in-page unavailable result for a valid non-identifying address when Keyverse
configuration is absent; it does not redirect to or imitate an identity
authority. This is storage and local UX evidence only: it does not create new
analysis data, replace the actual Keyverse acceptance gate, or resolve the
retained issuer-artifact ownership finding.

## Amendment: package-only psychometric linking (2026-08-15)

The report boundary now treats `fast-mlsirm` as the sole FIPC/CAT/EAP
computation authority. The in-process Python estimator and the former
recorded-response path were removed; `try_fast_mlsirm_link` accepts only
normalized linked scores returned by the separate HTTP or sibling-package
connector. Missing transport, connector errors, malformed score bodies, and
diagnostic-only bodies return `status=unavailable`, `source=unavailable`, and
an empty score list. They do not carry longitudinal state or create
`analysis_linked_scores` rows.

This preserves the required Rust-backed psychometric boundary, prevents a
convenience estimate from being presented as calibrated output, and keeps
report publication useful through an explicit “연결 점수 없음” state. Existing
package-produced scores remain readable; this amendment does not rewrite
source documents or silently relabel persisted observations.

Evidence: `try_fast_mlsirm_link`, `score_period_reports`, the package-only
connector regressions in `tests/test_prototype_surfaces.py` and
`tests/test_lineage_runtime_contract.py`, and the current full source gate
(337 tests; 7,313 statements and 2,828 branches at 100 percent
line-and-branch coverage). The guarded 2026-08-15 PostgreSQL reconciliation
replayed 80 persisted Judge slices through the local package connector and
left 400 `fast_mlsirm` scores, zero orphan scores, zero reports without
scores, and zero legacy fallback payload rows.

## Amendment: complete product-side enrollment removal (2026-08-15)

The customer flow is now backed by the same ownership decision at every layer:
LineageWeave has no product-side account provisioning, local email capture,
browser-passkey challenge parsing, or attestation relay. Keyverse alone owns
first-time account and passkey policy after a successful authorization hand-off.
The retired `/api/register` and `/api/register/complete` paths reject both
`GET` and `POST` with `404` before session authorization, preventing an
authentication failure from obscuring their retirement.

The current full source gate passed 331 tests with 7,095 statements and 2,760
branches at 100 percent line-and-branch coverage; compilation, the Compose
identity guard, and the React production build also passed. A rebuilt direct-
PostgreSQL product returned healthy database status and verified all eight
issuer/registration boundary probes as `404`. Browser checks verified the
single email-first action, invalid-email guidance, and the generic
unconfigured-Keyverse result without navigation to an identity substitute.

The retained issuer-shaped source artifact was not changed. It remains an
unresolved ownership/audit finding and cannot be used as product identity or
release evidence. Actual production Keyverse configuration, real-account
login/callback/session/logout, product-aligned Figma browser parity, TEPP
service acceptance where required, and independent approval remain release
gates.

## Amendment: current protected-PR observation (2026-08-15)

A fresh read-only check of Keyverse PR #100 lists 23 passing entries (including
the completed CodeRabbit review) and eight explicitly skipped workflow entries;
the API check rollup itself contains 22 `SUCCESS` entries and eight `SKIPPED`
entries. Its current `coverage-evidence` check is successful, while the
remaining automated change request cites an earlier coverage-evidence failure.
The review decision nevertheless remains
`CHANGES_REQUESTED` and there are no independent approvals. This discrepancy
does not authorize self-approval, a retry, protection bypass, auto-merge, or
merge; independent review remains a release gate.

## Amendment: fresh general-user OIDC conformance (2026-08-15)

The general-user surface is now covered by a reproducible, data-bearing
browser acceptance record in addition to the local development-actor check.
The conformance runner started a clean test-only external IdP/RP pair on
unique ports and used the direct PostgreSQL runtime as the relying party's
source. The browser completed email login, authorization-code callback,
authenticated session, reader 업무 홈, 업무공간, 고객 화면, document popup,
source-evidence drawer, and semantic KG checks. The data-bearing assertion
observed 43,483 actor-authorized document rows and three actor-scoped customer
accounts.

This does not turn the fixture into Keyverse, add an issuer to the product
Compose profile, or prove a production business-account/passkey ceremony.
The runner's cleanup trap removes only its test RP/IdP projects. The product
authorization decision remains server-side: corp and PU are verified identity
attributes, the customer master remains account-to-document-evidence-bound,
and general users see 업무 홈, 업무공간, and 고객 화면 without administrator
diagnostic controls. This amendment records the missing customer-facing
acceptance surface requested by the product brief and keeps its Ontology and
Semantic Layer boundary explicit.

Evidence: `scripts/run_oidc_conformance_e2e.sh`,
`tests/compose.oidc-e2e.yml`, `tests/compose.oidc-conformance-idp.yml`,
`web/e2e/lineageweave.mjs`, and the 2026-08-15 unique-port run.

The post-documentation source gate remains 333 tests with 7,186 statements and
2,804 branches at 100 percent line-and-branch coverage; Python compilation,
workflow YAML parsing, Compose identity-boundary validation, runtime-schema
validation, the React production build, and the public disclosure scan also
passed.

## Amendment: measurable React presentation-model coverage (2026-08-15)

The React product now separates its deterministic presentation model from the
stateful component: email validation, Keyman normalization, safe asset-preview
eligibility, semantic display values, and customer-tree ordering live in
`web/src/ui-model.js`. Vitest V8 verifies that module at 100 percent: 82
statements, 148 branches, 24 functions, and 68 lines. The hourly verifier and
container web build run the V8 gate after `npm ci` and before the production
React build.

V8 reports and the bundled React output are generated only and are excluded
from version control and the container build context. This prevents absolute
local paths or transient bundles from being treated as public product artifacts.

This is intentionally scoped evidence. It does not claim that every stateful
`App.jsx` interaction is unit-covered; those flows retain their browser
contract/E2E evidence. The Python product-runtime gate remains 333 tests,
7,186 statements, and 2,804 branches at 100 percent. Production Keyverse,
real-account browser acceptance, a product-aligned Figma target, TEPP service
acceptance where required, retained-artifact ownership disposition, and
independent approval remain release gates.

## Amendment: reproducible no-issuer login-gate browser check (2026-08-15)

`web/e2e/login-gate.mjs` makes the configuration-independent login UX
repeatable with the product's existing Playwright dependency. Against a running
product origin, it verifies empty and malformed email guidance, a synthetic
valid address's explicit unavailable result, one email-first action, no legacy
brand or identity-protocol vocabulary, and no navigation to another origin.
When the unavailable mode is selected, all non-product browser requests are
aborted before navigation; no identity authority is emulated or contacted.

The 18100 direct-PostgreSQL product run passed this script. It is local UX and
boundary evidence only, not a production Keyverse account, callback, session,
logout, passkey, Figma-parity, TEPP-service, retained-artifact, or independent
approval acceptance claim.

## Amendment: no-issuer UX boundary and resilient report reads (2026-08-15)

The local login gate does not construct, start, contact, or represent an
identity authority. It verifies only the product's empty/malformed business
email feedback and its generic unavailable response when Keyverse is not
configured. It cannot be used as an approximation of real Keyverse or as
login/callback/session/logout release evidence.

Persisted weekly/monthly reports and their package-produced linked scores are
now read independently of optional evaluation-metric rows. If the optional
metric query is unavailable, valid report metadata and linked scores remain
visible while the metric list is empty; an unavailable decoration must not
erase a usable direct-PostgreSQL report surface.

Evidence: 333 Python tests with 7,173 statements and 2,798 branches at 100
percent line-and-branch coverage; V8 presentation-model coverage at 100
percent; a rebuilt Compose product with a healthy database; eight
registration/issuer probes returning `404`; and the synthetic-email browser
gate remaining on the product origin. The current read-only observation of
Keyverse PR #100 is `CHANGES_REQUESTED`, 22 successful checks, eight skipped
checks, one pending check, and zero independent approvals. It remains blocked
from merge and from release acceptance. Production Keyverse configuration,
real-account browser acceptance, product-aligned Figma parity, TEPP service
acceptance where required, retained-artifact ownership disposition, and
independent approval remain mandatory external gates.

## Amendment: evidence-status correction for Figma and linking (2026-08-15)

The product contains no in-process psychometric linker. Report linking accepts
only package-produced `fast-mlsirm` output from the configured HTTP or sibling
package connector; unavailable, malformed, or diagnostic-only connector bodies
remain unavailable rather than becoming a Python estimate.

The Figma comparison has passed structural QA only. Its supplied reference
frames and the live product intentionally differ in information architecture,
so the release-level product/Figma parity result is blocked until a matching
target frame and paired production browser capture exist. This correction does
not weaken the visual implementation or claim a defect; it prevents structural
token alignment from being misrepresented as final visual acceptance.

Likewise, the retained isolated protocol harness is not Keyverse and is not
current browser acceptance evidence. Product Compose starts no identity
authority, and the local login gate starts or contacts none. Actual Keyverse,
real business-account login/callback/session/logout, retained-artifact
ownership disposition, and independent approval remain required for release.

## Amendment: customer-visible lineage terminology (2026-08-15)

The product labels the user-facing document flow `글 자체의 Lineage`.
`event_lineage` remains the internal API/data-contract name so existing
direct-PostgreSQL payloads and observed-versus-relatedness controls stay
compatible. The wording change does not turn semantic relatedness into a
transition: only explicit observed successor markers connect events, and the
separate relatedness panel continues to say that it is not the next event.

## Amendment: correction — no local OIDC acceptance path (2026-08-15)

The earlier entries that described a separate test IdP/RP protocol fixture as
general-user browser acceptance are superseded as release evidence. That
retained material is an ownership/audit finding only: it must not be started,
used, or cited as a Keyverse substitute, a Keyverse emulator, or a login
acceptance path. This correction does not delete, move, chmod, or otherwise
alter the retained artifact.

The only current local login evidence is product-only UX and boundary evidence:
business-email validation, a generic unavailable result when Keyverse is not
configured, retired registration routes, and issuer-shaped worker routes that
reject requests. The Compose worker must not import, ship, serve, or contact a
local issuer. Actual acceptance still requires configured production Keyverse,
a real business-account login, callback, authenticated session, logout, and
the separate Figma, TEPP, artifact-ownership, and independent-approval gates.

## Amendment: evidence-gated event presentation (2026-08-15)

`event_lineage.has_observed_transition` is now derived only from a persisted,
observed `row_successor` edge. The React surface draws a numbered horizontal
Lineage only when that flag is true. When there is no direct event-transition
evidence, it explicitly says that no Lineage connection was confirmed and
renders unnumbered independent observations instead. Search result order,
semantic relatedness, and predicted/inferred edges cannot supply the flag or
produce a visual successor edge.

A first ad-hoc aggregate read the edge `reason` field instead of
`relation_name`; the corrected read-only direct-PostgreSQL check found 1,372
observed document-level edges, including 107 persisted `row_successor` edges.
All 78 documents with multiple observed events had a direct event transition;
zero such documents lacked one. The aggregate read no document body or source
identifier. This confirms the current data and makes the no-evidence UI path a
future-safe guard rather than a fabricated fallback.

The same `READ ONLY` transaction confirmed that the latest run metadata matches
43,814 rows, 43,707 documents, and 42,467 threads; all 80 persisted reports
have judge source and verdict, 400 linked scores have zero orphans and cover
every report, and the 135-row transactional outbox has zero pending events.

Evidence: 333 Python tests with 7,181 statements and 2,800 branches at 100
percent line-and-branch coverage; React V8 at 100 percent; a rebuilt
direct-PostgreSQL Compose product with healthy database status; the identity
boundary guard; and the product-only unavailable-Keyverse browser gate. None
of this is real-Keyverse login acceptance or final Figma/TEPP/review evidence.

## Amendment: refreshed Figma target evidence (2026-08-15)

The two supplied Figma reference nodes were re-read directly. They support
only structural reference for semantic search and detail-card hierarchy; they
retain legacy-brand marker text and have a different information architecture
from the current email-first product and `글 자체의 Lineage` surface. No Figma
file was modified, and the public product-source scan remains clear of the
legacy brand.

Therefore the Figma result remains `partial`: structural visual language is
verified, while product/Figma browser parity is blocked pending a matching
target frame and paired product capture. Historical isolated-identity browser
records are not evidence for either production Keyverse or final visual
acceptance.

## Amendment: partial-transition segmentation (2026-08-15)

The event surface now partitions beads into maximal direct-transition segments
and independent observations. A numbered horizontal segment contains only
adjacent beads joined by persisted observed `row_successor` evidence. If a
selected document has both connected and unconnected events, each connected
segment is rendered separately and every unconnected event is unnumbered in a
neutral observation grid. If the aggregate transition flag and bead evidence
ever disagree, the UI fails safe by rendering all events as observations.

This closes the remaining visual-order ambiguity: neither result order nor a
gap inside an otherwise valid event set can place an unrelated item at the end
of a Lineage row. The current direct-PostgreSQL corpus has no such gap among
its 78 multi-event documents, but the pure presentation-model regression covers
partial, empty, and malformed sequences before production data reaches React.

Evidence: 333 Python tests with 7,186 statements and 2,804 branches at 100
percent line-and-branch coverage; React V8 with 82 statements and 148 branches
at 100 percent; rebuilt direct-PostgreSQL Compose health; the identity-boundary
guard; and the product-only unavailable-Keyverse browser gate. This is not a
replacement for actual Keyverse, Figma, TEPP, ownership, or approval gates.

## Amendment: external TEPP and Keyverse release-gate recheck (2026-08-15)

A fresh read-only inventory of the running product Compose configuration found
no configured TEPP service URL or credential. Separately, the current TEPP
source and its HTTP-interchange doctoring explicitly state that the
analysis-run HTTP shape is **not** a live HTTP server and that the foundation
slice makes no production-readiness claim. LineageWeave therefore remains in
the explicit `tepp_service_unavailable` state for an actual run; it has not
started, contacted, or substituted a loopback, mock, or local service to make
that state look integrated.

The v1 port and normalized direct-PostgreSQL run registry remain useful
fail-closed product behavior, but are contract evidence only until an
operator-owned HTTPS TEPP deployment and credential can complete a real
authorized `POST`/`GET` lifecycle. No configuration value, source identifier,
or document content was read or recorded during this recheck.

The same external-gate check found Keyverse PR #100 open and blocked with one
pending check, one outstanding changes-requested review, and no approval.
No retry, self-approval, bypass, or merge was performed. The release condition
remains: actual production Keyverse and business-account login/callback/session/logout,
an operator-owned TEPP service acceptance, a matching Figma browser comparison,
the retained-artifact ownership disposition, and independent approval.

## Amendment: retired local-OIDC operating instructions (2026-08-15)

The current testing and architecture guides no longer present the retained
local OIDC/Keycloak fixture as an executable browser-login procedure. Static
syntax and source-boundary inspection remain permitted for the audit artifact,
but it must not be started, used, or cited as Keyverse, an identity substitute,
or release evidence. The product Compose profile continues to contain no
issuer.

This documentation correction preserves historical records rather than
rewriting them. It makes the operational path unambiguous: local browser work
may check email UX and unavailable configuration only; actual login, callback,
session, and logout require the operator-configured production Keyverse service
and a real business account.

The legacy filename of the ignored operator environment example now explicitly
means a local **product** configuration only. Its contents and README require
an externally operated Keyverse issuer; no loopback, host-bridge, Keycloak, or
Keyverse imitation is an approved substitute.

## Amendment: observed group-relationship coverage (2026-08-15)

The group-relationship algorithm supports same-company/different-PU,
cross-company, and cross-company/same-PU transaction and thread relations, but
it emits only source-observed actor co-occurrence. A bounded `READ ONLY`
aggregate of the current direct-PostgreSQL snapshot found two corporate scopes,
eight PU scopes, four observed same-company/different-PU transaction edges,
zero multi-corporate documents, zero multi-corporate threads, and zero
same-PU multi-corporate threads.

Therefore cross-company relation paths remain tested capability rather than a
claim about this corpus. No cross-company edge, synthetic actor, or inferred
transition is added merely to demonstrate the model. When a future authorized
snapshot contains the required co-occurrence evidence, the existing typed
relations may be materialized with their evidence status and provenance.

## Amendment: current reader report surface and ADR boundary (2026-08-15)

The general-user contract now includes the persisted report detail, not only
the document workspace and customer master. A reader enters `업무 홈`, can
move to `업무공간` or `고객 화면`, and can open an authorized weekly/monthly
report detail. The report detail presents the four persisted RAGAS-aligned
Judge observations with their verdict, score or abstention state, rationale,
and bounded evidence-document links. Selecting an evidence link continues
through the existing actor-filtered document and source-evidence routes.

This is a business surface, not an operator debugging view. Technical row,
thread, KG, queue, access-policy, Lineage override, LLM-enrichment, and TEPP
lifecycle controls remain absent from reader navigation and independently
role-gated on the server. The administrator surface keeps those controls for
review and mutation workflows; hiding them in React is never the
authorization mechanism.

The customer master remains semantically grounded rather than a client-side
name list. `analysis_customer_accounts`,
`analysis_customer_affiliates`, and
`analysis_customer_document_links` are read through the actor-scoped route;
only evidence that passes the document corp/PU/visibility predicate can
expose an account, affiliate, source document, or semantic customer node.
Normalized Ontology/Semantic Layer assignments continue to bind those
entities to `schema:Organization`, `schema:subOrganization`, and
`schema:about`. A displayed hierarchy candidate or relatedness result cannot
be promoted to an observed event transition.

The current local data-bearing browser contract rendered the reader
navigation, customer master, document popup, source drawer, Knowledge Graph,
and a report detail containing four metric cards and 32 authorized evidence
links. This is contract evidence only: production Keyverse login/callback/
session/logout, a product-aligned Figma comparison, and independent review
remain release gates.

## Amendment: Keyman selection as a KG entry point (2026-08-15)

The document popup's Keyman rows are interactive KG entry points. Selecting an
available LLM-derived actor requests only the actor-authorized
`/api/documents/{document}/knowledge` neighborhood, preserves typed node and
relationship direction, and renders the evidence-qualified result in the
popup. The generic KG chip remains a fallback for documents without a
persisted Keyman row; neither path creates a chronological event transition.

The data-bearing browser contract now prefers the actual Keyman button and
checks the relationship-direction region after the HTTP response. This is
local development-actor evidence, not production Keyverse acceptance.

The current Vitest V8 presentation-model gate covers 103 statements, 196
branches, 28 functions, and 88 lines at 100 percent. Older amendments retain
their historical measurements; this amendment is the current source-of-truth
for the directed-Keyman presentation gate.

## Amendment: directed Keyman-KG presentation (2026-08-15)

The persisted Keyman Knowledge Graph already returns authorization-filtered
nodes and directed `source`/`target` edges. The product now presents each valid
edge as `source → target`, alongside its entity types, customer-readable
relation label, unchanged relation code, and evidence status. It renders the
entire server-bounded neighborhood rather than clipping it in the browser.
This makes the direction and typed relationship visible without recomputing,
upgrading, or inventing an edge.

The display fails closed for malformed graph data: an edge is omitted when its
source, target, or relation cannot be resolved to an authorized labeled node.
It never exposes orphan identifiers as if they were a legitimate connection.
This guard is presentation validation only; server-side authorization and the
persisted evidence tier remain the authority for graph membership and meaning.

Evidence: the pure `knowledgeEdgeRows` model covers observed and unknown
relation types, directions, entity labels, evidence states, and malformed
endpoints at 100% V8 coverage (103 statements, 196 branches, 28 functions,
and 88 lines); the React surface contract passes; and the production React
bundle builds. This implementation does not replace the outstanding production
Keyverse, operator-owned TEPP, Figma-parity, retained-artifact, or independent
approval release evidence.

## Amendment: current identity and Figma acceptance boundary (2026-08-15)

No local, isolated, simulated, or otherwise substitute identity authority is a
valid Keyverse test or release path. The retained issuer-shaped source material
is an unresolved ownership/audit finding only and remains untouched. The
product's local browser check is limited to synthetic-address email guidance:
empty input, malformed input, and an unconfigured valid address. It neither
contacts an authority nor proves a login, callback, session, logout, or
passkey journey.

The currently accessible Figma source exposes a design-document cover rather
than a product-aligned frame. Its source content was not retained in the
repository. A visual-parity result would therefore be false precision; the
latest design QA records parity as blocked. Actual production Keyverse with a
real business account, a matching Figma target and paired browser capture,
operator-owned TEPP service acceptance where required, retained-artifact
ownership disposition, and independent approval remain the release condition.

## Amendment: authorized ticket-status lifecycle and current coverage (2026-08-15)

Issue tickets now use one common-table `ticket_status` enum with the allowed
values `open`, `in_progress`, and `resolved`. The change does not invent an
assignee directory or new identity capability. A status update first resolves
the document under the caller's existing authorization context, requires the
same `manage_tickets` decision as ticket creation, and validates the submitted
enum value before any write.

One direct-PostgreSQL operation scopes the ticket lookup and both state updates
to the requested document: the issue ticket and its linked To Do rows receive
the same status. The established `issue_ticket_changed` transactional-outbox
event is then flushed through the existing Valkey path. The in-memory detail
projection is refreshed only when present; a missing cache or document node is
not treated as persistence failure. The React detail surface exposes the
status selector only to actors that can manage tickets, while other readers
remain read-only.

Focused application, HTTP, enum, and React contracts cover valid changes,
invalid values, denied actors, missing tickets, cache-absent branches, the
paired database updates, and the outbox event. The corresponding current source
gate passed 340 tests across 7,419 statements and 2,896 branches at 100 percent
line-and-branch coverage. This test evidence does not replace the
actual production Keyverse/business-account journey, matching Figma browser
comparison, operator-owned TEPP acceptance where required, retained-artifact
ownership disposition, or independent approval release gates.

A fresh read-only check of Keyverse PR #100 remains open, merge-blocked, and
changes-requested, with 22 completed-success checks, eight completed-skipped
checks, one non-terminal check entry, and no independent approval. No retry,
self-approval, bypass, or merge action was taken.

The 2026-08-15 upstream recheck also found TEPP main after its latest
persistence merge and fast-mlsirm main after its recent item-bank/many-facet
merges, while contextual-orchestrator main had no corresponding recent merge.
Contextual-orchestrator PRs #563 and #566 have passing technical checks but
remain review-required; the selected fast-mlsirm PR #864 has a failing Strix
check. These are external protected-branch facts, not LineageWeave integration
evidence. No retry, self-approval, bypass, or merge was performed.

## Amendment: general-user product surface and administrator separation (2026-08-15)

The authenticated product now has an explicit general-user surface. Every
verified actor enters `업무 홈`, where the product presents recent authorized
work, customer relationships, report availability, and the actor's effective
scope in business language. The actor can then open `업무공간` for the
evidence-backed post/event workspace and report detail, or `고객 화면` for the
evidence-bound customer master and affiliate tree. Report cards expose the
persisted Judge metrics and linked or explicitly unlinked psychometric state;
source-document buttons continue through the same actor-filtered document
route.

The reader navigation does not contain technical row/thread/KG/queue
diagnostics, access-policy editing, Lineage overrides, enrichment controls,
TEPP lifecycle controls, or Keyverse account administration. Document popup
content, evidence, KG, chat, report evidence, and customer-master relations
remain read-only unless the verified actor also has the server-side management
role required for that mutation. React hiding is only product presentation;
every API route rechecks the Keyverse actor's corp, PU, role, visibility, and
document evidence before reading or writing PostgreSQL.

This decision also fixes the product-language boundary: the general-user
experience is not a developer debugging dashboard, while administrators retain
a separate `관리자 모드` for policy and operational review. The customer master
shown to readers remains an Ontology/Semantic Layer consumer: accounts and
affiliate edges are exposed only when normalized customer-document evidence
passes the same actor predicate, and no hierarchy candidate becomes an
observed event transition.

Evidence: the data-bearing reader browser run reached 업무 홈, 업무공간,
고객 화면, report detail with four metric cards, document popup, source drawer,
and Knowledge Graph; its reader actor had no administrator navigation or
diagnostic KPI strip. Production Keyverse login/callback/session/logout,
operator-owned TEPP acceptance, matching Figma parity, and independent review
remain release gates.

## Amendment: evidence-bound factor-item catalog and calibrated report bank (2026-08-15)

The report-scoring path now separates item discovery from item calibration. A
live `factor_item_catalog` request sees only a bounded sample of persisted
report slices and writings. Its parser allowlists factor and document IDs,
deduplicates item stems, caps item size, and rejects any candidate without
supplied report/document evidence. Candidate metadata is persisted in
`analysis_factor_items`; many-valued support is normalized in
`analysis_factor_item_evidence`; and fast-mlsirm calibration output is kept in
`analysis_factor_item_calibrations`.

The current direct-PostgreSQL run used 10 fixed anchor items and five live LLM
candidates. The separate Rust-backed connector returned 15 finite calibration
rows and all 15 items are marked `calibrated`. It produced five linked scores
for each of 58 report slices (290 total); 22 of the 80 slices remain explicitly
unlinked because their item responses were insufficient. A missing response is
not imputed and an unavailable connector cannot promote an item or create a
score. Broader labeled psychometric validation and independent review remain
required before business KPI use.

## Amendment: evidence-text agreement for organization aliases (2026-08-15)

The organization-alias boundary now verifies the content of the cited external
evidence, not only the model-supplied evidence IDs. The contextual LLM may
propose a canonical organization from the authorized document context, but
automatic R&R expansion promotes it only when organization-only SearXNG text
contains both the source alias and the same canonical name. The administrator
alias route applies the same fail-closed rule: a `verified` model verdict with
an unrelated, missing, or conflicting cited excerpt becomes `insufficient`.

This keeps `skos:exactMatch` a directional inferred semantic assertion with
auditable evidence while preventing a search result for a different entity
from changing a person affiliation, customer account, or event history. The
alias assertion remains outside `row_successor` and can never create a
chronological Lineage connector. Existing persisted assertions are retained as
historical review records, but snapshot reconstruction applies the same text
support check before exposing them in the KG; unsupported history is not
deleted, promoted, or presented as a current semantic fact.

The current source gate after this change completed 347 tests across 7,526
statements and 2,934 branches at 100 percent line-and-branch coverage. The
React build and direct PostgreSQL schema contract remain companion gates.

A read-only runtime audit found 13 alias candidate records, 11 historical
`verified` decisions, and 60 external evidence rows. Only one verified review
candidate satisfied the current canonical-text rule; the rebuilt KG projection
exposed one alias edge while the remaining historical decisions stayed in the
review ledger. No source row, document body, or external identifier was printed
by the audit.

## Amendment: bounded live customer-commitment enrichment and scoped delivery (2026-08-15)

Customer-commitment derivation must produce a real model result without
creating a Keyverse user, local issuer, or synthetic identity acceptance path.
The operator-only direct-PostgreSQL batch therefore has no user actor. It
selects at most 64 persisted document summaries that contain an appointment
hint and an explicit date, and sends only the bounded title/summary projection
through the existing live product-model transport.

The batch replaces a document's extracted appointment rows only when every
returned row is structurally valid and explicitly model-derived. A fallback,
malformed, or unavailable result leaves the existing extraction untouched.
Each completed row writes the existing transactional outbox with a fresh,
internal batch marker. Delivery happens only after the PostgreSQL transaction
commits and selects event type, non-user operator actor, and that exact marker;
it cannot invoke a global pending-outbox flush or deliver unrelated mutations.
At-least-once semantics remain: a Valkey acknowledgement is followed by the
outbox publish mark, so consumers deduplicate by the existing event ID.

One bounded 16-document live-HTTP batch completed 14 model-derived appointment
refreshes and retained two fallback extractions. An aggregate-only direct
PostgreSQL verification found 6,982 appointment rows across 6,982 documents:
14 model-derived and 6,968 extracted. The 14 scoped Valkey events were
acknowledged and marked published, with zero scoped events pending and Valkey
ready. No source body, model text, event identifier, credential, or account
identity was retained in this evidence.

The current explicit source gate passed 340 tests across 7,409 statements and
2,894 branches at 100 percent line-and-branch coverage. This production-data
evidence does not replace actual production Keyverse/business-account login,
callback, session, and logout; a product-aligned Figma browser comparison;
operator-owned TEPP acceptance where required; retained issuer-artifact
ownership disposition; or independent review and approval.

## Amendment: evidence-scoped customer-search ancestry (2026-08-15)

The customer screen is a hierarchy, so returning only the text-matched
subsidiary can make a real persisted relation appear as an unconnected root.
The server now starts with the query matches, keeps those accounts first for
the client selection model, then follows the persisted `parent_of` relation to
include only ancestor accounts already present in the actor-scoped customer
master. It filters affiliate edges again against that final account set.

This is presentation context, not relationship creation. A missing parent
record remains absent; the server does not synthesize a customer, bypass the
document-evidence filter, or fetch a parent from another corp/PU scope. The
bounded current aggregate found that all 22 stored affiliate edges have both
persisted account endpoints, so a searched subsidiary can retain its existing
tree path without a fabricated node.

Focused customer-surface, HTTP, and React contracts pass. The current explicit
source gate passed 340 tests across 7,419 statements and 2,896 branches at 100
percent line-and-branch coverage. This does not replace production Keyverse
real-account acceptance, Figma target parity, operator-owned TEPP acceptance,
retained-artifact ownership disposition, or independent approval.

## Amendment: evidence-backed unscheduled issue work and scoped live refresh (2026-08-15)

The issue-work prompt requires an empty `due_on` when the supplied evidence
does not explicitly support a date. The former shared mapping silently filled
that absence with the current date, which made an unscheduled follow-up look
like a factual calendar commitment. The product now accepts only a complete,
valid calendar date for issue work. `analysis_calendar_items.occurred_on` is
nullable, historical `pending_llm` rows with the synthetic fallback are changed
to `NULL`, and the popup presents that state as `일정 미정`. A complete LLM
To Do/calendar pair can therefore remain LLM-derived without inventing a date.

The new operator-only direct-PostgreSQL refresh selects at most 64 pending
tickets and sends the existing live product transport only the title plus a
bounded Korean summary. It does not create a Keyverse user, contact an
identity authority, or create a local issuer path. A response missing either
work body leaves the persisted pending work unchanged. A completed pair
upserts its 3NF parent/work rows and writes a transactional outbox event with a
fresh internal batch marker. Valkey delivery filters by event type, the
non-user operator actor, and that exact marker, so it cannot flush unrelated
pending events.

One bounded live-HTTP run requested eight tickets: three complete LLM pairs
were persisted, five incomplete/fallback responses remained pending, and all
three matching events were acknowledged by Valkey with zero scoped events
pending. An aggregate-only direct-PostgreSQL check then found five LLM and
28,207 pending rows in each work relation. All pending calendar rows were
unscheduled; three of the five LLM calendar rows were intentionally
unscheduled because no explicit date was supplied. No source body, model text,
credential, account identity, or event identifier was retained in this record.

The current full-source gate passed 343 tests across 7,494 statements and
2,920 branches at 100 percent line-and-branch coverage; the V8 presentation
model gate (101 statements, 190 branches, 27 functions, 86 lines), production
React build, Compose configuration, and issuer-free Compose boundary guard
also passed. A fresh read-only Keyverse PR #100 observation remains open,
merge-blocked, and changes-requested with 22 successful checks, eight skipped
checks, one non-terminal check, and no independent approval. No retry,
self-approval, bypass, or merge was performed. Production Keyverse with a
real business account, matching Figma browser parity, operator-owned TEPP
acceptance where required, retained-artifact ownership disposition, and
independent approval remain release conditions.

## Amendment: shared thread identifiers are not document revisions (2026-08-15)

The direct PostgreSQL evidence model previously treated a common thread
identifier plus timestamp order as an observed `acth_revision` transition.
That claim was too strong: identifier co-membership is evidence that records
should be considered together, not evidence that one document caused,
superseded, or directly followed another. It could make an arbitrary set of
related writings look like a linear history.

The product now permits only observed same-document `row_successor` edges to
form the chronological event presentation. Documents sharing a thread
identifier become the inferred, non-temporal `shared_thread_identifier`
relation. The graph builds canonical unordered document pairs so endpoint
storage does not communicate time order; the React detail presents the result
as `같은 스레드 단서` below the timeline, never as a numbered bead or connector.
An administrator can suppress or restore that inferred relation through the
existing normalized override ledger.

For safe continuity, product startup runs a narrow idempotent PostgreSQL
correction against only legacy rows that match the historical relation,
observed tier, and same-thread rationale. It updates the corresponding
Lineage and Knowledge Graph relation/tier/rationale in place; it deletes no
document, source record, content asset, or audit row. Aggregate-only checking
confirmed matching legacy records existed in both projections before the
correction path was introduced. On 2026-08-15, the rebuilt Compose product
started against the direct PostgreSQL runtime and corrected 1,265 matching rows
in each projection. A post-start aggregate retained 107 observed
same-document `row_successor` edges and showed the 1,265 shared-thread rows
only as inferred `shared_thread_identifier`; no historical observed
`acth_revision` row remained. Unit contracts cover both no-table and
two-projection migration paths, the new all-pairs relatedness construction,
and the assertion that shared-thread relatedness can never create an event
connector.

A separate read-only runtime probe found that the older product container used
by the prior browser capture still served the SPA fallback for the bare
`/authorize` alias, while the current Compose product rejects it. This is a
legacy runtime-boundary recurrence, not evidence that the current source or
worker serves an issuer. The older container was not stopped, replaced,
modified, or used for acceptance; the retained issuer-shaped source artifact
also remains untouched and unresolved for ownership audit.

The latest Figma connector read exposes only the supplied file's cover page,
contradicting the earlier recorded target-frame inventory. The earlier target
claim is therefore withdrawn as current acceptance evidence. A reproducibly
readable target frame plus a user-chosen-browser capture at the same real
Keyverse-authenticated document state remain required for design parity.

## Amendment: administrator directory degradation without policy loss (2026-08-15)

The administrator browser now treats the Keyverse account directory as a
separate external capability. If the reviewed Keyverse Admin configuration is
absent, `/api/admin/keyverse/accounts` remains unavailable and account-claim
mutation is not simulated. The React screen reports a Korean availability state
instead of exposing the raw `keyverse_admin_configuration_required` string or
claiming that the tenant has zero accounts.

This does not reduce the administrator's local product controls: the same
verified admin can still inspect and mutate actor-scoped 게시글 공개 정책 and
review durable Lineage overrides through the server-authorized PostgreSQL
routes. No local issuer, synthetic account, or recorded Keyverse response is
introduced. A fresh admin browser run reached `accessPolicyScreen` and
`lineageReviewScreen`, loaded three review candidates, completed private/public
restoration and typed organization-Keyman save/restore with HTTP 200, and showed
the directory-unavailable message.

## Amendment: current Compose product, route aliases, and Figma target evidence (2026-08-15)

The current product Compose profile was rebuilt with direct PostgreSQL runtime
configuration, development identity disabled, and no Keyverse or OIDC
environment interpolation. The configuration stays outside the repository;
the rebuilt product reached healthy state while an anonymous session remained
Keyverse-gated. Runtime source fingerprints match the rebuilt worktree and the
retained issuer-shaped utility is absent from the product filesystem. This
proves only that the RP can start safely without an
identity substitute; it does not contact Keyverse or prove login, callback,
session, logout, passkey, or real-account acceptance.

Both the product and the Compose model worker rejected the standard
discovery/authorization/token/introspection paths. The product additionally
now rejects the bare authorization, token, and introspection aliases before
the React fallback can return the app shell. The retained issuer-shaped source
artifact remains untouched and unresolved for ownership audit. A read-only
inspection of older Compose-managed product containers found the standard
issuer-shaped routes rejected there as well; no local issuer was started,
modified, or used as acceptance evidence.

The current product and worker each returned `404` for both `GET` and `POST`
across the four standard issuer surfaces and their common bare/canonical
aliases. This executable check is boundary evidence only; it does not replace
Keyverse login acceptance.

The latest Figma connector read exposes only the supplied file's cover page,
which contradicts the earlier target-frame inventory. That earlier inventory
is therefore withdrawn as current visual truth. A reproducibly readable target
frame and a user-chosen-browser capture at the same real Keyverse-authenticated
document state are both required before parity can be assessed.

Focused HTTP route contracts and the Compose identity-boundary guard passed
after the alias hardening. The complete current-source gate also passed 350
tests across 7,569 statements and 2,954 branches at 100 percent line-and-
branch coverage; the React V8 gate (103 statements, 196 branches, 28
functions, and 88 lines) and production build passed at 100 percent as well.
The rebuilt container's direct database health and issuer-route probes passed
without emitting source content, credentials, account identities, or Figma
internals. A fresh read-only Keyverse PR #100 observation remains open,
merge-blocked, and changes-requested: its current check rollup has 22
successful checks, eight skipped checks, and one pending check. The sole
changes-requested review cites an earlier coverage-evidence failure, while the
current coverage-evidence check is successful; that discrepancy still requires
independent human review. No retry, self-approval, protection bypass, or merge
was performed. Production Keyverse with a real
business account, paired Figma browser comparison, operator-owned TEPP
acceptance where required, retained-artifact ownership disposition, and
independent approval remain release conditions.

## Amendment: remote PR regression and check normalization (2026-08-15)

The remote LineageWeave PR that carried the ontology/role-responsibility
changes exposed a real vision-response parser regression: the label matcher
consumed the opening Markdown emphasis marker from values such as
`TEXT: **LT7**`. The matcher was narrowed so emphasized labels and emphasized
field values are parsed independently; a changelog entry and an existing
regression test document the contract.

Commit `88a58d6` was pushed to the PR branch after a complete local run passed
350 tests with 16 skips. The fresh remote Full test suite, frontend build,
coverage evidence, security scans, Noema, OpenCode, and dependency checks all
passed. Strix remained in progress at this observation, and the PR was not
merged because an independent approval was absent and the protected branch
reported `BLOCKED`. No approval, bypass, or synthetic review was used.

## Amendment: reader/customer semantics and stale-thread response filtering (2026-08-15)

The product entry point for an ordinary authenticated user is a business
surface, not the operator console. The React reader starts at `업무 홈` and
offers only actor-scoped `업무공간` and `고객 화면`; administrator policy,
Lineage review, enrichment, TEPP, and Keyverse account-directory controls are
separate navigation and separately authorized routes. This is a product
boundary, not a CSS distinction: the server derives every document, customer,
evidence, KG, report, chat, and mutation result from the verified Keyverse
actor's corp, PU, visibility, role, and evidence scope.

`고객 화면` is the reader projection of the normalized semantic model. A
customer account is an `schema:Organization` node, a persisted affiliate
relation is `schema:subOrganization`, and the account-to-document evidence is
`schema:about`. The three PostgreSQL relations
`analysis_customer_accounts`, `analysis_customer_affiliates`, and
`analysis_customer_document_links` remain separate 3NF facts. A UI label,
LLM suggestion, or account-tree position cannot make an unsupported customer
or affiliate relation visible; a visible customer must retain an authorized
source document that can be reopened from the screen.

The response layer now applies the same temporal truth rule after persistence:
legacy `shared_thread_identifier` rows are returned only when both current
document endpoints still carry the stored thread identifier. Stale historical
rows are therefore excluded from reader Lineage, administrator review, and
Keyman/KG neighborhoods without deleting source, document, or audit records.
Only same-document `row_successor` remains a numbered chronological event.

The product test workflow provisions an isolated PostgreSQL service before
the process-local database fixture runs. Product images and the test-only
OIDC conformance image declare non-root runtime users; Keyverse remains an
external relying-party boundary. Manual review of the explicit Semgrep
exceptions confirms that table identifiers are immutable product constants,
row values are bound parameters, and every dynamic HTTP request is built only
after the corresponding HTTPS/loopback allowlist validation.

## Amendment: runtime alias and current-thread recheck (2026-08-15)

A fresh read-only runtime probe found a current-product recurrence: the
`/oidc/*` issuer-shaped aliases were reaching the single-page-app fallback
instead of the existing issuer-route rejection guard. The Compose worker was
already rejecting them. The product guard now covers the same discovery,
authorization, token, and introspection aliases; both `GET` and `POST` are
covered by the HTTP contract. After rebuilding the direct-PostgreSQL product,
all 32 product-and-worker issuer-shaped requests returned `404`; health stayed
ready and an anonymous session stayed Keyverse-gated. The retained
issuer-shaped source artifact was neither imported, copied into the product
image, executed, nor modified.

The direct PostgreSQL aggregate also found one retained historical
shared-thread audit row in each of the Lineage and KG projections whose current
endpoints no longer match its stored thread evidence. It remains preserved for
audit, but the shared response guard returns 3,020 current matching pairs in
each projection and excludes that historical pair from reader detail,
administrator review, and KG neighborhoods. The only observed chronological
edges remain 107 same-document `row_successor` records. No source content,
document identifiers, account values, or credentials were emitted by this
check.

The current source gate passed 350 tests and 100 percent line-and-branch
coverage for the shipped product/runtime sources (7,569 statements and 2,954
branches); the React V8 model gate and production build also passed. A fresh
read-only Keyverse PR #100 check remains open, merge-blocked, and
changes-requested. Its current check rollup is terminal and coverage evidence
is successful, but an independent review/approval remains required; no retry,
self-approval, bypass, or merge was performed. Real Keyverse business-account
login/callback/session/logout, a reproducible Figma target with paired
user-chosen-browser comparison, operator-owned TEPP acceptance where needed,
retained-artifact ownership disposition, and independent approval remain
release conditions.

## Amendment: complete product-task live-model fallback (2026-08-15)

The Compose service is an issuer-free model proxy, not a recorded-response
adapter. Previously, it could forward Keyman, content inspection, and event
chat, while the product transport for customer-master, role classification,
appointments, issue work, ontology verification, factor-item generation, and
report judging required a direct gateway. That asymmetry made the product
degrade differently depending on which LLM feature a user entered.

The product transport now follows one boundary: use the direct verified HTTPS
gateway when configured; otherwise start or reuse the Compose worker and send
the explicit product task to `/api/v1/product_task`. The worker owns a bounded
allowlist and task-specific structured-output prompts, then forwards the task
to the live gateway. A gateway `404` on a task-specific endpoint may fall back
to the provider-compatible chat endpoint, but a missing or unreachable gateway
returns an explicit unavailable/503 result. No local issuer, account, token,
recorded response, or fabricated business result is introduced.

This preserves the Ontology/Semantic Layer and ABAC boundary: the server
authorizes the actor and constructs the evidence-scoped body before transport;
the worker cannot widen that scope or authenticate a user. The worker remains
HTTP-only and independent of TEPP and contextual-orchestrator internals.
Focused worker and runtime contracts cover direct product forwarding, Compose
fallback routing, unsupported-task rejection, and Compose failure reporting.

## Amendment: truthful browser identity evidence (2026-08-15)

The browser interaction runner can use an already-authenticated development
actor to validate reader/admin screens against the direct PostgreSQL product.
That session is not an identity-authority test. Its result now reports
`preauthenticated_session: true`, `reached_identity_authority: false`, and
`identity_form: false`; requesting Keyverse-required or completed-login mode
with the shortcut fails immediately. Only a real authorization-code callback,
verified session, and logout can set the Keyverse acceptance result. This keeps
the general-user/customer/admin browser evidence useful without overstating
the external Keyverse release gate.

## Amendment: persisted HTML and inline-image analysis evidence (2026-08-15)

The direct PostgreSQL runtime now has a read-only aggregate proving that the
content path was exercised on real source data: 267 normalized content blocks,
299 DOM/format hints, 7 asset profiles, 7 multimodal inspections with
non-empty OCR text, 3 persisted object labels, and 29 semantic chunk
embeddings. Format hints remain separate from embedding text so tags, color,
alignment, bullets, and font-size signals do not pollute the semantic vector.
Each inspection remains bound to its document, source position, asset digest,
and authorized evidence route. A missing future multimodal provider is an
explicit unavailable result; it cannot be replaced by `[image: content
unavailable]` as a fabricated analysis or by a guessed graph assertion.

The same runtime aggregate contains 8 Ontology namespaces, 46 terms, 28
relation rules, 264,750 Knowledge Graph nodes, 838,550 Knowledge Graph edges,
836,794 semantic edge assertions, and 308,457 semantic node assignments.
These are persisted normalized facts and assertions, not permission to expose
the whole graph: every reader and agent request still receives only the
verified actor's authorized evidence-scoped subgraph.

## Amendment: permission-aware live LLM browser evidence (2026-08-15)

The browser workflow now distinguishes product permissions before exercising
LLM controls. A reader cannot see or invoke the manager-only Keyman derivation
button, but can ask the document-scoped Event Lineage chat. Against the
configured live gateway, the reader run returned a non-empty answer with five
citations and a VOC citation opened and closed the authorized source drawer.
An administrator run returned HTTP 200 for live Keyman derivation, preserved a
typed organization actor without coercing it into a person, and passed the same
chat citation/source checks. These development sessions validate product
authorization and workflow behavior only; they are not Keyverse login
acceptance evidence.

## Amendment: administrator report-quality retry (2026-08-15)

The administrator console now exposes a report-quality action at
`POST /api/admin/reports/refresh`. It reuses the existing PostgreSQL advisory
lock and bounded stale-slice maintenance path, so a temporary Judge or
fast-mlsirm outage can be retried after the live provider returns without
rebuilding valid report rows or fabricating a score. The server requires the
verified administrator role and emits `period_report_refresh_completed` through
the transactional event outbox; the browser then reloads the actor-filtered
report surface. An unchanged result remains an explicit no-op/abstention, not a
successful measurement.

The implementation was rechecked against the current source tree: 351 Python
tests passed with one expected skip because the optional fast-mlsirm interpreter
is not installed, the five measured runtime modules covered 7,598
statements and 2,966 branches at 100%, and the administrator browser workflow
received HTTP 200 from the refresh action against the direct PostgreSQL data
path. This is product behavior evidence; it does not waive the independent
review, real-Keyverse, or Figma selection gates.

## Amendment: reader Keyman vocabulary boundary (2026-08-15)

A visual review of the direct-PostgreSQL general-user browser flow found that
the document popup still exposed the implementation labels `source` and
`status`, including the internal LLM/orchestrator values. The server and
administrator audit payloads retain those provenance fields, but the reader
surface now renders only business terms: `분석 상태: 자동 도출`,
`분석 상태: 사용자 관리`, and the corresponding management-state labels.
The popup headings also use `Keyman · 사측` and `Keyman · 상대측` rather than
an implementation name. This keeps the ordinary-user screen a business
workspace while preserving technical provenance for authorized review.

This presentation rule does not change the Ontology/Semantic Layer boundary:
Keyman nodes and their related organizations, people, events, and documents
continue to come from the actor-filtered, evidence-backed semantic graph. It
also does not change the general-user/admin split: readers can select a
Keyman and inspect authorized relationships, while derivation and mutation
remain server-gated management actions.

Evidence: `test_web_page_uses_verified_session_and_real_api`, the React
production build, and the visual reader browser capture reviewed on
2026-08-15.

## Amendment: immutable container and workflow dependencies (2026-08-15)

The supply-chain review identified mutable base-image references and unhashed
workflow installation of the pinned `uv` runner. Product, Compose worker,
SearXNG, and isolated OIDC-conformance images now use the exact registry
digests captured by the security review. The product's React build stage runs
as the non-root `node` account; runtime stages keep their existing explicit
non-root users. Both the ordinary test workflow and the hourly proposal
verifier install the Linux `uv` wheel with `--require-hashes`.

This is a reproducibility and least-privilege boundary only. It does not add
credentials to images, change the issuer-free Compose worker, grant the
proposal agent write or review authority, or alter the PostgreSQL/Keyverse/
Valkey/HTTP integration boundaries.

Evidence: `test_container_images_pin_base_digests_and_run_non_root`,
`test_workflow_python_bootstrap_is_hash_pinned`, the OIDC conformance contract,
and the post-change Scorecard, Trivy, and Semgrep checks.

## Amendment: general-user report and customer vocabulary (2026-08-15)

The direct-PostgreSQL browser review found that a reader could see generated
report titles such as `weekly project <identifier>`, Judge verdict codes such
as `pass`/`fail`, and customer hierarchy storage tiers such as `group`, `hq`,
and `plant`. A report detail also exposed score-linking/source codes and
technical `θ`/`SE` notation. Those are useful persistence and audit values,
but they are not an appropriate product language for a general user. The
React reader now maps period and scope to `주간`/`월간` and
`PU`/`팀`/`프로젝트`, maps Judge outcomes to `검토 완료`/`추가 확인`/
`판정 보류`/`평가 대기`, translates score-linking/source codes to business
labels, and maps hierarchy to `그룹`/`법인`/`본사`/`사업장`/`팀`.
Generated slice identifiers are omitted from reader titles, and report detail
uses Korean score/오차 labels rather than implementation notation.

This is presentation-only: PostgreSQL normalization, actor-filtered API
payloads, report identifiers, and administrator audit data remain unchanged.
The customer screen continues to expose only account facts and hierarchy
edges supported by authorized document evidence; Ontology classes, semantic
predicates, and evidence assertions are not inferred from the display label.

Evidence: `test_web_page_uses_verified_session_and_real_api`, the direct
reader browser capture, and the React production build on 2026-08-15.

## Amendment: evidence-backed reader report scope labels (2026-08-15)

The preceding vocabulary boundary removed opaque generated project identifiers
from the general-user report title, but that left multiple project reports with
the indistinguishable label `주간 프로젝트 보고서` or `월간 프로젝트 보고서`.
That is a real product failure: a reader cannot select the correct business
scope even though the report already has authorized source documents.

The response path now loads the bounded persisted report-document fields once,
applies the same document ABAC predicate used by report filtering, and passes
only those authorized documents to `attach_report_display_labels`. PU and team
reports receive their business attribute code as `slice_label`. A project
report receives the first non-empty, whitespace-normalized `title_sample`, or
its Korean summary when the title is absent, from a document listed in that
report's evidence set. If no authorized document supplies a label, the UI
keeps the generic scope label; it never falls back to the opaque project
`slice_key`.

This is deliberately a response-time presentation projection. The normalized
report row, opaque slice key, report identifier, document evidence set, and
administrator/audit payload are unchanged. `slice_label` is not inserted into
the Ontology or Semantic Layer, does not create a customer/account assertion,
and cannot create or reorder a chronological Lineage transition. The
Ontology/Semantic Layer remains the source of persisted classes, predicates,
and evidence assertions; the reader label only names an already-authorized
report scope. Regression coverage verifies title, summary, PU/team, missing
evidence, and no-mutation cases, while the direct PostgreSQL report endpoint
continues to retain its traceable storage fields.

Evidence: `attach_report_display_labels`, the application-method and
PostgreSQL authorization contracts, `reportBusinessTitle`, the React surface
contract, the direct-PostgreSQL browser run, and the 2026-08-15 full Python
line-and-branch coverage run (354 tests plus one expected optional skip, 7,627
statements, and 2,984 branches; 100% with no coverage exclusion).

## Amendment: actionable Keyman Knowledge Graph nodes (2026-08-15)

The reader could previously inspect a Keyman neighborhood only as a static
list. That made the precomputed KG useful for explanation but weak for the
requested “select a Keyman and follow related people, companies, events, and
posts” workflow.

Each returned, server-authorized KG node is now an explicit action: person and
organization nodes request another bounded neighborhood using the existing
adaptive depth policy; event and content nodes open their authorized source
evidence drawer; and related document nodes reopen the actor-filtered document
detail. Nodes without a safe document/evidence identifier remain non-navigating
and the browser never creates or promotes an edge. Ontology classes, semantic
predicates, evidence assertions, and Lineage transitions remain PostgreSQL
facts and are not changed by a click.

Evidence: `openKnowledgeNode`, the `knowledge-node-link` React contract, the
authorized `/knowledge`/evidence/document routes, and the direct PostgreSQL
browser workflow.

## Amendment: administrator policy-list pagination and search (2026-08-15)

The administrator 게시글 권한 통제 surface previously rendered the first 20
entries from the workspace's already-loaded document page. That made the
control technically present but operationally incomplete for a large corpus:
an administrator could not locate a later document or distinguish “not in the
first page” from “not in the authorized scope.”

The policy panel now calls the existing actor-authorized `/api/documents`
index with a bounded page size of 20, server-side document/title/PU search,
and an explicit total. A `게시글 더 보기` action requests the next offset and
the React state retains only the returned document summaries. No full graph,
source body, or new permission path is exposed. The server's existing corp/PU
ABAC decision remains authoritative for every page and every visibility
mutation.

After a successful visibility mutation, the reader index and the administrator
policy list update together from the server response. A failed mutation leaves
both views unchanged and reports the error. This is a user-interface
operability improvement only: it does not add an Ontology/Semantic Layer fact,
alter customer-master evidence, or change chronological Lineage semantics.

Evidence: `adminDocuments`, `adminDocumentFilter`, and
`loadMoreAdminDocuments` in `web/src/App.jsx`; the React surface contract;
the administrator browser contract in `web/e2e/lineageweave.mjs`; and the
direct `/api/documents` authorization boundary.

## Amendment: customer relationship evidence display (2026-08-15)

The customer screen previously showed a persisted parent-child affiliate edge
as a plain name pair. Although the server had already required an authorized
account-to-document intersection before returning that edge, the UI did not
make the evidence visible to the business user. This weakened trust in the
customer master and made an LLM-derived hierarchy look like an unexplained
label mapping.

The customer detail now renders each returned edge with three bounded facts:
a business-readable semantic relation, a business-readable derivation label,
and the count plus identifiers of its authorized source documents. Storage
relation codes remain available only in the authorized API/audit boundary. Each source
identifier is an existing document action and re-enters the actor-scoped
workspace; it does not read raw content in the customer screen. The API's
account-to-document intersection remains the only eligibility rule, and the
browser does not infer descendants, create ontology assertions, or promote a
customer edge to an observed event transition.

This is a presentation improvement over the existing normalized
`analysis_customer_accounts`, `analysis_customer_affiliates`, and
`analysis_customer_document_links` relations. The semantic mapping remains
`schema:Organization` for the entity, `schema:subOrganization` for the
affiliate relation, and `schema:about` for document evidence. The source label
is not a new ontology predicate and cannot override an evidence assertion.

Evidence: `customerRelationSourceLabel`, the customer-detail relation cards,
the `edge.document_nos` source actions, `TRACEABILITY.md`, and the direct
PostgreSQL browser/React verification on 2026-08-15.

## Amendment: reader-role product surface and Figma implementation baseline (2026-08-15)

The general-user requirement is now a first-class product boundary rather than
an administrator console with hidden controls. A verified reader receives
`업무 홈`, `업무공간`, `고객 화면`, and report entry points. The header exposes
the actor's business scope and the Korean permission label `열람`; it does not
expose administrator navigation, queue diagnostics, policy mutation, Lineage
override, enrichment, or account-directory controls. The server remains the
source of authorization, and React visibility is only a supplementary
presentation boundary.

The customer screen is an Ontology/Semantic Layer consumer, not a free-form
name tree. Persisted customer entities use `schema:Organization`, hierarchy
edges use `schema:subOrganization`, and document support uses `schema:about`.
The reader sees only account and affiliate rows that have an actor-authorized
account-to-document intersection. Each visible edge supplies a business
relation label, derivation label, evidence count, and authorized source
document actions. The browser cannot infer a descendant, create an ontology
assertion, or convert a customer edge into chronological Event Lineage.

For design traceability, the running reader-only React surface was captured in
the supplied Figma file at
[node 304:2](https://www.figma.com/design/SBpgot7uTvMxEaxUwvoc0S?node-id=304%3A2).
The captured metadata verifies the reader navigation and absence of
`관리자 모드`. This is an implementation baseline generated from the actual
product, not an independent design-target parity result; production Keyverse
login and independent visual review remain external release gates.

Evidence: Figma node `304:2`, `#userHome`/`#customerScreen`, the authorized
customer API and normalized semantic relations, the reader-only direct-data
browser run, the React production build, and the full Python line-and-branch
coverage run.

## Amendment: explicit no-transition reader presentation (2026-08-15)

The reader detail previously rendered a selected document as an `observed`
Lineage node even when its event-lineage payload contained no bead and no
observed transition. That presentation could make an unrelated search result
look chronologically connected. The no-transition state now renders an
explicit `독립 관측` item with the message `확인된 사건 전이가 없어 Lineage로
연결하지 않습니다.` and emits no connector. The same rule remains true when
relatedness exists: inferred or predicted neighbors stay in the separate
relatedness section and cannot become chronological Event Lineage.

This is a presentation correction over the existing evidence boundary. It
does not create an edge, change the normalized Ontology/Semantic Layer, or
alter the observed `row_successor` facts. The direct-data browser acceptance
confirmed a one-node/no-observed-edge result for the affected state, while the
React static contract and production build cover the explicit no-transition
copy.
