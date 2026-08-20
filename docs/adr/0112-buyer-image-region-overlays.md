# ADR 0112: Overlay persisted visual-region boxes on the source image

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0067](0067-visual-region-vision-agent.md), [0091](0091-visual-region-embedding-persistence.md), [0110](0110-buyer-image-evidence-rendering.md)

## Context

ADR 0067 and ADR 0091 persist parent-relative `x_ratio`, `y_ratio`,
`width_ratio`, and `height_ratio` for each accepted visual region. ADR 0110
renders captions, OCR, tags, and a region list, but the buyer still cannot
see which panel of the source image supplied that evidence.

## Decision

- When the source image can be reattached and a region has a finite persisted
  box inside the unit square, draw that box on the figure as a
  keyboard-focusable control. Selecting it announces the persisted caption or
  OCR as the current image region.
- Never invent coordinates. Invalid, missing, non-finite, zero-area, or
  out-of-bounds boxes stay list-only. When the source image cannot be
  reattached, keep the region list and do not draw empty overlays.
- Do not surface LLM instructions from image `unit_text`. Overlay labels come
  only from persisted region caption or extracted text.
- Translate overlay and current-region labels through the five-locale UI
  catalog.

## Consequences

Buyers can locate panel-level evidence on the source image. Search and
embedding remain bound to the existing region tables. A missing bitmap still
fails closed to the list rather than fabricating a locator.
