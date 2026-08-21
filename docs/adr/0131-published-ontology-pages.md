# ADR 0131 — Publish the ontology namespace as a deterministic GitHub Pages artifact

**Decision status:** Accepted  
**Date:** 2026-08-21

## Context

ADR 0004 established `docs/ontology/lineageweave-kg.ttl` as the formal,
machine-validated OWL 2 / RDF Schema / SKOS vocabulary for LineageWeave. The
repository already verifies that the ontology and relational controlled
vocabulary do not drift. However, the product-facing URL
`https://contextualwisdomlab.github.io/LineageWeave/ontology#` returned no
published resource, so ontology IRIs shown to buyers and external consumers did
not lead to a documentation endpoint.

Publishing the authenticated LineageWeave application itself is not the right
fix. The ontology is a public specification artifact. It must remain usable
without tenant credentials, runtime APIs, PostgreSQL, contextual-orchestrator,
or any private source data.

A second concern is namespace identity. Existing source code and RDF artifacts
use the lowercase semantic namespace
`https://contextualwisdomlab.github.io/lineageweave/ontology#`. Silently
rewriting those IRIs to match the repository's display-case path would be a
breaking ontology migration, not a deployment repair.

## Decision

1. Add a deterministic Python builder, `scripts/build_ontology_site.py`, that
   reads the authoritative Turtle source and emits a static Pages tree.
2. Publish a fragment-addressable HTML vocabulary at
   `https://contextualwisdomlab.github.io/LineageWeave/ontology`, with one
   stable anchor for every documented class, property, concept scheme, and
   concept.
3. Publish equivalent machine-readable artifacts beside the HTML:
   `ontology.ttl`, `ontology.jsonld`, `ontology.nt`, the PROV-O support profile,
   and a source-digest manifest.
4. Preserve `lineageweave-kg.ttl` byte-for-byte as the published Turtle
   artifact. JSON-LD and N-Triples are generated from a canonicalized RDF graph
   and are tested for semantic isomorphism with the source.
5. Do not add a build timestamp. The same source tree must produce the same
   artifact bytes. The manifest records the source SHA-256 instead.
6. Validate publication behavior on pull requests, including 100% statement
   and branch coverage for the builder. Deploy only from `main` or an explicit
   protected manual dispatch through the `github-pages` environment.
7. Pin every third-party GitHub Action by full commit SHA and grant Pages and
   OIDC permissions only to the deployment job.
8. Keep the existing lowercase ontology IRI unchanged. The Pages document
   clearly distinguishes the public documentation endpoint from the semantic
   identifier. Any future namespace change requires a separate versioned ADR,
   compatibility vocabulary, and consumer migration plan.
9. The repository must have Pages source set to **GitHub Actions** once. After
   that administrative enablement, publication is entirely workflow-driven.

## Consequences

- The requested URL becomes a stable public specification surface after this
  change reaches `main` and the Pages environment completes successfully.
- External consumers can inspect human-readable terms or download equivalent
  RDF serializations without running LineageWeave.
- A changed ontology cannot publish if its lookup-code contract, semantic
  round-trip, deterministic-build contract, or builder coverage fails.
- GitHub Pages remains a static documentation host; it does not provide HTTP
  content negotiation or become a graph database, SPARQL endpoint, or source
  of runtime truth.
- No private tenant data, runtime secrets, model output, or authenticated UI is
  present in the artifact.

## Related decisions

- [ADR 0004](0004-knowledge-graph-ontology.md): ontology and relational
  vocabulary contract.
- [ADR 0011](0011-prov-o-standard-relations.md): standard PROV-O relations.
- [ADR 0065](0065-prov-o-provenance-boundary.md): provenance authority
  boundary.

## References — APA 7th

GitHub. (2026). *Using custom workflows with GitHub Pages*.
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web*.
World Wide Web Consortium. https://www.w3.org/TR/cooluris/

Villazón-Terrazas, B., Vilches-Blázquez, L. M., Corcho, O., & Gómez-Pérez, A.
(2011). Methodological guidelines for publishing government linked data. In
D. Wood (Ed.), *Linking government data* (pp. 27–49). Springer.
https://doi.org/10.1007/978-1-4614-1767-5_2
