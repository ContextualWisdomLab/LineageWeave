# ADR 0104: Retain valid partial visual regions and parent evidence

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0067](0067-visual-region-vision-agent.md), [0091](0091-visual-region-embedding-persistence.md)

## Context

The visual locator asks for complete image coverage, but a vision provider may
return only valid salient panels. Replacing those panels with one full-image
region discards the coordinates needed to search and explain the panel. Using
only the panels would instead lose text outside them.

## Decision

- Keep every valid, bounded locator region even when the collection does not
  cover the full image.
- Describe each retained region independently and persist its coordinates and
  status as before.
- For a partial collection, also describe the original parent image once so
  uncovered content remains searchable in the parent image unit.
- If the parent call fails but at least one region succeeds, retain the merged
  successful region evidence; if both fail, preserve the existing failed state.
- An empty or invalid locator response still falls back to one parent-sized
  region, preserving the previous unavailable/whole-image behavior.

## Consequences

Buyer search can open a specific visual panel without sacrificing OCR and
caption evidence from the rest of the image. Partial locator responses cost
one additional parent-image VISION call, which is intentional because
evidence completeness is more important than latency.

## References

World Wide Web Consortium. (n.d.). *Web Content Accessibility Guidelines
(WCAG) 2.2*. W3C. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (n.d.). *HTML Living Standard: The `img` element*.
WHATWG. https://html.spec.whatwg.org/multipage/embedded-content.html#the-img-element
