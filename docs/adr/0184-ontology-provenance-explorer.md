# ADR 0184: Heterogeneous ontology and provenance explorer

**Status:** Accepted
**Date:** 2026-08-21
**Figma:** File ID `1Su3lDRmiZdcUs47t1QwIX`
**Issue:** [#341](https://github.com/ContextualWisdomLab/LineageWeave/issues/341)

**Context:** The workspace DAG is reconstructed Event Lineage (post/record nodes and inferred parent-to-child links). The formal LineageWeave ontology also defines heterogeneous instance types (`Post`, `Person`, `CorporateEntity`, `Team`, `Project`) and properties (`mentions`, `mentionsProject`, `affiliatedWith`, `coMentionedWith`, SKOS broader). Calling Event Lineage an ontology graph overstates what that surface renders. PR #330 remains the Event Lineage readability slice and must not become a mixed lineage/ontology graph. Project projection is completed by [ADR 0222](0222-project-nodes-in-ontology-neighborhood.md).

**Decision:**

1. PostgreSQL remains authoritative. OWL/RDF/JSON-LD is a governed projection, not a second mutable store.
2. `GET /api/ontology/neighborhood` returns a bounded typed neighborhood with explicit `focus_node_type`, `focus_node_id`, depth/node/edge bounds, property filter, `knowledge_cutoff`, and opaque `after:` cursor.
3. RBAC/ABAC and source eligibility run before any node, edge, label, count, or path enters the response. A hidden endpoint removes the edge. Truncation never reports how many neighbors were omitted. Corporate hierarchy parents use the same visible-post evidence gate as other corporate-entity endpoints; a visible child alone does not reveal a hidden parent label.
   A missing and a non-visible focus return the same not-found status and buyer
   surface, so the response cannot become a catalog-existence oracle.
4. Truth status is one of `truth_authoritative`, `truth_observed`, `truth_inferred`, `truth_proposed`, `truth_superseded`, `truth_rejected`. Display never promotes inference to authority.
   Node truth and `recorded_at` are catalog-owned metadata. A missing catalog
   value is omitted from JSON-LD and represented as `null` in the typed API;
   edge truth and edge availability never fill a node field.
5. SKOS broader is projected from `corporate_entity.parent_entity_id`. OWL class subsumption is schema, not an instance neighborhood edge, and fails closed.
6. `knowledge_cutoff` binds `available_time`. An evidence-backed graph edge is
   available at the later of its creation and its earliest supporting source;
   a project mention is available at the later of its mention and source
   creation. Current-only facts without a time contract stay out of an as-of
   response.
7. The workspace surface extends the existing Keyman/evidence panel with **Inspect ontology neighborhood**. It is not a second GNB destination.
8. Node type uses shape plus text (never color alone). Every edge carries both endpoint type codes and IDs, so heterogeneous catalogs remain unambiguous even if UUIDs collide. Keyboard users can select every visible node and edge. The graph SVG has no enclosing ARIA `img`; native browser text layout wraps complete node labels instead of truncating or estimating character widths. Exact-value table, CSV, JSON-LD, and print expose the same authorized visible graph. JSON-LD emits the source-to-target property assertion directly and describes its evidence-bearing edge as an RDF reified statement with exact `rdf:subject`, `rdf:predicate`, and `rdf:object`; it does not make the edge resource itself the relationship subject. JSON-LD represents system time with `prov:generatedAtTime` and non-null validity bounds as OWL-Time `time:Instant` values using `time:inXSDDateTimeStamp`; it omits unavailable bounds rather than inventing them.
9. Synthetic Storybook frames cover desktop, narrow exact-value-first, node drawer, edge drawer, legend, empty, truncated, denied, stale, and rejected states. No confidential Figma content enters the repository. Storybook inventory records the implementation surface; frame IDs are not copied from the confidential design file (ADR 0002).

**Consequences:**

- Event Lineage and ontology neighborhood stay distinct product capabilities.
- Related-node RWR ranking is unchanged; the neighborhood is a typed BFS with fail-closed bounds.
- Coverage, public docstrings, i18n (`en`/`ko`/`zh`/`ja`/`vi`), and Storybook gates apply to this slice.
- Continuing past the SQL source window is [ADR 0124](0124-ontology-source-window-cursor.md) / issue #363.

**References**

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 concepts and abstract syntax* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/rdf11-concepts/

Brickley, D., & Guha, R. V. (Eds.). (2014). *RDF Schema 1.1* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/rdf-schema/

World Wide Web Consortium. (2012). *OWL 2 web ontology language document overview (second edition)* (W3C Recommendation). https://www.w3.org/TR/owl2-overview/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization system reference* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Cox, S., & Little, C. (Eds.). (2022). *Time ontology in OWL* (W3C Candidate Recommendation Draft). World Wide Web Consortium. https://www.w3.org/TR/owl-time/

Kellogg, G., Champin, P.-A., & Longley, D. (Eds.). (2020). *JSON-LD 1.1* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/json-ld11/

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes constraint language (SHACL)* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/shacl/

World Wide Web Consortium. (2024). *Web content accessibility guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

Open Worldwide Application Security Project. (2023). *API1:2023 broken object
level authorization*. https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
