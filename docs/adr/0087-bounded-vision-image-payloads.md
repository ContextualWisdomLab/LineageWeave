# ADR 0087: Bound VISION Image Payloads

- Status: Accepted
- Date: 2026-08-20

## Context

Real posts contain large JPEG/PNG/TIFF and transparent raster images. The
VISION path already converts unsupported raster formats and composites alpha to
white, but preserving unrestricted dimensions can still produce provider
payloads that fail or stall. A failed image must remain an explicit failed
evidence row and must not prevent other post units from being persisted.

## Decision

Before a VISION request, raster images are EXIF-corrected, alpha-composited to
white, and bounded to a maximum edge of 4096 pixels. PNG is preferred with
maximum compression. If the opaque PNG exceeds 8 MiB, the image is encoded as a
bounded opaque JPEG, reducing quality and then dimensions until the payload is
within the same limit.

The DOM/image-region decomposition remains unchanged. Cropped regions continue
to use opaque PNG because they are already bounded by their region dimensions.

## Consequences

- Unsupported raster formats and transparent PNGs remain usable by VISION.
- Oversized real images no longer send unbounded payloads to the orchestrator.
- Large photographic images may use JPEG and lose some lossless detail; OCR and
  semantic description are prioritized over byte-for-byte image fidelity.
- Original source HTML and raw image bytes remain preserved in `source_post`.
