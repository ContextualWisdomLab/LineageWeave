# ADR 0004 — Standards-composed Knowledge Graph ontology and semantic layer

**Decision status:** Accepted; amended 2026-08-21
**Original date:** 2026-08-13
**Related:** ADR 0006, ADR 0007, ADR 0009, ADR 0036, ADR 0065

## Context

Every Buyer surface that uses the Knowledge Graph—Keyman traversal, customer
and corporate hierarchy, VOC/VOM/VOP relationship classification, indirect
lineage nomination, project evidence, and Ask retrieval—needs a governed,
machine-checkable semantic contract rather than an informal collection of
lookup strings.

The relational model already contains the core facts:

- `knowledge_graph_edge` has a subject–predicate–object shape;
- `common_lookup_value` owns the controlled codes for node, edge,
  relationship, person-side, corporate level, and role-actor vocabularies;
- `corporate_entity.parent_entity_id` stores real organizational containment;
- `corporate_entity.entity_level_code` classifies an organization as Group,
  Company, or Plant; and
- `cataloged_team.affiliated_corporate_entity_id` binds a team to the
  organization that owns it.

The first ontology slice correctly introduced OWL 2, RDFS, SKOS, PROV-O, and
W3C ORG terms and tested relational lookup-code drift. It nevertheless modeled
`CorporateEntity` itself as a subclass of `skos:Concept` and described
`parent_entity_id` with `skos:broader`/`skos:narrower`.

That conflates two different things:

1. a real organization that can own teams, appear in records, and participate
   in business relationships; and
2. a classification concept such as Group, Company, or Plant.

SKOS broader/narrower is appropriate for the second. W3C ORG organization and
sub-organization relations are appropriate for the first. Leaving them
conflated would make standards-aware consumers treat an actual customer or
company as a taxonomy term and would obscure the difference between
organizational containment and level classification.

OWL and RDFS also use open-world semantics: domain/range statements support
inference but do not provide the closed-world required-cardinality validation
needed by an interchange contract. A separate SHACL profile is therefore
needed rather than misusing OWL restrictions as database-style validation.

## Decision

Publish the relational vocabulary as a versioned, standards-composed ontology
in `docs/ontology/lineageweave-kg.ttl`, with PostgreSQL remaining the source of
record.

### RDF, RDFS, and OWL 2

- Classes, object properties, datatype properties, inverse properties, and
  symmetric properties use RDF/RDFS/OWL 2.
- The ontology has a stable ontology IRI, `owl:versionIRI` 1.0.0, and
  `owl:versionInfo`.
- `owl:imports` records the exact external semantic dependencies—W3C ORG,
  PROV-O, and SKOS—as metadata. Runtime loading parses committed local
  artifacts and never dereferences imports over the network.

### W3C ORG for real organizational structure

- `CorporateEntity` is an `org:Organization`.
- `Team` is an `org:OrganizationalUnit`.
- local `subOrganizationOf` specializes `org:subOrganizationOf` and represents
  `corporate_entity.parent_entity_id`.
- local `hasSubOrganization` is its inverse and specializes
  `org:hasSubOrganization`.
- `teamAffiliatedWith` specializes `org:unitOf`, preserving the existing
  Team-to-CorporateEntity stored edge direction.

These properties express real organizational containment and unit ownership;
they are not taxonomy links.

### SKOS for controlled classification and labels

- `CorporateEntityLevel` is a class of SKOS concepts.
- `GroupLevel`, `CompanyLevel`, and `PlantLevel` are instances of that class in
  `corporateEntityLevelScheme`.
- `skos:broader`/`skos:narrower` orders the classification concepts from Group
  to Company to Plant.
- `hasEntityLevel` binds one real `CorporateEntity` to one level concept.
- verified organization aliases continue to map naturally to `skos:altLabel`
  and canonical names to `skos:prefLabel`; the relational alias-resolution
  evidence remains authoritative.

### PROV-O for acting parties and provenance

- role actors retain their separate PROV-O grounding:
  `RoleActorPerson` subclasses `prov:Person` and
  `RoleActorOrganization` subclasses `prov:Organization`.
- the standards-complete provenance assertion store in ADR 0065 remains
  separate from the compact Buyer navigation graph. This ontology does not
  flatten qualified PROV-O assertions or literal properties into
  `knowledge_graph_edge`.

### Product vocabulary and relational lookup codes

- `Post`, `Person`, `CorporateEntity`, and `Team` remain the navigation node
  classes associated with `node_type` lookup codes.
- mention, affiliation, co-mention, team, organization, VOC/VOM/VOP/VOCC/VOCO/
  VOS, and semantic-project properties retain explicit domain and range.
- every term backed by `common_lookup_value` carries exactly one `lookupCode`
  annotation. Application code resolves these IRIs through
  `lineageweave.ontology` instead of retyping strings.
