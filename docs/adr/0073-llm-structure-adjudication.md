# ADR 0073: Evidence-aware post structure adjudication

- Status: Accepted
- Date: 2026-08-19

## Context

Visual line breaks, list markers, HTML styles, and OOXML formatting are not
equivalent evidence of document hierarchy. A marker heuristic may propose a
structure, but it cannot be persisted or presented as fact.

## Decision

Post structure is resolved in this order:

1. Explicit HTML, CSS, or OOXML indentation is authoritative.
2. When explicit evidence is absent, contextual-orchestrator adjudicates the
   text units and returns an indentation level, confidence, and evidence.
3. If adjudication is unavailable or incomplete, the structure is stored as
   unresolved with level zero. Marker depth is never stored as authoritative
   structure.

Structure evidence is stored one-to-one in the normalized
post_content_unit_structure table. The buyer UI uses the resolved level for
indentation and never renders an LLM instruction or internal prompt text.

All LLM and vision requests continue through contextual-orchestrator. The
caller does not select an LLM model.

## Consequences

- Flat display is an explicit unresolved state, not a fabricated hierarchy.
- Reprocessing can replace adjudication evidence without changing source text.
- Search and embeddings continue to use semantic units; visual wrapping is not
  treated as a paragraph boundary.
