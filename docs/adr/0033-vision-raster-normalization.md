# ADR 0033: Normalize raster input before orchestrated Vision calls

Status: accepted

## Context

Source posts can contain raster images whose file extension or declared MIME
type is not accepted by the configured Vision model. Transparent pixels also
have model-dependent semantics: sending an alpha channel can make a white
page appear checkerboarded or otherwise change OCR and captioning results.

## Decision

1. Every production Vision request is built by
   `orchestrator_vision_client`, using the configured contextual-orchestrator
   gateway rather than a provider endpoint called directly by this repo.
2. `normalize_vision_image` decodes the raster bytes, applies EXIF orientation,
   composites RGBA pixels onto an opaque white background, and emits
   `image/png` bytes for the Vision request.
3. An unsupported or invalid raster raises a validation error. The ingestion
   path must not replace a failed Vision call with invented OCR, captions, or
   tags; the image channel remains unavailable or fails explicitly according
   to its caller's transaction contract.
4. The normalized bytes are request input only. PostgreSQL remains the source
   of persisted post-content units and their extracted artifacts.

## Consequences

- OCR and captioning receive one stable, opaque PNG representation regardless
  of the source raster format or alpha channel.
- EXIF orientation and alpha flattening add CPU work before the gateway call,
  but avoid provider-specific format and transparency behavior.
- Vector artwork, PDF, animated formats, and corrupt bytes are not silently
  guessed into raster content; a future format-specific converter needs its
  own supported-input contract and tests.

## References

- `lineageweave/vision_image.py`
- `lineageweave/image_content.py`
- `migrations/0026_post_content_artifacts.sql`
