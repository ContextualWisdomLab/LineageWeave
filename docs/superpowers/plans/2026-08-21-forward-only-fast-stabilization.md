# Forward-Only Fast Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the Event Lineage and ontology buyer surfaces quickly without deleting, shrinking, or reverting accepted product capability.

**Architecture:** Keep feature work intact and converge it into one reviewable forward stack. Fix exact-head defects test-first, merge the current protected `main` normally into stale feature branches, then stack overlapping follow-up UI work on the stabilized Event Lineage head. The heterogeneous Ontology Explorer remains an independent capability and is hardened rather than folded into the record-lineage renderer.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Vitest 4, Storybook 10, CSS design tokens, FastAPI/PostgreSQL for independent ontology work, GitHub protected pull requests.

**Spec:** `docs/adr/0002-figma-access-boundary.md`, PR #330, PR #349, PR #350, issue #341.

## Global Constraints

- Do not delete, narrow, or revert buyer-visible capability merely to reduce PR size.
- Do not force-push or rewrite shared branch history.
- Use ordinary merges for stack repair.
- Never transfer predecessor-head checks or reviews to a new head.
- Preserve synthetic-only public fixtures and the Figma confidentiality boundary.
- Keep Event Lineage as reconstructed post/record lineage; keep Ontology Explorer heterogeneous and provenance-aware.
- Every production change starts with a failing regression test.
- Required hosted checks and an independent exact-head approval remain merge gates.

---

### Task 1: Close the Event Date CSS Specificity Defect

**Files:**
- Create: `frontend/src/LineageDag.css.test.ts`
- Modify: `frontend/src/LineageDag.css`

**Interfaces:**
- Consumes: the existing `.lineage-dag-node text` rule in `frontend/src/App.css`.
- Produces: a selector whose specificity guarantees the date's 9px muted style wins without `!important`.

- [ ] **Step 1: Write the failing CSS contract test**

```ts
/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "LineageDag.css"), "utf-8");

describe("LineageDag CSS contracts", () => {
  it("keeps the event-date selector at least as specific as the shared node-text rule", () => {
    expect(css).toContain(".lineage-dag-node text.lineage-dag-node-date {");
    expect(css).not.toMatch(/(^|\n)\.lineage-dag-node-date\s*\{/);
  });
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd frontend && pnpm exec vitest run src/LineageDag.css.test.ts`

Expected: FAIL because the stylesheet still declares only `.lineage-dag-node-date`.

- [ ] **Step 3: Apply the minimal specificity fix**

```css
.lineage-dag-node text.lineage-dag-node-date {
  font-size: 9px;
  opacity: 0.72;
  fill: var(--text);
}
```

- [ ] **Step 4: Run focused and full frontend verification**

Run:

```bash
cd frontend
pnpm exec vitest run src/LineageDag.css.test.ts src/LineageDag.test.tsx src/lineageDagI18n.test.ts
pnpm run lint
pnpm run test
pnpm run build
pnpm run build-storybook
```

Expected: all commands pass without warnings introduced by this task.

- [ ] **Step 5: Resolve the exact review thread only after the fix is committed**

Reply with the new exact head, focused/full verification receipt, and the selector-specificity rationale; then resolve `PRRT_kwDOT22WIM6bAzd8`.

### Task 2: Repair the Event Lineage Stack Without Dropping Capability

**Files:**
- Modify only conflict files produced by the ordinary merge of current protected `main` into `feat/lineage-dag-regression`.
- Update: PR #330 description and `docs/product-technical-gap-baseline.md` exact-head receipt.

**Interfaces:**
- Consumes: protected `main@ef6f5a5ffcb467bd935dc1e53acc0029669b0bd7` or its accepted successor.
- Produces: a branch that is not behind protected `main` and retains every PR #330 behavior and test.

- [ ] **Step 1: Record pre-merge exact identities and changed-file inventory**
- [ ] **Step 2: Ordinary-merge protected `main` into `feat/lineage-dag-regression`; never rebase or force-push**
- [ ] **Step 3: Resolve conflicts by retaining both current-main product changes and the complete Event Lineage contract**
- [ ] **Step 4: Run the focused DAG suite, all frontend tests, lint, production build, Storybook, documentation hygiene, and `git diff --check`**
- [ ] **Step 5: Update the PR body with the resulting exact parent/head and request a new independent exact-head review**

### Task 3: Stack the UI/UX Guide Follow-Up on the Stabilized DAG

**Files:**
- PR #350 branch conflict files only.
- PR #350 description and exact-head receipt.

**Interfaces:**
- Consumes: the accepted current head of PR #330.
- Produces: one forward stack where #350 adds the authenticated mobile shell and UI/UX Guide v3 work without reimplementing or weakening #330.

- [ ] **Step 1: Compare #350 against the stabilized #330 head and list overlapping Event Lineage files**
- [ ] **Step 2: Write or retain regression tests for every behavior unique to either PR before conflict resolution**
- [ ] **Step 3: Ordinary-merge the stabilized #330 head into `fix/uiux-standard-guide-v3-postmerge`**
- [ ] **Step 4: Resolve overlap by preserving #330 direction/evidence/accessibility semantics and #350 navigation/responsive shell semantics**
- [ ] **Step 5: Retarget #350 to `feat/lineage-dag-regression` once GitHub reports the forward stack mergeable**
- [ ] **Step 6: Run frontend, Storybook, accessibility, i18n, and browser-width regression gates; request exact-head review**

### Task 4: Harden the Independent Ontology Explorer in Parallel

**Files:**
- Only files changed by PR #349 and focused follow-up tests.

**Interfaces:**
- Consumes: the protected `main` ontology/ABAC/provenance contracts.
- Produces: a merge-ready heterogeneous explorer without moving its capability into Event Lineage.

- [ ] **Step 1: Re-read every unresolved exact-head review thread on #349**
- [ ] **Step 2: For each valid defect, add the smallest failing test and verify RED**
- [ ] **Step 3: Implement one root-cause fix per test cycle**
- [ ] **Step 4: Run PostgreSQL, backend, frontend, Storybook, export-equivalence, accessibility, i18n, SAST, and documentation gates**
- [ ] **Step 5: Normally merge current `main` if the branch becomes behind; update exact-head evidence without deleting scope**

### Task 5: Protected Integration

- [ ] **Step 1: Merge #330 only after current-head terminal checks, zero unresolved threads, and independent approval**
- [ ] **Step 2: Revalidate and merge #350 after #330 using the new protected base**
- [ ] **Step 3: Merge #349 independently when its own exact-head gates qualify**
- [ ] **Step 4: Re-run the buyer Event Lineage and Ontology Explorer end-to-end journeys on protected `main`**
- [ ] **Step 5: Update `CHANGELOG.md`, the gap baseline, release/version evidence, and remove only temporary repair machinery whose purpose is complete**
