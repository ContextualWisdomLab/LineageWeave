# ADR 0119: Retire "Buyer" as the reader-facing terminology

**Status:** Accepted
**Date:** 2026-08-21

**Context:** ADR 0037 named the four-destination frontend shell the "Buyer
GNB" and the term spread into component names (`BuyerNav`,
`BuyerDestination`), CSS classes (`.buyer-gnb`), i18n keys ("Buyer
navigation"), a visible legend label ("BUYER EVIDENCE"), Python identifiers
(`_buyer_evidence_kind`), and prose across `AGENTS.md`, `ARCHITECTURE.md`,
and docstrings. LineageWeave has no explicit buyer actor — it is an internal
analyst/marketing-intelligence workspace, not a storefront with a buyer
role. "Buyer" was a leftover label from early drafting, not a modeled
domain entity, and reads as confusing or inaccurate to anyone reading the
code or product surface.

**Decision:**
1. Rename the frontend navigation shell: `BuyerNav` → `WorkspaceNav`,
   `BuyerDestination` → `WorkspaceDestination`, `.buyer-gnb*` CSS →
   `.workspace-gnb*`, `.buyer-destination*` → `.workspace-destination*`,
   the "Buyer navigation" i18n key/aria-label → "Workspace navigation", and
   the `#mobile-buyer-navigation` id → `#mobile-workspace-navigation`.
2. Rename the Event Lineage legend label "BUYER EVIDENCE" → "LINEAGE
   EVIDENCE".
3. Rename backend/Python identifiers that described the same concept:
   `_buyer_evidence_kind` → `_cited_evidence_kind`,
   `_buyer_evidence_text` → `_cited_evidence_text`.
4. Replace prose that referred to "the buyer" as the person reading the
   product with "the reader" (docstrings, comments, `AGENTS.md`,
   `ARCHITECTURE.md`, living docs under `docs/`) or with "workspace" where
   the prose named the navigation shell itself.
5. Do not rewrite historical ADRs (0002–0118) or `CHANGELOG.md` /
   `CHANGELOG.d/*.md` entries — those are point-in-time records of the
   decisions and releases made under the terminology that existed then.
   This ADR documents the rename going forward; historical documents keep
   their original wording for an accurate record.
6. Leave "buyer" where it appears as ordinary English inside simulated
   post/table content (`lineageweave/fixtures.py`,
   `tests/test_chunking.py`) — that is domain content a real sales note
   could plausibly contain, not this project's own naming.

**Consequences:**
- No source, test, or living-doc identifier or user-facing string uses
  "Buyer" going forward; `grep -ri buyer` outside historical ADRs,
  `CHANGELOG*`, and fixture/test content returns nothing.
- Historical ADRs and changelog entries remain internally consistent with
  the PRs they describe; readers encountering "Buyer GNB" in ADR 0037 or
  CHANGELOG 2.13.0 know it is the old name for what this ADR renames.
- Component/file rename (`BuyerNav.tsx` → `WorkspaceNav.tsx`) is a breaking
  change for any external Storybook story or import path that referenced
  the old name; none exist outside this repo at the time of this ADR.

**References:**
- ADR 0037 (Buyer GNB and product-facing frontend surface) — superseded
  terminology only, decision content unchanged.
- ADR 0118 (UI·UX Standard Guide Ver.3.0 Design Overhaul)
