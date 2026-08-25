# Naruon Email and Project Lineage Contract Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task by task. Follow TDD and verify exact-head evidence before publication.

**Goal:** Publish a strict, store-agnostic LineageWeave package contract that Naruon can later consume for evidence-bounded email lineage and project-history candidates.

**Architecture:** `external_lineage_contract.py` owns immutable request/result models, strict parsing, canonical serialization, bounded vocabularies, and deterministic SHA-256 digests. `external_lineage_analysis.py` adapts authorized records to the current reconstruction kernel, enforces `available_at <= knowledge_cutoff`, validates caller-observed parent relations, rejects excess pair work before optional provider activity, and projects inferred channel evidence plus proposed project groupings.

**Tech stack:** Python 3.12+, standard-library dataclasses/JSON/datetime/hashlib, existing LineageWeave reconstruction kernel, pytest, coverage.py, JSON Schema Draft 2020-12.

## Global constraints

- Contract version: `1.0.0`.
- Request records: 1–500.
- Candidate window: 1–200.
- Candidate-pair budget: 1–5,000 and enforced before optional LLM calls.
- Identifiers are opaque bounded references; provider credentials and direct database access are forbidden.
- Timestamps are offset-aware RFC 3339 and serialize in UTC with `Z`.
- Caller parent relations remain `observed`, are same-group and acyclic; reconstructed edges remain `inferred`.
- Missing LLM evidence is unavailable, never zero.
- Project projections remain `proposed`.
- New production statement/branch coverage and public docstrings: 100%.

## Task 1 — Strict contract

**Files:**
- `lineageweave/external_lineage_contract.py`
- `tests/test_external_lineage_contract.py`

- [x] Write failing tests for strict object parsing, unknown fields, duplicate references, bounded identifiers/text, offset-aware timestamps, policy bounds, canonical serialization, deterministic digests, result partitions, channel math, and package exports.
- [x] Confirm RED before implementation.
- [x] Implement frozen dataclasses, `LineageContractError`, parser, request/result serializers, and digest functions.
- [x] Confirm focused tests GREEN.

## Task 2 — Reconstruction adapter

**Files:**
- `lineageweave/external_lineage_analysis.py`
- `tests/test_external_lineage_analysis.py`

- [x] Write failing tests for cutoff filtering, explicit RFC parent precedence, cycle/missing/forward-parent rejection, pair-budget pre-call enforcement, LLM status, per-channel evidence, project grouping, and deterministic results.
- [x] Confirm RED before implementation.
- [x] Implement request round-trip validation, available-time partitioning, explicit-parent validation, exact candidate-pair budgeting, core-kernel adaptation, observed/inferred edge projection, limitations, and project projections.
- [x] Confirm focused tests GREEN.

## Task 3 — Public schema and architecture evidence

**Files:**
- `docs/contracts/external-lineage-analysis-v1.schema.json`
- `docs/adr/0214-external-email-project-lineage-contract.md`
- `docs/doctoring/EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md`
- `CHANGELOG.d/external-lineage-contract.md`
- `lineageweave/__init__.py`

- [x] Add JSON Schema Draft 2020-12 mirroring parser names, bounds, and vocabularies.
- [x] Add ADR 0214 and APA 7th references for RFC 3339, RFC 5322, RFC 5256, PROV-O, and OWL-Time.
- [x] Export the contract and adapter from the package root.
- [x] Add changelog evidence.

## Task 4 — Exact-head verification and Draft PR

- [x] Focused suite: `57 passed`.
- [x] Isolated new-module coverage: 425/425 statements and 140/140 branches, 100%.
- [x] Public function/class/module docstrings: complete.
- [x] `compileall`, JSON syntax, line-length, and `git diff --check`: passed.
- [ ] Publish the branch from exact protected `main@2feba74b75863810869cde680b19032a93fba413`.
- [ ] Open one Draft PR tracking LineageWeave #338.
- [ ] Keep Draft until exact-head hosted CI/security/documentation gates, review-thread resolution, and independent approval pass.
