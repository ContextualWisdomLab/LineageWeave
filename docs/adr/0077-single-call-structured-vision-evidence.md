# ADR 0077: Single-call structured VISION evidence per DOM image

- Status: Accepted
- Date: 2026-08-19

## Context

Post content is split into DOM units, and each embedded image must contribute
searchable OCR, a human-readable caption, and meaningful visual regions. The
previous implementation first located regions, then called VISION once per
region, then called VISION again for the whole image. A single post could
therefore perform an unbounded serial sequence of remote calls. Persistence
and embeddings happened only after all of those calls completed, so a slow or
failed run left no content artifact or vector.

## Decision

Each DOM image first crosses the contextual-orchestrator VISION boundary with
one `json_object` region-location request. Accepted normalized regions are
cropped locally, and each crop crosses the same orchestrated `describe`
boundary for OCR, caption, and tags. A single `(0, 0, 1, 1)` response is not a
decomposition and is rejected as locator evidence. If no meaningful region is
returned, the whole image is described once. LineageWeave persists the image
and image-region evidence without inventing coordinates. Every request uses `mode=auto` and
`reasoning_effort=auto`; it does not select a provider model or force a
sampling temperature. Direct provider calls and monkey patches remain
forbidden.

The orchestrator still supports and tests `json_schema` for structured
workflows. The multimodal VISION path deliberately uses `json_object` because
the configured provider's real image request timed out on the schema contract
while the equivalent object contract completed. This is a provider-shaped
boundary decision, not a removal of orchestrator schema support.

## Consequences

- Region-level evidence remains queryable, and a locator failure or a
  single full-image box degrades to whole-image evidence without fabricating a
  full-image region row.
- The parser boundary enforces normalized coordinate bounds and the documented
  JSON object shape without claiming provider schema support that the live
  multimodal path does not currently satisfy.
- Provider capability and reasoning policy remain centralized in
  contextual-orchestrator.
- A provider that cannot produce the structured response falls back to the
  existing whole-image description path; it does not fabricate regions.
