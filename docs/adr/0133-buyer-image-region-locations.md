# ADR 0133: Show persisted image-region locations to buyers

- Status: Accepted
- Date: 2026-08-22
- Depends on: [0067](0067-visual-region-vision-agent.md), [0091](0091-visual-region-embedding-persistence.md), [0110](0110-buyer-image-evidence-rendering.md)

## Context

Normalized visual-region coordinates (`x_ratio`, `y_ratio`, `width_ratio`,
`height_ratio`) already persist beside captions, OCR, and tags. The buyer
popup listed those regions as unlabeled evidence, so an operator could not
tell where on the source image a caption or OCR excerpt came from. Cai, Yu,
Wen, and Ma (2003) treat a visual block's bounding box as first-class
evidence; hiding the box after extraction made the stored coordinates
unusable at the product boundary.

Stacked PR work already rendered these locations on a non-main branch. This
record lands the same buyer action on protected `main` without mixing into
unrelated stacks.

## Decision

- Render each persisted region's axis-aligned box as a percent range next to
  its caption or OCR excerpt: `Region location: left%, top% – right%, bottom%`.
- Translate the label through the five-locale UI catalog.
- Omit the location row when any coordinate is non-finite. Do not invent a
  box, a pixel overlay, or an internal LLM instruction.
- Keep image tags, OCR tables, and the source raster on their existing
  contracts. This is a presentation boundary, not a new VISION call.

## Consequences

After opening a post whose image analysis produced regions, a buyer can read
where each caption or OCR excerpt sits. Internal prompts such as `This post
is an image` remain hidden. Complete overlay rendering and authorized-corpus
quality remain later slices.

## References

Cai, D., Yu, S., Wen, J.-R., & Ma, W.-Y. (2003). *VIPS: A vision-based page
segmentation algorithm* (Microsoft Research Technical Report MSR-TR-2003-79).
Microsoft Research. https://www.microsoft.com/en-us/research/publication/vips-a-vision-based-page-segmentation-algorithm/
