# ADR 0067: Decompose embedded images into visual regions through the orchestrator

- Status: Accepted
- Date: 2026-08-19
- Depends on: ADR 0062, ADR 0066

## Context

DOM parsing identifies the position of an embedded `<img>`, but a single
image can itself be a pasted email, table, drawing, or multi-panel screenshot.
Sending that bitmap once to a vision model loses region-level searchable
evidence and makes it impossible to tell which panel supplied an OCR match.

## Decision

Image processing has two levels:

1. The existing DOM chunker remains the outer document unit and preserves the
   image's position among paragraphs.
2. A `VisionRegionAgent` uses the configured contextual-orchestrator VISION
   model to return bounded visual regions as normalized coordinates. The
   application crops those regions with Pillow, sends each crop through the
   same orchestrator, and stores one OCR/caption/tag result per region.

The agent is not a direct provider call and it is not allowed to invent a
region when the VISION channel is unavailable. Invalid boxes, overlapping
duplicates, and provider failures are recorded as processing outcomes rather
than converted into fabricated descriptions. Region evidence must retain the
parent image, region order, normalized box, model, and processing status.

Region text is an additional semantic unit under ADR 0062. The buyer view
shows only persisted OCR/caption evidence; it must never show an internal
instruction such as “extract Keyman” as source-post content. Existing posts
are reprocessed only by an explicit operator backfill with selected post IDs;
the buyer read path never starts an unbounded VISION job.

The locator contract does not carry an authoritative assertion that a set of
boxes exhausts the source image. LineageWeave therefore requests parent-image
evidence whenever it accepts any proper subregion, even when the returned
rectangles appear to tile the normalized plane. It does not estimate coverage
from sampled points or implement rectangle-union arithmetic locally. A single
explicit `(0, 0, 1, 1)` locator result is treated as the parent image rather
than persisted as a decomposed region.

## Consequences

- Search can attribute a hit to a document image and a specific visual panel.
- A region locator call plus one call per accepted crop costs more than a
  whole-image call; the implementation must cap regions and keep the parent
  image fallback for provider failures.
- The normalized region tables and embedding linkage are written by the same
  persistence transaction used during import and by the selected-post
  backfill command. A provider failure leaves the post eligible for retry and
  is never presented as successful image evidence.
