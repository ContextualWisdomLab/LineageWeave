# ADR 0116: Serialize VISION analysis within one post

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0067](0067-visual-region-vision-agent.md), [0077](0077-single-call-structured-vision-evidence.md), [0079](0079-orchestrator-owns-default-reasoning-effort.md)
- Figma: N/A (backend processing contract)

## Context

The image-region contract requires one locator request and one contextual-
orchestrator VISION request per accepted crop. The implementation previously
used a pool for image chunks and another pool for regions inside each image.
That allowed one post to issue dozens of simultaneous requests through the
same orchestrator session. A bounded private run persisted descriptions for
all five images in an inspected post, but only 8 of 31 regions were described;
23 were recorded as failed. A single stored crop processed serially through
the same VISION boundary and returned OCR and a caption within a bounded
diagnostic timeout.

## Decision

Process a post's image chunks and each image's visual regions in document order
on the caller's thread. Keep the existing normalized-region limit, crop
conversion, per-region failure evidence, parent-image fallback, and
`mode=auto`/`reasoning_effort=auto` orchestrator contract. Do not select a
provider model or add a local retry pool.

The post's existing LLM metadata context remains active for every sequential
request, so all VISION and embedding work for the post continues to share its
orchestrator session id. Any future concurrency must be introduced only after
measured orchestrator capacity and a new ADR.

## Consequences

- Region evidence is slower but avoids nested gateway overload and preserves
  the accuracy-first requirement for real posts.
- A single failed region remains a failed region; it is not silently replaced
  by invented text or coordinates.
- The buyer API continues to expose only persisted captions, OCR, tags, and
  region evidence; no internal VISION instruction is rendered.
