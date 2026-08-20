# ADR 0091: Persist embeddings for visual-region semantic units

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0062](0062-semantic-unit-embedding.md), [0067](0067-visual-region-vision-agent.md), [0084](0084-lineage-research-grounding.md)

## Context

ADR 0067 requires each accepted visual region to remain an independently
searchable semantic unit. The implementation persisted each region's OCR,
caption, tags, normalized coordinates, and status, but only embedded the
parent image unit after merging all region descriptions. That loses the
region-level retrieval boundary required by ADR 0062 and makes an image hit
impossible to attribute to the panel that supplied it.

## Decision

- Keep the parent DOM image unit and its aggregate description and embedding.
- For every successfully described region, render only that region's OCR and
  caption as its own embedding input.
- Store region vectors in dedicated third-normal-form tables keyed by
  `post_content_image_region_id` and `embedding_model_code`; do not overload
  the parent `post_content_unit` key or encode a region in an artificial unit
  index.
- Persist no vector for unavailable, failed, malformed, or provider-aborted
  region evidence. The existing source and processing outcome remain retryable.
- Continue sending all embedding requests through contextual-orchestrator;
  this ADR adds storage and provenance, not a local provider or model choice.

## Consequences

- Semantic search can distinguish an image-level hit from a specific visual
  panel while retaining the parent image as context.
- Region embedding storage grows with successful regions, bounded by the
  existing VISION region cap and embedding batch limits.
- Existing parent-image queries remain compatible; consumers that need panel
  attribution can join the region tables by their normalized coordinates.
