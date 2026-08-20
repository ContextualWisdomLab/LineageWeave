# ADR 0061: Decode HTML character references in post-body display

- Status: Accepted
- Date: 2026-08-19

## Context

Imported board posts may contain HTML character references such as `&nbsp;`,
`&amp;`, and numeric references. Rendering the source body as React text is
safe, but showing those references literally makes the post unreadable. The
board and post detail popup share `splitPostBody`, so decoding only one view
would leave inconsistent behavior.

## Decision

`splitPostBody` removes HTML tags, decodes character references with the
browser's native HTML parser for at most three passes, and then normalizes
whitespace. The bounded passes cover source exports that encoded an already
encoded body without allowing malformed input to create an unbounded loop. The
decoded value remains a React text node; the body is never assigned to
`innerHTML` for display. The no-image fallback uses the same cleanup path.

Backend DOM normalization applies the same bounded three-pass decoding after
Python's `HTMLParser` character-reference handling, so LLM and embedding input
does not retain the export artifact either.

## Consequences

- Board cards and post detail display readable text for encoded source bodies.
- Embedded data-URI image extraction and comparison-operator handling remain
  unchanged.
- A literal entity reference authored intentionally is displayed as its decoded
  character, matching normal HTML text semantics.
