# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Inventory is
the three buyer screens only. Modules attach to that flow.

| Story | Buyer next action | Token / module |
|---|---|---|
| `주간 VOC/WeeklyVoc` | Open one VOC item for this week. | `--space-panel-block`, `--radius-panel`, `WeeklyVoc` |
| `사건 lineage/EventLineagePanel` | Select a node on the Event Lineage DAG. | `--color-accent-border`, `EventLineagePanel`, `LineageDag` |
| `사건 lineage/OriginalSource` | Read the selected node's source text (pictures stay pictures). | `--space-panel-block`, `OriginalSource`, `PostBody` |
| `사건 lineage/FiveW1H` | Read grounded 누가/무엇을/언제/어디서/왜/어떻게, or the empty next action. | `--space-control-gap`, `--color-text-heading`, `FiveW1H` |
| `사건 lineage/GroundedQa` | Ask what happened on this lineage; read the grounded slot or the fail-closed next action. | `--space-control-gap`, `GroundedQa` |
| `역할·책임/RolesResponsibilities` | Decide the next human action from named Person / Organization / Team actors. | `--font-size-badge`, `RolesResponsibilities` |

Repeated web objects must use `frontend/src/styles/tokens.css` and a module
under `frontend/src/components/`. Do not add a second Node package manager;
Storybook is installed with the existing pnpm pin on Node 24.

## References — APA 7th

Design Tokens Community Group. (2025). *Design Tokens Format Module 1.0*
(W3C Community Group Draft Report). https://tr.designtokens.org/format/

Storybook. (2026). *Storybook for React & Vite*.
https://storybook.js.org/docs/get-started/frameworks/react-vite

World Wide Web Consortium. (2023). *Web content accessibility
guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/
