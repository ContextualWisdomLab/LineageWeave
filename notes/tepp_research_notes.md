# TEPP/Contextual-Orchestrator evidence notes

This product references the following TEPP-facing sources to keep orchestration and
lineage behavior aligned with the organization’s ADR contracts.

The complete APA 7th register copied into product doctoring includes the TEPP
standards register plus the task-level research and standards references used
by the current TEPP documentation. This note keeps the shorter
implementation-oriented mapping and the explicit HTTP-boundary limitations.

## Core orchestration papers (APA 7th form)

1. Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Preprint]. arXiv. https://arxiv.org/abs/2606.21228
2. Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2026). Learning to orchestrate agents in natural language with the Conductor. In *International Conference on Learning Representations (ICLR 2026)*. https://arxiv.org/abs/2512.04388
3. Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2026). TRINITY: An evolved LLM coordinator. In *International Conference on Learning Representations (ICLR 2026)*. https://arxiv.org/abs/2512.04695

## Repository anchors checked for this product

- ContextualWisdomLab. (2026). *TEPP README and normative-document index*.
  https://github.com/ContextualWisdomLab/TEPP — the current public branch
  describes the Rust workspace foundation, immutable evidence direction, and
  temporal/relational platform boundary. LineageWeave therefore keeps its
  product graph and source API separate from TEPP's future arithmetic layer.
- ContextualWisdomLab. (2026). *Contextual Orchestrator README*.
  https://github.com/ContextualWisdomLab/contextual-orchestrator — the current
  public README describes a single model-like HTTP interface with routing,
  delegation, verification, synthesis, request validation, and trace controls.
  LineageWeave carries this contract over HTTP and does not copy the service's
  internal implementation.

## TEPP source anchors (authoritative local docs)

1. `TEPP` ADR: `docs/adr/0010-adaptive-llm-orchestration.md`
   - governs direct model routing vs adaptive composition, ablation and budget-aware routing
2. `TEPP` ADR: `docs/adr/0016-tdt-chronos-event-intelligence-boundary.md`
   - governs observed/inferred/predicted separation and event transition authority
3. `TEPP` reference register: `docs/research/standards-and-literature.md`
   - records the full primary literature and standards register, including
     temporal/event, topic-network, multilingual, evidence, AI-risk, and
     orchestration contracts
4. `TEPP` repository policy in `docs/THREAT_MODEL.md` and `docs/TRACEABILITY.md`
   - used to keep BI + evidence outputs auditable and non-contradictory

## Implementation mapping currently completed

1. Real-data extraction from the runtime source table uses a direct `psycopg` connection and is persisted in PostgreSQL analysis tables.
2. Versioned BI analytics are exposed through `/api/analytics` and the compiled React workspace.
3. The React product consumes the live API to provide:
   - paged document browsing and per-thread revision chains
   - row-level timeline inspection with an AJAX evidence drawer
   - Korean summary, R&R, Event Lineage, two-sided Keyman, tickets, and visibility
   - precomputed KG neighborhoods across PUs and legal companies
4. ADR-0016 statuses on every edge:
   - `row_successor` is the only `observed` identifier/time transition
   - shared-thread and `topic_affinity` relations are `inferred` and are never emitted as promoted transitions
   - `make_lineage_edge` rejects inferred/predicted promotion into transition relations
5. Fugu / Conductor / TRINITY variables are carried on Keyman and event-chat requests. Keyman uses the direct live gateway; the local Compose service is an optional no-identity proxy for event chat and image inspection and never returns a recorded answer.
6. Inline-image OCR is a separate bounded worker task: direct PostgreSQL source retrieval, strict raster validation, verified TLS, and normalized inspection/label relations. It does not alter observed or inferred lineage edges.
7. Keyverse authentication uses OIDC authorization code with S256 PKCE. The
   product maps verified `sub`, `org`, `workspace`, and `role` claims to its
   account, legal-company, PU, and RBAC fields; it has no password relay or
   browser-entered tenant attribute.
8. The product Compose profile builds the React service, reads PostgreSQL
   directly, and uses service-DNS paths for Valkey and the no-identity worker.
