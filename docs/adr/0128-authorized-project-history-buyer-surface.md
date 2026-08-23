# ADR 0128: Authorized project-history buyer surface

- Status: Proposed on PR #285; not protected-main behavior
- Date: 2026-08-20
- Figma file: `SBpgot7uTvMxEaxUwvoc0S`
- Figma frames: `308:2` (desktop), `309:2` (mobile), `309:50` (evidence boundary), `310:2` (selected event)

## Context

Project evidence existed as post-level hints, but a buyer could not select one
exact authorized project and follow its visible chronology. A fuzzy project
search would create false joins, while a post-only view hides repeated
responsibility, event, and related-lineage evidence. The feature must remain
source-grounded: a semantic mention is an inferred candidate, a source field
is an observed hint, and a lineage edge is related history rather than proof of
causation.

## Decision

Add a bounded project index and project-history read model behind the existing
`post_read` RBAC and source-eligibility plus public/same-corporate-entity ABAC
checks. Normalize exact project identities with the same Unicode-compatible
key on both reads. Apply the knowledge cutoff before selecting event IDs, then
constrain matches, roles, and lineage paths to that authorized ID set.
The project index first bounds its input to the newest authorized source rows,
marks the response truncated when that bound is reached, and applies a local
five-second PostgreSQL statement timeout. Expression and recency indexes support
the bounded list and exact-detail paths; forward and rollback migrations remain
symmetric. All response clocks use canonical UTC RFC 3339 `Z` serialization.

Expose the read model through the Buyer `Project history` destination and the
post-detail project-evidence card. Both entry points use the same
`ProjectHistoryTimeline`; source-post drill-through returns to the Board while
preserving Project History as the Event Lineage focus. Counts, display names,
responsibility transitions, and related paths are bounded projections, not an
HR ledger or a causal graph.

The UI uses the existing design-token and Storybook component boundary. The
Figma file above is the design source for the desktop, mobile, and evidence
boundary states; no second component-specific token system is introduced.

## Consequences

- Buyers can move from an exact project identity to authorized chronology and
  source evidence in one workflow.
- Hidden or post-cutoff records cannot affect the index, counts, transitions,
  or related paths.
- Semantic project mentions remain visibly inferred and do not overwrite a
  source project identity.
- The current document-time fallback remains explicit until a durable event
  clock is introduced.
- The project chooser is a bounded recent-project view, not an unbounded catalog
  export; buyers are told when its source or display limit is reached.
- A future customer-master graph may reuse the projection pattern, but this
  ADR deliberately does not invent organization roles or temporal facts that
  are absent from persisted evidence.

## Verification

- `tests/test_project_history.py` covers exact normalization, lifecycle
  classification, responsibility evidence, and bounded index SQL.
- `backend/tests/test_api.py` covers live PostgreSQL/API index and history
  reads, cutoff propagation, source/semantic project evidence, and malformed
  project/focus inputs.
- Frontend tests, lint, production build, and Storybook cover the shared
  destination, post-detail entry point, and keyboard-accessible timeline.

## References

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2021). *WAI-ARIA Authoring Practices 1.2*.
https://www.w3.org/WAI/ARIA/apg/
