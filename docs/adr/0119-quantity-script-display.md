# ADR 0119: Render quantity superscripts as text runs, Unicode in units

- Status: Accepted
- Date: 2026-08-22
- Depends on: [0061](0061-post-body-character-reference-decoding.md), [0062](0062-semantic-unit-embedding.md), [0102](0102-semantic-source-unit-boundaries.md)

## Context

Imported posts write cubic metres and similar quantities as HTML
`<sup>`/`<sub>` or as caret exponents (`m^3`). The display path converted
`<sup>` into a caret and then rendered the paragraph as a React text node,
so buyers saw `m^3` instead of a superscript. The DOM chunker dropped the
tags entirely, so embeddings received concatenated `m3`, which is a
different quantity. Comparison operators such as `qty < 50` must remain
plain text, and a leading footnote caret (`^1 …`) is not a unit exponent.

## Decision

- Preserve the source body. Derived semantic text maps HTML `<sup>`/`<sub>`
  and quantity caret exponents onto Unicode Super/Subscript characters
  (The Unicode Consortium, 2024, §22.4) so search and embeddings can tell
  `m³` from `m3` without keeping markup in the unit (Cai, Yu, Wen, & Ma,
  2003).
- The buyer post view splits those Unicode (or leftover caret) runs and
  renders them as React `<sup>`/`<sub>` elements. The body is never
  assigned to `innerHTML` (ADR 0061).
- Only a letter, digit, or closing `)` immediately followed by `^` and a
  short numeric/`n` exponent is treated as a quantity. A leading `^1`
  footnote marker and comparison operators stay literal.
- Unmapped script runs keep a caret or underscore so they remain visible
  rather than silently concatenating. Full formula ontology remains out of
  scope; this decision covers quantity display and unit-level text.

## Consequences

- The post popup shows `12 m³` and `H₂O` as superscripts and subscripts.
- Newly persisted `post_content_unit` text stores Unicode quantities, so
  later retrieval does not depend on HTML surviving the chunker.
- Existing concatenated `m3` units stay until re-ingestion; caret-form
  units still render through the display splitter.

## References

Cai, D., Yu, S., Wen, J.-R., & Ma, W.-Y. (2003). *VIPS: A vision-based
page segmentation algorithm* (Microsoft Research Technical Report
MSR-TR-2003-79). Microsoft Research.

International Organization for Standardization. (2022). *Quantities and
units — Part 1: General* (ISO 80000-1:2022).

The Unicode Consortium. (2024). *The Unicode Standard* (Version 16.0.0).
https://www.unicode.org/versions/Unicode16.0.0/

WHATWG. (n.d.). *HTML living standard: The `sub` and `sup` elements*.
https://html.spec.whatwg.org/multipage/text-level-semantics.html#the-sub-and-sup-elements
