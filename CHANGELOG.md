# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Ask Agent citations can now open a focused evidence layer that preserves the
  current answer while exposing persisted text and image evidence, with
  Storybook coverage for populated, empty, missing-OCR, null-caption, and
  blank-caption states.

### Fixed

- The Ask citation evidence layer now contains forward and reverse keyboard
  focus while marked modal, gives its modal evidence lists citation-specific
  accessible names, and falls back to `Untitled image` for blank captions.
- `make smoke` and `make seed` now run through the locked project `uv`
  environment, so local OIDC and synthetic-data workflows resolve the same
  pinned dependencies as CI.

## [2.12.6] - 2026-08-20

### Added

- Production OIDC can now use a real Keyverse issuer through
  `KEYVERSE_ISSUER` and `KEYVERSE_CLIENT_ID`. The backend discovers the
  provider's JWKS and verifies the issuer; Compose keeps local Keycloak only
  as an explicit development fallback and does not emulate Keyverse.
- Relation verification now preserves a separately authorized internal source
  post containing normalized organization and relationship context. Open that
  evidence from the counterparty popup without treating it as an external URL.
- Large corpora now use bounded post and Event Lineage landing projections so
  buyers can open complete post-specific detail from a responsive first view.

## [2.12.5] - 2026-08-18

### Fixed

- Migrations 0019 and 0025 (R&R role-catalog identity backfills) both
  used `min(uuid_column)` to pick "the" value from a `having count(*)
  = 1` group -- Postgres has no built-in `min(uuid)` aggregate, so
  both failed outright the first time either was actually run against
  a real, non-trivial dataset. Fixed to
  `min(uuid_column::text)::uuid`, safe given the query's own
  `having count(*) = 1` already guarantees exactly one value per
  group. Applying the full migration set 0001-0029 against a real,
  long-lived dataset also surfaced that this database's original
  bootstrap had left several *earlier* migrations (0001, 0016)
  partially applied -- specific tables/indexes/backfills their own
  later statements defined were missing even though their initial
  `create table` statements had run. All 29 migrations are now
  confirmed genuinely, fully applied end to end against a real
  43,814-post dataset; every table/index any migration defines is now
  present, verified via direct schema comparison, not assumption.

### Known issue (not fixed here, flagged for follow-up)

- `backend/tests/test_api.py::test_start_analysis_run_recovers_the_a100_fork`
  and `::test_tepp_start_persists_published_accepted_evidence`
  deterministically fail against a real live PostgreSQL/Keycloak/Valkey
  stack (this whole test module is `skipif`-guarded and never runs in
  CI) with `CheckViolationError` on `analysis_run_status_time_check`
  (`occurred_at <= recorded_at`): the row's `occurred_at`
  (`datetime.now(timezone.utc)`, captured in `backend/app/analysis_run_start.py`)
  reproducibly lands ~15-20ms *after* `recorded_at`
  (`clock_timestamp()`, evaluated later, at actual insert time, inside
  a `before insert` trigger) -- the wrong direction, given
  `recorded_at` is evaluated strictly after `occurred_at` is captured
  in every code path. Confirmed via a direct clock-sync measurement
  (5 samples, Python vs. Postgres `clock_timestamp()` interleaved)
  that there is no measurable systemic clock drift between the test
  process and this Postgres instance under normal conditions, and
  confirmed the failure is 100% reproducible in isolation (not a
  concurrency/load artifact) and entirely pre-existing (verified via
  `git diff` that no file in this change touches
  `analysis_run_start.py` or the 0018 migration that defines this
  constraint). Root cause not yet conclusively identified; deferred
  as out of scope for this migration-catchup change (a different
  feature area -- analysis-run/TEPP lifecycle, not R&R/summary/
  verification) rather than rushed. 553 other tests unaffected (some
  tests skipped by design in CI).
