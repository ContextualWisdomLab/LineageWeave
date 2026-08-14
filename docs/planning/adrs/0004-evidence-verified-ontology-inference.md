---
id: "0004"
title: "Verify inferred ontology relationships with evidence-bounded LLM review"
status: accepted
proposed_date: 2026-08-13
accepted_date: 2026-08-13
deciders:
  - "LineageWeave delivery owner"
consulted:
  - "TEPP evidence and orchestration contract"
  - "product request"
informed:
  - "Database, Keyverse, model, and search operators"
related:
  - path: "docs/planning/adrs/0001-lineageweave-runtime-and-governance.md"
    relation: "influenced-by"
    note: "Preserves the observed-versus-inferred lineage boundary."
  - path: "docs/planning/adrs/0003-keyverse-authorization-code-pkce.md"
    relation: "influenced-by"
    note: "Requires a verified actor and the manage_lineage authorization decision."
affected_components:
  - "lineageweave.py"
  - "lineageweave_server.py"
  - "compose.yaml"
  - "web/src/App.jsx"
  - "tests/test_lineage_runtime_contract.py"
  - "tests/test_application_methods.py"
  - "tests/test_postgres_and_valkey_contract.py"
  - "tests/test_http_contract.py"
asr_triggers:
  - kind: security
    evidence: "External search is untrusted and may return malicious URLs or content."
    note: "Only two bounded organization labels are searched; returned citations require safe HTTP(S) URLs and model input is evidence-bounded."
  - kind: compliance
    evidence: "Inferred relationships can affect tenant-scoped knowledge surfaces."
    note: "The route requires manage_lineage and preserves provenance, actor, and decision records in PostgreSQL."
  - kind: availability
    evidence: "Search and model services can be absent or unavailable."
    note: "No configured search, malformed output, or failed model verification produces insufficient rather than a promoted relation."
  - kind: maintainability
    evidence: "Evidence and decision lifecycles must remain reviewable without raw-source duplication."
    note: "Run, candidate, and evidence relations are persisted separately with bounded fields and explicit decision enums."
  - kind: evolvability
    evidence: "Search providers and verifier models may change independently."
    note: "SearXNG is an optional HTTPS endpoint and the product LLM is resolved through the existing live transport boundary."
success_criteria:
  - metric: "No automatic promotion"
    target: "An inferred or predicted relationship is never rewritten as observed or as a temporal transition by verification."
    measurement_window: "each verification run"
    source: "derive_ontology_relationship_verification and persisted KG evidence status"
  - metric: "Restart-safe graph evidence"
    target: "The lineage relation and its document-to-document KG projection retain the same evidence status and optional rationale after a process restart."
    measurement_window: "each persisted snapshot load"
    source: "analysis_lineage_edges, analysis_knowledge_graph_edges, and merge_lineage_evidence_into_knowledge_graph"
  - metric: "Evidence-bounded LLM production"
    target: "Every non-empty candidate run uses the live product transport and accepts only verified, rejected, or insufficient decisions tied to supplied evidence IDs."
    measurement_window: "each candidate"
    source: "verify_lineage_inferences and normalize_ontology_relationship_verification"
  - metric: "Privacy-preserving external query"
    target: "External search receives at most two nearby organization labels, never person labels, raw source content, credentials, or browser-selected tenant attributes."
    measurement_window: "each external lookup"
    source: "inference_organization_labels and search_external_inference_evidence"
  - metric: "Failure closure"
    target: "Missing evidence, invalid LLM output, unsafe search configuration, or unavailable SearXNG cannot produce verified."
    measurement_window: "each failure path"
    source: "normalization, URL validation, and search contract tests"
  - metric: "Auditable delivery"
    target: "Each request records a normalized run/candidate/evidence graph and emits a durable outbox event after commit."
    measurement_window: "each verification request"
    source: "analysis_inference_* tables and lineage_inferences_verified event"
effort: M
---

# ADR-0004: Verify inferred ontology relationships with evidence-bounded LLM review

## Context

