# ADR 0002 — Figma access boundary for the Phase 4 popup UI

**Decision status:** Accepted
**Date:** 2026-08-13
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Figma File URL:** https://www.figma.com/design/1Su3lDRmiZdcUs47t1QwIX

## Context

Phase 4 asks for the post-detail popup to match a referenced Figma frame:
Korean summary, key events, R&R derivation, an Event Lineage display,
Keyman panels, and an in-popup LLM chat with a sliding-panel evidence
view.

A Figma MCP server with real, already-authenticated read access is
available in this environment. Fetching the referenced file's metadata
(page/frame listing only -- no design content, no screenshot) surfaced
two things that change how this reference can be used:

1. **The file's own cover/index page is the source organization's real,
   confidential internal content** -- it names the organization, and
   cites real production statistics and a real internal system/table
   reference (matching this project's existing "never in a public file"
   banned-string list from earlier milestones' data-boundary work). This
   is not a generic or already-anonymized design reference; it is the
   organization's own private material.
2. **No frame for the popup/Event-Lineage UI exists in the file yet** --
   only the cover/index page was present at the time of this check. The
   9 as-is / 9 to-be screens the cover page's own text describes as
   forthcoming were not found as sibling pages.

## Decision

The Phase 4 popup UI is built from the *textual* frame description
already given in the product brief (Korean summary, key events, R&R,
Event Lineage, Keyman panels, chat with sliding evidence) and standard,
defensible UI conventions for each section -- **not** derived from the
referenced Figma file's actual content. No real organizational detail,
statistic, or internal identifier observed while checking the file's
metadata is repeated anywhere in this repository, in code, in docs, or
in commit history.

The newly created file identified above is the safe design-system boundary
for LineageWeave's buyer surface. It currently contains no copied source
organization content; future token or component work must keep that boundary.

## Rationale

- This repository's oldest and most consistently enforced rule (see
  `AGENTS.md`'s "no real data, ever" section and every prior milestone's
  data-boundary discipline) is that no file identifying the source
  organization, and no real production content, ever lands in this
  public repository. A design reference whose own cover page is the
  organization's real internal material falls squarely inside that rule
  -- structurally mimicking it would risk reintroducing exactly the kind
  of identification this project has otherwise been careful to avoid.
- Separately and independently of the confidentiality question: there is
  currently no actual popup/Event-Lineage frame in the file to build
  against even if that concern didn't apply -- only a cover page exists.
- Guessing a "close enough" layout and *calling it* Figma-matched would
  misrepresent a source that was neither consulted for its content nor
  (yet) contains the relevant screen.

## Consequences

- The popup UI ships and is tested (both backend contract and frontend
  render logic) against the textual spec, not any Figma file content.
- If the organization later adds the actual popup frame to a Figma file
  and wants a real design-to-code pass, that is a distinct, explicit
  follow-up -- likely still needing the same care ADR 0001 already
  established for identity/content (build the *mechanism* faithfully,
  keep any organization-identifying specifics out of the public repo).
- This is consistent with, not an exception to, ADR 0001's reasoning --
  both ADRs name a real gap explicitly rather than fake or stall.

## Related

Builds directly on [ADR 0001](0001-demo-identity-and-data-boundary.md)
and `AGENTS.md`'s "no real data, ever" rule -- the same boundary applied
to a design-reference source discovered mid-session rather than a
data-analysis source.
