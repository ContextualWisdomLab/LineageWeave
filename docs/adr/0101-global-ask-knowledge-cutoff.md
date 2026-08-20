# ADR 0101: Global Ask optional knowledge cutoff is evidence-honest

- Status: Accepted
- Date: 2026-08-20
- Related: [0016](0016-analysis-run-knowledge-cutoff-posts.md),
  [0025](0025-source-post-revision.md),
  [0039](0039-global-ask-agent-source-boundary.md),
  [0096](0096-ask-agent-open-focuses-event-lineage.md)
- Refs: Issue #271

## Context

Analysis-run detail already preserves `knowledge_cutoff` and reads the
cutoff-known body from `source_post_revision` (ADR 0016 / ADR 0025).
Global Ask still assembled only the live `source_post` row. A dated
question could therefore cite a later rewrite without saying so.

W3C Time Ontology in OWL (World Wide Web Consortium, 2022) and ISO
8601-1:2019 keep event time, valid time, and transaction/available time
distinct. Jensen and Snodgrass (1999) keep valid-time intervals
half-open. A prompt-only date is not a retrieval boundary.

## Decision

1. `POST /api/ask` accepts an optional `knowledge_cutoff` ISO-8601 clock.
   Omitting it preserves the live-query contract and must never label the
   answer as as-of.
2. When the cutoff is present, candidate and visible source rows require
   `created_at <= knowledge_cutoff`. A post created after the cutoff is
   excluded even when its live text matches.
3. Each selected post resolves to the latest `source_post_revision`
   covering that clock (`written_at <= cutoff < superseded_at`). That
   retained title and body enter the orchestrator context. The live body
   is never substituted.
4. If the post existed by the cutoff but no covering revision remains,
   the assembler records `historical_body_unavailable` and drops that
   body from the reason-and-cite set. Absence is not a fabricated earlier
   sentence.
5. Project, role, Keyman, graph, and source-hint facts that lack their
   own recorded/effective-time contract stay out of a historical answer.
   Current facts must not leak into an as-of response.
6. Each citation names source identity, revision identity when retained,
   evidence-available time, the requested cutoff, whether the live row
   changed after the cutoff, and any unavailable historical channel.
7. `grounding_status` is `live_only`, `fully_cutoff_grounded`, or
   `partially_cutoff_grounded`. A live-only answer is never called
   as-of.
8. Browser Ask Agent uses this assembler. Authenticated MCP is not on
   this Event Lineage slice; later MCP work must call the same function
   rather than a second retrieval path.

No TEPP theta is invented. No SearXNG claim is invented. No LLM score is
invented. Issues #79 and #87 remain outside this slice.

## Consequences

- Ask Agent can name a dated question and show which retained bodies
  existed by that clock.
- A rewritten Demo public post contributes its January sentence at a
  January cutoff and is marked live-after-cutoff when the live row moved.
- A February post stays out of a January cutoff even when its title
  matches.
- Buyer next action distinguishes fully grounded, partly grounded, and
  live-only answers.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management.
*IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44.
https://doi.org/10.1109/69.755613

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
