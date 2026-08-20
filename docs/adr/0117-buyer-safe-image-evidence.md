# ADR 0117: Keep Internal Image Instructions Out of Buyer Evidence

## Status

Accepted

## Context

VISION analysis may receive or inherit an internal instruction such as
`This post is an image. Ask questions to read its text.` or its Korean
equivalent. That text is an agent instruction, not a caption describing the
source image. Persisted legacy content can still contain it even after the
prompt is corrected.

## Decision

At the image and visual-region evidence boundary, normalize captions and suppress captions that
match the known internal instruction forms. Apply the same rule when creating
LLM/embedding placeholders and when rendering the buyer-facing post body.
Retain the original image, OCR text, tags, region coordinates, and provenance;
only the non-evidence caption is removed. If no useful caption remains, show
the image and available evidence without inventing a description.

## Consequences

- Buyer screens cannot expose the analysis agent's instruction as post content.
- Existing persisted image rows are safe immediately; re-ingestion is not
  required merely to hide the legacy caption.
- OCR, region evidence, and semantic search remain available.
- New provider-specific instruction variants require an explicit, reviewed
  pattern and a regression test rather than a broad caption guess.
