# ADR 0105: Source-only whitespace is not authoritative structure

- Status: Accepted
- Date: 2026-08-20
- Depends on: [0073](0073-llm-structure-adjudication.md), [0102](0102-semantic-source-unit-boundaries.md)

## Context

Rich-text exports often contain leading spaces or `&nbsp;` characters that
only preserve an editor's visual alignment. Treating every distinct width as
a nesting level makes unrelated list items appear deeply nested, especially
when an export mixes tabs, non-breaking spaces, and manual alignment. The
result is an authoritative structure decision without structural evidence.

## Decision

`Chunk` retains the total source indentation for diagnostics and fallback
rendering, but exposes declared indentation separately. Only HTML/CSS/OOXML
declarations and nested list-container depth populate declared indentation.
Persistence may mark a unit `explicit` only when declared indentation exists.
Source-only whitespace follows the existing contextual-orchestrator
adjudication path; if that channel is unavailable, it remains `unresolved`
with level zero.

## Consequences

- Visual alignment cannot manufacture hierarchy or distort the buyer view.
- Real CSS, OOXML, and list-container structure remains authoritative.
- Reprocessing with contextual-orchestrator can resolve source-only cases while
  preserving the original body and diagnostic width.

## References

World Wide Web Consortium. (n.d.). *HTML Living Standard: The `ol`, `ul`, and
`li` elements*. WHATWG. https://html.spec.whatwg.org/multipage/grouping-content.html

World Wide Web Consortium. (n.d.). *CSS box model module level 3*. W3C.
https://www.w3.org/TR/css-box-3/
