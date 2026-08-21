# ADR 0066: Preserve image identity and document position

- Status: Proposed
- Date: 2026-08-19

## Context

An embedded image can contain the only customer, project, or Keyman evidence in
a source post. OCR or caption text stored without its document position loses
the context needed to review where the evidence appeared. Repeated images also
should not be stored as separate byte copies.

## Decision

The proposed persistence contract separates:

- one `source_document` row per source artifact;
- one content-addressed `embedded_image` row per image byte hash;
- many-to-many `image_tag` rows for searchable tags;
- `document_image_position` rows that place each image at its unified DOM
  chunk position among text and image units.

OCR, captions, tags, processing timestamp, and processing model remain
explicitly distinguishable. Vision processing uses contextual-orchestrator and
the existing image normalization contract; an unavailable or failed vision
channel is not converted into fabricated text.

The currently accepted product persistence remains the
`post_content_unit`/`post_content_image`/`post_content_embedding` contract.
The richer `source_document` decomposition is not accepted for migration until
its source-document identity and atomic vision claim/lease behavior are
specified.

## Consequences

- Search results can identify both the matching image and its position in the
  source document.
- Content hashes support idempotent storage, but a separate atomic claim or
  lease is required to prevent duplicate concurrent vision calls.
- The design remains explicitly proposed rather than pretending that the
  future source-document tables already exist in the running product.
