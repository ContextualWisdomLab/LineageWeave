"""Temporarily harden the Milestone 2 analysis-run registry test-first."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(source: str, old: str, new: str, label: str) -> str:
    """Replace one deterministic anchor or fail without partial output."""

    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def add_tests() -> None:
    """Add failing contracts before changing the migration."""

    path = Path("tests/test_analysis_run_registry_schema.py")
    text = path.read_text(encoding="utf-8")
    if "test_run_scope_and_request_evidence_are_immutable" in text:
        raise SystemExit("hardening tests already exist")

    function_start = text.index("def _insert_run(")
    function_end = text.index("\n\ndef test_registry_contract", function_start)
    function = text[function_start:function_end]
    function = replace_once(
        function,
        '    run_kind_code: str = "analysis_run_lineage",\n) -> str:',
        '    run_kind_code: str = "analysis_run_lineage",\n'
        '    requested_at: str = "2026-08-15T00:45:00Z",\n'
        ') -> str:',
        "run helper signature",
    )
    function = replace_once(
        function,
        "             configuration_schema_version, configuration_sha256,\n"
        "             code_revision_sha)\n"
        "        values (%s, %s, %s, %s, %s, 'lineage-run-v1', %s, %s)",
        "             configuration_schema_version, configuration_sha256,\n"
        "             code_revision_sha, requested_at)\n"
        "        values (%s, %s, %s, %s, %s, 'lineage-run-v1', %s, %s, %s)",
        "run helper SQL",
    )
    function = replace_once(
        function,
        '            "c" * 40,\n        ),',
        '            "c" * 40,\n            requested_at,\n        ),',
        "run helper parameters",
    )
    text = text[:function_start] + function + text[function_end:]
    text = replace_once(
        text,
        '            knowledge_cutoff="2026-08-16T00:00:00Z",\n        )',
        '            knowledge_cutoff="2026-08-16T00:00:00Z",\n'
        '            requested_at="2026-08-16T00:30:00Z",\n'
        '        )',
        "second cutoff request time",
    )
    text = replace_once(
        text,
        '    assert "reject_analysis_run_update" in migration\n',
        '    assert "reject_analysis_run_mutation" in migration\n'
        '    assert "reject_analysis_run_scope_mutation" in migration\n'
        '    assert "analysis_run_scope_required" in migration\n',
        "static immutability contract",
    )

    insertion_anchor = (
        "\ndef test_rollback_refuses_data_loss_then_removes_an_empty_registry"
    )
    if text.count(insertion_anchor) != 1:
        raise SystemExit("registry test insertion anchor changed")
    new_tests = r'''

def test_run_scope_and_request_evidence_are_immutable(registry_db) -> None:
    """Authorization scope and request identity cannot be rewritten or erased."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="immutable-run",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "update analysis_run_scope set scope_kind_code = scope_kind_code "
                "where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run_scope where analysis_run_id = %s",
                (run_id,),
            )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "delete from analysis_run where analysis_run_id = %s",
                (run_id,),
            )


