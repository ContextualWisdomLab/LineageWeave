# ADR 0080: Semantic backfill for posts without project fields

- Status: Accepted
- Date: 2026-08-20
- Deciders: LineageWeave maintainers

## Context

The source system does not reliably populate project fields. A post may name a
project only in its title, body, image evidence, customer context, sales-pool
context, or the author's organizational context. Explicit project fields are
useful evidence, but they are not a complete project ontology.

The repository already has an evidence-backed `post_project_mention` projection
and a contextual-orchestrator summary contract. A local keyword heuristic must
not promote a phrase to a project fact, especially when the customer value is a
weak sentinel such as `other` or `unregistered`.

## Decision

1. Keep `source_post.source_project_code` and `source_project_name` as explicit
   source evidence. They are hints for semantic extraction, not a replacement
   for the semantic projection.
2. For eligible posts without an explicit project field, derive project
   mentions through `ContextualOrchestratorPostSummaryClient` after
   `normalize_post_body` has converted DOM and VISION evidence into safe text.
3. Pass source author, author account, process-unit, sales-pool, customer, and
   project fields as labeled priors. Author affiliations and Keyman signals may
   guide interpretation, but never become facts without evidence in the post.
4. Persist only the existing `post_project_mention` contract with
   `extraction_method = contextual_orchestrator_semantic`, ontology IRI,
   evidence text, and confidence. No local heuristic may silently write this
   projection.
5. All requests for one post run inside the same `use_llm_metadata` context,
   whose deterministic post session id is attached to every orchestrator call.
6. The operator backfill is bounded by default and requires explicit `--all`
   for corpus-wide work. It is never exposed as a buyer HTTP route and never
   touches the analysis-run registry.

## Consequences

- Project search and customer/project navigation can use explicit fields and
  semantic mentions without treating weak customer sentinels as identities.
- Semantic coverage grows incrementally and remains auditable by post, source
  evidence, ontology IRI, extraction method, and confidence.
- A full-corpus backfill consumes orchestrator and VISION capacity; operators
  must run it in bounded checkpoints and retain the resulting runtime evidence.
- Posts that cannot be processed remain without a semantic project fact rather
  than receiving an invented classification.

