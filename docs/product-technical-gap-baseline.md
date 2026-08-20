# Product and Technical Gap Baseline

**Status:** active delivery baseline  
**Owner boundary:** LineageWeave source ingestion, evidence projection, and buyer popup  
**Design boundary:** Figma file `1Su3lDRmiZdcUs47t1QwIX` (see [ADR 0002](adr/0002-figma-access-boundary.md))  
**Data rule:** this document uses synthetic case labels only; production post identifiers, names, bodies, and screenshots never enter the repository.

## Buyer outcome

When a buyer opens a source record, the product must preserve the meaning that
was visible in the source: document order, table rows, list depth, footnotes,
image regions, named actors, project boundaries, time/place/method/reason, and
the next person or team action. Every displayed fact must link back to a
persisted source unit or an explicitly unavailable channel. The UI must never
turn missing evidence into a confident negative or an invented actor.

## Current gap register

| Gap | Buyer-visible failure | Durable contract | Verification |
| --- | --- | --- | --- |
| `structure-footnote` | Superscript or marker footnotes look like ordinary body text. | A footnote keeps its source unit and `footnote` label; numeric superscripts are accepted only when the source marks them as superscript. | Synthetic HTML tests cover `*`, `†`, `‡`, and numeric `<sup>` markers. |
| `structure-list-depth` | Nested `li`/exporter `oi` items are flattened or appear in reverse order. | Parent items precede children; list depth remains explicit metadata and is never inferred from unrelated whitespace. | Synthetic nested `ol`/`ul`/`oi` tests cover order and depth. |
| `structure-table-rows` | HTML/OOXML tables lose row and cell relationships. | One persisted unit represents one row, with cells joined by a stable delimiter and a source label. | Synthetic HTML and Word-table tests cover headers, data rows, and nested cell blocks. |
| `structure-markdown-table` | A Markdown table becomes one flattened paragraph in the API or popup. | A CommonMark-style header/separator/data block becomes row units and renders as a table in the buyer surface. | Python normalization, persistence contract, React render, and Storybook checks cover a synthetic table. |
| `structure-explicit-indent` | CSS/OOXML indentation is displayed at the wrong level. | Explicit source width is authoritative; list-container depth is structural and does not double-count explicit width. | CSS shorthand, OOXML, nested list, and unresolved-structure tests. |
| `semantic-project-boundary` | Events from distinct projects or matters are blended into one narrative. | Each event, project mention, and evidence phrase carries a stable project/matter boundary; ambiguous candidates remain below grouping threshold. | Multi-matter synthetic summary contract and persistence tests. |
| `semantic-actor-identity` | A company factory is mislabeled as a partner/supplier, or a group of PMs is shown without names and affiliations. | Actor type, stated affiliation, requester, and processor remain separate source-grounded fields; no organization relationship is inferred without evidence. | Parser rejection tests, role catalog foreign-key tests, and ambiguous-relationship tests. |
| `semantic-five-w-one-h` | `when`, `where`, `why`, or `how` disappears from the summary. | Each supported slot stores value plus evidence; absent slots expose a next action rather than a placeholder fact. | Slot parser, API contract, and buyer popup tests cover present, absent, and conflicting evidence. |
| `vision-region-evidence` | Image tables receive generic OCR and only a partial visual region is described. | Region discovery covers the full image, persists coordinates, OCR, caption, tags, and independent embeddings through contextual-orchestrator. | Synthetic multi-region image client tests cover full coverage, table-like regions, failures, and document order. |
| `lineage-dag` | Related records exist but the buyer cannot see the branch history. | The focused post subgraph is rendered as a source-order DAG with branch points and clickable nodes; unrelated project groups are excluded. | Layout unit tests, browser interaction tests, and Storybook inventory checks. |

## Implementation order

1. **Source structure:** finish the shared Python/TypeScript semantic-unit
   contract for footnotes, lists, HTML/OOXML rows, and Markdown rows.
2. **Evidence persistence:** ensure the queue considers structure, unit
   embeddings, image-region descriptions, and region embeddings complete as a
   single invariant; retry only bounded, changed, or incomplete work.
3. **Semantic extraction:** keep contextual-orchestrator as the only LLM/VISION
   boundary, and persist project, actor, requester, processor, and 5W1H
   evidence in normalized relations.
4. **Buyer surface:** render tables, footnotes, image evidence, focused DAG
   branches, and actionable empty states with shared design tokens and
   Storybook coverage.
5. **Release gate:** run the complete backend, PostgreSQL, frontend, Storybook,
   security, coverage, and protected-merge checks. Version and changelog
   changes are made only after the current protected head has formal review and
   terminal required checks.

## Evidence and safety rules

- Synthetic fixtures are the only committed test data. Live validation returns
  aggregate counts and status codes, never source text or identifiable names.
- Missing provider channels remain unavailable. They do not produce zero
  vectors, guessed roles, generic captions, or fabricated 5W1H values.
- Provider credentials and model selection remain in contextual-orchestrator;
  this repository never calls a provider API directly.
- A relationship involving the organization's own factory is not classified
  from a job title or catalog hint alone. The source must state the relation or
  the result remains unresolved.
- Structural rendering is additive: the raw source remains available so a
  buyer can compare the derived view with the original evidence.

## Definition of done

A gap is closed only when its synthetic behavior test fails before the change,
passes after the change, its persistence/API contract is covered where
applicable, the buyer action is visible in frontend tests and Storybook, and
the corresponding ADR and APA 7 references are updated. A green local test is
not a protected merge, release, or production-data success claim.

## References

See [ADR 0101](adr/0101-semantic-document-evidence-contract.md) and
[`docs/doctoring/PRODUCT_TECHNICAL_GAP_REFERENCES.md`](doctoring/PRODUCT_TECHNICAL_GAP_REFERENCES.md)
for the normative standards boundary.
