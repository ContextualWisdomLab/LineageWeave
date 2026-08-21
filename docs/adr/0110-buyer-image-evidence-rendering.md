# ADR 0110: Render image evidence as buyer content, not LLM instructions

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0067](0067-visual-region-vision-agent.md), [0091](0091-visual-region-embedding-persistence.md), [0102](0102-semantic-source-unit-boundaries.md)

## Context

Image analysis stores parent-image and region-level OCR, captions, tags, and
normalized coordinates. When the raw image was not available for a later
render, the frontend used the persisted image unit's `unit_text` as a normal
paragraph. That text can be a provider/agent instruction or an embedding
placeholder and is not buyer content.

## Decision

- Render a source image with its accessible caption, OCR, tags, and region
  evidence when the raw data URI is present.
- At the render boundary, accept only canonical base64 data URIs for inert
  raster image media types. Reject external, script, SVG, and malformed
  sources and fall back to persisted caption/OCR/region evidence.
- When the source image cannot be reattached, render only the persisted
  `PostImageContent` evidence in a figure; never render the image unit's
  internal `unit_text` as buyer prose.
- Keep parent and region evidence visibly distinct, and translate the label
  used for image tags through the five-locale UI catalog.
- When OCR preserves a consistent pipe-delimited row structure, render that
  evidence as a buyer-facing HTML table; otherwise keep it as readable text.
- Continue retaining the original source body and normalized image provenance;
  this is a presentation boundary, not evidence deletion.

## Consequences

Buyers see useful image evidence without seeing instructions intended for an
LLM. Search and embedding artifacts remain backed by the existing normalized
parent/region tables and contextual-orchestrator boundary.