9. When `LINEAGEWEAVE_ZOTERO_ATTACHMENTS=1`, the Local Zotero Connector receives
   each bounded OA original through its `saveItems` and `saveAttachment`
   contracts. PostgreSQL retains the attachment outcome and SHA-256 digest;
   the initial live run stored eight parents and eight originals. The current
   run stores thirteen parents and thirteen originals, including four multimodal
   document-analysis papers and the RAGAS evaluator. A repeat read resolves the actual child key and
   digest instead of fabricating either value.

## Applied literature mapping

- RDF's subject-predicate-object model, RDFS/OWL class and property contracts,
  PROV-O attribution, the Organization Ontology, and SKOS concept matching
  inform the relational semantic profile. The profile stores standard URIs,
  domain/range rules, entity-role concepts, and evidence assertions rather
  than treating a display-label graph as an ontology. See World Wide Web
  Consortium. (2009). *SKOS simple knowledge organization system reference*.
  https://www.w3.org/TR/skos-reference/; World Wide Web Consortium. (2012).
  *OWL 2 web ontology language document overview (Second Edition)*.
  https://www.w3.org/TR/owl2-overview/; World Wide Web Consortium. (2013).
  *PROV-O: The PROV ontology*. https://www.w3.org/TR/prov-o/; World Wide Web
  Consortium. (2014a). *RDF 1.1 concepts and abstract syntax*.
  https://www.w3.org/TR/rdf11-concepts/; and World Wide Web Consortium.
  (2014b). *The organization ontology*. https://www.w3.org/TR/vocab-org/.
- Allan (2002), ISO 24617-1:2012, and Anagnostopoulos et al. (2013) motivate
  the separation of observed event transitions, inferred links, and hypothetical
  completion. LineageWeave preserves those statuses rather than displaying a
  topic relation as history.
- Blei and Lafferty (2006), Chang and Blei (2009), and Roberts et al. (2014,
  2019) motivate temporal, relational, and covariate-aware future topic work.
  The current product deliberately exposes evidence-backed structural links
  first; it does not make an uncalibrated topic-model claim.
- Bianchi et al. (2021), Unicode normalization guidance, and Universal
  Dependencies v2 inform future multilingual unitization. They do not justify
  destructive normalization of source evidence.
- Lebo et al. (2013), Moreau and Missier (2013), and NIST FIPS 180-4 motivate
  stable evidence identifiers, provenance-bearing edges, and digest-bound image
  inspection output.
- Jensen and Snodgrass (1999) motivate keeping valid-time facts, transaction-time
  database state, and restored temporal windows independently auditable. Swanson
  et al. (2010) motivate explicit recovery validation rather than treating a
  completed restore as proof of integrity.
- WCAG 2.2, NIST AI RMF, ISO/IEC 23894, ISO/IEC 42001, CSAP, and AICPA Trust
  Services Criteria are treated as deployment/readiness inputs. They are not a
  self-certification claim.

The full APA 7th citations remain in TEPP's authoritative standards register.
LineageWeave cites only the sources that determine its current product behavior
and records an explicit boundary when a TEPP research layer has not yet been
implemented.

## RAGAS runtime application (2026-08-15)

The RAGAS paper is now represented by four persisted evaluation definitions and
is applied by the live report-judge task rather than a local scoring substitute.
The current direct-PostgreSQL state contains 80 report slices and 320 metric
observations, each joined to a report and a metric definition with model source,
verdict, and rationale; evidence references are stored in the separate
`analysis_report_metric_evidence` relation. This is an evidence-scoped, dichotomous
RAGAS-aligned evaluation; it does not claim reference-answer-based context recall
when a reference answer is absent. The current live run supplied all four scores
for every slice, while the parser and schema retain an explicit abstention path.

## Deliberate boundary

- This repository does not modify contextual-orchestrator. Its policy controls and
  ablation work remain owned by that service and are called only through its HTTP
  contract.
- Mutation delivery uses a PostgreSQL transactional outbox and a Valkey Stream;
  this keeps the product's event queue separate from the model orchestration
  boundary.
- Any future LLM-assisted clustering or topic-link prediction needs a reproducible
  evidence manifest before it is added to the KG.
- The accepted product decisions and local rollback paths are in ADR-0001,
  ADR-0002, and ADR-0003.
