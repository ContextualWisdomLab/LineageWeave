# ADR 0122: Preserve explicit metric scripts in semantic text

**Status:** Accepted on this PR; not protected-main truth  
**Date:** 2026-08-21  
**Owners:** LineageWeave ingestion and buyer-surface maintainers

## Context

Source posts commonly encode a unit such as `m<sup>3</sup>`, `m<sub>3</sub>`,
`m^3`, or `m_3` with HTML or plain-text notation. Dropping the markup changes
the searchable meaning to `m3`, while treating every numeric `sup` element as
mathematics would break the existing numeric-footnote contract. Full MathML
parsing is not yet justified by the current product surface, but the loss of
explicit unit scripts is a buyer-visible defect.

MathML 4 defines `msup`, `msub`, and `msubsup` as structural script elements;
HTML `sup`/`sub` are a permitted lighter-weight notation when detailed
mathematical markup is not required. This decision therefore adds a bounded
normalization boundary and keeps the source representation unchanged.

## Decision

1. Preserve the immutable source body exactly as imported.
2. In derived semantic text only, normalize an explicitly bounded metric base
   (`m`, `cm`, `mm`, `km`, or `kg`, optionally preceded by a number) followed
   by numeric `sup`/`sub` markup or plain-text `^`/`_` notation into Unicode
   superscript/subscript digits. For example, `5m<sup>3</sup>` and `5m^3`
   become `5m³`, while `m<sub>3</sub>` and `m_3` become `m₃`.
3. Keep ordinary numeric superscripts and caret expressions on prose under the existing footnote
   role contract. Do not infer a mathematical formula from an arbitrary word.
4. Apply the same bounded normalization in backend semantic chunks and the
   React buyer display so search text and visible text agree.
5. Defer full MathML/LaTeX parsing, expression trees, and ontology term
   creation until an authorized fixture demonstrates a need beyond metric
   scripts. Any such change requires a new ADR and parser contract.

## Consequences

- Search and the buyer popup retain the visible distinction between `m³` and
  `m3` without exposing source HTML to the embedding model.
- Existing numeric-footnote tests remain unchanged because the bounded metric
  pattern is the only new conversion.
- The current implementation does not claim to understand arbitrary equations;
  unsupported script markup remains ordinary source text and must not be
  presented as a parsed ontology expression.

## References (APA 7th)

World Wide Web Consortium. (2026). *Mathematical Markup Language (MathML)
Version 4.0* (W3C Recommendation). https://www.w3.org/TR/mathml4/
