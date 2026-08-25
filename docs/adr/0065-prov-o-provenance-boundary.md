# ADR 0065: Keep PROV-O provenance separate from navigation lineage

- Status: Accepted
- Date: 2026-08-19

## Context

W3C PROV-O has normative classes, object/datatype properties, qualified
influences, inverses, domains, ranges, and literal values. Flattening those
assertions into the product navigation graph would lose qualification and make
literal provenance indistinguishable from a navigational edge.

## Decision

- Maintain a standards-complete PROV-O layer for the 30 classes, 50 normative
  properties, qualification mappings, property hierarchies, inverse aliases,
  domains, ranges, and literal validation.
- Canonicalize compact names, full IRIs, local names, and Appendix B inverse
  names into the preferred W3C direction. Reverse only resource relations;
  datatype properties cannot accept inverse aliases that would make a literal
  the subject.
- Persist explicit provenance assertions and qualified influence resources in
  the normalized PostgreSQL provenance store. Materialize qualified-to-
  unqualified implications, hierarchy/inverse closure, and event-time
  shortcuts deterministically.
- Keep `knowledge_graph_edge` as an explicit, removable navigation projection;
  it is not the provenance assertion store and must not replace it.
- Treat external IRIs and values as data. Serialization performs no external
  dereference, and product API exposure applies the authenticated tenancy
  boundary before binding product nodes to provenance resources.

## Consequences

- Provenance can be serialized as RDF/Turtle/JSON-LD without losing qualified
  relations or literal values.
- The database and materializer are more extensive than a flat edge table.
- Navigation consumers get a compact projection while provenance consumers get
  the full standards contract.

## References (APA 7th)

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013, April 30). *PROV-O: The PROV Ontology* [W3C Recommendation]. World Wide Web Consortium. https://www.w3.org/TR/2013/REC-prov-o-20130430/

Moreau, L., & Missier, P. (Eds.). (2013, April 30). *PROV-DM: The PROV Data Model* [W3C Recommendation]. World Wide Web Consortium. https://www.w3.org/TR/2013/REC-prov-dm-20130430/