The knowledge graph distinguishes observed relationships from inferred and
predicted relationships. Similarity, shared membership, or a model suggestion
is useful for navigation but is not proof of an ontology assertion or a
chronological transition. A user with authority to manage lineage needs a way
to ask whether a proposed relationship is supported by the visible semantic
graph and, when configured, independent public-web evidence.

The verifier must use an LLM because its outcome is consumed as a semantic
review actor. It must nevertheless remain a proposal: it cannot promote an
edge, manufacture evidence, expand its access, or make a search result an
authoritative source. TEPP requires evidence-bounded interpretation, an
independent verification role, provenance, role-specific access, and abstention
when evidence is insufficient. FactKG likewise treats knowledge-graph fact
verification as explicit reasoning over linked concepts rather than a label-only
classification task.

That contract is only meaningful when a persisted KG retains the evidence tier
and rationale of its lineage edges. A relation whose `inferred` or `predicted`
status disappears after restart becomes invisible to the verifier and can be
mistaken for an observed graph link. The direct PostgreSQL snapshot therefore
has to preserve this metadata, while an additive migration restores the status
of legacy snapshots from their authoritative lineage relation. A historical
rationale that was never stored remains null rather than being invented.

> Citation: ContextualWisdomLab. (2026). *TEPP LLM orchestration and test-time compute contract*. https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/LLM_ORCHESTRATION.md

> Citation: Kim, J., Park, S., Kwon, Y., Jo, Y., Thorne, J., & Choi, E. (2023). *FactKG: Fact verification via reasoning on knowledge graphs*. https://doi.org/10.18653/v1/2023.acl-long.895

> Citation: World Wide Web Consortium. (2012). *OWL 2 Web Ontology Language document overview (Second Edition)*. https://www.w3.org/TR/owl2-overview/

## Decision Drivers

- Keep observed evidence and candidate relationships distinguishable.
- Give authorized users a real LLM-produced review, not a scripted verdict.
- Search internally first and allow optional SearXNG web evidence without
  disclosing people, raw document content, credentials, or hidden graph scope.
- Preserve a queryable, normalized audit trail and Valkey event notification.
- Preserve the evidence tier and rationale through a direct PostgreSQL restart.
- Fail closed when the live model, external search, evidence bundle, or schema
  contract is unavailable.

## Considered Options

| Option | Evidence integrity | Privacy and authorization | Operational behavior | Decision |
| --- | --- | --- | --- | --- |
| Promote inferred edges when similarity exceeds a threshold | Conflates a heuristic with evidence | Makes later access filtering harder to audit | Fast but irreversible in meaning | Rejected |
| Use an LLM over labels alone | Can fabricate support or overgeneralize | Sends unnecessary labels and has no source trail | Produces persuasive but ungrounded text | Rejected |
| Use only deterministic internal graph checks | Auditable but cannot provide the requested LLM review or optional external corroboration | Strong scope boundary | Useful guard, incomplete review actor | Rejected |
| Authorize, assemble bounded internal and optional SearXNG evidence, then obtain a live LLM verdict | Keeps candidate/evidence/decision separate | Minimizes external query and preserves actor scope | Abstains safely when dependencies are absent | Accepted |

## Decision Outcome

Adopt an evidence-verification workflow for inferred and predicted ontology
relationships:

| Decision driver | Selected behavior | Rejected behavior |
| --- | --- | --- |
| Evidence integrity | Persist candidate, evidence, and verdict separately | Rewrite an inferred edge as observed or temporal |
| LLM consumer requirement | Use the existing live product transport over supplied evidence IDs | Return a scripted or recorded verdict |
| External corroboration | Query optional SearXNG with at most two organization labels | Send people, raw source content, or unbounded graph context |
| Restart semantics | Persist and rehydrate evidence status plus optional rationale in both lineage and KG relations | Treat a cache-only KG edge as authoritative evidence |
| Operational failure | Normalize missing/invalid support to `insufficient` | Guess support or broaden the search scope |

1. `POST /api/documents/{document}/lineage/verify` loads only the authorized
   document graph and requires the `manage_lineage` decision.
2. The workflow selects at most sixteen candidate edges touching that document.
   Only `inferred` and `predicted` evidence statuses qualify.
