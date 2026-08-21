# ADR 0125 — Ask Agent evidence workspace and composer contract

**Decision status:** Accepted
**Date:** 2026-08-21
**Figma File ID:** `1Su3lDRmiZdcUs47t1QwIX`
**Stack placement:** This change is a direct child of PR #264 head `8832216fcd2b0a1dcb486ea83269e25695ce378a`.

## Context

The stacked buyer surface already provided authorized Global Ask, durable
session recovery, cited-post navigation, and Event Lineage focus continuity.
The visible Ask Agent screen, however, remained a generic content section: the
composer reused a Keyman link-style button, the answer, timeline, citations,
and evidence facts shared one undifferentiated card, and the screen had no
component or Storybook state boundary of its own.

The project UI/UX Standard Guide v3.0 requires a clearly differentiated focused
input, visible action controls, responsive PC/tablet/phone behavior, and a
mobile layout that places the primary action within the content flow. ADR 0002
also established the safe Figma file above as the public design-system boundary
and forbids copying confidential source-organization material.

## Decision

1. Extract the destination into `AskAgentWorkspace`, with a stateful controller
   and a presentational `AskAgentWorkspaceView`.
2. Use a semantic form and a visually primary Ask button. Enter submits,
   Shift+Enter inserts a line break, and an IME composition Enter never submits.
3. Separate composer, pending/error/empty state, answer, Event Lineage timeline,
   and cited evidence into explicit regions. A completed answer receives focus.
4. Keep every existing security and truth boundary: only the authenticated
   `/api/ask` contract is called, stale sessions retry once without the expired
   identifier, previous evidence is hidden while a replacement answer is
   pending, and source actions retain the #263/#264 Event Lineage handoff.
5. Reuse existing design tokens and define responsive breakpoints at 1024px and
   768px. The phone state uses a single column and a full-width primary action.
6. Inventory Empty, Loading, Answered, Unavailable, and Phone Answered scenes in
   Storybook. These executable scenes are the current review source until a
   dedicated safe Figma frame is added to the recorded file.

## Consequences

- Ask Agent is no longer coupled to the post-popup or Keyman control styles.
- Future streaming, follow-up history, or source comparison can evolve inside a
  bounded component without expanding `App.tsx`.
- The component preserves the exact accessible labels relied on by existing
  integration tests and downstream stacked PRs.
- This ADR does not claim the unmerged stack is protected-main behavior.

## Verification

- Focused controller and keyboard interaction tests.
- Existing App-level citation, timeline, stale-session, pending-answer, and
  Event Lineage focus regressions.
- Frontend lint, production build, complete Vitest suite, and Storybook build.
- Responsive and focus-visible CSS review against the UI/UX guide.