- `tests/test_ontology.py` continues the bidirectional check between committed
  seed/migration lookup codes and ontology annotations.

### SHACL for closed-world interchange constraints

Publish `docs/ontology/lineageweave-kg.shacl.ttl` as a separately versioned
SHACL shapes graph.

The first profile requires:

- exactly one corporate-entity level per `CorporateEntity`;
- at most one direct parent organization, matching the current relational
  self-reference;
- exactly one owning organization per `Team`; and
- the corresponding W3C ORG and LineageWeave classes.

SHACL is the external RDF validation contract. PostgreSQL foreign keys,
not-null constraints, and application authorization remain authoritative for
stored product data.

## Rationale

### Do not replace PostgreSQL with a parallel triple store

The existing relational model, ABAC joins, reconstruction pipeline, and Buyer
queries are operationally useful. Publishing formal semantics and validation
does not require duplicating mutable truth in a new RDF database. An external
SPARQL service can be added later as a projection if a concrete consumer
requires it.

### Keep organizations and classifications distinct

A company is not a kind of taxonomy term. The company may be classified by a
level concept, while independently participating in an organization hierarchy.
W3C ORG and SKOS complement one another precisely when these responsibilities
are separated.

### Keep inference and validation distinct

RDFS/OWL domain, range, subclass, inverse, and symmetry axioms define meaning
and support inference. SHACL defines required cardinalities and accepted graph
shape. Conflating them either weakens validation or distorts the ontology.

### Keep provenance and navigation distinct

PROV-O represents activities, entities, agents, qualified influences, and
literal-valued properties. `knowledge_graph_edge` remains a bounded,
removable navigation projection and must not become the provenance assertion
store.

## Consequences

### Positive

- External consumers can distinguish an actual customer organization from its
  Group/Company/Plant classification.
- Corporate and team containment reuse standard W3C ORG relations.
- SKOS remains focused on controlled concepts and multilingual labels.
- Versioned ontology and SHACL artifacts can be pinned by APIs, dossiers, and
  downstream MCP consumers.
- Lookup-code drift, semantic-role drift, and cardinality regressions are
  covered by separate tests.

### Costs and limitations

- RDF producers must emit both real organization relations and level
  classifications instead of overloading one SKOS edge.
- The current SHACL profile covers the high-value organization boundaries, not
  every relational constraint in the product schema.
- `owl:imports` is metadata only in the runtime; integrated offline reasoner
  and full SHACL-engine conformance remain additive validation lanes.
- The ontology does not itself grant access. Every product projection must pass
  the existing authenticated RBAC/ABAC boundary before exposing an IRI, node,
  relation, label, or source body.

## Rejected alternatives

### Keep CorporateEntity as `skos:Concept`

Rejected because it conflates a real organization with its classification and
uses taxonomy hierarchy for organizational containment.

### Use only W3C ORG and drop SKOS

Rejected because organization levels, canonical labels, aliases, and other
controlled vocabularies still need a concept-scheme model independent of the
organization instances.

### Treat OWL domain/range as data validation

Rejected because OWL/RDFS primarily infer types under open-world semantics;
they do not provide the required closed-world cardinality contract.

### Add a second mutable RDF system of record

Rejected because it would duplicate PostgreSQL authority and force every
write, authorization, migration, and repair path to coordinate two stores.

## References — APA 7th

Brickley, D., & Guha, R. V. (Eds.). (2014). *RDF Schema 1.1*. World Wide Web
Consortium. https://www.w3.org/TR/rdf-schema/

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 concepts and
abstract syntax*. World Wide Web Consortium.
https://www.w3.org/TR/rdf11-concepts/

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes constraint language
(SHACL).* World Wide Web Consortium. https://www.w3.org/TR/shacl/

Lebo, T., Sahoo, S., McGuinness, D., Belhajjame, K., Cheney, J., Corsar, D.,
Garijo, D., Soiland-Reyes, S., Zednik, S., & Zhao, J. (Eds.). (2013).
*PROV-O: The PROV ontology*. World Wide Web Consortium.
https://www.w3.org/TR/prov-o/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS Simple Knowledge Organization
System reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Prud'hommeaux, E., & Carothers, G. (Eds.). (2014). *RDF 1.1 Turtle: Terse RDF
Triple Language*. World Wide Web Consortium. https://www.w3.org/TR/turtle/

Reynolds, D. (Ed.). (2014). *The organization ontology*. World Wide Web
Consortium. https://www.w3.org/TR/vocab-org/

W3C OWL Working Group. (2012). *OWL 2 Web Ontology Language document overview*
(2nd ed.). World Wide Web Consortium. https://www.w3.org/TR/owl2-overview/
