# ADR 0159 — Publish the ontology namespace as a deterministic GitHub Pages artifact

**Decision status:** Accepted
**Date:** 2026-08-21

## Context

ADR 0004 established `docs/ontology/lineageweave-kg.ttl` as the formal,
machine-validated OWL 2 / RDF Schema / SKOS vocabulary for LineageWeave. The
repository already verifies that the ontology and relational controlled
vocabulary do not drift. However, the product-facing URL
`https://contextualwisdomlab.github.io/LineageWeave/ontology#` returned no
published resource, so ontology terms shown to buyers and external consumers
did not lead to a documentation endpoint.

Publishing the authenticated LineageWeave application itself is not the right
fix. The ontology is a public specification artifact. It must remain usable
without tenant credentials, runtime APIs, PostgreSQL, contextual-orchestrator,
or any private source data.

A second concern is namespace identity. The knowledge-graph Turtle and runtime
lookup predicate use the lowercase semantic namespace
`https://contextualwisdomlab.github.io/lineageweave/ontology#`, while the
committed PROV-O support profile and its contract test use the repository-case
namespace `https://contextualwisdomlab.github.io/LineageWeave/ontology#`.
GitHub Pages paths are case-sensitive. Silently rewriting either form would be
a breaking ontology migration, not a deployment repair. Issue #372 therefore
owns the inventory, canonical-namespace decision, compatibility vocabulary,
and consumer migration plan.

## Decision

1. Add a deterministic Python renderer, `scripts/build_ontology_site.py`, that
   reads the authoritative Turtle source and emits a static Pages tree.
2. Publish a fragment-addressable HTML vocabulary at
   `https://contextualwisdomlab.github.io/LineageWeave/ontology`, with one
   stable anchor for every documented class, property, concept scheme, and
   concept. A resource with more than one documented RDF type is rendered once
   with one anchor.
3. Publish equivalent machine-readable artifacts beside the HTML:
   `ontology.ttl`, `ontology.jsonld`, `ontology.nt`, the PROV-O support profile,
   and a source-digest manifest.
4. For a single governed Turtle source, preserve `lineageweave-kg.ttl`
   byte-for-byte as the published Turtle artifact. When a later accepted ADR
   adds governed fragments, publish the merged graph as deterministic canonical
   RDF that parses as Turtle; test every machine format for semantic
   isomorphism with the complete source graph. Never concatenate independent
   Turtle documents because their prefix and base declarations have
   document-local scope.
5. Do not add a build timestamp. The same source tree must produce the same
   artifact bytes. The manifest records every governed source path and SHA-256,
   the ordered source-tree SHA-256, and the complete published
   ontology-directory inventory instead.
6. Run publication through `scripts/publish_ontology_site.py`, a fail-closed
   boundary that rejects duplicate HTML fragments, non-HTTP(S) linked IRIs,
   symlink outputs, source-overlapping outputs, and replacement of directories
   that do not contain the generator marker. This prevents ontology data from
   becoming executable links and prevents a misconfigured output path from
   deleting unrelated files.
7. Validate publication behavior on pull requests, including 100% statement
   and branch coverage for both the renderer and publication boundary. Deploy
   only from `main`; a manual dispatch from any other ref is not a publication
   path.
8. Pin every third-party GitHub Action by full commit SHA and grant Pages and
   OIDC permissions only to the deployment job. Pull-request validation may
   cancel superseded runs, while the single publication concurrency group does
   not cancel an in-progress deployment.
9. Keep existing semantic IRIs unchanged in this deployment PR. The Pages
   document distinguishes the public documentation endpoint from the semantic
   identifier. Issue #372 and a future versioned ADR must govern any namespace
   migration, compatibility mappings, deprecation interval, and stored-data
   migration.
10. The repository must have Pages source set to **GitHub Actions** once. After
    that administrative enablement, publication is entirely workflow-driven.

## Consequences

- The requested URL becomes a stable public specification surface after this
  change reaches `main`, the repository Pages source is configured for GitHub
  Actions, and the Pages environment completes successfully.
- External consumers can inspect human-readable terms or download equivalent
  RDF serializations without running LineageWeave.
- A changed ontology cannot publish if its lookup-code contract, semantic
  round-trip, deterministic-build contract, public-link safety, unique-fragment
  contract, filesystem replacement boundary, or coverage gate fails.
- GitHub Pages remains a static documentation host; it does not provide HTTP
  content negotiation or become a graph database, SPARQL endpoint, or source
  of runtime truth.
- No private tenant data, runtime secrets, model output, or authenticated UI is
  present in the artifact.
- The existing case-distinct namespace forms remain a tracked interoperability
  gap rather than being hidden by this deployment change.

## Related decisions and work

- [ADR 0004](0004-knowledge-graph-ontology.md): ontology and relational
  vocabulary contract.
- [ADR 0011](0011-prov-o-standard-relations.md): standard PROV-O relations.
- [ADR 0065](0065-prov-o-provenance-boundary.md): provenance authority
  boundary.
- Issue #372: reconcile lowercase and repository-case public namespace IRIs.
- PR #349: authenticated Ontology Explorer consumer surface.

## References — APA 7th

GitHub. (2026). *Using custom workflows with GitHub Pages*.
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web*.
World Wide Web Consortium. https://www.w3.org/TR/cooluris/

Villazón-Terrazas, B., Vilches-Blázquez, L. M., Corcho, O., & Gómez-Pérez, A.
(2011). Methodological guidelines for publishing government linked data. In
D. Wood (Ed.), *Linking government data* (pp. 27–49). Springer.
https://doi.org/10.1007/978-1-4614-1767-5_2