3. `analysis_lineage_edges` and `analysis_knowledge_graph_edges` both retain
   `evidence_status` and an optional `reason`. On load, document-to-document KG
   relations are reconciled from the lineage relation before any candidate is
   selected; a changed legacy snapshot is rewritten atomically with its semantic
   assertions. The migration restores status but leaves an unavailable legacy
   rationale null.
4. It searches source-addressable, observed internal evidence around each
   candidate. An optional SearXNG request is made only when two nearby
   organization labels exist. Person labels, raw content, and browser identity
   inputs are never part of the web query.
5. The existing direct live product transport supplies the candidate and exactly
   those evidence identifiers to the ontology-verification LLM contract. The
   accepted output is the closed decision set `verified`, `rejected`, or
   `insufficient`; absent, malformed, unsupported, or ungrounded output is
   normalized to `insufficient`.
6. PostgreSQL records a run, its candidates, and their evidence in separate
   normalized tables. It then commits a `lineage_inferences_verified` outbox
   event for at-least-once delivery to the Valkey Stream.

The browser displays the verdict and bounded evidence references. A verdict is
not an edge mutation: it never changes an inferred/predicted edge to observed,
and never changes it into a forward temporal transition. A zero-candidate run
is persisted and emits its event without calling a model.

SearXNG is optional. Its URL must be HTTPS in deployment; local HTTP is allowed
only in explicit development mode for an allowlisted loopback or Docker host
bridge. The response is bounded, decoded as JSON, and each untrusted citation
is retained only when it is a credential-free HTTP(S) URL. Search failure is an
availability condition, not a reason to broaden a query or guess a verdict.

## Consequences

Positive:

- The product now has a real internal/external evidence-verification Agent with
  a live LLM decision contract.
- Each decision can be reviewed by document, actor, candidate, evidence kind,
  search mode, and outbox event without copying an entire source document.
- A restart cannot silently hide a persisted inferred or predicted
  document-to-document relation from the verification Agent.
- Users can see that a useful relation is still provisional rather than mistaking
  it for an observed fact or a causal/chronological claim.
- External search is deliberately narrow and optional, preserving the direct
  PostgreSQL and Keyverse authorization boundaries.

Trade-offs:

- A live model gateway is required for non-empty verification and may return an
  unavailable result when the deployment has not configured it.
- External search can be unavailable, incomplete, or unsuitable for a candidate;
  `not_configured`, `not_applicable`, and `unavailable` are expected outcomes.
- Internal evidence uses the persisted, actor-filtered graph; it cannot recover
  evidence that is outside the requester's authorized scope.
- The additive migration can restore a legacy evidence tier, but cannot recreate
  a rationale that an earlier schema never retained; that field stays null.
- The review is semantic verification, not proof of causality, legal authority,
  or temporal state transition.

## Risks and Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| A model presents an unsupported relationship as fact | Closed output schema, exact supplied evidence IDs, and fail-closed normalization; no status promotion path | verifier normalizer and runtime contract test |
| External web query discloses an individual or internal content | Derive a maximum of two organization labels from the authorized graph; do not send people or source text | organization-label and SearXNG query test |
| Untrusted result links introduce unsafe navigation | Keep only bounded credential-free HTTP(S) URLs | safe external URI filter test |
| Search endpoint weakens transport trust | Require HTTPS outside explicit local development and use the deployment CA context | SearXNG URL validation |
| Audit rows duplicate high-risk source content | Persist bounded candidate/evidence metadata and references rather than source bytes | normalized inference persistence |
| A requester uses the verifier to inspect hidden graph facts | Require document authorization and `manage_lineage` before candidate selection, evidence search, model call, or persistence | application authorization test |
| A restart erases the tier of a provisional relationship | Store the tier and optional rationale in both edge tables, reconcile legacy document-to-document KG edges, and atomically rewrite only changed snapshots | PostgreSQL snapshot and rehydration contract tests |
| Valkey outage loses the audit signal | Commit PostgreSQL outbox first and retry Stream delivery independently | outbox flush behavior |

## Rollback / Exit Strategy

