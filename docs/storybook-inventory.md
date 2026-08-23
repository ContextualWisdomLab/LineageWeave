# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Each story is a
reader-facing control you can click before changing product CSS.

| Story | Reader next action | Token / module |
|---|---|---|
| `Evidence/CitationChip` | Click a cited title to open that source post. | `--color-chip-border`, `--radius-chip`, `CitationChip` |
| `AnalysisRun/CutoffKnownBody` | Read the cutoff-known sentence, then compare it with the live body below. | `--color-accent-border`, `--space-panel-block`, `--radius-panel`, `CutoffKnownBody` |
| `AnalysisRun/CutoffKnownBody` BothClocks | Compare the cutoff-known body with the live rewrite using both clocks. | `CutoffKnownBody` |
| `AnalysisRun/NextAction` FailedLineage | Retry reconstruction from a current snapshot. Do not connect TEPP. | `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` FailedTepp | Connect the measurement service from this Failed row. | `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` FailedReport | Open the period report, then rebuild from a current snapshot. | `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` PendingTepp | Confirm the cutoff posts, then start TEPP measurement. This is not a calibrated result. | `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` RunningLineageQueued | Refresh this run. Do not start over. | `--size-control-min`, `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` SucceededReportLanding | Read Demo Corp mean θ and member posts, then open a post. | `AnalysisRunNextAction` |
| `AnalysisRun/NextAction` CutoffLiveBodyWarning | Compare **Body this run knew** with the live rewrite. | `CutoffKnownBody` |
| `Analysis/LeftoverPairButton` ClosestPair | Open Public post, then read Post quality criterion sales-lead. | `LeftoverPairButton`, leftoverPairGuidance |
| `Analysis/LeftoverPairButton` FarthestPair | Open the farthest leftover post, then read Post quality criterion negative. | `LeftoverPairButton` |
| `Evidence/RoleEvidence` UnresolvedAffiliation | Keep reading the mention as unbound, or open the catalog to bind it. | `RoleEvidence`, analysisEvidenceDiagnosis |
| `Evidence/RoleEvidence` EvidenceDiagnosisKinds | Distinguish catalog-unbound, dropped channel, and confident-negative next actions. | analysisEvidenceDiagnosis |
| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |
| `Chrome/PopupCloseButton` | Close the evidence panel or post popup. | `--space-close-inset`, `--font-size-close`, `PopupCloseButton` |
| `Evidence/LineageDag` | Inspect a branching Event Lineage, then open a record or read its evidence trail. | `--color-primary`, `--color-accent-orange`, `LineageDag` |
| `Evidence/LineageDag` LongLabelMultiTopic | Read full titles, Topic A-100 vs B-200, and predecessor → successor, then open the current branch record. | `LineageDag`, wrapLabel |
| `Analysis/LineageDag` LongLabelMultiTopic | Read the same long-label multi-Topic branching case from the analysis catalog. | `LineageDag` |
| `Evidence/KnowledgeGraph` MixedNodeStates | Compare focus, catalog, and evidence nodes, then open a post node. | `--color-accent-orange`, `KnowledgeGraphView` |
| `Evidence/KnowledgeGraph` DirectedTemporalRelation | Follow the source → target arrow, then read the evidence trail. | `KnowledgeGraphView` |
| `Evidence/KnowledgeGraph` LongLabels | Read the untruncated titles and relation on the graph, then open the focus post. | `KnowledgeGraphView`, wrapLabel |
| `Evidence/SummaryStatus` Processing | Wait while the source evidence is still being analyzed. | `--color-accent-border`, `SummaryStatus` |
| `Evidence/SummaryStatus` Unavailable | Retry summary, or continue with the source record. | `--color-exception-*`, `--size-control-min`, `SummaryStatus` |
| `Evidence/SummaryStatus` Empty | Read the source record when no saved summary exists. | `SummaryStatus` |
| `Evidence/SummaryStatus` RetryableTransportFailure | Retry the failed request, or continue with saved evidence. | `--color-exception-*`, `--size-control-min`, `ExceptionAlert` |
| `Evidence/SummaryStatus` FormFieldError | Correct the highlighted fields, then retry. | `--color-exception-*`, `ExceptionAlert` inline |
| `Evidence/SummaryStatus` AuthFailure | Log in again to open the workspace. | `--color-exception-*`, `--size-control-min`, `ExceptionAlert` |
| `Evidence/SummaryStatus` ContinueWithSavedEvidence | Retry opening this source, or keep reading the saved answer. | `--color-exception-*`, `--size-control-min`, `ExceptionAlert` |
| `Workspace/AskAgentPanel` Unanchored | Start a question across all authorized evidence. | `AskAgentPanel` |
| `Workspace/AskAgentPanel` Anchored | Ask from one visible starting source or clear the anchor. | `AskAgentPanel` |
| `Workspace/AskAgentPanel` SavedHistory | Continue a saved evidence-grounded conversation. | `aria-current`, `AskAgentPanel` |
| `Workspace/AskAgentPanel` Unavailable | Retry loading conversation history. | `ExceptionAlert`, `AskAgentPanel` |
| `Workspace/AskAgentPanel` Phone | Review the anchored flow at the phone viewport. | `AskAgentPanel` phone breakpoint |
| `Workspace/ChatPanel` SeededDump | Read seeded questions on a post, then ask a new question. | `ChatPanel` |
| `Workspace/ChatPanel` SavedHistory | Select a saved post conversation, then start a new conversation. | `aria-current`, `ChatPanel` |
| `Workspace/ChatPanel` Phone | Review post Ask history at the phone viewport. | `ChatPanel` phone breakpoint |

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
