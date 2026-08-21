# ADR 0004 — Knowledge Graph as a real Ontology + Semantic Layer, not just a polymorphic edge table

**Decision status:** Accepted (this ADR covers the first slice: a real,
machine-validated ontology artifact and the vocabulary contract other
code and future consumers use; it does not add a triple store or a
SPARQL endpoint -- see Consequences)
**Date:** 2026-08-13

## Context

The product brief's latest revision is explicit that every place the
Knowledge Graph is used -- Keyman-to-related-node traversal, the
integrated customer/corporate hierarchy tree, entity-relationship
classification (VOC/VOM/VOP/VOCC/VOCO/VOS), indirect lineage linking,
and the in-popup chat's evidence retrieval -- rests on a real Ontology
and a real Semantic Layer, "FULL 표준" (full standard), not an informal
convention.

What already exists (`migrations/0001_initial_schema.sql`):

- `knowledge_graph_edge`: `(source_node_type_code, source_node_id) --
  [edge_type_code] --> (target_node_type_code, target_node_id)`. This
  is *already*, structurally, an RDF triple (subject, predicate,
  object) -- W3C's RDF 1.1 Concepts and Abstract Syntax (Cyganiak,
  Wood, & Lanthaler, 2014) defines a triple in exactly this shape.
- `common_lookup_value`: the closed vocabulary for `node_type_code`
  (`node_person`, `node_corporate_entity`, `node_post`), `edge_type_code`
  (`edge_mention`, `edge_affiliation`, `edge_co_mention`), and
  `entity_relationship_type` (`rel_voc`/`rel_vom`/`rel_vop`/`rel_vocc`/
  `rel_voco`/`rel_vos`) -- a controlled vocabulary in substance, but
  documented only as human-readable code/label pairs, with no formal
  class hierarchy, no declared domain/range constraints on the
  properties, and no artifact any other system (or a future reasoner)
  could actually load and validate against.
- `corporate_entity`'s self-referencing `parent_entity_id` is a real
  broader/narrower hierarchy (Acme Group -> Acme Electronics Korea ->
  Acme Electronics Gwangju Plant) but, again, undocumented as a formal
  taxonomy relation.

So the gap is not "there is no graph" -- the gap is that the graph's
vocabulary has never been published as a real ontology a standard tool
can parse, validate, or reason over, and nothing currently checks that
the *database's own* `common_lookup_value` rows stay consistent with
whatever the intended vocabulary is.

## Decision

Publish the existing vocabulary as a real OWL 2 / RDF Schema ontology,
in Turtle syntax (`docs/ontology/lineageweave-kg.ttl`), and make it
the single source of truth the relational schema's controlled
vocabulary must match -- checked by a real, running test, not just
prose:

- **Classes** (`owl:Class`): `Post`, `Person`, `CorporateEntity`,
  plus `Person` split into `OurSidePerson` /
  `CounterpartyPerson` subclasses (`rdfs:subClassOf`) matching
  `person_side_code`. Issue tickets stay a separate table
  (`issue_ticket`), not a knowledge-graph node type.
- **Object properties** (`owl:ObjectProperty`, each with
  `rdfs:domain`/`rdfs:range`): `mentionedIn` (Person -> Post, the
  canonical direction stored by `edge_mention`; `mentions` is its
  declared RDF inverse), `affiliatedWith` (Person -> CorporateEntity, from
  `edge_affiliation`), `coMentionedWith` (symmetric, Person <-> Person,
  from `edge_co_mention`), and one object property per entity-
  relationship-type code (`hasVocRelationship`, `hasVomRelationship`,
  etc., domain `Post`, range `CorporateEntity`).
- **Taxonomy relation**: `CorporateEntity`'s hierarchy is modeled with
  SKOS (Miles & Bechhofer, 2009) `skos:broader`/`skos:narrower` on top
  of the OWL class, rather than inventing a bespoke relation -- SKOS is
  the W3C standard specifically for this kind of organizational/
  concept hierarchy, and it composes with OWL rather than competing
  with it.
