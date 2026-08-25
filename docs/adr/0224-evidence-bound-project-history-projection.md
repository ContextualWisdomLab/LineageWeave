# ADR 0224: Evidence-bound project history projection

- Status: Accepted
- Date: 2026-08-26
- Issues: #280, #284
- Figma file ID: `SBpgot7uTvMxEaxUwvoc0S`

## Context

The PRD requires an operations analyst to find a project and inspect cited
evidence. Project evidence already exists in normalized `source_post`,
`post_project_mention`, `post_summary_role`, and `post_lineage_edge` rows. A
second project-history ledger would duplicate truth. Free-text lifecycle
classification would also turn words into unsupported business facts.

## Decision

`GET /api/projects/{project_key}/history` returns a read-only projection over
those existing rows. RBAC, corporate-entity scope, process-unit scope, source
eligibility, and knowledge cutoff are applied before child evidence is read.
Project identity uses exact NFKC-normalized source or semantic evidence; no
fuzzy match is allowed.

The existing post-detail popup hosts the shared timeline; there is no new
navigation destination. Controlled VOC codes may label VOC evidence. Other
records remain `source_recorded`; source stage and detail-state codes are shown
without inferred lifecycle meaning. Adjacent responsibility rows describe
document evidence only. Persisted Event Lineage paths are labelled related and
non-causal. Dates disclose that `source_post.created_at` is the fallback clock.

The projection is bounded and declares truncation. A missing or unauthorized
project is indistinguishable as HTTP 404. The Figma identifier records the
design authority; Storybook remains the executable state inventory.

## Consequences

- Users can move from one permitted post to project-wide evidence without a
  duplicate store or invented handover interval.
- Issue #280 is satisfied only after protected-main API, UI, Storybook, and
  screenshot evidence exists.
- Issue #284 remains open until an owned source adapter supplies authoritative,
  versioned lifecycle events and idempotent reconciliation. This projection
  must not impersonate that future write boundary.

## References

W3C. (2013). *PROV-O: The PROV ontology*. World Wide Web Consortium.
https://www.w3.org/TR/2013/REC-prov-o-20130430/

W3C. (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*. World Wide Web
Consortium. https://www.w3.org/TR/WCAG22/
