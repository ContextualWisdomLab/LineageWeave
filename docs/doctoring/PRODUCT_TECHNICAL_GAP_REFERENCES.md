# Product technical-gap references

These references are the normative basis for the semantic-unit boundary in
[ADR 0103](../adr/0103-semantic-document-evidence-contract.md). Dates and
versions are recorded so a later standards refresh can be reviewed rather
than silently changing parser behavior.

## APA 7th edition

CommonMark. (2024). *CommonMark spec (Version 0.31.2)*. https://spec.commonmark.org/0.31.2/

WHATWG. (2026). *HTML: Living Standard*. https://html.spec.whatwg.org/multipage/

## Applied mapping

| Source | Boundary used in LineageWeave |
| --- | --- |
| CommonMark (2024) | Recognizable Markdown block/header/separator shape; unrecognized dialects remain source text. |
| WHATWG (2026) | HTML list, table-row, and `sup` semantics; source order and element identity are retained as unit metadata. |

These standards define syntax and semantics, not an LLM extraction license.
Provider-derived summaries, image descriptions, project boundaries, and
5W1H values still require contextual-orchestrator provenance and explicit
source evidence.
