# ADR 0119: Retire "Buyer" Terminology From Live Code And Docs

**Status:** Accepted
**Date:** 2026-08-23

**Context:** LineageWeave is an internal B2B marketing-intelligence/knowledge-graph
tool over VOC/board-post data, not a storefront -- there is no literal
e-commerce buyer role. Earlier work (ADR 0037, ADR 0110, ADR 0114) named the
app-wide navigation bar, several CSS classes, i18n keys, code comments, and
test descriptions after "Buyer" as a generic stand-in for "whoever is using
the product." Per this project's naming convention, internal code should not
use "Buyer" unless a literal e-commerce buyer role exists; the codebase
already has an established term for the generic app user -- "reader" (see
`lineageweave/post_summary.py`, `backend/app/activity_stream.py`,
`backend/app/knowledge_graph.py`).

**Decision:**
1. `frontend/src/components/BuyerNav.tsx` (and its test) is renamed to
   `WorkspaceNav.tsx`. The exported `BuyerNav` component becomes
   `WorkspaceNav`; the `BuyerDestination` type becomes `WorkspaceDestination`.
2. CSS classes `.buyer-gnb`, `.buyer-gnb-item`, `.buyer-gnb-tools` become
   `.workspace-gnb`, `.workspace-gnb-item`, `.workspace-gnb-tools`; the
   `.buyer-destination` / `.buyer-destination-intro` class names used in
   `App.tsx` become `.workspace-destination` / `.workspace-destination-intro`.
3. The i18n key `"Buyer navigation"` becomes `"Workspace navigation"` across
   all five locale blocks in `frontend/src/i18n.ts` (en/ko/zh/ja/vi).
4. Internal Python identifiers `_buyer_evidence_kind` / `_buyer_evidence_text`
   in `lineageweave/post_chat.py` become `_reader_evidence_kind` /
   `_reader_evidence_text`.
5. Prose in code comments, docstrings, test descriptions, `AGENTS.md`, and
   `ARCHITECTURE.md` that used "buyer" as a generic reference to the person
   using the product now says "reader," matching the term already
   established elsewhere in this codebase.
6. Test-only opaque idempotency-key string literals prefixed `buyer-` (e.g.
   `"buyer-create-2026-w02"`) become `run-`-prefixed, since they are
   arbitrary unique test values with no functional dependency on the
   substring.
7. Out of scope, deliberately unchanged: numbered ADRs already on `main`
   that record past decisions in the terminology of their time (ADR 0037,
   0069, 0110, 0114, and others) -- these are point-in-time records, not
   live naming; `CHANGELOG.md` and `CHANGELOG.d/*.md` historical entries,
   for the same reason; and domain-content prose that names an actual
   business role called "buyer" inside synthetic fixture text
   (`lineageweave/fixtures.py`'s sales-note fixtures). One ambiguous case,
   `tests/test_chunking.py`'s `"Owner | Buyer"` markdown-table fixture, is
   left as-is because it reads as a plausible real business-table header
   rather than a naming choice.

**Consequences:**
- No user-visible behavior changes; this is a naming-only rename plus
  translated-string updates.
- `WorkspaceNav`/`WorkspaceDestination` and `.workspace-gnb*` are now the
  canonical names for the app-wide navigation bar and its destinations.
- Future internal naming should default to "reader" for the generic app
  user, consistent with `post_summary.py` and `activity_stream.py`, and
  should avoid "Buyer" unless a literal e-commerce buyer role is added.

**References:**
- ADR 0037 (Buyer GNB surface -- the component this ADR renames)
- ADR 0110 (Buyer image evidence rendering)
- ADR 0114 (Stale summary buyer continuity)
- ADR 0118 (UI/UX Standard Guide Ver.3.0, most recent GNB touch point)
