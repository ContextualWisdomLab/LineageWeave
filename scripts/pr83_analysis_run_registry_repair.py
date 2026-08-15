#!/usr/bin/env python3
"""Apply the test-first PR #83 temporal provenance repair.

This is a transient branch-only helper. The verified workflow removes it before
creating the product commit, so it cannot become part of the protected product.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent, indent

ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "tests" / "test_analysis_run_registry_schema.py"
MIGRATION_PATH = ROOT / "migrations" / "0018_analysis_run_registry.sql"
ROLLBACK_PATH = ROOT / "migrations" / "rollback" / "0018_analysis_run_registry.sql"
ADR_PATH = ROOT / "docs" / "adr" / "0013-normalized-analysis-run-registry.md"
OLD_CHANGELOG_PATH = ROOT / "CHANGELOG.d" / "0.78.0-analysis-run-registry.md"
NEW_CHANGELOG_PATH = ROOT / "CHANGELOG.d" / "0.79.0-analysis-run-registry.md"


def add_tests() -> None:
    """Add RED regressions and make the database fixture failure-safe."""

    text = TEST_PATH.read_text(encoding="utf-8")
    fixture_start = text.index("@pytest.fixture\ndef registry_db():")
    connection_start = text.index(
        "        connection = psycopg2.connect(_database_dsn(database_name))",
        fixture_start,
    )
    connection_close = text.index("        connection.close()", connection_start)
    connection_end = connection_close + len("        connection.close()")
    connection_block = indent(
        dedent(
            '''\
            connection = psycopg2.connect(_database_dsn(database_name))
            try:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                    cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
                yield connection
            finally:
                connection.close()
            '''
        ).rstrip(),
        "        ",
    )
    text = text[:connection_start] + connection_block + text[connection_end:]

    helper_start = text.index("def _insert_snapshot(cursor) -> str:")
    helper_end = text.index(
        "\n\ndef test_registry_persists_normalized_snapshot_scope_and_status",
        helper_start,
    )
    helper = dedent(
        '''\
        def _insert_snapshot(cursor) -> str:
            """Insert one synthetic immutable snapshot and return its identifier."""
            cursor.execute(
                """
                insert into analysis_source_snapshot
                    (snapshot_sha256, source_contract_version, knowledge_cutoff,
                     maximum_available_time, captured_at)
                values (%s, %s, %s, %s, %s)
                returning analysis_source_snapshot_id
                """,
                (
                    "a" * 64,
                    "source-contract-v1",
                    "2026-08-15T00:00:00Z",
                    "2026-08-14T23:59:00Z",
                    "2026-08-15T01:00:00Z",
                ),
            )
            return str(cursor.fetchone()[0])
        '''
    ).rstrip()
    text = text[:helper_start] + helper + text[helper_end:]

    marker = "def test_registry_persists_normalized_snapshot_scope_and_status(registry_db) -> None:\n"
    if text.count(marker) != 1:
        raise RuntimeError("missing registry persistence test marker")
    regressions = dedent(
        '''\
        def test_snapshot_temporal_boundary_blocks_future_information(registry_db) -> None:
            """Availability, not capture order, is the historical leakage boundary."""
            assert psycopg2 is not None
            with registry_db.cursor() as cursor:
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cursor.execute(
                        """
                        insert into analysis_source_snapshot
                            (snapshot_sha256, source_contract_version, knowledge_cutoff,
                             maximum_available_time, captured_at)
                        values (%s, 'source-contract-v1',
                                '2026-08-15T00:00:00Z',
                                '2026-08-15T00:00:01Z',
                                '2026-08-15T01:00:00Z')
                        """,
                        ("b" * 64,),
                    )
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cursor.execute(
                        """
                        insert into analysis_source_snapshot
                            (snapshot_sha256, source_contract_version, knowledge_cutoff,
                             maximum_available_time, captured_at)
                        values (%s, 'source-contract-v1',
                                '2026-08-15T02:00:00Z',
                                '2026-08-15T01:00:00Z',
                                '2026-08-15T00:59:59Z')
                        """,
                        ("c" * 64,),
                    )
                cursor.execute(
                    """
                    insert into analysis_source_snapshot
                        (snapshot_sha256, source_contract_version, knowledge_cutoff,
                         maximum_available_time, captured_at)
                    values (%s, 'source-contract-v1',
                            '2026-08-15T02:00:00Z',
                            '2026-08-15T00:30:00Z',
                            '2026-08-15T01:00:00Z')
                    returning analysis_source_snapshot_id
                    """,
                    ("d" * 64,),
                )
                assert cursor.fetchone()[0] is not None


        def test_snapshot_counts_freeze_when_a_run_references_them(registry_db) -> None:
            """Immutable evidence cannot be rewritten after or during derivation."""
            assert psycopg2 is not None
            with registry_db.cursor() as cursor:
                snapshot_id = _insert_snapshot(cursor)
                cursor.execute(
                    """
                    insert into analysis_source_count
                        (analysis_source_snapshot_id, count_type_code, count_value)
                    values (%s, 'analysis_count_document', 12)
                    """,
                    (snapshot_id,),
                )
                with pytest.raises(psycopg2.errors.RaiseException):
                    cursor.execute(
                        """
                        update analysis_source_snapshot
                           set source_contract_version = 'rewritten'
                         where analysis_source_snapshot_id = %s
                        """,
                        (snapshot_id,),
                    )
                with pytest.raises(psycopg2.errors.RaiseException):
                    cursor.execute(
                        """
                        update analysis_source_count
                           set count_value = 13
                         where analysis_source_snapshot_id = %s
                        """,
                        (snapshot_id,),
                    )
                cursor.execute(
                    """
                    insert into analysis_run
                        (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                         configuration_schema_version, configuration_sha256,
                         code_revision_sha)
                    values (%s, 'analysis_run_lineage', 'freeze-evidence',
                            'lineage-run-v1', %s, %s)
                    """,
                    (snapshot_id, "e" * 64, "f" * 40),
                )
                with pytest.raises(psycopg2.errors.RaiseException):
                    cursor.execute(
                        """
                        insert into analysis_source_count
                            (analysis_source_snapshot_id, count_type_code, count_value)
                        values (%s, 'analysis_count_thread', 8)
                        """,
                        (snapshot_id,),
                    )
                with pytest.raises(psycopg2.errors.RaiseException):
                    cursor.execute(
                        """
                        delete from analysis_source_count
                         where analysis_source_snapshot_id = %s
                           and count_type_code = 'analysis_count_document'
                        """,
                        (snapshot_id,),
                    )


        def test_status_event_records_system_time_and_rejects_future_occurrence(registry_db) -> None:
            """Status evidence preserves both occurrence and database record time."""
            assert psycopg2 is not None
            with registry_db.cursor() as cursor:
                snapshot_id = _insert_snapshot(cursor)
                cursor.execute(
                    """
                    insert into analysis_run
                        (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                         configuration_schema_version, configuration_sha256,
                         code_revision_sha)
                    values (%s, 'analysis_run_lineage', 'status-clock',
                            'lineage-run-v1', %s, %s)
                    returning analysis_run_id
                    """,
                    (snapshot_id, "1" * 64, "2" * 40),
                )
                run_id = cursor.fetchone()[0]
                with pytest.raises(psycopg2.errors.CheckViolation):
                    cursor.execute(
                        """
                        insert into analysis_run_status_event
                            (analysis_run_id, status_ordinal, status_code, occurred_at)
                        values (%s, 1, 'analysis_status_running', now() + interval '1 hour')
                        """,
                        (run_id,),
                    )
                cursor.execute(
                    """
                    insert into analysis_run_status_event
                        (analysis_run_id, status_ordinal, status_code, occurred_at)
                    values (%s, 1, 'analysis_status_running', now())
                    returning recorded_at
                    """,
                    (run_id,),
                )
                assert cursor.fetchone()[0] is not None


        '''
    )
    TEST_PATH.write_text(text.replace(marker, regressions + marker, 1), encoding="utf-8")


def implement() -> None:
    """Implement the GREEN migration, rollback, ADR, and changelog contracts."""

    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    table_start = migration.index("create table if not exists analysis_source_snapshot (")
    table_end = migration.index("\n\ncomment on table analysis_source_snapshot", table_start)
    snapshot_table = dedent(
        '''\
        create table if not exists analysis_source_snapshot (
            analysis_source_snapshot_id uuid primary key default uuid_generate_v4(),
            snapshot_sha256 text not null unique,
            source_contract_version text not null,
            knowledge_cutoff timestamptz not null,
            maximum_available_time timestamptz not null,
            captured_at timestamptz not null,
            created_at timestamptz not null default now(),
            constraint analysis_source_snapshot_digest_check
                check (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
            constraint analysis_source_snapshot_contract_check
                check (length(btrim(source_contract_version)) between 1 and 128),
            constraint analysis_source_snapshot_leakage_check
                check (maximum_available_time <= knowledge_cutoff),
            constraint analysis_source_snapshot_capture_check
                check (maximum_available_time <= captured_at)
        );
        '''
    ).rstrip()
    migration = migration[:table_start] + snapshot_table + migration[table_end:]

    snapshot_comment = """comment on table analysis_source_snapshot is
    'Immutable identity and temporal eligibility boundary for one source snapshot; no source text or source-table name is stored.';"""
    snapshot_guard = snapshot_comment + "\n\n" + dedent(
        '''\
        create or replace function reject_analysis_source_snapshot_update()
        returns trigger
        language plpgsql
        as $$
        begin
            raise exception 'analysis_source_snapshot_is_immutable';
        end
        $$;

        drop trigger if exists analysis_source_snapshot_update_reject
            on analysis_source_snapshot;
        create trigger analysis_source_snapshot_update_reject
        before update on analysis_source_snapshot
        for each row execute function reject_analysis_source_snapshot_update();
        '''
    ).rstrip()
    if migration.count(snapshot_comment) != 1:
        raise RuntimeError("missing source snapshot comment")
    migration = migration.replace(snapshot_comment, snapshot_guard, 1)

    count_comment = """comment on table analysis_source_count is
    'One normalized aggregate count per snapshot and count vocabulary; values are aggregate acceptance evidence, not source records.';"""
    count_guard = count_comment + "\n\n" + dedent(
        '''\
        create or replace function reject_analysis_source_count_update()
        returns trigger
        language plpgsql
        as $$
        begin
            raise exception 'analysis_source_count_is_immutable';
        end
        $$;

        drop trigger if exists analysis_source_count_update_reject
            on analysis_source_count;
        create trigger analysis_source_count_update_reject
        before update on analysis_source_count
        for each row execute function reject_analysis_source_count_update();
        '''
    ).rstrip()
    if migration.count(count_comment) != 1:
        raise RuntimeError("missing source count comment")
    migration = migration.replace(count_comment, count_guard, 1)

    run_comment = """comment on table analysis_run is
    'One idempotent analysis request bound to a source snapshot and reproducibility digests; current state is derived from status events.';"""
    run_guards = run_comment + "\n\n" + dedent(
        '''\
        create or replace function lock_analysis_source_snapshot_for_run()
        returns trigger
        language plpgsql
        as $$
        begin
            perform 1
              from analysis_source_snapshot
             where analysis_source_snapshot_id = new.analysis_source_snapshot_id
             for update;
            return new;
        end
        $$;

        drop trigger if exists analysis_run_snapshot_lock
            on analysis_run;
        create trigger analysis_run_snapshot_lock
        before insert on analysis_run
        for each row execute function lock_analysis_source_snapshot_for_run();

        create or replace function enforce_analysis_source_count_freeze()
        returns trigger
        language plpgsql
        as $$
        declare
            affected_snapshot_id uuid;
        begin
            if tg_op = 'DELETE' then
                affected_snapshot_id := old.analysis_source_snapshot_id;
            else
                affected_snapshot_id := new.analysis_source_snapshot_id;
            end if;

            perform 1
              from analysis_source_snapshot
             where analysis_source_snapshot_id = affected_snapshot_id
             for update;

            if exists (
                select 1
                  from analysis_run
                 where analysis_source_snapshot_id = affected_snapshot_id
            ) then
                raise exception 'analysis_source_count_frozen_after_run';
            end if;

            if tg_op = 'DELETE' then
                return old;
            end if;
            return new;
        end
        $$;

        drop trigger if exists analysis_source_count_freeze_guard
            on analysis_source_count;
        create trigger analysis_source_count_freeze_guard
        before insert or delete on analysis_source_count
        for each row execute function enforce_analysis_source_count_freeze();
        '''
    ).rstrip()
    if migration.count(run_comment) != 1:
        raise RuntimeError("missing analysis run comment")
    migration = migration.replace(run_comment, run_guards, 1)

    status_start = migration.index("create table if not exists analysis_run_status_event (")
    status_end = migration.index(
        "\n\ncreate index if not exists analysis_run_status_current_idx", status_start
    )
    status_table = dedent(
        '''\
        create table if not exists analysis_run_status_event (
            analysis_run_id uuid not null
                references analysis_run (analysis_run_id)
                on delete cascade,
            status_ordinal integer not null,
            status_code text not null
                references common_lookup_value (lookup_code),
            occurred_at timestamptz not null,
            recorded_at timestamptz not null default now(),
            failure_code text,
            retryable boolean not null default false,
            primary key (analysis_run_id, status_ordinal),
            constraint analysis_run_status_code_check
                check (status_code in (
                    'analysis_status_pending',
                    'analysis_status_running',
                    'analysis_status_succeeded',
                    'analysis_status_failed',
                    'analysis_status_cancelled'
                )),
            constraint analysis_run_status_ordinal_check
                check (status_ordinal >= 1),
            constraint analysis_run_status_recorded_check
                check (occurred_at <= recorded_at),
            constraint analysis_run_status_failure_shape_check
                check (
                    (status_code = 'analysis_status_failed'
                        and failure_code is not null
                        and length(btrim(failure_code)) between 1 and 128)
                    or
                    (status_code <> 'analysis_status_failed'
                        and failure_code is null
                        and retryable = false)
                )
        );
        '''
    ).rstrip()
    migration = migration[:status_start] + status_table + migration[status_end:]
    status_view_anchor = "       status_event.occurred_at,\n       status_event.failure_code,"
    if migration.count(status_view_anchor) != 1:
        raise RuntimeError("missing status projection clock anchor")
    migration = migration.replace(
        status_view_anchor,
        "       status_event.occurred_at,\n       status_event.recorded_at,\n       status_event.failure_code,",
        1,
    )
    MIGRATION_PATH.write_text(migration, encoding="utf-8")

    rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
    anchor = "drop function if exists reject_analysis_run_status_mutation();"
    functions = dedent(
        '''\
        drop function if exists reject_analysis_run_status_mutation();
        drop function if exists enforce_analysis_source_count_freeze();
        drop function if exists lock_analysis_source_snapshot_for_run();
        drop function if exists reject_analysis_source_count_update();
        drop function if exists reject_analysis_source_snapshot_update();
        '''
    ).rstrip()
    if rollback.count(anchor) != 1:
        raise RuntimeError("missing rollback function anchor")
    ROLLBACK_PATH.write_text(rollback.replace(anchor, functions, 1), encoding="utf-8")

    adr = ADR_PATH.read_text(encoding="utf-8")
    adr = adr.replace(
        "        timestamptz knowledge_cutoff\n        timestamptz captured_at",
        "        timestamptz knowledge_cutoff\n        timestamptz maximum_available_time\n        timestamptz captured_at",
        1,
    )
    adr = adr.replace(
        "        timestamptz occurred_at\n        text failure_code",
        "        timestamptz occurred_at\n        timestamptz recorded_at\n        text failure_code",
        1,
    )
    replacements = {
        "1. `analysis_source_snapshot` identifies one immutable source snapshot by SHA-256 and separates `knowledge_cutoff` from later capture time. The constraint `knowledge_cutoff <= captured_at` prevents a snapshot from claiming evidence was captured before the analysis was allowed to know it.":
            "1. `analysis_source_snapshot` identifies one immutable source snapshot by SHA-256 and separates `maximum_available_time`, `knowledge_cutoff`, and capture time. `maximum_available_time <= knowledge_cutoff` prevents future-information leakage, while `maximum_available_time <= captured_at` proves that every admitted fact could have existed in the captured snapshot. Capture may legitimately precede a later analysis cutoff.",
        "2. `analysis_source_count` stores one non-negative aggregate per count vocabulary. Counts are not repeated in a run row or metadata JSON.":
            "2. `analysis_source_count` stores one non-negative aggregate per count vocabulary. Snapshot rows and existing counts reject updates, and the complete count set freezes under a shared snapshot-row lock when the first `analysis_run` references the snapshot. Counts are not repeated in a run row or metadata JSON.",
        "5. `analysis_run_status_event` is append-only. Bounded machine failure codes may be stored; raw exceptions and provider/source payloads may not.":
            "5. `analysis_run_status_event` is append-only and records both event occurrence time and database system time. Bounded machine failure codes may be stored; raw exceptions and provider/source payloads may not.",
        "- Real PostgreSQL tests apply the current product schema plus migration 0018, replay the migration, exercise valid snapshot/run/scope/status writes, and reject malformed digests, negative counts, duplicate idempotency, incoherent scopes, incomplete failure events, and status mutation.":
            "- Real PostgreSQL tests apply the current product schema plus migration 0018, replay the migration, exercise valid snapshot/run/scope/status writes, and reject future-information leakage, post-derivation snapshot/count mutation, future-dated status events, malformed digests, negative counts, duplicate idempotency, incoherent scopes, incomplete failure events, and status mutation.",
    }
    for old, new in replacements.items():
        if adr.count(old) != 1:
            raise RuntimeError(f"missing ADR replacement anchor: {old[:48]}")
        adr = adr.replace(old, new, 1)
    ADR_PATH.write_text(adr, encoding="utf-8")

    changelog = OLD_CHANGELOG_PATH.read_text(encoding="utf-8")
    changelog = changelog.replace(
        "# 0.78.0 — Normalized analysis-run registry",
        "# 0.79.0 — Normalized analysis-run registry",
        1,
    )
    old_bullet = (
        "- Adds database constraints for hash shape, temporal cutoff, supported lookup\n"
        "  codes, non-negative counts, mutually exclusive scopes, bounded failure codes,\n"
        "  and status immutability.\n"
    )
    new_bullet = (
        "- Adds database constraints for hash shape, evidence availability at the\n"
        "  knowledge cutoff, capture eligibility, supported lookup codes, non-negative\n"
        "  counts, mutually exclusive scopes, bounded failure codes, occurrence/system\n"
        "  clocks, snapshot/count immutability, and race-safe count-set freezing.\n"
    )
    if changelog.count(old_bullet) != 1:
        raise RuntimeError("missing changelog temporal-contract bullet")
    NEW_CHANGELOG_PATH.write_text(changelog.replace(old_bullet, new_bullet, 1), encoding="utf-8")
    OLD_CHANGELOG_PATH.unlink()


def main() -> int:
    """Dispatch the requested test or implementation phase."""

    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("tests", "implementation"))
    args = parser.parse_args()
    if args.phase == "tests":
        add_tests()
    else:
        implement()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
