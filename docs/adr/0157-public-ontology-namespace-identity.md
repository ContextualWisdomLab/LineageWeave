# ADR 0157 — Keep the lowercase public ontology namespace canonical

**Decision status:** Accepted
**Date:** 2026-08-23
**Issue:** [#372](https://github.com/ContextualWisdomLab/LineageWeave/issues/372)

## Context

LineageWeave has minted two case-distinct HTTP IRI families. The knowledge-
graph ontology, runtime resolver, API fixtures, and frontend fixtures use
`https://contextualwisdomlab.github.io/lineageweave/ontology#`. The PROV-O
support profile uses
`https://contextualwisdomlab.github.io/LineageWeave/ontology#`. RDF treats
these as different identifiers, and GitHub Pages treats the project paths as
different paths.

Both forms must be treated as externally durable. The lowercase form can be
stored in `post_project_mention.ontology_iri`, returned by APIs, and copied
into RDF or downstream graph stores. The repository-case form is shipped in a
public RDF support profile. There is no repository evidence that either form
is unused outside LineageWeave. The exact inventory and current-head evidence
are recorded in
[`ONTOLOGY_NAMESPACE_INVENTORY.md`](../doctoring/ONTOLOGY_NAMESPACE_INVENTORY.md).

W3C guidance favors stable, manageable HTTP identifiers. Changing the wider
deployed namespace merely to match a hosting path would make infrastructure
spelling determine semantic identity. OWL equivalence is also term-kind
specific: class, property, individual, and SKOS-concept mappings are not
interchangeable.

## Decision

1. The canonical namespace for existing and future LineageWeave ontology
   terms is the lowercase
   `https://contextualwisdomlab.github.io/lineageweave/ontology#` namespace.
   New runtime values, RDF exports, database rows, examples, and API payloads
   must not mint repository-case term IRIs.
2. The repository-case namespace is a deprecated compatibility namespace. It
   remains dereferenceable and is never reused for different meanings.
3. The future publication slice must serve both namespace documents with
   `200 OK`. The lowercase document is authoritative. The repository-case
   document is a compatibility vocabulary that identifies the canonical
   document and carries only validated mappings. A redirect alone is
   insufficient because it neither proves RDF equivalence nor reliably
   communicates fragment-level term mappings.
4. Compatibility mappings are generated from the two parsed RDF graphs and
   emitted only when local-name uniqueness, term kind, and defining semantics
   match:
   - class to class: `owl:equivalentClass`;
   - object/datatype/annotation property to the same property kind:
     `owl:equivalentProperty`;
   - SKOS concept to SKOS concept: `skos:exactMatch` only after concept meaning
     is verified;
   - individuals: `owl:sameAs` only with evidence of identical identity.
   A term without sufficient evidence receives no equivalence assertion.
5. Existing repository-case class IRIs in the PROV-O support profile are
   compatibility inputs, not authority to mint more repository-case terms.
   Their migration is a later implementation slice with RDF-isomorphism and
   term-kind tests.
6. Historical RDF, provenance bundles, and evidence rows are immutable.
   Migration tooling may create a versioned canonical projection and retain a
   source-to-target mapping, but must not silently rewrite the historical
   artifact. Relational migrations must be deterministic, idempotent,
   transactional, and reversible from that mapping.
7. Producers stop minting repository-case IRIs in the migration release.
   Compatibility documentation and resolution remain available indefinitely.
   The repository-case vocabulary is marked deprecated for at least 180 days
   and two minor releases, whichever is later, before support can be reduced;
   dereferenceability and mappings are not removed at the end of that window.
8. Deployment of the lowercase namespace requires an owned route at that
   exact path. Repository rename, client-side case folding, and undocumented
   hosting redirects are not substitutes. Until both paths are verified in
   production, publication and migration remain incomplete.

## Considered options

### Keep lowercase canonical — chosen

This preserves the ontology's existing identifier, runtime constant, API
contract, and wider set of serialized examples. It follows the principle that
published semantic identifiers should not change with hosting implementation.
It does require an organization-site route in addition to the repository-case
GitHub Pages project path.

### Make repository-case canonical

This matches the current repository name and the Pages project path, but would
replace the more widely used semantic identifier for a deployment convenience
and require migration of runtime, API, database, frontend, and graph consumers.

### Treat both namespaces as canonical

Rejected because RDF consumers correctly treat the IRIs as different
resources. Maintaining two authorities would preserve the interoperability
defect and make every new term ambiguous.

## Consequences

- Existing lowercase identifiers remain stable and new producers have one
  unambiguous namespace.
- The repository-case support-profile terms remain resolvable through a
  compatibility vocabulary rather than disappearing or being silently folded.
- A separate implementation PR is required for publication routing, validated
  mappings, stored-value migration, rollback, consumer fixtures, and exact HTTP
  tests. This ADR intentionally performs no namespace rewrite.
- Hosting is more involved than a single Pages project deployment. That cost is
  accepted to keep semantic identity independent of repository-case spelling.
- Unknown downstream graphs are treated as real compatibility obligations; an
  absence of repository evidence is not evidence that they do not exist.

## Verification required for the implementation slice

- Exact `200` responses for both namespace documents and representative
  fragments, with the lowercase document identified as canonical.
- RDF graph isomorphism and term-kind tests for every emitted compatibility
  mapping; no duplicate local fragments.
- Consumer fixtures proving old graphs still resolve and new serialization
  mints only lowercase IRIs.
- Transactional migration tests proving idempotency, rollback, and preservation
  of historical provenance bundles.
- Synchronized runtime constants, Turtle/JSON-LD/N-Triples, support profile,
  API/frontend contracts, database seeds, generated Pages artifacts, and
  changelog.

## Related decisions

- [ADR 0004](0004-knowledge-graph-ontology.md): ontology vocabulary authority.
- [ADR 0011](0011-prov-o-standard-relations.md): PROV-O support profile.
- [ADR 0065](0065-prov-o-provenance-boundary.md): provenance/navigation
  separation.
- Issue #372 owns the implementation and migration verification.
- PR #349 is an open ontology consumer and PR #426 is an open publication
  implementation; neither is protected-main evidence.

## References — APA 7th

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference* (W3C Recommendation). World Wide Web
Consortium. https://www.w3.org/TR/skos-reference/

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web* (W3C
Interest Group Note). World Wide Web Consortium.
https://www.w3.org/TR/cooluris/

World Wide Web Consortium. (2008). *Best practice recipes for publishing RDF
vocabularies* (W3C Working Group Note).
https://www.w3.org/TR/swbp-vocab-pub/

W3C OWL Working Group. (2012). *OWL 2 web ontology language quick reference
guide* (2nd ed., W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/owl2-quick-reference/
