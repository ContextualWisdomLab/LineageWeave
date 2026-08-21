# ADR 0108: Preserve authored semantic source-unit boundaries

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0062](0062-semantic-unit-embedding.md), [0084](0084-lineage-research-grounding.md), [0091](0091-visual-region-embedding-persistence.md)

## Context

Some imported posts use real HTML/OOXML list containers, while others arrive
as markup-free text with blank paragraphs, numbered items, or Markdown tables.
The previous path persisted a single plain-text unit when no DOM block existed,
so the buyer view could not reproduce paragraph boundaries and semantic search
could not attribute a table row or list item. CSS, `&nbsp;`, and WordprocessingML
indentation remain evidence, but presentation-only continuation-line alignment
must not become embedding text.

## Decision

- Treat `ol`/`ul` container depth as explicit indentation and persist `li` as
  its own DOM semantic unit.
- Preserve semantic footnote labels from HTML/Word markers such as
  `role="doc-footnote"`, footnote containers, `MsoFootnoteText`, and Word
  footnote-definition backlink pairs; a footnote remains a searchable unit,
  not a list item inferred only from its leading glyph. A body citation must
  remain part of its enclosing body paragraph.
- For markup-free input, split at authored blank paragraphs and list markers;
  continuation lines remain in the preceding item after visual alignment is
  removed.
- Recognize consecutive Markdown table rows only when they contain at least
  two cells, discard the delimiter row, and persist each data row with
  `unit_label = 'tr'` and `cell | cell` text.
- The API response's persisted units are authoritative for buyer rendering.
  The frontend may use source-derived indentation or footnote markers only
  when the persisted structure source is unresolved; an LLM structure decision
  remains authoritative when present.
- All derived units continue through the existing contextual-orchestrator
  embedding boundary. The original body remains unchanged for provenance and
  retry.

## Consequences

Paragraphs, lists, and table rows can be rendered and searched as distinct
meaning-bearing units without a second parser in the API. Existing HTML, CSS,
`&nbsp;`, and OOXML evidence remains available, while manual line alignment is
removed only from derived semantic text.

## Evidence boundary

This decision does not infer nesting from a marker alone. A plain `1.`, `2)` or
`-` marker without source whitespace, DOM nesting, declared formatting, or an
orchestrator decision remains level zero.
