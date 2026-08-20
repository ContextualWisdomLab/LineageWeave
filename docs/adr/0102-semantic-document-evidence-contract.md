# ADR 0102 — Preserve semantic document evidence across source and buyer views

**Decision status:** Proposed on the stacked product-gap branch  
**Date:** 2026-08-20  
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`  
**Related baseline:** [Product and Technical Gap Baseline](../product-technical-gap-baseline.md)

## Context

Live aggregate inspection identified recurring buyer-visible loss at the
source boundary: superscript footnotes, nested list order/depth, table rows,
and Markdown tables were not represented consistently between Python
ingestion, PostgreSQL units, and the React popup. A flattened string cannot
reconstruct a table row, a branch in a list, or the position of an image. It
also makes a later LLM summary less auditable.

The HTML Living Standard defines the semantic elements used by the source
boundary, including `ol`, `li`, `table`, `tr`, and `sup`. CommonMark provides a
versioned baseline for Markdown block parsing; table syntax remains an
extension in many Markdown dialects, so the implementation accepts only a
recognizable header/separator/data shape and otherwise preserves plain text.

## Decision

1. Parse source content into ordered semantic units before embedding or
   summarization. A unit retains its source label, source order, indentation
   metadata, and image position.
2. Group HTML and OOXML table cells into row units. Markdown tables are
   recognized only when a header row is immediately followed by a separator
   row; the separator itself is not evidence content.
3. Treat explicit CSS/OOXML indentation as authoritative. List-container
   nesting contributes structural depth but must not double-count an explicit
   source width.
4. Mark a numeric footnote only when the source uses a numeric `sup` marker;
   a numeric table cell or ordinary numbered text is not a footnote by itself.
5. Keep the frontend's raw-source fallback aligned with the persisted unit
   labels. Persisted row units render as accessible tables; unresolved
   structure remains visibly unresolved and actionable.

## Rejected alternatives

- Flattening all bodies into one embedding string: loses row, list, and image
  boundaries and cannot be repaired at display time.
- Treating every leading number as a footnote: mislabels table rows and
  numbered instructions.
- Calling a provider directly from the parser: violates the orchestrator
  trust boundary and makes evidence/cost lineage incomplete.
- Creating a separate parsing service: the existing shared chunker and
  persistence boundary are sufficient; Ponytail favors the smaller change.

## Consequences

- Search and summaries receive smaller, meaningful units without exposing raw
  markup or image base64.
- The database keeps the existing normalized unit tables; this decision adds
  no denormalized JSON field or new service.
- Markdown dialects outside the narrow recognized shape remain plain text and
  are reported as a future parser extension rather than guessed.

## Verification

The baseline's synthetic tests cover numeric superscript footnotes, marker
footnotes, nested `ol`/`ul`/`oi` order and depth, HTML/OOXML rows, Markdown
rows, React table rendering, and unresolved indentation. Full CI remains the
release gate.
