# ADR 0207 — Make the repository-case public ontology namespace canonical

**Decision status:** Accepted
**Date:** 2026-08-25
**Supersedes:** [ADR 0157](0157-public-ontology-namespace-identity.md)
**Resolves:** [#372](https://github.com/ContextualWisdomLab/LineageWeave/issues/372)
**Amended by:** [ADR 0229](0229-legacy-ontology-namespace-publication.md)

## Context

ADR 0157 made the lowercase
`https://contextualwisdomlab.github.io/lineageweave/ontology#` namespace
canonical and demoted the repository-case
`https://contextualwisdomlab.github.io/LineageWeave/ontology#` to a
compatibility vocabulary. Its decision 8 required an owned route at the exact
lowercase path before migration could complete. That owned lowercase route
does not exist and is not planned: GitHub Pages serves this repository only at
the project path `/LineageWeave/`, which matches the repository name, and an
organization-site alias for a second case-distinct path would permanently
split one publication into two hosting surfaces that must be kept in lockstep.

The product owner has now directed the opposite resolution: the public
ontology namespace must use the repository-case spelling `LineageWeave`, the
same case GitHub Pages actually serves. This aligns the semantic identifier
with (a) the dereferenceable documentation endpoint already published at
`https://contextualwisdomlab.github.io/LineageWeave/ontology` ([ADR
0159](0159-published-ontology-pages.md)), (b) the repository name every
downstream consumer sees, and (c) the PROV-O support profile's historical
IRIs. RDF treats the two spellings as different resources, so the flip is a
real identifier change with real compatibility obligations -- it is not a
cosmetic edit. Per ADR 0157's own terms, both forms are externally durable:
stored `post_project_mention.ontology_iri` values may still carry the
lowercase form, and downstream graphs may have copied either.

The same slice completes the ontology's missing definitions: node attribute
datatype properties, a SKOS post-type concept scheme grounded in the seeded
`voc_type` controlled vocabulary, OWL disjointness and inverse constraints,
and a SHACL shapes graph for closed-world data validation ([Knublauch &
Kontokostas, 2017]). SHACL carries the cardinality and value-range checks
OWL's open-world semantics deliberately does not, so DB-to-RDF projections
fail loudly instead of silently polluting downstream graphs.

## Decision

1. The canonical namespace for all existing and future LineageWeave ontology
   terms is the repository-case
   `https://contextualwisdomlab.github.io/LineageWeave/ontology#`. New runtime
   values, RDF exports, database rows, examples, API payloads, and generated
   Pages artifacts mint only repository-case term IRIs.
2. The lowercase namespace is now the deprecated compatibility namespace and
   is never reused for different meanings. ADR 0229 clarifies that its current
   `404` path is not described as dereferenceable.
3. The publication slice serves the repository-case namespace document and
   its `namespace-compatibility.ttl` mapping document with `200 OK`. The
   repository-case document is authoritative; the mapping document identifies
   it via `dcterms:isReplacedBy`, carries `owl:deprecated true`, and holds only
   validated mappings. It does not make the lowercase namespace path a served
   document (ADR 0229).
4. Compatibility mappings are generated between the two parsed graphs and
   emitted only when local-name uniqueness, term kind, and defining semantics
   match: class-to-class `owl:equivalentClass`; property-to-same-kind
   `owl:equivalentProperty`; SKOS-concept-to-SKOS-concept `skos:exactMatch`
   after meaning verification; individuals `owl:sameAs` only with identity
   evidence. A term without sufficient evidence receives no equivalence
   assertion. The publication validator enforces local-name equality and term
   kinds fail-closed in both directions.
5. Historical RDF, provenance bundles, and evidence rows are immutable.
   `scripts/migrate_legacy_namespace.py` now rewrites stored lowercase IRIs to
   the repository-case spelling -- dry-run by default, transactional,
   idempotent, never touching provenance columns, refusing unknown third
   spellings.
6. Producers stop minting lowercase IRIs in this release. The lowercase
   compatibility vocabulary stays marked deprecated for at least 180 days and
   two minor releases, whichever is later; dereferenceability and mappings are
   not removed at the end of that window.
7. Node-attribute datatype properties are declared only for columns the
   relational schema actually defines (`source_post.post_title`,
   `post_body`, `created_at`, `updated_at`, `event_occurred_at`;
   `cataloged_person.person_name`, `last_known_job_title`;
   `corporate_entity.corporate_entity_code`, `entity_name`). No invented
   column-backed property (country, business registration number) is minted.
   Shared timestamp properties carry no `rdfs:domain` because two `rdfs:domain`
   statements on one property entail subjects belong to both classes -- the
   same multi-domain trap ADR 0004's edge design already avoids; per-class
   cardinality lives in the SHACL shapes instead.
8. The post-type classification is formalized as SKOS exactly where the
   relational source has a governed vocabulary: the five seeded `voc_type`
   codes (`voc`, `vocc`, `voco`, `vom`, `vop`) become concepts in a
   `skos:ConceptScheme`. Keyman job titles and industry sectors remain free
   text in the schema with no lookup category, so no scheme is invented for
   them yet; that gap is tracked rather than fabricated.
9. Logical integrity constraints are stated explicitly:
   `:OurSidePerson owl:disjointWith :CounterpartyPerson` (a person side is one
   or the other, per the seeded `person_side` vocabulary), and
   `:hasAffiliate owl:inverseOf :affiliatedWith` so bidirectional person-to-
   entity queries resolve without a second stored edge. The inverse carries no
   relational lookup code, mirroring the existing `:mentions` /
   `:mentionedIn` pair.
10. A separate SHACL shapes graph validates projected data:
    required post title/body/timestamps, a complete single-valued RDF
    `subject`/`predicate`/`object` chain for every `ProjectMention`,
    single-valued decimal confidence within `[0.0, 1.0]`, required names on
    persons and entities, and the closed-world complement of the
    our-side/counterparty disjointness. Publication copies
    the shapes artifact beside the ontology and refuses dangling shape targets
    outside the canonical namespace.

## Considered options

### Repository-case canonical — chosen

Matches the only hosting path Pages actually serves, keeps one publication
surface, honors the owner directive, and preserves the support profile's
historical IRIs. Cost: stored lowercase IRIs migrate once through the existing
transactional tooling, and the compatibility vocabulary flips direction.

### Keep lowercase canonical (ADR 0157 status quo)

Would require building and operating a second, organization-hosted lowercase
route forever, splitting semantic identity from the served documentation path.
Rejected by the owner directive and by deployment simplicity.

### Treat both namespaces as canonical

Rejected for the same reason ADR 0157 rejected it: RDF consumers correctly
treat distinct IRIs as distinct resources; dual authorities preserve the
interoperability defect.

## Consequences

- One canonical namespace aligned with the served Pages path; new producers
  are unambiguous.
- The compatibility mapping document remains resolvable indefinitely;
  existing serialized graphs can translate through validated mappings.
- Stored-value migration runs through `scripts/migrate_legacy_namespace.py`
  with its existing dry-run/refusal discipline, direction reversed.
- Runtime constants, Turtle/JSON-LD/N-Triples, support profile, API and
  frontend fixtures, database seeds' consumers, and the generated Pages
  artifact move in one synchronized release.
- SHACL validation becomes a first-class test gate over the source graph.

## Verification

- Exact `200` responses for the canonical namespace and compatibility mapping
  documents, plus explicit `404` evidence for the unserved lowercase path.
- RDF graph-isomorphism and term-kind tests for every emitted mapping; no
  duplicate local fragments across namespaces.
- Consumer fixtures prove old lowercase graphs still resolve and new
  serialization mints only repository-case IRIs.
- Transactional migration tests prove idempotency, rollback safety, and
  provenance-column preservation (direction-reversed).
- SHACL conformance of the source ontology plus a negative violation test;
  publication manifest lists the shapes artifact deterministically.

## Related decisions

- [ADR 0004](0004-knowledge-graph-ontology.md): ontology vocabulary authority.
- [ADR 0011](0011-prov-o-standard-relations.md) /
  [ADR 0065](0065-prov-o-provenance-boundary.md): PROV-O boundary.
- [ADR 0157](0157-public-ontology-namespace-identity.md): superseded; its
  compatibility-mapping mechanics are retained with direction reversed.
- [ADR 0159](0159-published-ontology-pages.md): deterministic Pages
  publication pipeline extended with the shapes artifact.
- Issue #372 owns the completed implementation and verification.

## References — APA 7th

Knublauch, H., & Kontokostas, R. (Eds.). (2017). *SHACL: Shapes constraint
language* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/shacl/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge organization
system reference* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web* (W3C
Interest Group Note). World Wide Web Consortium. https://www.w3.org/TR/cooluris/

W3C OWL Working Group. (2012). *OWL 2 web ontology language quick reference
guide* (2nd ed., W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/owl2-quick-reference/
