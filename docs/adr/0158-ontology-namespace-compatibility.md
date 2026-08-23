# ADR 0158 — Implement canonical lowercase ontology namespace compatibility

**Decision status:** Accepted
**Date:** 2026-08-23
**Issue:** [#372](https://github.com/ContextualWisdomLab/LineageWeave/issues/372)

## Context

GitHub Pages project paths are case-sensitive. Committed artifacts currently
use two distinct public namespace forms:

- Knowledge-graph ontology and runtime lookup:
  `https://contextualwisdomlab.github.io/lineageweave/ontology#`
- PROV-O support profile:
  `https://contextualwisdomlab.github.io/LineageWeave/ontology#`

RDF 1.1 treats IRI equality as character-for-character identity, so a
case difference is a different resource (Cyganiak, Wood, & Lanthaler,
2014, section 3.2). An HTTP redirect from the repository-case Pages path
is a documentation convenience, not `owl:sameAs`.

The lowercase namespace is already on the runtime `LW` constant, API
payloads, frontend fixtures, and persisted lookup IRIs. Silently rewriting
those strings would change historical evidence.

The PROV-O support profile only declares four class alignments (`Post`,
`Person`, `CorporateEntity`, `Team`). Those local names are also
`owl:Class` in the KG ontology, so a typed compatibility map is valid.
Other KG fragments (`OurSidePerson`, `mentionedIn`, `Project`, …) have no
matching repository-case term.

PR #491 records the identity decision as ADR 0157. This record is the
implementation slice: compatibility vocabulary, fail-closed resolver,
documented HTTP 200 for both documents, and tests. It does not depend
on #491 merging and does not rewrite stored rows.

## Decision

1. Keep
   `https://contextualwisdomlab.github.io/lineageweave/ontology#`
   as the **canonical** knowledge-graph namespace for runtime, API, and
   new persisted evidence. New producers must not mint repository-case
   term IRIs.
2. Keep
   `https://contextualwisdomlab.github.io/LineageWeave/prov-o-support`
   as the PROV-O support-profile document IRI. Do not merge that document
   with the KG ontology document.
3. Publish `docs/ontology/namespace-compatibility.ttl` mapping the four
   matching **classes** with `owl:equivalentClass`. Mappings are generated
   from the two parsed RDF graphs and emitted only when local-name
   uniqueness, term kind, and meaning match. Do not claim
   `owl:equivalentProperty` or `owl:equivalentClass` for unmatched
   fragments. Do not claim `owl:sameAs` between the two ontology
   documents; `skos:closeMatch` records documentation proximity only.
4. Provide a fail-closed resolver (`canonical_iri` /
   `migrate_stored_iri`) that is identity on historical KG IRIs, maps
   only the four class aliases, and raises on unknown aliases. The
   resolver is opt-in tooling. It does not rewrite database rows.
5. Document HTTP behavior: both namespace documents are specified as
   `200 OK`. In-repository Turtle is the source of truth. A Pages
   redirect must not be treated as RDF identity. Live dereference of
   GitHub Pages is out of band for CI.
6. Do not rewrite rows already stored under the canonical namespace.
   Bulk migration of the four class aliases is opt-in, idempotent, and
   never invents a term.

Deprecation window: the repository-case class IRIs remain published
for at least 180 days and two minor releases, whichever is later, so
existing PROV-O profile consumers can load the compatibility
vocabulary. Dereferenceability and mappings are not removed at the
end of that window. After that window, new terms are canonical-only.

## Consequences

- RDF consumers that load the compatibility file can treat the four class
  pairs as the same class without collapsing the two ontology documents.
- Buyers inspecting persisted IRIs continue to see the historical
  lowercase form.
- Stacked ontology-explorer work (issue #349) must consume the canonical
  namespace and the compatibility file rather than minting a third prefix.
- Relational `post_project_mention.ontology_iri` and
  `provenance_resource.resource_iri` rows are not inspected or rewritten
  in this slice. Unknown downstream stores are treated as real
  compatibility obligations.

## Related decisions

- [ADR 0004](0004-knowledge-graph-ontology.md): ontology vocabulary authority.
- [ADR 0011](0011-prov-o-standard-relations.md): PROV-O support profile.
- [ADR 0065](0065-prov-o-provenance-boundary.md): provenance/navigation
  separation.
- PR #491 / ADR 0157: identity decision (docs-only; may land separately).

## References

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 concepts
and abstract syntax*. World Wide Web Consortium.
https://www.w3.org/TR/rdf11-concepts/

GitHub. (2024). *About GitHub Pages*. GitHub Docs.
https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web*
(W3C Interest Group Note). World Wide Web Consortium.
https://www.w3.org/TR/cooluris/

W3C OWL Working Group. (2012). *OWL 2 web ontology language document
overview* (2nd ed.). World Wide Web Consortium.
https://www.w3.org/TR/owl2-overview/

World Wide Web Consortium. (2008). *Best practice recipes for publishing
RDF vocabularies* (W3C Working Group Note).
https://www.w3.org/TR/swbp-vocab-pub/
