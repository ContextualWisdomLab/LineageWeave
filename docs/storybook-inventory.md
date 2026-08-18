# Storybook inventory

Open the catalog after `cd frontend && pnpm run storybook`. Inventory is
the four buyer GNB destinations. Modules attach to that flow.
Tokens and Storybook frames live on the operator Remote machine. This
Cloud slice does not attach Figma and does not invent a fourth screen
from a missing frame (ADR 0002).

| Story | Buyer next action | Token / module |
|---|---|---|
| `게시판/Board` | Open a post or a scheduled newspaper. Weekly VOC is a filter. | `--space-panel-block`, `Board`, `NewspaperCard` |
| `게시판/OriginalSource` | Read the selected node's source text (pictures stay pictures). | `--space-panel-block`, `OriginalSource`, `PostBody` |
| `게시판/FiveW1H` | Read grounded 누가/무엇을/언제/어디서/왜/어떻게, or the empty next action. | `--space-control-gap`, `FiveW1H` |
| `게시판/EventLineagePanel` | Select a node on the Event Lineage DAG. | `--color-accent-border`, `EventLineagePanel`, `LineageDag` |
| `고객 마스터/CustomerMaster` | Read Orgmetra customers and Keymen, or the fail-closed next action. Corp / PU stay Keyverse attributes. | `--space-panel-block`, `CustomerMaster` |
| `달력/Calendar` | Read CalDAV consume events, or the fail-closed next action. Do not invent events. | `--space-panel-block`, `Calendar` |
| `Ask Agent/GroundedQa` | Ask what happened on this lineage; read the grounded slot, 미검증 후보, or the fail-closed next action. Promote a candidate to 고객 마스터. | `--space-control-gap`, `GroundedQa` |

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
