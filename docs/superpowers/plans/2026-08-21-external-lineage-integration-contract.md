# External Lineage Integration Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a strict, store-agnostic LineageWeave contract that accepts bounded caller-authorized evidence and returns opaque-reference lineage and project projections for Naruon and other consumers.

**Architecture:** Keep the existing reconstruction kernel authoritative for candidate scoring and RankWeave fusion. Add a pure contract/parser layer plus a pure execution adapter that performs available-time cutoff filtering, work-budget checks, explicit-vs-inferred relation separation, channel-evidence projection, and canonical digests without database or provider access. Caller-observed children bypass alternative inference and optional model disclosure while remaining available as candidate history for later records.

**Tech Stack:** Python 3.12+, dataclasses, JSON Schema Draft 2020-12, pytest, coverage.py, Ruff, RankWeave, ThreadWeave.

**Spec:** `docs/adr/0214-external-email-project-lineage-contract.md`

## Global Constraints

- Inputs contain only caller-authorized bounded evidence and opaque references.
- `available_at <= knowledge_cutoff` is the historical-evidence admission rule.
- Missing optional LLM evidence is unavailable, never a fabricated zero.
- Observed RFC/thread relations remain distinct from inferred semantic lineage.
- Children with an explicit observed parent consume no inferred-pair budget and are not sent to the optional LLM for an alternative edge.
- Project projections remain proposed and cannot mutate caller or provider state.
- No direct application-database access, provider credential, persistence, or network call is added to the pure execution adapter.
- Changed production statement and branch coverage must be 100%; public symbols require docstrings.

---

### Task 1: Strict contract and canonical serialization

**Files:**
- Create: `lineageweave/external_lineage_contract.py`
- Create: `docs/contracts/external-lineage-analysis-v1.schema.json`
- Test: `tests/test_external_lineage_contract.py`

**Interfaces:**
- Produces: `parse_lineage_analysis_request(payload) -> LineageAnalysisRequest`
- Produces: `serialize_lineage_analysis_request(request) -> dict[str, object]`
- Produces: `serialize_lineage_analysis_result(result) -> dict[str, object]`
- Produces: `request_digest(request) -> str` and `result_digest(result) -> str`

- [ ] Write failing parser tests for unknown fields, invalid vocabularies, duplicate opaque references, offset-naive timestamps, payload bounds, unsafe references, and policy bounds.
- [ ] Run `uv run --locked --extra dev pytest -q tests/test_external_lineage_contract.py` and confirm the tests fail because the contract does not exist.
- [ ] Implement immutable dataclasses, stable errors, strict parsing, canonical UTC serialization, digest calculation, and result-integrity checks.
- [ ] Add the Draft 2020-12 schema and a drift test comparing its fixed vocabularies and bounds with the parser.
- [ ] Re-run the focused contract tests until they pass.

### Task 2: Evidence-bounded execution adapter

**Files:**
- Create: `lineageweave/external_lineage_analysis.py`
- Test: `tests/test_external_lineage_analysis.py`
- Test: `tests/test_external_lineage_explicit_parent_budget.py`

**Interfaces:**
- Consumes: `LineageAnalysisRequest` and the existing candidate-scoring/fusion kernel.
- Produces: `analyze_external_lineage(request, *, llm=None) -> LineageAnalysisResult`.

- [ ] Write failing tests for available-time cutoff exclusion, pair-budget rejection before channel execution, explicit observed parent precedence, explicit-parent validation, optional LLM status, project projection, deterministic output, and content-minimized evidence.
- [ ] Add a failing regression proving caller-observed children neither consume inferred-pair budget nor disclose alternative label pairs to an optional LLM.
- [ ] Run the focused execution tests and confirm the missing or defective adapter is the failure cause.
- [ ] Implement request revalidation, explicit-parent acyclicity/group/time checks, cutoff filtering, inference-only pair-budget calculation, core-record adaptation, channel projection, limitations, and result digesting.
- [ ] Preserve an explicit child in candidate history so later unobserved records may still select it as an inferred parent.
- [ ] Re-run the focused execution tests until they pass.

### Task 3: Public package, decision records, and quality gate

**Files:**
- Modify: `lineageweave/__init__.py`
- Create: `docs/adr/0214-external-email-project-lineage-contract.md`
- Create: `docs/doctoring/EXTERNAL_LINEAGE_CONTRACT_REFERENCES.md`
- Create: `CHANGELOG.d/external-lineage-contract.md`

**Interfaces:**
- Produces: a supported package API for consumer contract tests.

- [ ] Export the contract types, parser/serializer/digest functions, error type, and `analyze_external_lineage` from `lineageweave`.
- [ ] Record the LineageWeave/Naruon authority split, truth statuses, cutoff semantics, model-disclosure minimization, and packaging boundary in the ADR.
- [ ] Record APA 7th sources and one consolidated changelog fragment.
- [ ] Run `uvx ruff check` on changed Python and test files.
- [ ] Run focused statement/branch coverage with `--fail-under=100` for both new production modules.
- [ ] Run documentation hygiene, schema JSON parsing, Python compileall, and `git diff --check`.
- [ ] Open a Draft PR linked to LineageWeave #338; keep Naruon runtime integration out of this slice.