- **The "semantic layer"** is this ontology file itself, in the sense
  W3C's own stack uses the term: RDFS/OWL is the standard technology
  for a governed, machine-checkable conceptual layer over raw relational
  data (Cyganiak et al., 2014; W3C OWL Working Group, 2012) -- not a
  separate BI-metrics product. `lineageweave/ontology.py` exposes the
  same IRIs as importable Python constants so application code has one
  canonical name for each class/property instead of re-typing the
  `common_lookup_value` lookup codes as bare strings.
- **A real correctness test**, not just a parseable file:
  `tests/test_ontology.py` loads the Turtle file with `rdflib` (the
  standard Python RDF/OWL library) and asserts every `node_type_code`,
  `edge_type_code`, and `entity_relationship_type` lookup code the
  relational schema actually defines has a corresponding class or
  property IRI in the ontology, and vice versa -- the two are not
  allowed to drift apart silently.

## Rationale

- Ponytail: the relational `knowledge_graph_edge` table already has
  the right *shape* (a triple store, functionally) -- the fix is
  publishing its vocabulary formally and testing it against reality,
  not replacing working Postgres storage with a parallel RDF triple
  store the rest of this codebase (random-walk-with-restart, ABAC
  joins, the reconstruct pipeline) would then have to be rewritten
  around.
- SKOS for the corporate hierarchy specifically, rather than folding
  it into OWL class subsumption, because a corporate entity being
  "part of" a larger one is an organizational/concept relationship
  (concept scheme), not a taxonomic is-a relationship in the OWL sense
  -- SKOS is the standard built for exactly that distinction.
- A round-trip test against the live `common_lookup_value` vocabulary
  is the only way "grounded in a real standard" is actually verified
  rather than merely asserted in a docstring; every other pluggable
  channel in this repo already keeps this discipline (real LLM calls,
  real Docker verification) and the ontology should not be the one
  place that's citation-only.

## Consequences

- No new runtime dependency on a triple store or SPARQL engine --
  `knowledge_graph_edge` stays the source of record; the ontology is a
  published specification and validation artifact, not a second
  database. If a future need justifies real SPARQL querying (e.g. an
  external Ontology/Semantic-Layer consumer), that is an additive,
  separate slice building on this vocabulary, not a rewrite of it.
- `rdflib` becomes a real dependency (pure Python, no Rust/C toolchain
  requirement, unlike `fast-mlsirm` -- see ADR 0003), used both for the
  correctness test and by `lineageweave/ontology.py` at import time to
  parse the Turtle file once.
- Every future addition to `common_lookup_value`'s `node_type`,
  `edge_type`, or `entity_relationship_type` categories must add the
  matching class/property to `lineageweave-kg.ttl` in the same PR, or
  `tests/test_ontology.py` fails -- this is the enforcement mechanism,
  not a style guideline.

## Related

Builds on the existing `knowledge_graph.py` (Tong, Faloutsos, & Pan,
2006, random-walk-with-restart) and `affiliate_tree.py` modules, and
on [ADR 0003](0003-fast-mlsirm-report-integration.md)'s reuse-not-
reimplement discipline for external standards.

## References (APA 7th)

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 concepts and abstract syntax*. World Wide Web Consortium. https://www.w3.org/TR/rdf11-concepts/

Brickley, D., & Guha, R. V. (Eds.). (2014). *RDF Schema 1.1*. World Wide Web Consortium. https://www.w3.org/TR/rdf-schema/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS Simple Knowledge Organization System reference*. World Wide Web Consortium. https://www.w3.org/TR/skos-reference/

Prud'hommeaux, E., & Carothers, G. (Eds.). (2014). *RDF 1.1 Turtle: Terse RDF Triple Language*. World Wide Web Consortium. https://www.w3.org/TR/turtle/

W3C OWL Working Group. (2012). *OWL 2 Web Ontology Language document overview* (2nd ed.). World Wide Web Consortium. https://www.w3.org/TR/owl2-overview/
