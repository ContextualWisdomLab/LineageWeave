# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
operator-facing control you can click before changing product CSS.

| Story | Operator next action | Token / module |
|---|---|---|
| `Customer Master/Linking guidance` | Before linking a customer, compare the source identifier with related posts and organization evidence. `Desktop` and `Narrow` keep the same next action without exposing implementation terms. | `workspace-destination-intro`, `CustomerLinkingGuidance` |
| `Workspace/OperationsDashboard` | Compare Event and post counts, inspect external-information coverage, then open the cited source behind a claim, handover, repeat issue, or topic-context influence. `TopicInfluenceAccepted` preserves exact ties, multiple membership, time states, uncertainty, and source actions; `EvidenceReady` shows the producer-contract unavailable state. `NarrowViewport`, `ExternalInformationEmpty`, `RequiredFactMissing`, `AnalysisPendingAndMissingEvidence`, `AnalysisFailed`, `ConcurrentLoading`, `LoadError`, and `VoiceSummaryLoadError` cover mobile, scoped-empty, explicit evidence-absence, analysis-pending, retryable failure, one accessible announcement for parallel loading, whole-dashboard transport failure, and independently retryable voice-summary failure. | `--color-dashboard-*`, `OperationsDashboard`, `TopicContextInfluence` |
| `Ask Agent/AnswerEvidenceTimeline` | Select an answer citation to focus its event card, select the card to return to the answer, then open its evidence, source post, or persisted related public source. `MissingObservedTime` keeps an absent event clock explicit and `NarrowViewport` verifies the single-column interaction. | `--color-accent-*`, `--radius-panel`, `--size-control-min`, `AskAnswerTimeline` |
| `Ask Agent/Knowledge cutoff` | Ask with public verification enabled, then follow the displayed next action when no claim is eligible. `NoEligiblePublicClaim` and `NoEligiblePublicClaimNarrow` render the full result panel at desktop and mobile widths. | `ask-delivery`, `AskAgentPanel` |
| `Post/SimilarVocPanel` | Compare ontology/semantic similar VOC and prior action evidence, then open the source; unavailable states show no fabricated TEPP theta or weight. | `SimilarVocPanel.css`, `SimilarVocPanel` |
| `Post/Recorded perspectives` | Read the imported primary and every evidence-connected additional Voice with its recorded truth state instead of flattening them into one compound category. `CombinedEvidence`, `RejectedEvidence`, and `NarrowViewport` cover desktop, rejected-evidence, and narrow layouts. | `VoicePerspectiveList`, `ticket-list`, `post-meta` |
| `Post/Connect perspective` | Choose one unassigned Voice and an explicit evidence state, then record the open post as its evidence. `Ready`, `Completed`, and `NarrowViewport` cover untouched, successful, and mobile states. | `VoiceAssignmentForm`, `admin-form`, `btn-primary` |
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `Evidence/OrganizationAliasChip` | Click a cataloged org; the parenthetical is the unique corroborated SKOS companion. | `--color-chip-border`, `--radius-chip`, `OrganizationAliasChip` |
| `Evidence/OntologyExplorer` | Distinguish Event Lineage from typed ontology facts, inspect Post/Person/Organization/Team/Project shapes, token-backed secondary cues, and truth labels, then open authorized evidence. The named exact-values region supports keyboard scrolling; `LongLabelsAndEvidenceTable` proves complete labels wrap without character-count truncation, while `CombinedVoiceEvidence` covers primary-plus-additional Voice assignments and focuses the evidence action distinct from the carrying-Post action. Desktop, narrow, drawers, legend/filter, empty, truncated, partial, denied, stale, and rejected scenes cover ADR 0184/0222/0251 states. | `OntologyExplorer`, `ontologyLayout`, `--ontology-node-*-fill`, `--color-table-border` |
| `Evidence/OntologyExplorer` | Distinguish Event Lineage from typed ontology facts, inspect Post/Person/Organization/Team/Project/Work-evidence shapes, token-backed secondary cues, and truth labels, then open authorized evidence. The populated scene includes one assertion-backed occupational construct without a person-trait promotion. The named exact-values region supports keyboard scrolling; `LongLabelsAndEvidenceTable` proves complete labels wrap without character-count truncation. Desktop, narrow, drawers, legend/filter, empty, truncated, partial, denied, stale, and rejected scenes cover ADR 0184/0222/0255 states. | `OntologyExplorer`, `ontologyLayout`, `--ontology-node-*-fill`, `--color-table-border` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Admin/AdminPanel` | Change the tenant brand name, then verify the saved or failed state before leaving settings. | `--surface`, `--border`, `--space-panel-block`, `AdminPanel` |
| `Lineage/LineageDag` | Open a reconstructed connection to read its inferred channel scores and Allen interval relation, or open the current branch node; compare empty, single-branch, grouped/forked, mobile-scroll, ungrouped, and long-title states before changing graph CSS. On narrow viewports, swipe the named viewport or focus it and use arrow keys to inspect the full lineage. | `--color-accent-background`, `--radius-control`, `--surface`, `--border`, `--color-focus-border`, `--size-control-min`, `LineageDag` |
| `Chrome/StatusNotice` | Read success, unavailable, or retry copy, then take the named next action. Success and unavailable are a named region (not live `role=status`); Retry is `role=alert` and only on the retry kind. Calendar's missing Naruon projection uses unavailable. | `--badge-status-success-*`, `--badge-status-pending-*`, `--badge-status-danger-*`, `StatusNotice` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `Workspace/WorkspaceCalendar` | Read observed Naruon events, or open a commitment to land on that post. Fail-closed copy stays `이 범위의 일정을 아직 받을 수 없습니다`. | `--color-chip-border`, `WorkspaceCalendar`, `EvidenceStatusMark` |
| `Ask Agent/Public claim verification` | Compare supported, refuted, and not-enough-information states; open only the external evidence link, then review the separate internal citation before changing governed graph state. | `--space-panel-block`, `--space-control-gap`, `--color-border`, `--size-control-min`, `PublicClaimVerification` |
| `Post/Source research` | Open the cited public resource, then compare it with the highlighted passage or image detail from this post. `SupportedAndUnavailable` and `PrivatePost` cover cited retrieval, fail-closed private egress, and the research action. | `--space-panel-block`, `--space-control-gap`, `--color-border`, `--size-control-min`, `SourceResearchPanel` |
| `Ask Agent/Knowledge cutoff` | Exercise partial historical grounding, retained-revision provenance, later-live-change disclosure, and the narrow viewport before relying on a historical answer. | Native `datetime-local`, `--space-panel-block`, `--space-control-gap`, `--color-border`, `--size-control-min` |
| `Post/ProductEvidenceList` | Open the cited product span and its connected project or operational fact. If the identity is unresolved, review the product catalog before using the relationship. Compare catalog-linked relation and catalog-review-required states. | `--surface`, `--border`, `ProductEvidenceList` |
| `Dashboard/VoiceTaxonomySummary` | Compare source and semantic classifications, note overlapping memberships, then review disagreements and records waiting for evidence; `KoreanMobile` verifies locale-complete customer copy in the narrow viewport. | `--surface`, `--border`, `VoiceTaxonomySummary` |
| `Navigation/WorkspaceNav` | Reach every workspace destination and the language action; `MobileAllDestinations` keeps all actions visible without horizontal clipping. | `--gnb-height`, `--size-control-min`, `WorkspaceNav` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

The `Post/Source research` candidate was rendered with synthetic evidence at
1440×1000 and an iPhone 14 viewport. The governed captures are
[`source-research-desktop.png`](screenshots/source-research-desktop.png) and
[`source-research-mobile.png`](screenshots/source-research-mobile.png). Desktop
and narrow inspection confirmed readable
wrapping without horizontal overflow, a token-sized action control, visible
link semantics, and customer-action copy without storage or provider names.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 2025.10*
(W3C Community Group Final Specification).
https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
# Project history timeline

`Projects/History Timeline` covers the evidence-bearing default
timeline and its exact-value table. Keyboard roving focus, the current event,
responsibility-evidence gaps, non-causal lineage paths, and source-record
actions are executable component-test states governed by ADR 0243. The
1440×1000 and 390×844 audits are retained in
`docs/screenshots/project-history-time-source-{desktop,mobile}.png`; both show
the customer-readable time source without exposing the stored basis code.
