# Naruon Calendar Projection Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each task with test-first verification.

**Goal:** Publish a strict read-only LineageWeave consumer contract for calendar observations authorized and projected by Naruon, without making LineageWeave a CalDAV/provider authority.

**Architecture:** Keep commitments and issue/todo records authoritative in LineageWeave. Consume Naruon event occurrences through one bounded service-to-service HTTP contract, reject schema or policy drift fail-closed, and leave provider synchronization, revisions, credentials, writeback, retry, and reconciliation in Naruon.

**Tech Stack:** Python 3.12+, dataclasses, JSON Schema Draft 2020-12, RFC 3339, pytest, coverage.py, shared bounded HTTP client.

**Spec:** `docs/adr/0183-naruon-calendar-projection-boundary.md`

## Global Constraints

- No provider or end-user credential enters this contract.
- External occurrences are `observed`; LineageWeave commitments remain a separate authority.
- Windows are at most 366 days, pages at most 200 events, and response bodies at most 1 MiB.
- Unknown versions, fields, vocabularies, URL-shaped references, duplicate occurrences, and invalid clocks fail closed.
- Runtime wiring remains disabled until Naruon publishes an immutable provider contract and audience.
- Changed production statement/branch coverage and public docstrings must reach 100%.

---

### Task 1: Write strict parser and transport RED tests

**Files:**
- Create: `tests/test_naruon_calendar_projection.py`
- Create: `tests/test_naruon_calendar_projection_edges.py`
- Modify: `tests/test_http_client.py`
- Modify: `tests/test_http_client_edges.py`

**Interfaces:**
- Produces expected public API: `parse_naruon_calendar_page` and `NaruonCalendarProjectionClient`.

- [ ] Add failing tests for strict fields, timestamps, closed vocabularies, duplicate occurrence identity, cursor/base URL safety, service-token whitespace, numeric bounds, response-byte bounds, and public exports.
- [ ] Run the focused tests and confirm failure is caused by the missing contract and byte-bound transport.

### Task 2: Implement bounded package contract

**Files:**
- Create: `lineageweave/naruon_calendar_projection.py`
- Modify: `lineageweave/http_client.py`
- Modify: `lineageweave/__init__.py`

**Interfaces:**
- Produces: `parse_naruon_calendar_page(payload, *, maximum_events=200) -> NaruonCalendarPage`.
- Produces: `NaruonCalendarProjectionClient.list_events(...) -> NaruonCalendarPage`.
- Extends: `get_json(..., maximum_response_bytes=None)`.

- [ ] Implement immutable occurrence/page models and exact parser validation.
- [ ] Implement service-credential transport with 366-day, 200-row, 1 MiB, and 30-second ceilings.
- [ ] Reject whitespace/control-bearing tokens and ambiguous numeric values.
- [ ] Export the supported package surface.
- [ ] Run focused tests until green, then run branch coverage at 100%.

### Task 3: Record truth, standards, and activation boundary

**Files:**
- Modify: `docs/adr/0038-calendar-source-contract.md`
- Create: `docs/adr/0183-naruon-calendar-projection-boundary.md`
- Create: `docs/contracts/naruon-calendar-projection-v1.schema.json`
- Create: `docs/doctoring/NARUON_CALENDAR_PROJECTION_REFERENCES.md`
- Create: `CHANGELOG.d/naruon-calendar-projection-contract.md`

**Interfaces:**
- Produces one immutable provider/consumer schema for Naruon conformance fixtures.

- [ ] Correct the pseudo-CalDAV product claim while preserving events-versus-commitments separation.
- [ ] Record the Naruon/LineageWeave authority and runtime activation gate.
- [ ] Add RFC 4791, RFC 5545, RFC 6578, PROV-O, and bounded-resource traceability.
- [ ] Validate JSON syntax, ADR uniqueness, documentation hygiene, compileall, Ruff, and diff hygiene.
- [ ] Open a clean PR from current protected `main`, supersede the inherited stacked PR, and keep runtime integration disabled.