1. Remove `LINEAGEWEAVE_SEARXNG_URL` to disable only external corroboration;
   internal observed-evidence review remains bounded.
2. Disable the live model gateway to make non-empty verification return an
   unavailable result; do not substitute a recorded or synthetic verdict.
3. Retain the immutable run/candidate/evidence records and their outbox events
   for audit; do not rewrite existing edge evidence status.
4. Keep the additive edge metadata columns through normal retention; never
   backfill missing legacy rationale with a generated explanation.
5. If the feature is retired, remove the route/UI entry point only after an ADR
   and data-retention decision; database records remain historical evidence.

## Affected Components

- `lineageweave.py`: candidate selection, internal semantic evidence search,
  privacy-limited organization-label extraction, SearXNG validation, safe URL
  handling, LLM-output normalization, restart-safe edge reconciliation, and
  normalized persistence.
- `lineageweave_server.py`: `manage_lineage` authorization, live transport
  invocation, event-outbox commit, and bounded response shaping.
- `compose.yaml`: optional SearXNG URL and CA-bundle propagation to the product
  service; the Compose model worker remains identity-free.
- `web/src/App.jsx`: authorized Event Lineage action, status, and evidence
  drawer/link behavior.
- Contract tests: deterministic evidence bounds, invalid-output failure closure,
  privacy-safe web search, database persistence, HTTP routing, and deployment
  configuration.

## Verification and Monitoring

- Unit and application tests assert candidate/evidence limits, organization-only
  web queries, safe external URLs, no evidence-free `verified` result, persisted
  3NF relations, required live transport for non-empty candidate sets, zero-model
  empty-run behavior, outbox publication, `manage_lineage` authorization, and
  evidence-status/rationale survival across a KG snapshot reload.
- The deployment health surface reports the Valkey stream and pending outbox
  count. A separate SearXNG endpoint is optional and does not become an
  authentication or database boundary.
- Release review checks that every current inferred relationship stays distinct
  from observed and temporal-transition relations, and that no private source
  identifier is present in public documentation.
- A production acceptance run additionally needs an operator-configured live
  model gateway, a permitted SearXNG endpoint if external corroboration is
  desired, and an authorized Keyverse account. Those external prerequisites are
  intentionally not represented by a local test double.
- Direct PostgreSQL acceptance on 2026-08-13 reloaded the repaired graph after
  restart with 3,027 inferred and 8 predicted relations. One bounded live-model
  run used two internal evidence references, returned `insufficient`, and
  published its durable outbox event. No external search was configured for that
  run.
- A 2026-08-14 organization-alias acceptance run used the Compose SearXNG
  service and live product LLM, stored one `verified` inferred candidate with
  five external evidence records, and mapped its directional KG assertion to
  SKOS `exactMatch`. Candidate, evidence, and verdict remain separate; the
  original edge is not promoted to observed. The mutation persists only its
  two nodes and one edge under the shared advisory lock and does not load or
  rewrite the complete graph.
- The 2026-08-15 alias guard now checks the cited evidence text itself: a
  `verified` result is accepted only when the same external item contains both
  the queried alias and the proposed canonical organization. Automatic R&R
  expansion uses the same LLM/SearXNG agreement rule; an LLM-only or conflicting
  candidate remains unresolved and cannot enter the semantic graph. During
  snapshot reconstruction, historical candidates that fail this check remain
  auditable in `analysis_inference_*` but are excluded from the current KG
  projection.

## References

ContextualWisdomLab. (2026). *TEPP LLM orchestration and test-time compute contract*. https://github.com/ContextualWisdomLab/TEPP/blob/main/docs/LLM_ORCHESTRATION.md

Kim, J., Park, S., Kwon, Y., Jo, Y., Thorne, J., & Choi, E. (2023). FactKG: Fact verification via reasoning on knowledge graphs. In *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 16190–16206). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.acl-long.895

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

SearXNG. (n.d.). *Search API*. https://github.com/searxng/searxng/blob/master/docs/dev/search_api.rst

World Wide Web Consortium. (2012). *OWL 2 Web Ontology Language document overview (Second Edition)*. https://www.w3.org/TR/owl2-overview/
