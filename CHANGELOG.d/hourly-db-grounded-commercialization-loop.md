# Hourly DB-grounded commercialization loop

## Added

- An hourly product-gap workflow now reads the live pull-request queue and
  exits without mutation whenever an open PR exists. The organization-central
  scheduler remains the only review, repair, branch-update, and merge writer.
- When the pull-request queue is empty, a pinned OpenCode CLI using only
  `NVIDIA_NIM_API_KEY` selects one buyer-visible gap from the approved
  DB-grounded Figma design, writes a failing regression first, implements one
  bounded vertical slice, validates it in an unprivileged network-isolated
  copy, and opens exactly one protected pull request.
- Permanent workflow-contract tests bind the hourly schedule, central
  single-writer boundary, read-only queue gate, credential removal,
  no-Copilot rule, test-first evidence, protected paths, stale-work checks,
  and no-self-merge boundary.
- Product design and doctoring documentation now records the truthful mapping
  from PostgreSQL cardinalities to Records, Lineage, Record Detail, Entity
  Catalog, Calendar, Reports, Accounts, Roles, and read-only system-policy
  interactions, with APA 7th references for WCAG 2.2, WAI-ARIA 1.2,
  ISO/IEC 25010:2023, ISO/IEC 40500:2025, and NIST zero-trust controls.
- The accepted Figma baseline is now bound to canonical and archive page IDs.
  Unsupported graph history, buyer-facing provenance, and access-audit claims
  remain archived, while helper copy directs customers to evidence-backed next
  actions and synthetic report labels remain consistent with their grouping
  kind.
