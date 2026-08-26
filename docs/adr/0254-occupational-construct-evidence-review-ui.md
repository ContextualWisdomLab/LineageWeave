# ADR 0254: Occupational construct evidence review UI

**Status:** Accepted
**Date:** 2026-08-27
**Extends:** [ADR 0118](0118-uiux-standard-guide-v3-design-overhaul.md), [ADR 0248](0248-occupational-construct-evidence-boundary.md), [ADR 0253](0253-catalog-bound-occupational-construct-extraction.md)

## Context

ADR 0253 produces reviewable evidence, but the Post-detail API did not say
whether an empty assertion list meant a completed negative result, active
processing, or unavailable analysis. Rendering all three as blank would fake
product readiness. This is an extension of the existing Post-detail evidence
hierarchy, not a new navigation flow or visual identity, so no Figma file is
needed and no Figma file ID exists for this decision. Public UIZZE search
returned no specific evidence-review reference; repository evidence therefore
remains the declared design source.

## Design contract and decision

| Field | Decision |
|---|---|
| Screen job | Review what work construct the record supports and the exact words supporting it |
| Primary user and action | Evidence reviewer opens the official catalog definition after checking the cited span |
| Content hierarchy | Construct label/family, verbatim evidence, catalog action, then provenance details |
| Navigation and controls | Stay in Post detail; use a real external definition link and native `details` disclosure |
| Visual language | Reuse `popup-section`, `post-evidence-list`, `post-badge`, and `semantic-provenance`; no new surface or decorative card |
| Required states | Complete with evidence, complete empty, processing, unavailable, historical-cutoff unavailable |
| Responsive behavior | Text wraps in the existing responsive popup; the link and native disclosure remain keyboard/touch operable |
| Evidence used | Existing Project evidence and EvidenceStatusMark patterns; WCAG 2.2 and Storybook inventory |
| Forbidden defaults | No confidence score, person trait, internal method name, generic dashboard card, icon-only status, or inert control |
| Acceptance criteria | Exact evidence and official IRI are visible; inference has text/non-color status; empty states prescribe the next action; all five locales agree |

The API returns `occupational_construct_evidence_status` as `complete`,
`processing`, or `unavailable` by comparing the durable extraction run with
the current content-job digest. Authorization occurs before this status query.
The UI never exposes internal extraction methods or treats inference as fact.
Because assertions have no revision-validity interval, an `as_of` Post read
returns no live assertion and explicitly directs the reviewer to the
cutoff-known body.

## Verification

- Component tests cover exact links/evidence, hidden internal method names,
  localized next actions, and all empty states.
- Storybook covers populated, supported-empty, processing, unavailable, and
  narrow scenes.
- Desktop and mobile screenshots are required before protected delivery.
