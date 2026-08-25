# ADR 0222: Project nodes in the ontology neighborhood

**Status:** Accepted  
**Date:** 2026-08-26  
**Extends:** [ADR 0036](0036-semantic-project-and-keyman-evidence.md), [ADR 0184](0184-ontology-provenance-explorer.md)  
**Figma:** File ID `1Su3lDRmiZdcUs47t1QwIX`

## Context

The published vocabulary and PRD define `Project` and `mentionsProject`, and
`post_project_mention` already preserves a normalized lexical project key, visible
label, confidence, evidence phrase, ontology IRI, extraction method, and
creation time. The bounded ontology API nevertheless recognizes only Post,
Person, CorporateEntity, and Team. A customer can therefore see project
evidence in a post summary but cannot traverse the same governed assertion in
the ontology neighborhood. That contradicts PRD-FR-2 across PostgreSQL, RDF,
API, and UI.

## Decision

1. Register `node_project` and `edge_mention_project` in the governed lookup
   vocabulary and map them to canonical `:Project` and `:mentionsProject`
   terms. PostgreSQL remains the source of truth; no second project store is
   created.
2. `project_key` is a normalized lexical candidate key, not a resolved Project
   identity. A Project candidate node id is the exact
   `<evidence-post-uuid>/<project_key>` pair. The API validates both components
   and never merges same-named candidates from different posts. A future
   source/tenant-scoped Project catalog may resolve multiple candidates to one
   identity through a separate evidence-backed decision; this projection does
   not perform that resolution or mint a cross-post identity.
3. Each visible `post_project_mention` projects one Post `mentionsProject`
   Project fact. Its availability time is the later of source-post creation
   and mention persistence. The fact is `truth_proposed`, never observed or
   authoritative, because contextual-orchestrator extraction remains a
   reviewable semantic candidate.
4. Authorization, source eligibility, knowledge cutoff, snapshot time,
   traversal bounds, and cursor ordering apply in the same SQL source window
   as every Knowledge Graph fact. A Project focus and every expanded Project
   endpoint are authorized only by eligible visible evidence posts.
5. The candidate's source-preserved `project_name` is its display label. Hidden
   rows cannot select or alter the label.
6. The UI uses a text-labeled diamond and exposes the same assertion through
   the graph, exact-value table, CSV, JSON-LD, print, and evidence drawer.
7. `project_project_mention_rdf` is the deterministic DB-row projection for a
   joined `source_post` / `post_project_mention` record. It emits the direct
   `mentionsProject` triple and the complete reified `ProjectMention`
   subject/predicate/object chain, evidence, confidence, creation time, and
   PROV derivation. It performs no database access and creates no mutable RDF
   store; callers must still apply authorization before supplying a row.

## Consequences

- Project evidence becomes traversable without copying or promoting it.
- Project candidate IDs are intentionally the one composite ontology node
  identifier; all other governed node types keep their UUID validation.
- Same-name candidates remain separate until an evidence-backed Project
  catalog resolves them. This preserves uncertainty instead of collapsing
  unrelated work into one Project node.
- Confidence and evidence text remain on `post_project_mention` and its
  summary projection. Adding them to the neighborhood edge needs a separate
  typed API decision; this change does not invent edge scores.
- SHACL acceptance now exercises the production row projector rather than a
  hand-authored ProjectMention graph that could drift from application IRIs.

## Verification

- Ontology/lookup round-trip and SHACL publication tests.
- Assembler and ingestion tests for proposed truth, cutoff-safe availability,
  visible-label conflict behavior, and canonical focus validation.
- Frontend interaction, i18n, Storybook build, and desktop/mobile screenshot
  review with a synthetic Project node.

## References

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1 concepts and abstract syntax*. World Wide Web Consortium. https://www.w3.org/TR/rdf11-concepts/

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes constraint language (SHACL)*. World Wide Web Consortium. https://www.w3.org/TR/shacl/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/
