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

The contextual-orchestrator VISION boundary receives one structured
`json_object` request per DOM image. The prompt defines the response shape:
whole-image text, caption, tags, and up to twelve normalized regions with
  their own text, caption, and tags. The parser accepts the gateway's
  equivalent `description`/`region` aliases and treats null regions as no
  region evidence. LineageWeave persists the response into
the existing image and image-region tables. The request uses `mode=auto` and
`reasoning_effort=auto`; it does not select a provider model or force a
sampling temperature. Direct provider calls and monkey patches remain
forbidden.

The orchestrator still supports and tests `json_schema` for structured
workflows. The multimodal VISION path deliberately uses `json_object` because
the configured provider's real image request timed out on the schema contract
while the equivalent object contract completed. This is a provider-shaped
boundary decision, not a removal of orchestrator schema support.

The legacy locate-then-describe path remains as a compatibility fallback for
test doubles and clients that do not implement the structured method.

## Consequences

- One image has one orchestrated VISION request instead of a serial region
  fan-out, while region-level evidence remains queryable.
- The parser boundary enforces the documented JSON object shape without
  claiming provider schema support that the live multimodal path does not
  currently satisfy.
- Provider capability and reasoning policy remain centralized in
  contextual-orchestrator.
- A provider that cannot produce the structured response falls back to the
  existing whole-image description path; it does not fabricate regions.
