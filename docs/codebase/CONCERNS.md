# Concerns and explicit gaps

- `[IN PROGRESS]` The product now has a bounded HTTPS embedding transport, DOM-text chunk manifest, normalized direct-PostgreSQL vector linkage, idempotent content rematerialization, and actor-filtered inferred retrieval. It deliberately uses finite JSONB vectors and a 24-neighbor in-process cap rather than a new pgvector dependency. A live labeled multilingual query retained its intended document at 0.440; a content read retained all 29 indexed chunks; and a generic 0.25 regression remains suppressed by the bounded 0.40 floor. The current source-hash coverage gate passes; larger labeled calibration and real-Keyverse route acceptance remain required before promotion.
- `[BOUNDARY]` LineageWeave does not duplicate a Rust/GPU psychometrics engine.
  Production report linking must resolve the separate fast-mlsirm HTTP or local
  connector; its installed local path was exercised against real persisted
  report observations through the Rust-backed EAP implementation. There is no
  in-process Python linker: an unavailable, malformed, or diagnostic-only
  connector result remains unavailable and creates no substitute score.
- `[BOUNDARY]` Product Compose starts no identity authority. The retained
  isolated protocol harness is audit material, not Keyverse and not production
  acceptance evidence; the current local browser gate does not start or contact
  an authority. Production HTTPS Keyverse provisioning, real
  business-account/passkey acceptance, and target-Figma browser parity remain
  external release gates.
- `[DONE]` Bounded live image-inspection has CLI wiring: `--sweep-content-inspections` with optional `--inspection-document-limit` can materialize content blocks/assets and run OCR/object inspection on selected documents.
- `[DONE]` Zotero metadata writes are connector operations; bounded OA attachment
  ingestion records its outcome and content digest. The local Connector may
  return no attachment key, so the product does not invent one.
- `[DONE]` Task-aware orchestration now allocates simple calls to one-model
  routing and enrichment, verification, report, and multimodal calls to a
  bounded deep workflow. Portable policy metadata is sent to every gateway;
  top-level route/conduct controls are limited to an explicitly configured
  contextual-orchestrator endpoint. Upstream multimodal message acceptance is
  still an independent review/merge gate.
- `[DONE]` Organization-alias expansion is now evidence-bound at both model
  paths: automatic R&R expansion requires LLM/SearXNG agreement, and the
  administrator verification route requires the cited external text to contain
  the proposed canonical organization. A disagreement remains unresolved and
  cannot create a KG assertion or chronological transition.
- `[DONE]` General users can inspect persisted RAGAS/LLM-Judge report metrics,
  rationale, abstention state, and authorized evidence-document links from the
  React report detail; the data-bearing browser contract renders all four
  current metrics.
- `[IN PROGRESS]` The report item bank now has an evidence-bound live-LLM
  candidate catalog and Rust-backed fast-mlsirm calibration. The current
  PostgreSQL run calibrated ten fixed anchors plus five candidates and leaves
  22 slices explicitly unlinked when item responses are insufficient. Broader
  labeled psychometric validation and human review are still required before
  these linked scores become a business KPI.
- `[BOUNDARY]` Upstream GitHub changes remain separate until their protected-branch
  review and merge gates are satisfied. The current TEPP semantic-unit/image,
  interpretation, temporal, and privacy candidate PRs are still open with
  review required and several cancelled historical checks. The current
  contextual-orchestrator multimodal and agent-pool security PRs have successful
  technical checks but remain review-blocked; release-authorization and admin
  session PRs still have changes requested. LineageWeave therefore consumes
  only the published HTTP contract and does not claim those branches are
  integrated.
- `[BOUNDARY]` A fresh read-only upstream recheck found TEPP main at its
  2026-08-14 persistence merge, fast-mlsirm main after the recent item-bank and
  many-facet merges, and contextual-orchestrator main with no corresponding
  recent merge. Contextual-orchestrator PRs #563 and #566 have passing
  technical checks but still require review; the selected fast-mlsirm PR #864
  has a failing Strix check. No self-approval, retry, bypass, or merge was
  performed. LineageWeave continues to use the separate HTTP/local connector
  boundary and does not copy upstream internals.
- `[DONE]` `scripts/run_real_lineageweave.sh` now performs read-only upstream PR status recheck for ContextualWisdomLab/TEPP and ContextualWisdomLab/contextual-orchestrator on every run and records both counts/state values in the real-run audit events.

These are deliberate boundaries, not hidden fallbacks. Each needs a reproducible fixture, provenance, and acceptance metric before implementation is promoted.

## Evidence

- `.codegraph/`
- `docs/codebase/.codebase-scan.txt`
- `notes/lineageweave_milestone2_run_summary.md`
- `CHANGELOG.md`
- GitHub PR list checks for TEPP and contextual-orchestrator
