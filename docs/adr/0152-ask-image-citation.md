# ADR 0152: Global Ask cites persisted image evidence, never raw bytes

- Status: Accepted
- Date: 2026-08-22
- Related: [0066](0066-position-preserving-image-content.md), [0039](0039-global-ask-agent-source-boundary.md)

## Context

An Ask answer citing a post whose evidence actually came from an embedded
picture (a screenshot, a diagram) read as an unmarked text claim -- the
reader had no way to tell the citation was image-sourced rather than
drawn from the post's written body. Separately, no code path in this
repository ever sends embedded image bytes to a client: `post_content_image`
persists each image's OCR text, caption, and tags (ADR 0066), and
`GET /api/posts/{id}/content` already returns only that description, never
the image itself. `lineageweave.image_content`'s normalization step
likewise replaces every embedded image with a bracketed text placeholder
before any LLM or API response is built.

## Decision

"Cite images" is satisfied inside that existing, deliberate boundary
rather than by adding a new image-serving mechanism. `cited_post_images`
(`backend/app/post_chat_ingestion.py`) reads `post_content_image`/
`post_content_image_tag` for the already-cited post ids and returns their
persisted `mime_type`, `caption`, `extracted_text`, and `tags` -- the same
fields `GET /api/posts/{id}/content` renders, scoped to citations.
`POST /api/ask` returns this as a new `cited_post_images` field; the
Ask answer view renders an explicit "Image evidence" line per cited post
carrying one.

No additional ABAC check runs inside `cited_post_images`: `cited_post_ids`
only ever contains ids drawn from `gather_global_chat_sources`'s
already-authorized source set -- the same trust boundary
`cited_post_evidence`/`cited_post_summaries` (`lineageweave.post_chat`)
already rely on without re-checking visibility per call.

## Considered alternatives

- Add an endpoint that serves the original image bytes for a citation:
  rejected -- this would be the first place in the codebase raw embedded
  image bytes ever leave the server, reopening a boundary ADR 0066 and
  `lineageweave.image_content`'s normalization step deliberately closed.
  Nothing about "citing" an image requires the pixels themselves; the
  persisted description is the citable claim.
- Fold image evidence into the existing `cited_post_evidence` fact list
  (reusing its `kind`/`text` shape): rejected -- an image's caption and
  its OCR text are two independently useful strings (a diagram's caption
  says what it's a diagram *of*; its OCR says what text appears *in* it),
  which the flat `{kind, text}` shape cannot carry without concatenating
  them into one opaque string.

## Consequences

- A reader can now tell when an Ask citation's evidence came from a
  picture rather than the post's written body, without any new image
  storage or serving surface.
- The response payload grows by one field (`cited_post_images`); existing
  consumers that ignore unknown fields are unaffected.
- Region-level citation (pointing at a specific area of a larger image,
  as `post_content_image_region` already supports for the post-detail
  popup) is not surfaced here -- a future enhancement, not required by
  this decision.