def test_status_requires_scope_and_cannot_predate_request(registry_db) -> None:
    """Lifecycle evidence starts only after an immutable authorized request."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="scoped-status",
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 1, 'analysis_status_pending', "
                "'2026-08-15T01:00:00Z')",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.RaiseException):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at) "
                "values (%s, 1, 'analysis_status_pending', "
                "'2026-08-15T00:44:59Z')",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at, recorded_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z', '2099-01-01T00:00:00Z') "
            "returning recorded_at",
            (run_id,),
        )
        recorded_at = cursor.fetchone()[0]
    assert recorded_at.year < 2099


def test_machine_codes_and_canonical_idempotency_are_fail_closed(registry_db) -> None:
    """Audit identifiers are canonical and failure details stay machine-safe."""

    with registry_db.cursor() as cursor:
        snapshot_id = _insert_snapshot(cursor)
        account_id = _insert_account(cursor)
        with pytest.raises(psycopg2.errors.RaiseException):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key="future-request",
                requested_at="2099-01-01T00:00:00Z",
            )
        with pytest.raises(psycopg2.errors.CheckViolation):
            _insert_run(
                cursor,
                snapshot_id=snapshot_id,
                account_id=account_id,
                idempotency_key=" padded-key ",
            )
        run_id = _insert_run(
            cursor,
            snapshot_id=snapshot_id,
            account_id=account_id,
            idempotency_key="machine-safe",
        )
        cursor.execute(
            "insert into analysis_run_scope "
            "(analysis_run_id, scope_kind_code) "
            "values (%s, 'analysis_scope_all_visible')",
            (run_id,),
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 1, 'analysis_status_pending', "
            "'2026-08-15T01:00:00Z')",
            (run_id,),
        )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at) "
            "values (%s, 2, 'analysis_status_running', "
            "'2026-08-15T01:00:00Z')",
            (run_id,),
        )
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                "insert into analysis_run_status_event "
                "(analysis_run_id, status_ordinal, status_code, occurred_at, "
                "failure_code, retryable) "
                "values (%s, 3, 'analysis_status_failed', "
                "'2026-08-15T01:00:00Z', 'provider timeout', true)",
                (run_id,),
            )
        cursor.execute(
            "insert into analysis_run_status_event "
            "(analysis_run_id, status_ordinal, status_code, occurred_at, "
            "failure_code, retryable) "
            "values (%s, 3, 'analysis_status_failed', "
            "'2026-08-15T01:00:00Z', 'provider_timeout', true)",
            (run_id,),
        )
'''
    text = text.replace(insertion_anchor, new_tests + insertion_anchor, 1)
    path.write_text(text, encoding="utf-8")


def apply_implementation() -> None:
    """Implement the failing audit, scope, and clock contracts."""

    migration_path = Path("migrations/0018_analysis_run_registry.sql")
    migration = migration_path.read_text(encoding="utf-8")
    migration = replace_once(
        migration,
        "    constraint analysis_run_idempotency_key_check\n"
        "        check (length(btrim(idempotency_key)) between 1 and 256),",
        "    constraint analysis_run_idempotency_key_check\n"
        "        check (\n"
        "            idempotency_key = btrim(idempotency_key)\n"
        "            and length(idempotency_key) between 1 and 256\n"
        "            and idempotency_key !~ '[[:cntrl:]]'\n"
        "        ),",
        "canonical idempotency key",
    )
    migration = replace_once(
        migration,
        "    constraint analysis_run_configuration_version_check\n"
        "        check (length(btrim(configuration_schema_version)) between 1 and 128),",
        "    constraint analysis_run_configuration_version_check\n"
        "        check (\n"
        "            configuration_schema_version = btrim(configuration_schema_version)\n"
        "            and length(configuration_schema_version) between 1 and 128\n"
        "        ),",
        "canonical configuration version",
    )
    if migration.count(
        "references analysis_run (analysis_run_id) on delete cascade,"
    ) != 2:
        raise SystemExit("analysis-run cascading foreign-key anchors changed")
    migration = migration.replace(
        "references analysis_run (analysis_run_id) on delete cascade,",
        "references analysis_run (analysis_run_id),",
        2,
    )
    migration = replace_once(
        migration,
        "                and scope_key is not null\n"
        "                and length(btrim(scope_key)) between 1 and 256)",
        "                and scope_key is not null\n"
        "                and scope_key = btrim(scope_key)\n"
        "                and length(scope_key) between 1 and 256\n"
        "                and scope_key !~ '[[:cntrl:]]')",
        "canonical thread scope key",
    )
    migration = replace_once(
        migration,
        "                and failure_code is not null\n"
        "                and length(btrim(failure_code)) between 1 and 128)",
        "                and failure_code is not null\n"
        "                and failure_code ~ '^[a-z][a-z0-9_]{0,127}$')",
        "machine failure code",
    )
    migration = replace_once(
        migration,
        "begin\n"
        "    select maximum_available_time, captured_at\n",
        "begin\n"
        "    if new.requested_at > clock_timestamp() then\n"
        "        raise exception 'analysis_run_request_time_in_future';\n"
        "    end if;\n\n"
        "    select maximum_available_time, captured_at\n",
        "future request rejection",
    )

    old_run_guard = """create or replace function reject_analysis_run_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_request_is_immutable';
end
$$;

