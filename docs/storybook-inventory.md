# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
operator-facing control you can click before changing product CSS.

| Story | Operator next action | Token / module |
|---|---|---|
| `Workspace/OperationsDashboard` | Compare Event and post counts, inspect external-information coverage, then open the cited source behind a claim, handover, repeat issue, or topic-context influence. `TopicInfluenceAccepted` preserves exact ties, multiple membership, time states, uncertainty, and source actions; `EvidenceReady` shows the producer-contract unavailable state. `NarrowViewport`, `ExternalInformationEmpty`, `RequiredFactMissing`, `AnalysisPendingAndMissingEvidence`, `AnalysisFailed`, `ConcurrentLoading`, `LoadError`, and `VoiceSummaryLoadError` cover mobile, scoped-empty, explicit evidence-absence, analysis-pending, retryable failure, one accessible announcement for parallel loading, whole-dashboard transport failure, and independently retryable voice-summary failure. | `--color-dashboard-*`, `OperationsDashboard`, `TopicContextInfluence` |
| `Ask Agent/AnswerEvidenceTimeline` | Select an answer citation to focus its event card, select the card to return to the answer, then open its evidence or source post. `MissingObservedTime` keeps an absent event clock explicit and `NarrowViewport` verifies the single-column interaction. | `--color-accent-*`, `--radius-panel`, `--size-control-min`, `AskAnswerTimeline` |
| `Post/SimilarVocPanel` | Compare ontology/semantic similar VOC and prior action evidence, then open the source; unavailable states show no fabricated TEPP theta or weight. | `SimilarVocPanel.css`, `SimilarVocPanel` |
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `Evidence/OrganizationAliasChip` | Click a cataloged org; the parenthetical is the unique corroborated SKOS companion. | `--color-chip-border`, `--radius-chip`, `OrganizationAliasChip` |
| `Evidence/OntologyExplorer` | Distinguish Event Lineage from typed ontology facts, inspect Post/Person/Organization/Team/Project shapes, token-backed secondary cues, and truth labels, then open authorized evidence. The named exact-values region supports keyboard scrolling; `LongLabelsAndEvidenceTable` proves complete labels wrap without character-count truncation. Desktop, narrow, drawers, legend/filter, empty, truncated, partial, denied, stale, and rejected scenes cover ADR 0184/0222 states. | `OntologyExplorer`, `ontologyLayout`, `--ontology-node-*-fill`, `--color-table-border` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Admin/AdminPanel` | Change the tenant brand name, then verify the saved or failed state before leaving settings. | `--surface`, `--border`, `--space-panel-block`, `AdminPanel` |
| `Lineage/LineageDag` | Open a reconstructed connection to read its inferred channel scores and Allen interval relation, or open the current branch node; compare empty, single-branch, grouped/forked, mobile-scroll, ungrouped, and long-title states before changing graph CSS. On narrow viewports, swipe the named viewport or focus it and use arrow keys to inspect the full lineage. | `--color-accent-background`, `--radius-control`, `--surface`, `--border`, `--color-focus-border`, `--size-control-min`, `LineageDag` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `Workspace/WorkspaceCalendar` | Read observed Naruon events, or open a commitment to land on that post. Fail-closed copy stays `이 범위의 일정을 아직 받을 수 없습니다`. | `--color-chip-border`, `WorkspaceCalendar`, `EvidenceStatusMark` |
| `Evidence/OntologyExplorer` | Distinguish Post, Person, Organization, and Team by shape and text, use the token-backed surface as a secondary cue, then open the exact-value table or cited evidence. Compare desktop, narrow, drawer, empty, truncated, denied, stale, and rejected states. | `--ontology-node-*-fill`, `OntologyExplorer` |
| `Post/ProductEvidenceList` | Open the cited product span. If the identity is unresolved, review the product catalog before using the relationship. Compare catalog-linked and catalog-review-required states. | `--surface`, `--border`, `ProductEvidenceList` |
| `Dashboard/VoiceTaxonomySummary` | Compare source and semantic classifications, note overlapping memberships, then review disagreements and records waiting for evidence. | `--surface`, `--border`, `VoiceTaxonomySummary` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 2025.10*
(W3C Community Group Final Specification).
https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
