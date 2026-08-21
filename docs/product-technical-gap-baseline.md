# Product & Technical Gap Baseline

> Audit scope: the current `feat/uiux-standard-guide-v3-restacked` worktree,
> compared with `origin/main`, the UI/UX Standard Guide v3.0 supplied for this
> product, ADR 0118, the accepted TEPP PRD/contracts, and the
> contextual-orchestrator architecture. Real source identifiers are deliberately
> replaced with case labels; they must not enter repository artifacts.

## 1. Exact-head evidence

Audit anchor: the exact source state carried by this commit at 2026-08-21;
record the final PR head with `git rev-parse HEAD` during acceptance.

- **Implemented in source:** PostgreSQL-backed API boundaries, Keyverse/OIDC
  identity boundary, buyer navigation, post popup, ABAC/RBAC surfaces, Korean
  summary, 5W1H, R&R/Keyman, customer hierarchy, tickets/calendar, chat,
  provenance/evidence, and reconstructed lineage API/DAG layout.
- **Implemented in source, runtime evidence still required:** TEPP import/API
  transport, contextual-orchestrator LLM/VISION transport, SearXNG
  corroboration, Local Zotero ingestion, real PostgreSQL import, and browser
  login-to-evidence workflows. A source adapter or a synthetic test is not live
  integration proof.
- **Figma reference:** ADR 0118 records file `1Su3lDRmiZdcUs47t1QwIX`; the
  inspected Event Lineage frames are desktop `5:14` and mobile `5:15`.
- **Current PR gate:** PR #347 is review-required; Devin Review failed, the
  required OpenCode/Noema reviews and product/security checks were pending at
  audit time, and CodeRabbit skipped review because the diff exceeded its file
  limit. This is not merge-ready evidence.

## 2. UI/UX Standard Guide v3.0 comparison

### 2.1 Satisfied or substantially present

- Desktop shell has a sticky header, top-right user/logout controls, GNB,
  footer with brand/copyright, standard breakpoints, 1920px maximum layout,
  Noto Sans family, CI/BI palette tokens, table alignment tokens, focus styles,
  required-field marker, and 50% modal backdrop.
- GNB active state is exposed with `aria-current`; the lineage DAG has keyboard
  activation and branch/root/current visual states.
- PostgreSQL, orchestrator, TEPP, provenance, and synthetic-fixture boundaries
  are documented in `ARCHITECTURE.md` and the applicable ADRs.

### 2.2 Gaps and status

- **Mobile drawer — fixed in this worktree:** CSS referenced a drawer trigger but
  the authenticated shell rendered no trigger or drawer. The shell now renders
  an accessible hamburger button, close action, overlay, and reusable BuyerNav.
- **Event Lineage Figma parity — fixed in this worktree:** the DAG now includes
  buyer-evidence context, legend, horizontal overflow on phones, inference
  boundary, direction markers, and an evidence trail table/cards treatment.
- **Approved CI/BI asset — open:** the header/footer currently render the
  tenant brand name as text. Do not invent or alter a corporate logo; add the
  approved asset only after the tenant CI/BI source and usage permission are
  available.
- **Header utilities/search — partial:** search exists on the board, but a
  global header search and site-map utility are not yet implemented.
- **Locale document metadata — open:** `frontend/index.html` has a fixed
  `lang="en"`; it should follow the selected locale for accessibility.
- **Phone content affordance — runtime verify:** the guide requires a visible
  portion of content below the fold. Verify this with Playwright at 390px after
  the authenticated runtime is available.

## 3. Supplied parsing and semantic cases

The following user-reported cases remain tracked without storing real post IDs:

- `case-footnote-01`: footnote/list `li`/`ol` boundary is misclassified.
- `case-table-01`: HTML table parsing fails.
- `case-indent-01` and `case-indent-02`: semantic indentation is wrong.
- `case-multi-project-01`: two projects must produce separate event streams;
  internal facilities must not be guessed as Partner/Supplier.
- `case-image-table-01`: image tables need region-aware OCR/description and
  rendered Markdown/table support.
- `case-summary-affiliation-01`: a role such as PM needs person, title, and
  organization evidence rather than an unqualified collective label.
- `case-r-and-r-01`: requester, assignee, action, and cost/payment owner must
  remain explicit in R&R evidence.
- `case-math-01`: units such as m³ need superscript-preserving source/semantic
  representations and ontology-safe rendering.

These are not “resolved” merely because a prompt or heuristic was changed.
Each requires synthetic unit coverage plus an authorized runtime reproduction
or an explicit unavailable result.

## 4. Product and technical gaps

- **Entity and abbreviation resolution — open:** canonical names, aliases,
  multilingual labels, team-vs-organization typing, title-aware person
  disambiguation, and SearXNG/internal corroboration need end-to-end evidence.
- **Image/HTML semantic units — partially implemented:** source DOM, layout
  metadata, region evidence, and provenance must remain separate from embedding
  text; transparent/unsupported image conversion and multimodal processing need
  live verification.
- **TEPP measurement — boundary accepted, runtime open:** LineageWeave must
  call TEPP through its published import/REST contract and must not implement a
  local theta, psychometric calibration, CAT, or judge score. TEPP owns the
  Rust numerical/psychometric layer and its multilevel/multiple-membership/time
  model.
- **Orchestration — boundary accepted, runtime open:** all LLM/VISION/embedding
  work must cross contextual-orchestrator with provenance, session, cost, schema
  validation, synthesis/repair, and capability discovery. No provider key or
  model selector belongs here.
- **Authorization — runtime open:** verify actual Keyverse/OIDC login, corp/PU
  attributes, post visibility, ABAC/RBAC denials, and no cross-tenant evidence
  leakage using aggregate, non-identifying results.
- **Database/operations — audit open:** verify 3NF constraints, hot-partition
  behavior, lock boundaries, Valkey event delivery, multithreaded server
  behavior, retention grants, and read/write contention on the local Compose
  stack.
- **Literature/Zotero — open:** record APA 7 references and verify Local Zotero
  API availability before claiming synchronization. The repository must retain
  only metadata/citations appropriate for public artifacts.
- **Release/quality gates — open:** current PR checks and required reviews must
  complete on the exact current head; frontend, backend, browser, accessibility,
  Storybook, security, and coverage evidence must be collected before release.

## 5. Next acceptance loop

1. Re-fetch the exact PR head and required reviews/checks.
2. Run frontend lint, tests, build, Storybook, backend tests, and authenticated
   browser checks when the local stack is available.
3. Reproduce each case label using synthetic fixtures or authorized runtime
   aggregates, preserving `unavailable` as an explicit result.
4. Fix only evidence-backed failures, then repeat the exact-head protected merge
   gate. Do not self-approve, bypass protection, or claim a PR is merged without
   a merge SHA.

## 6. References (APA 7th)

ContextualWisdomLab. (2026). *TEPP* [Computer software]. GitHub.
https://github.com/ContextualWisdomLab/TEPP

ContextualWisdomLab. (2026). *contextual-orchestrator architecture notes*
[Computer software]. GitHub.
https://github.com/ContextualWisdomLab/contextual-orchestrator/blob/main/docs/architecture.md

Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2025).
*Learning to orchestrate agents in natural language with the Conductor*.
arXiv. https://doi.org/10.48550/arXiv.2512.04388

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H.,
Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., & Kuroki, S.
(2026). *Sakana Fugu technical report*. arXiv.
https://arxiv.org/abs/2606.21228

Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2025).
*TRINITY: An evolved LLM coordinator*. arXiv.
https://doi.org/10.48550/arXiv.2512.04695

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
 (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