comment on function reject_analysis_run_update() is
    'Rejects mutation of actor, scope root, cutoff, or reproducibility digests; '
    'run progress belongs to append-only status events.';

drop trigger if exists analysis_run_update_reject
    on analysis_run;
create trigger analysis_run_update_reject
before update on analysis_run
for each row execute function reject_analysis_run_update();
"""
    new_run_guard = """drop trigger if exists analysis_run_update_reject
    on analysis_run;
drop trigger if exists analysis_run_mutation_reject
    on analysis_run;
drop function if exists reject_analysis_run_update();

create or replace function reject_analysis_run_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_request_is_immutable';
end
$$;

comment on function reject_analysis_run_mutation() is
    'Rejects update or delete of actor, cutoff, idempotency, and reproducibility '
    'evidence; run progress belongs to append-only status events.';

create trigger analysis_run_mutation_reject
before update or delete on analysis_run
for each row execute function reject_analysis_run_mutation();

create or replace function reject_analysis_run_scope_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_scope_is_immutable';
end
$$;

comment on function reject_analysis_run_scope_mutation() is
    'Rejects update or delete of the authorization-relevant scope attached to '
    'an immutable analysis request.';

drop trigger if exists analysis_run_scope_mutation_reject
    on analysis_run_scope;
create trigger analysis_run_scope_mutation_reject
before update or delete on analysis_run_scope
for each row execute function reject_analysis_run_scope_mutation();
"""
    migration = replace_once(
        migration, old_run_guard, new_run_guard, "run and scope mutation guards"
    )
    migration = replace_once(
        migration,
        "    previous_occurred_at timestamptz;\n"
        "begin\n"
        "    -- The immutable parent row is a per-run serialization lock. It prevents\n"
        "    -- concurrent writers from both accepting the same next ordinal.\n"
        "    perform 1\n"
        "      from analysis_run\n"
        "     where analysis_run_id = new.analysis_run_id\n"
        "     for update;\n\n"
        "    if not found then\n"
        "        raise exception 'analysis_run_not_found';\n"
        "    end if;\n",
        "    previous_occurred_at timestamptz;\n"
        "    run_requested_at timestamptz;\n"
        "begin\n"
        "    -- The immutable parent row is a per-run serialization lock. It prevents\n"
        "    -- concurrent writers from both accepting the same next ordinal.\n"
        "    select requested_at\n"
        "      into run_requested_at\n"
        "      from analysis_run\n"
        "     where analysis_run_id = new.analysis_run_id\n"
        "     for update;\n\n"
        "    if not found then\n"
        "        raise exception 'analysis_run_not_found';\n"
        "    end if;\n"
        "    if not exists (\n"
        "        select 1 from analysis_run_scope\n"
        "         where analysis_run_id = new.analysis_run_id\n"
        "    ) then\n"
        "        raise exception 'analysis_run_scope_required';\n"
        "    end if;\n"
        "    if new.occurred_at < run_requested_at then\n"
        "        raise exception 'analysis_run_status_before_request';\n"
        "    end if;\n"
        "    new.recorded_at := clock_timestamp();\n",
        "scoped lifecycle clock guard",
    )
    migration = replace_once(
        migration,
        "comment on function enforce_analysis_run_status_transition() is\n"
        "    'Serializes status appends and enforces pending-first, contiguous ordinals, '\n"
        "    'monotonic occurrence time, legal transitions, and terminal finality.';",
        "comment on function enforce_analysis_run_status_transition() is\n"
        "    'Serializes status appends and requires immutable scope, request-time '\n"
        "    'ordering, database-recorded time, legal transitions, and terminal finality.';",
        "status transition comment",
    )
    migration = replace_once(
        migration,
        "comment on table analysis_run_scope is\n"
        "    'At most one authorization-relevant product scope for an immutable run; '\n"
        "    'process-unit ownership remains derivable from process_unit.';",
        "comment on table analysis_run_scope is\n"
        "    'One immutable authorization-relevant scope is required before lifecycle '\n"
        "    'evidence; process-unit ownership remains derivable from process_unit.';",
        "scope table comment",
    )
    migration_path.write_text(migration, encoding="utf-8")

    rollback_path = Path("migrations/rollback/0018_analysis_run_registry.sql")
    rollback = rollback_path.read_text(encoding="utf-8")
    rollback = replace_once(
        rollback,
        "drop function if exists reject_analysis_run_update();\n",
        "drop function if exists reject_analysis_run_scope_mutation();\n"
        "drop function if exists reject_analysis_run_mutation();\n"
        "drop function if exists reject_analysis_run_update();\n",
        "rollback mutation functions",
    )
    rollback_path.write_text(rollback, encoding="utf-8")

    adr_path = Path("docs/adr/0013-normalized-analysis-run-registry.md")
    adr = adr_path.read_text(encoding="utf-8")
    adr = replace_once(
        adr,
        "The analysis request row rejects updates. Lifecycle changes are represented only\n"
        "by append-only status events.",
        "The analysis request and its authorization scope reject updates and deletes.\n"
        "Lifecycle changes are represented only by append-only status events, so a cascade\n"
        "cannot erase the derivation root or its access boundary.",
        "ADR immutability",
    )
    adr = replace_once(
        adr,
        "The first event must be `pending`. Failed events require a bounded machine\n"
        "failure code; raw exception text is prohibited. `recorded_at` is database system\n"
        "time and cannot precede `occurred_at`. `analysis_run_current_status` is a view,\n"
        "not a second mutable state authority.",
        "The first event must be `pending`, requires an immutable scope, and cannot predate\n"
        "the run request. Failed events require a lowercase machine-code identifier; raw\n"
        "exception text is prohibited. `recorded_at` is overwritten with database system\n"
        "time on every insert and cannot precede `occurred_at`.\n"
        "`analysis_run_current_status` is a view, not a second mutable state authority.",
        "ADR lifecycle",
    )
    adr = replace_once(
        adr,
        "`analysis_run_scope` stores at most one all-visible, corporate-entity,\n"
        "process-unit, or thread-group scope. Its shape is database constrained. The\n"
        "next repository/API slice must insert run, scope, and first status in one\n",
        "`analysis_run_scope` stores one immutable all-visible, corporate-entity,\n"
        "process-unit, or thread-group scope. Its shape is database constrained and the\n"
        "first lifecycle event is rejected until it exists. The next repository/API slice\n"
        "must insert run, scope, and first status in one\n",
        "ADR authorization scope",
    )
    adr = replace_once(
        adr,
        "Every run references a real `user_account`. `requested_by_account_id` is not\n"
        "nullable. The idempotency key is unique per authenticated account rather than\n",
        "Every run references a real `user_account`. `requested_by_account_id` is not\n"
        "nullable. Idempotency keys are trimmed, control-free canonical values and are\n"
        "unique per authenticated account rather than\n",
        "ADR idempotency",
    )
    adr = replace_once(
        adr,
        "- snapshot, count, and run immutability;\n",
        "- snapshot, count, run, and authorization-scope immutability;\n"
        "- deletion resistance for request and scope audit evidence;\n"
        "- scope-required lifecycle, request-time ordering, and database-owned record time;\n"
        "- canonical idempotency and bounded machine-code failure identifiers;\n",
        "ADR verification",
    )
    adr_path.write_text(adr, encoding="utf-8")

    changelog_path = Path("CHANGELOG.d/milestone2-analysis-run-registry.md")
    changelog = changelog_path.read_text(encoding="utf-8")
    changelog = replace_once(
        changelog,
        "- Added account-scoped idempotency, immutable request configuration, serialized\n"
        "  count/run locking, legal lifecycle transitions, and a derived current-status\n"
        "  view.",
        "- Added canonical account-scoped idempotency, immutable request and scope evidence,\n"
        "  deletion resistance, serialized count/run locking, scope-required request-time-\n"
        "  ordered lifecycle transitions, database-owned record time, and a derived\n"
        "  current-status view.",
        "changelog hardening",
    )
    changelog_path.write_text(changelog, encoding="utf-8")


def main() -> None:
    """Dispatch the requested deterministic repair phase."""

    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("add-tests", "apply"))
    args = parser.parse_args()
    if args.phase == "add-tests":
        add_tests()
    else:
        apply_implementation()


if __name__ == "__main__":
    main()
