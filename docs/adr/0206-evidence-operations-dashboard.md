# ADR 0206: Evidence-grounded operations dashboard

- Status: Accepted
- Date: 2026-08-25
- Figma file ID: `1Su3lDRmiZdcUs47t1QwIX`

## Context

The authenticated workspace opens on the Board, so a reader must search and
open records one at a time to assess delayed claim investigation, rebid or
handover gaps, external-market coverage, and a project's changing journey.
The stored corpus already separates source fields from semantic evidence:
`source_post`, `post_project_mention`, `post_summary_event`,
`post_summary_action`, `post_summary_role`, and `post_lineage_edge`.

Those tables do not yet contain claim-case, rebid/handover, specification
change, originating-order, or external-information semantic classifications.
Keyword matching, title fragments, and fixed confidence thresholds cannot
provide them: the same words occur in unrelated operational contexts. The
repository's existing contextual-orchestrator boundary can make a grounded
semantic classification while preserving the cited source span and model-run
provenance.

## Decision

1. `/` opens an evidence-operations Dashboard after authentication. Board
   remains independently reachable from the global navigation.
2. Dashboard requests are bounded by an inclusive event-time period.
   `source_post.event_occurred_at` is the primary clock and `created_at` is the
   explicit fallback, matching ADR 0202. The response names that clock.
3. Every count is authorization-filtered before aggregation. The API returns
   both event count and distinct post count; neither substitutes for the other.
4. Extend the existing post-summary semantic workflow through
   contextual-orchestrator with a schema-validated case analysis. It classifies
   zero or more case kinds (`claim_investigation`, `rebid_handover`,
   `external_information`, `repeat_issue`) and extracts the question-specific
   facts. Every positive classification carries a verbatim source evidence span. Keywords,
   regexes, provider-name ordering, local model selection, and hand-authored
   scoring weights are prohibited.
5. Persist the result in normalized post case-analysis tables with the source
   body digest and orchestrator session/run provenance. A changed source body
   invalidates the old result and queues re-analysis through the existing
   content-ingestion lifecycle. Schema-invalid or unavailable results fail the
   job and remain retryable; they are not converted into a negative case.
6. External-information coverage is the distinct count of visible posts with
   a persisted positive `external_information` classification divided by all
   visible posts in the same period. The stored `vom` source code is supplied
   to the orchestrator as labeled evidence, but does not replace semantic
   analysis. Zero total posts yields `0`.
7. Qualitative rows project only persisted evidence:
   project names and evidence spans, source sales-pool code/name, summary
   events, requester/processor action evidence, roles, and Event Lineage links.
   When the focal post lacks an answer, the orchestrator follows authorized
   Event Lineage and semantic project evidence before concluding the fact is
   absent from the authorized corpus.
8. Claim-investigation and rebid/handover panels include positively classified
   cases and show extracted answers plus cited spans. A required answer that
   the source does not support is stored as an explicit missing fact, so the
   next action is collection or human correction rather than keyword guessing.
9. Project journeys group events only by an explicit source project or stored
   semantic project mention. A multi-project post may appear in multiple
   journeys. Unbound events remain visible as unassigned evidence and are not
   attached to the nearest project.
10. A repeat-issue result carries both the issue-pattern evidence and any
   source-supported improvement action. Its Dashboard flow is As-Is evidence
   to To-Be action: rebid history retrieval, originating-order/specification
   reverse tracing, repeated-issue grouping, and design-improvement return.
   Similarity alone never establishes that two issues are the same type.
11. The Dashboard uses existing design tokens and native HTML controls. Tables
   and ordered journey steps remain usable without color, with visible focus,
   keyboard activation, responsive overflow, and reduced-motion support.
12. Storybook records populated, empty, analysis-failed, missing-evidence,
   error, desktop, and narrow-viewport scenes. Runtime screenshot review uses
   synthetic data only.
13. The Dashboard does not add a separate external-information Board. Its GNB
   destination contains the external count/rate and evidence filter; opening a
   result reuses the existing Board post detail.
14. TEPP is the measurement authority. Similar-VOC quality and operational
   outcome measures consume only accepted and persisted TEPP results. The
   Dashboard never creates a local theta or repairs a missing TEPP envelope.
   The current fast-mlsirm Event Lineage experiment is unanchored and inactive
   under ADR 0145/0200; the Dashboard does not consume its candidate vectors.
   RankWeave may fuse channels only after an independently anchored vector is
   authorized, and that rank is never a psychometric measure or substitute for
   TEPP. Missing estimates remain unavailable; no hand-picked weight is
   introduced.

## Consequences

The landing page answers what is known, how much evidence exists, and which
field or relationship must be obtained next. Classification is inferred inside
the governed stack and remains auditable through source spans and run
provenance; operational failure is visible and retryable rather than silently
treated as a negative case.

## Verification

- Parser and persistence tests cover multi-label output, cited spans, malformed
  responses, source-digest invalidation, and unavailable orchestrator states.
- Backend integration tests cover ABAC filtering, event-time fallback, event
  versus post counts, external-information percentage, multi-project
  membership, and explicit missing facts.
- Frontend tests cover period submission, navigation, empty/error states,
  evidence links, keyboard semantics, and non-color status copy.
- Storybook interaction tests and authenticated browser screenshots audit the
  rendered desktop and narrow layouts.
